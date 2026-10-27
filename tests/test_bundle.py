"""JSONL export is complete, scoped and deterministic in order."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from engine.bundle import (
    content_sha256,
    export_jsonl,
    export_records,
    graph_sha256,
    verify_export,
)
from engine.claims import add_claim
from engine.researches import create_research
from engine.errors import EngineError
from tests.support import DatabaseCase


class BundleTests(DatabaseCase):
    def setUp(self) -> None:
        super().setUp()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "bundle.jsonl"

    def test_export_writes_meta_first_and_every_record(self) -> None:
        research = self.add_research()
        add_claim(self.conn, research, "A claim.", "assumption", basis="a")
        counts = export_jsonl(self.conn, self.path)
        lines = [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(lines[0]["type"], "meta")
        types = [line["type"] for line in lines]
        self.assertIn("research", types)
        self.assertIn("claim", types)
        self.assertEqual(counts["claim"], 1)

    def test_scoped_export_excludes_other_programs(self) -> None:
        first = create_research(self.conn, "First")
        second = create_research(self.conn, "Second")
        add_claim(self.conn, first.id, "First claim.", "assumption", basis="a")
        add_claim(self.conn, second.id, "Second claim.", "assumption", basis="b")
        export_jsonl(self.conn, self.path, first.slug)
        text = self.path.read_text(encoding="utf-8")
        self.assertIn("First claim.", text)
        self.assertNotIn("Second claim.", text)

    def test_export_replaces_the_file_atomically(self) -> None:
        self.path.write_text("stale", encoding="utf-8")
        export_jsonl(self.conn, self.path)
        self.assertNotEqual(self.path.read_text(encoding="utf-8"), "stale")


    def test_export_includes_observations_and_events(self) -> None:
        from engine.claims import add_claim
        from engine.events import record
        from engine.observations import add_observation

        research = self.add_research()
        claim = add_claim(self.conn, research, "A.", "assumption", basis="a")
        add_observation(self.conn, claim.id, "baseline", 1.5)
        record(self.conn, "test.event", claim.id, "detail", research_id=research)
        export_jsonl(self.conn, self.path, research)
        types = {json.loads(line)["type"] for line in self.path.read_text(encoding="utf-8").splitlines()}
        self.assertIn("observation", types)
        self.assertIn("event", types)

    def test_observation_changes_the_digests(self) -> None:
        from engine.claims import add_claim
        from engine.observations import add_observation

        research = self.add_research()
        claim = add_claim(self.conn, research, "A.", "assumption", basis="a")
        before = (graph_sha256(self.conn, research), content_sha256(self.conn, research))
        add_observation(self.conn, claim.id, "baseline", 1.5)
        after = (graph_sha256(self.conn, research), content_sha256(self.conn, research))
        self.assertNotEqual(before[0], after[0])
        self.assertNotEqual(before[1], after[1])

    def test_generation_events_do_not_change_the_digests(self) -> None:
        from engine.claims import add_claim
        from engine.events import record

        research = self.add_research()
        claim = add_claim(self.conn, research, "A.", "assumption", basis="a")
        before = (graph_sha256(self.conn, research), content_sha256(self.conn, research))
        record(self.conn, "report.write", claim.id, "generated", research_id=research)
        after = (graph_sha256(self.conn, research), content_sha256(self.conn, research))
        self.assertEqual(before, after)


    def test_export_verifies_its_own_digest(self) -> None:
        self.add_research()
        export_jsonl(self.conn, self.path)
        result = verify_export(self.path)
        self.assertTrue(result["ok"], result)
        self.assertTrue(result["counts_match"])
        self.assertEqual(result["records"], 1)

    def test_a_tampered_record_is_detected(self) -> None:
        self.add_research()
        export_jsonl(self.conn, self.path)
        lines = self.path.read_text(encoding="utf-8").splitlines()
        lines[1] = lines[1].replace("Test research", "Altered research")
        self.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        result = verify_export(self.path)
        self.assertFalse(result["ok"])

    def test_a_legacy_export_without_a_digest_is_refused(self) -> None:
        self.add_research()
        export_jsonl(self.conn, self.path)
        lines = self.path.read_text(encoding="utf-8").splitlines()
        meta = json.loads(lines[0])
        meta.pop("export_digest")
        lines[0] = json.dumps(meta, sort_keys=True)
        self.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        with self.assertRaises(EngineError):
            verify_export(self.path)

    def test_a_count_mismatch_is_reported(self) -> None:
        self.add_research()
        export_jsonl(self.conn, self.path)
        lines = self.path.read_text(encoding="utf-8").splitlines()
        meta = json.loads(lines[0])
        meta["records"] = 999
        lines[0] = json.dumps(meta, sort_keys=True)
        self.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        result = verify_export(self.path)
        self.assertTrue(result["ok"])
        self.assertFalse(result["counts_match"])


    def test_an_unsupported_schema_is_reported_not_trusted(self) -> None:
        self.add_research()
        export_jsonl(self.conn, self.path)
        lines = self.path.read_text(encoding="utf-8").splitlines()
        meta = json.loads(lines[0])
        meta["schema"] = 99
        lines[0] = json.dumps(meta, sort_keys=True)
        self.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        result = verify_export(self.path)
        self.assertTrue(result["ok"])
        self.assertEqual(result["schema"], 99)
        self.assertFalse(result["schema_supported"])

    def test_a_non_numeric_record_count_is_handled(self) -> None:
        self.add_research()
        export_jsonl(self.conn, self.path)
        lines = self.path.read_text(encoding="utf-8").splitlines()
        meta = json.loads(lines[0])
        meta["records"] = "many"
        lines[0] = json.dumps(meta, sort_keys=True)
        self.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        result = verify_export(self.path)
        self.assertTrue(result["ok"])
        self.assertFalse(result["counts_match"])


if __name__ == "__main__":
    unittest.main()
