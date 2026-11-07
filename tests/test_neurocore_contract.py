"""NeuroCore consumption contract: the documented Python API and MCP surface stay callable."""

from __future__ import annotations

import json
import unittest

from adapters.lattice.database import open_database
from adapters.lattice.extraction import extract_from_paper
from adapters.lattice.repository import Repository
from adapters.lattice.synthesis import synthesize
from studio import api
from studio.mcp import handle_message


class NeuroCoreApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.connection = open_database(":memory:")
        self.addCleanup(self.connection.close)
        self.repo = Repository(self.connection)
        self.question = self.repo.add_question("Does sleep consolidate memory?")
        self.paper, _ = self.repo.add_paper(
            {
                "title": "Sleep and Memory Consolidation Trial",
                "study_type": "Randomized Controlled Trial",
            }
        )
        self.claim = self.repo.add_claim(
            self.paper.id,
            "Sleep improves memory recall.",
            "Sleep improved memory recall by 28%.",
            stance="supports",
            locator="abstract:s1",
        )
        self.repo.add_edge(self.claim.id, self.question.id, kind="supports")

    def test_documented_facade_symbols_exist_and_are_originals(self) -> None:
        for name in (
            "Repository",
            "Paper",
            "Claim",
            "Question",
            "ContextPack",
            "build_context_pack",
            "get_evidence_matrix",
            "get_hypothesis_evidence",
            "synthesize_question",
            "extract_claims_for_paper",
            "LatticeClient",
            "open_database",
        ):
            self.assertTrue(hasattr(api, name), name)
        self.assertIs(api.synthesize_question, synthesize)
        self.assertIs(api.extract_claims_for_paper, extract_from_paper)

    def test_evidence_bundle_and_matrix_are_json_ready(self) -> None:
        bundle = api.get_hypothesis_evidence(self.repo, self.question.id)
        self.assertEqual(bundle["question"]["id"], self.question.id)
        self.assertGreaterEqual(bundle["evidence_count"], 1)
        matrix = api.get_evidence_matrix(self.repo, [self.question.id])
        self.assertEqual([item["id"] for item in matrix["questions"]], [self.question.id])
        self.assertTrue(matrix["papers"])

    def test_context_pack_and_synthesis_are_callable(self) -> None:
        pack = api.build_context_pack(self.repo, [self.question.id], max_tokens=800)
        payload = pack.to_dict()
        self.assertEqual(payload["format"], "markdown")
        self.assertIn("questions", payload["data"])
        report = api.synthesize_question(self.repo, f"question:{self.question.id}", tokens=400)
        self.assertEqual(report.target, self.question.id)
        self.assertIn("consensus", report.to_dict())
        self.assertTrue(report.markdown)


class NeuroCoreMcpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.connection = open_database(":memory:")
        self.addCleanup(self.connection.close)
        self.repo = Repository(self.connection)

    def call(self, method: str, params: dict | None = None, request_id: int = 1):
        return handle_message(
            self.repo,
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": params or {},
            },
        )

    def tool(self, name: str, arguments: dict) -> dict:
        response = self.call("tools/call", {"name": name, "arguments": arguments})
        return json.loads(response["result"]["content"][0]["text"])

    def test_initialize_tools_resources_and_prompts(self) -> None:
        initialized = self.call("initialize")["result"]
        self.assertEqual(initialized["serverInfo"]["name"], "lattice")
        self.assertIn("protocolVersion", initialized)
        names = {tool["name"] for tool in self.call("tools/list")["result"]["tools"]}
        required = {
            "discover_papers",
            "add_paper",
            "extract_claims",
            "search",
            "get_entity",
            "neighbors",
            "subgraph",
            "related_findings",
            "outline",
            "add_claim",
            "add_question",
            "set_question_status",
            "add_edge",
            "brief",
            "review",
            "synthesize",
            "analyze_graph",
            "detect_contradictions",
            "export_snapshot",
            "import_snapshot",
            "stats",
        }
        self.assertTrue(required <= names, sorted(required - names))
        resources = {item["uri"] for item in self.call("resources/list")["result"]["resources"]}
        self.assertEqual(resources, {"lattice://stats", "lattice://questions", "lattice://matrix"})
        prompts = {item["name"] for item in self.call("prompts/list")["result"]["prompts"]}
        self.assertEqual(prompts, {"literature-synthesis"})

    def test_graph_write_read_and_synthesis_tools(self) -> None:
        question = self.tool("add_question", {"text": "Does sleep consolidate memory?"})["question"]
        paper = self.tool("add_paper", {"title": "Sleep Trial", "authors": "A"})["paper"]
        claim = self.tool(
            "add_claim",
            {
                "paper": paper["id"],
                "text": "Sleep improves recall.",
                "quote": "Sleep improved recall by 28%.",
                "stance": "supports",
                "locator": "abstract:s1",
            },
        )["claim"]
        self.tool(
            "add_edge",
            {
                "src": f"claim:{claim['id']}",
                "dst": f"question:{question['id']}",
                "kind": "supports",
            },
        )
        outline = self.tool("outline", {})
        self.assertEqual(outline["counts"]["questions"], 1)
        brief = self.tool("brief", {"target": f"question:{question['id']}"})
        self.assertTrue(brief)
        synthesis = self.tool("synthesize", {"target": f"question:{question['id']}", "tokens": 400})
        self.assertIn("consensus", synthesis)
        stats = self.call("resources/read", {"uri": "lattice://stats"})["result"]["contents"][0]
        stats_payload = json.loads(stats["text"])
        self.assertEqual(stats_payload["questions"], 1)
        prompt = self.call(
            "prompts/get",
            {"name": "literature-synthesis", "arguments": {"target": f"question:{question['id']}"}},
        )["result"]
        self.assertTrue(prompt["messages"])
