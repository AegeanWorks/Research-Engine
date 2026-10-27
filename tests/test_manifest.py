"""Generated report manifests and drift detection."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from engine.claims import add_claim
from engine.errors import EngineError
from engine.manifest import (
    LICENSE_ID,
    REPORT_SCHEMA,
    check_report,
    license_block,
    manifest_path,
    write_report,
)
from engine.synthesis import LIMITS, report
from tests.support import DatabaseCase


class ManifestTests(DatabaseCase):
    def setUp(self) -> None:
        super().setUp()
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        self.research = self.add_research()
        add_claim(self.conn, self.research, "Assumed premise.", "assumption", basis="a")

    def test_write_report_creates_report_and_manifest(self) -> None:
        target = self.directory / "report.md"
        result = write_report(self.conn, self.research, target)
        self.assertTrue(target.is_file())
        sidecar = manifest_path(target)
        self.assertTrue(sidecar.is_file())
        stored = json.loads(sidecar.read_text(encoding="utf-8"))
        self.assertEqual(stored["schema"], REPORT_SCHEMA)
        self.assertEqual(stored["research"]["id"], self.research)
        self.assertEqual(len(stored["report_sha256"]), 64)
        self.assertEqual(len(stored["graph_sha256"]), 64)
        self.assertEqual(stored["limits"], list(LIMITS))
        self.assertEqual(result["manifest"], str(sidecar))

    def test_check_passes_on_an_unchanged_graph(self) -> None:
        target = self.directory / "report.md"
        write_report(self.conn, self.research, target)
        result = check_report(self.conn, self.research, target)
        self.assertTrue(result["clean"], result["drift"])
        self.assertEqual(result["drift"], [])

    def test_graph_change_is_reported_as_drift(self) -> None:
        target = self.directory / "report.md"
        write_report(self.conn, self.research, target)
        add_claim(self.conn, self.research, "A later claim.", "assumption", basis="b")
        result = check_report(self.conn, self.research, target)
        self.assertFalse(result["clean"])
        self.assertTrue(any("graph" in item for item in result["drift"]))

    def test_missing_manifest_is_an_error(self) -> None:
        with self.assertRaises(EngineError):
            check_report(self.conn, self.research, self.directory / "absent.md")

    def test_unknown_manifest_schema_is_refused(self) -> None:
        target = self.directory / "report.md"
        write_report(self.conn, self.research, target)
        sidecar = manifest_path(target)
        stored = json.loads(sidecar.read_text(encoding="utf-8"))
        stored["schema"] = "research-engine.report/99"
        sidecar.write_text(json.dumps(stored), encoding="utf-8")
        with self.assertRaises(EngineError):
            check_report(self.conn, self.research, target)

    def test_manifest_identifies_the_license(self) -> None:
        target = self.directory / "report.md"
        write_report(self.conn, self.research, target)
        stored = json.loads(manifest_path(target).read_text(encoding="utf-8"))
        self.assertEqual(stored["license"]["id"], LICENSE_ID)
        self.assertEqual(len(stored["license"]["sha256"]), 64)
        self.assertEqual(license_block()["sha256"], stored["license"]["sha256"])

    def test_license_change_is_reported_as_drift(self) -> None:
        target = self.directory / "report.md"
        write_report(self.conn, self.research, target)
        sidecar = manifest_path(target)
        stored = json.loads(sidecar.read_text(encoding="utf-8"))
        stored["license"]["sha256"] = "0" * 64
        sidecar.write_text(json.dumps(stored), encoding="utf-8")
        result = check_report(self.conn, self.research, target)
        self.assertFalse(result["clean"])
        self.assertTrue(any("license" in item for item in result["drift"]))

    def test_report_prints_its_limits(self) -> None:
        text = report(self.conn, self.research)
        self.assertIn("## Limits", text)
        for limit in LIMITS:
            self.assertIn(limit, text)




    def test_reverification_does_not_report_content_drift(self) -> None:
        from engine.killtests import verify_test

        target = self.directory / "report.md"
        write_report(self.conn, self.research, target)
        demo = None
        from engine.demo import seed_demo

        demo = seed_demo(self.conn)
        write_report(self.conn, demo["research"], target)
        verify_test(self.conn, demo["test"])
        result = check_report(self.conn, demo["research"], target)
        self.assertTrue(result["clean"], result["drift"])

    def test_strict_check_reports_record_churn(self) -> None:
        from engine.demo import seed_demo
        from engine.killtests import verify_test

        target = self.directory / "report.md"
        demo = seed_demo(self.conn)
        write_report(self.conn, demo["research"], target)
        verify_test(self.conn, demo["test"])
        result = check_report(self.conn, demo["research"], target, strict=True)
        self.assertFalse(result["clean"])
        self.assertTrue(any("strict" in item for item in result["drift"]))

    def test_tampered_counts_are_reported(self) -> None:
        target = self.directory / "report.md"
        write_report(self.conn, self.research, target)
        sidecar = manifest_path(target)
        stored = json.loads(sidecar.read_text(encoding="utf-8"))
        stored["counts"]["claim"] = 99
        sidecar.write_text(json.dumps(stored), encoding="utf-8")
        result = check_report(self.conn, self.research, target)
        self.assertFalse(result["clean"])
        self.assertTrue(any("counts" in item for item in result["drift"]))


    def test_another_program_does_not_dirty_a_committed_report(self) -> None:
        from engine.demo import seed_demo
        from engine.researches import create_research
        from engine.claims import add_claim

        demo = seed_demo(self.conn)
        target = self.directory / "scoped.md"
        write_report(self.conn, demo["research"], target)
        other = create_research(self.conn, "Unrelated")
        add_claim(self.conn, other.id, "Broken elsewhere.", "assumption", basis="a")
        self.conn.execute(
            "UPDATE claim SET kind = 'empirical' WHERE research_id = ?", (other.id,)
        )
        result = check_report(self.conn, demo["research"], target)
        self.assertTrue(result["clean"], result["drift"])
        text = target.read_text(encoding="utf-8")
        self.assertNotIn("Broken elsewhere", text)
        stored = json.loads(manifest_path(target).read_text(encoding="utf-8"))
        self.assertEqual(stored["findings"], {"errors": 0, "warnings": 0})


    def test_strict_check_passes_right_after_generation(self) -> None:
        target = self.directory / "strict.md"
        write_report(self.conn, self.research, target)
        result = check_report(self.conn, self.research, target, strict=True)
        self.assertTrue(result["clean"], result["drift"])


if __name__ == "__main__":
    unittest.main()
