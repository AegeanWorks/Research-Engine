"""Fluid-universe rigor contracts: fingerprints, two-run compare and claim statuses."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from domains.fluid_universe.claims import (
    compare_ledger_and_scorecard,
    parse_claim_table,
    parse_scorecard,
    split_status,
)
from domains.fluid_universe.verification.compare import compare
from domains.fluid_universe.verification.fingerprint import fingerprints


def _root(case: unittest.TestCase) -> Path:
    directory = Path(tempfile.mkdtemp())
    case.addCleanup(lambda: __import__("shutil").rmtree(directory, ignore_errors=True))
    return directory


def _run(tag: str, fingerprint: dict, checks: list[dict]) -> dict:
    return {
        "meta": {
            "generated_utc": "2026-11-07T00:00:00+00:00",
            "git_commit": "deadbeef",
            "passed": sum(1 for check in checks if check["passed"]),
            "total": len(checks),
            "failed": sum(1 for check in checks if not check["passed"]),
            "fingerprints": fingerprint,
        },
        "checks": checks,
        "total": len(checks),
        "passed": sum(1 for check in checks if check["passed"]),
        "failed": sum(1 for check in checks if not check["passed"]),
        "failures": [check for check in checks if not check["passed"]],
    }


class FingerprintTests(unittest.TestCase):
    def test_source_and_result_digests_change_with_content(self) -> None:
        root = _root(self)
        (root / "theory").mkdir()
        (root / "results").mkdir()
        (root / "theory" / "model.py").write_text("VALUE = 1\n", encoding="utf-8")
        (root / "results" / "pdg_fit.json").write_text('{"q": 0.666}\n', encoding="utf-8")
        first = fingerprints(root)
        self.assertEqual(len(first["source_sha256"]), 64)
        self.assertEqual(len(first["results_sha256"]), 64)
        (root / "theory" / "model.py").write_text("VALUE = 2\n", encoding="utf-8")
        second = fingerprints(root)
        self.assertNotEqual(first["source_sha256"], second["source_sha256"])
        self.assertEqual(first["results_sha256"], second["results_sha256"])
        (root / "results" / "pdg_fit.json").write_text('{"q": 0.667}\n', encoding="utf-8")
        third = fingerprints(root)
        self.assertNotEqual(second["results_sha256"], third["results_sha256"])

    def test_excluded_directories_do_not_enter_the_digest(self) -> None:
        root = _root(self)
        (root / "theory").mkdir()
        (root / "theory" / "model.py").write_text("VALUE = 1\n", encoding="utf-8")
        baseline = fingerprints(root)["source_sha256"]
        (root / "__pycache__").mkdir()
        (root / "__pycache__" / "junk.py").write_text("ignored\n", encoding="utf-8")
        self.assertEqual(fingerprints(root)["source_sha256"], baseline)


class CompareTests(unittest.TestCase):
    def _fixture(self, root: Path, fingerprint: dict, left: list[dict], right: list[dict]) -> None:
        results = root / "results"
        results.mkdir(exist_ok=True)
        (results / "verification_run1.json").write_text(
            json.dumps(_run("run1", fingerprint, left)), encoding="utf-8"
        )
        (results / "verification_run2.json").write_text(
            json.dumps(_run("run2", fingerprint, right)), encoding="utf-8"
        )

    def test_two_agreeing_runs_are_accepted(self) -> None:
        root = _root(self)
        fingerprint = fingerprints(root)
        checks = [{"claim": "1a", "passed": True, "detail": "symbolic zero"}]
        self._fixture(root, fingerprint, checks, checks)
        result = compare(("run1", "run2"), root=root)
        self.assertTrue(result["meta"]["accepted"])
        self.assertTrue(result["meta"]["claims_agree"])
        self.assertTrue(result["meta"]["fingerprints_match"])
        self.assertTrue((root / "results" / "verification.json").is_file())

    def test_disagreeing_runs_are_refused(self) -> None:
        root = _root(self)
        fingerprint = fingerprints(root)
        self._fixture(
            root,
            fingerprint,
            [{"claim": "1a", "passed": True, "detail": "ok"}],
            [{"claim": "1a", "passed": False, "detail": "ok"}],
        )
        result = compare(("run1", "run2"), root=root)
        self.assertFalse(result["meta"]["accepted"])
        self.assertFalse(result["meta"]["claims_agree"])

    def test_stale_fingerprint_is_refused(self) -> None:
        root = _root(self)
        stale = {"source_sha256": "0" * 64, "results_sha256": "0" * 64}
        checks = [{"claim": "1a", "passed": True, "detail": "ok"}]
        self._fixture(root, stale, checks, checks)
        result = compare(("run1", "run2"), root=root)
        self.assertTrue(result["meta"]["claims_agree"])
        self.assertFalse(result["meta"]["fingerprints_match"])
        self.assertFalse(result["meta"]["accepted"])

    def test_identical_tags_are_refused(self) -> None:
        with self.assertRaises(ValueError):
            compare(("run1", "run1"))


class ClaimCompatibilityTests(unittest.TestCase):
    LEDGER = """\
| ID | Claim | Label | Status | Evidence | Kill test / next test |
|---|---|---|---|---|---|
| 1a | Claim one. | derived | **PROVEN** | a.py | symbolic zero |
| 1b | Claim two. | assumed | **FALSIFIED (ill-posed)** | b.py | counterexample |
| 3a | Claim three. | numeric | **NUMERIC** | c.py | rerun |
"""

    SCORECARD = """\
| ID | Status | One-line result |
|---|---|---|
| 1a | PROVEN | yes |
| 1b | FALSIFIED | no |
"""

    def test_ledger_parses_qualifiers_and_escaped_pipes(self) -> None:
        claims = parse_claim_table(self.LEDGER)
        self.assertEqual([claim.claim_id for claim in claims], ["1a", "1b", "3a"])
        self.assertEqual(claims[0].status, "PROVEN")
        self.assertEqual(claims[1].status, "FALSIFIED")
        self.assertEqual(claims[1].qualifier, "ill-posed")
        self.assertEqual(split_status("UNVERIFIED (null)"), ("UNVERIFIED", "null"))

    def test_scorecard_parses_and_reports_mismatches(self) -> None:
        claims = parse_claim_table(self.LEDGER)
        rows = parse_scorecard(self.SCORECARD)
        self.assertEqual([row.claim_id for row in rows], ["1a", "1b"])
        problems = compare_ledger_and_scorecard(claims, rows)
        self.assertEqual([problem["claim_id"] for problem in problems], ["3a"])
        self.assertEqual(problems[0]["reason"], "missing")

    def test_unknown_status_is_refused(self) -> None:
        with self.assertRaises(ValueError):
            split_status("MAYBE")
