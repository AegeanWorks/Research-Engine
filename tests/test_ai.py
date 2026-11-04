"""AI integration: provenance at birth, fabricated citations die, novelty can survive."""

from __future__ import annotations

import unittest
from pathlib import Path

from engine import ai
from engine.claims import get_claim, set_verdict
from engine.database import SCHEMA_VERSION
from engine.errors import EngineError
from engine.integrity import check

from tests.support import DatabaseCase

ENGINE_DIR = Path(__file__).resolve().parents[1] / "engine"
MODEL = "local:test-model-1"
PROMPT = "summarize the cohort evidence for question one"
OUTPUT = "the cohort suggests signal S rose with outcome O"


class ArtifactTests(DatabaseCase):
    def test_schema_carries_ai_artifact_table(self) -> None:
        row = self.conn.execute(
            "SELECT version FROM schema_meta"
        ).fetchone()
        self.assertEqual(int(row["version"]), SCHEMA_VERSION)
        self.assertGreaterEqual(SCHEMA_VERSION, 11)
        row = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'ai_artifact'"
        ).fetchone()
        self.assertIsNotNone(row)

    def test_record_hashes_only_never_raw_text(self) -> None:
        research = self.add_research()
        artifact = ai.record_artifact(
            self.conn, research, "sweep", MODEL, PROMPT, OUTPUT,
            [{"source_id": "s_000001", "locator": "p. 3"}],
        )
        self.assertEqual(artifact.actor, "model:" + MODEL)
        self.assertEqual(artifact.kind, "sweep")
        row = self.conn.execute(
            "SELECT * FROM ai_artifact WHERE id = ?", (artifact.id,)
        ).fetchone()
        blob = " ".join(str(row[key]) for key in row.keys())
        self.assertNotIn(PROMPT, blob)
        self.assertNotIn(OUTPUT, blob)
        self.assertEqual(len(artifact.prompt_sha256), 64)
        self.assertEqual(len(artifact.output_sha256), 64)

    def test_record_refuses_empty_model_or_payload(self) -> None:
        research = self.add_research()
        with self.assertRaises(EngineError):
            ai.record_artifact(self.conn, research, "sweep", "", PROMPT, OUTPUT)
        with self.assertRaises(EngineError):
            ai.record_artifact(self.conn, research, "sweep", MODEL, "", OUTPUT)
        with self.assertRaises(EngineError):
            ai.record_artifact(self.conn, research, "nope", MODEL, PROMPT, OUTPUT)
        with self.assertRaises(EngineError):
            ai.record_artifact(
                self.conn, research, "sweep", MODEL, PROMPT, OUTPUT,
                [{"source_id": "", "locator": ""}],
            )

    def test_external_fetch_always_refuses(self) -> None:
        with self.assertRaises(EngineError):
            ai.fetch_external("https://example.invalid/model", {"prompt": "hi"})


class IngestTests(DatabaseCase):
    def _extraction(self, research: str, cited=()) -> object:
        return ai.record_artifact(
            self.conn, research, "extraction", MODEL, PROMPT, OUTPUT, cited
        )

    def test_extract_enters_unverified_with_link(self) -> None:
        research = self.add_research()
        source = self.add_source(research)
        artifact = self._extraction(
            research, [{"source_id": source, "locator": "Results, paragraph 1"}]
        )
        claim = ai.ingest_claim(
            self.conn,
            artifact.id,
            "Signal S rose with O.",
            "empirical",
            source_ref=source,
            quote="Signal S rose with O.",
            locator="Results, paragraph 1",
            kill_test="A replicate in which S falls while O rises.",
        )
        self.assertEqual(claim.status, "UNVERIFIED")
        linked = ai.get_artifact(self.conn, artifact.id)
        self.assertEqual(linked.claim_id, claim.id)

    def test_fabricated_source_is_refused_and_flagged(self) -> None:
        research = self.add_research()
        artifact = self._extraction(
            research, [{"source_id": "s_999999", "locator": "p. 1"}]
        )
        with self.assertRaises(EngineError):
            ai.ingest_claim(
                self.conn,
                artifact.id,
                "A fabricated finding.",
                "empirical",
                source_ref="s_999999",
                quote="A fabricated finding.",
                locator="p. 1",
            )
        # The claim never entered the graph ...
        self.assertEqual(
            self.conn.execute("SELECT COUNT(*) AS n FROM claim").fetchone()["n"], 0
        )
        # ... but the fabricated run is flagged, in the log and in the gate.
        reject = self.conn.execute(
            "SELECT * FROM event WHERE kind = 'ai.reject' AND subject = ?",
            (artifact.id,),
        ).fetchone()
        self.assertIsNotNone(reject)
        codes = {finding.code for finding in check(self.conn)}
        self.assertIn("AI-001", codes)

    def test_cited_divergence_is_refused_and_flagged(self) -> None:
        research = self.add_research()
        source = self.add_source(research)
        artifact = self._extraction(
            research,
            [
                {"source_id": source, "locator": "Results, paragraph 1"},
                {"source_id": "s_999999", "locator": "p. 1"},
            ],
        )
        with self.assertRaises(EngineError):
            ai.ingest_claim(
                self.conn,
                artifact.id,
                "A claim with one fake citation.",
                "empirical",
                source_ref=source,
                quote="A claim with one fake citation.",
                locator="Results, paragraph 1",
            )
        self.assertEqual(
            self.conn.execute("SELECT COUNT(*) AS n FROM claim").fetchone()["n"], 0
        )
        reject = self.conn.execute(
            "SELECT * FROM event WHERE kind = 'ai.reject' AND subject = ?",
            (artifact.id,),
        ).fetchone()
        self.assertIsNotNone(reject)

    def test_source_outside_cited_list_is_refused(self) -> None:
        research = self.add_research()
        source = self.add_source(research)
        other = self.add_source(research, title="Other source")
        artifact = self._extraction(
            research, [{"source_id": source, "locator": "Results, paragraph 1"}]
        )
        with self.assertRaises(EngineError):
            ai.ingest_claim(
                self.conn,
                artifact.id,
                "A claim citing a source the model did not cite.",
                "empirical",
                source_ref=other,
                quote="A claim citing a source the model did not cite.",
                locator="Results, paragraph 1",
            )
        self.assertEqual(
            self.conn.execute("SELECT COUNT(*) AS n FROM claim").fetchone()["n"], 0
        )

    def test_ingest_defaults_actor_to_model(self) -> None:
        research = self.add_research()
        source = self.add_source(research)
        artifact = self._extraction(
            research, [{"source_id": source, "locator": "Results, paragraph 1"}]
        )
        claim = ai.ingest_claim(
            self.conn,
            artifact.id,
            "Signal S rose with O.",
            "empirical",
            source_ref=source,
            quote="Signal S rose with O.",
            locator="Results, paragraph 1",
        )
        event = self.conn.execute(
            "SELECT * FROM event WHERE kind = 'ai.ingest' AND subject = ?",
            (claim.id,),
        ).fetchone()
        self.assertIsNotNone(event)
        self.assertEqual(event["actor"], "model:" + MODEL)

    def test_wrong_kind_from_wrong_artifact_is_refused(self) -> None:
        research = self.add_research()
        artifact = ai.record_artifact(
            self.conn, research, "sweep", MODEL, PROMPT, OUTPUT
        )
        with self.assertRaises(EngineError):
            ai.ingest_claim(self.conn, artifact.id, "An idea.", "speculation")

    def test_idea_preregisters_hypothesis(self) -> None:
        research = self.add_research()
        artifact = ai.record_artifact(
            self.conn, research, "idea", MODEL, PROMPT, OUTPUT
        )
        hypothesis = ai.ingest_hypothesis(
            self.conn,
            artifact.id,
            "Raising S raises O in a randomized run.",
            "O fails to rise when S is raised.",
        )
        self.assertEqual(hypothesis.status, "PREREGISTERED")
        linked = ai.get_artifact(self.conn, artifact.id)
        self.assertEqual(linked.hypothesis_id, hypothesis.id)


class KillTestAdapterTests(DatabaseCase):
    def test_free_form_template_is_refused(self) -> None:
        research = self.add_research()
        artifact = ai.record_artifact(
            self.conn, research, "extraction", MODEL, PROMPT, OUTPUT
        )
        with self.assertRaises(EngineError):
            ai.propose_test(
                self.conn, artifact.id, "rm -rf /", "Evil probe", claim_ref=None
            )

    def test_template_probe_verifies_like_a_human_test(self) -> None:
        from engine.claims import add_claim
        from engine.killtests import verify_test

        research = self.add_research()
        source = self.add_source(research)
        claim = add_claim(
            self.conn,
            research,
            "The constant probe is stable.",
            "empirical",
            source_ref=source,
            quote="The constant probe is stable.",
            locator="Methods, paragraph 1",
            kill_test="The constant probe must print the same line twice.",
        )
        artifact = ai.record_artifact(
            self.conn, research, "extraction", MODEL, PROMPT, OUTPUT
        )
        test = ai.propose_test(
            self.conn, artifact.id, "constant-probe", "AI constant probe",
            claim_ref=claim.id,
        )
        result = verify_test(self.conn, test.id)
        self.assertTrue(result["verification_complete"])
        linked = ai.get_artifact(self.conn, artifact.id)
        self.assertEqual(linked.test_id, test.id)

    def test_tampered_template_command_trips_ai003(self) -> None:
        research = self.add_research()
        source = self.add_source(research)
        claim_id = self.add_empirical(research, "Signal S rose with O.")
        artifact = ai.record_artifact(
            self.conn, research, "extraction", MODEL, PROMPT, OUTPUT
        )
        test = ai.propose_test(
            self.conn, artifact.id, "constant-probe", "AI probe", claim_ref=claim_id
        )
        self.conn.execute(
            "UPDATE killtest SET command = ? WHERE id = ?",
            ("python -c \"print('tampered')\"", test.id),
        )
        codes = {finding.code for finding in check(self.conn)}
        self.assertIn("AI-003", codes)

    def test_ai_proven_without_a_run_trips_ai002(self) -> None:
        research = self.add_research()
        source = self.add_source(research)
        artifact = ai.record_artifact(
            self.conn, research, "extraction", MODEL, PROMPT, OUTPUT,
            [{"source_id": source, "locator": "Results, paragraph 1"}],
        )
        claim = ai.ingest_claim(
            self.conn,
            artifact.id,
            "Signal S rose with O.",
            "empirical",
            source_ref=source,
            quote="Signal S rose with O.",
            locator="Results, paragraph 1",
            kill_test="A replicate in which S falls while O rises.",
        )
        set_verdict(self.conn, claim.id, "PROVEN", "a hand-waved argument")
        self.assertEqual(get_claim(self.conn, claim.id).status, "PROVEN")
        codes = {finding.code for finding in check(self.conn)}
        self.assertIn("AI-002", codes)


class BoundaryTests(unittest.TestCase):
    def test_no_network_imports_anywhere_in_the_engine(self) -> None:
        banned = ("import socket", "import urllib", "from urllib", "import http",
                  "from http", "import requests", "urlopen")
        offenders = []
        for path in sorted(ENGINE_DIR.glob("*.py")):
            text = path.read_text(encoding="utf-8")
            if any(marker in text for marker in banned):
                offenders.append(path.name)
        self.assertEqual(offenders, [])

    def test_ai_module_never_calls_verdict_paths(self) -> None:
        text = (ENGINE_DIR / "ai.py").read_text(encoding="utf-8")
        for symbol in ("set_verdict(", "invalidate(", "retract_source(", "merge_claims(",
                       "record_outcome(", "import urllib", "import socket"):
            self.assertNotIn(symbol, text)

    def test_model_io_inside_repo_is_refused(self) -> None:
        from engine.cli import _ensure_outside_repo

        inside = str(ENGINE_DIR / "ai.py")
        with self.assertRaises(EngineError):
            _ensure_outside_repo(inside)

    def test_model_io_outside_repo_is_allowed(self) -> None:
        import tempfile

        from engine.cli import _ensure_outside_repo

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as handle:
            handle.write("prompt")
            path = handle.name
        try:
            resolved = _ensure_outside_repo(path)
            self.assertTrue(str(resolved))
        finally:
            Path(path).unlink(missing_ok=True)


class DraftTests(DatabaseCase):
    def _surviving_claim(self, research: str):
        from engine.killtests import verify_test
        from engine.questions import add_question

        question = add_question(self.conn, research, "Does S drive O?").id
        source = self.add_source(research)
        artifact = ai.record_artifact(
            self.conn, research, "extraction", MODEL, PROMPT, OUTPUT,
            [{"source_id": source, "locator": "Results, paragraph 1"}],
        )
        claim = ai.ingest_claim(
            self.conn,
            artifact.id,
            "Signal S rose with O.",
            "empirical",
            source_ref=source,
            quote="Signal S rose with O.",
            locator="Results, paragraph 1",
            kill_test="The constant probe must print the same line twice.",
            question_ref=question,
        )
        test = ai.propose_test(
            self.conn, artifact.id, "constant-probe", "AI probe", claim_ref=claim.id
        )
        result = verify_test(self.conn, test.id)
        self.assertTrue(result["verification_complete"])
        set_verdict(
            self.conn,
            claim.id,
            "NUMERIC",
            f"{test.id} two-run verification",
            evidence_group=result["run_group"],
        )
        return claim, result

    def test_draft_carries_kill_test_receipts(self) -> None:
        research = self.add_research()
        claim, result = self._surviving_claim(research)
        draft = ai.render_draft(self.conn, research)
        self.assertIn(claim.id, draft)
        self.assertIn(result["run_group"], draft)
        self.assertIn("NUMERIC", draft)

    def test_draft_withholds_unverified_claims(self) -> None:
        research = self.add_research()
        self._surviving_claim(research)
        source = self.add_source(research)
        artifact = ai.record_artifact(
            self.conn, research, "extraction", MODEL, PROMPT, OUTPUT,
            [{"source_id": source, "locator": "Discussion, paragraph 2"}],
        )
        idle = ai.ingest_claim(
            self.conn,
            artifact.id,
            "A plausible but untested assertion.",
            "empirical",
            source_ref=source,
            quote="A plausible but untested assertion.",
            locator="Discussion, paragraph 2",
            kill_test="A replicate that contradicts it.",
        )
        draft = ai.render_draft(self.conn, research)
        self.assertIn("Withheld", draft)
        self.assertIn(f"[{idle.id} | UNVERIFIED]", draft)

    def test_draft_refuses_a_failing_gate(self) -> None:
        research = self.add_research()
        artifact = ai.record_artifact(
            self.conn, research, "extraction", MODEL, PROMPT, OUTPUT,
            [{"source_id": "s_999999", "locator": "p. 1"}],
        )
        with self.assertRaises(EngineError):
            ai.render_draft(self.conn, research)


if __name__ == "__main__":
    unittest.main()
