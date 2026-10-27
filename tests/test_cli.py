"""The CLI surface: JSON output, exit codes and the error triad."""

from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from engine.cli import main


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.db = str(self.dir / "engine.db")

    def run_cli(self, *args: str) -> tuple[int, str, str]:
        out = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(["--db", self.db, *args])
        return code, out.getvalue(), err.getvalue()

    def test_init_and_demo(self) -> None:
        code, out, _ = self.run_cli("init")
        self.assertEqual(code, 0)
        self.assertIn("schema 5", out)
        code, out, _ = self.run_cli("--json", "demo")
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertIn("research", payload)
        self.assertEqual(len(payload["cascade_affected"]), 1)

    def test_demo_passes_integrity_gate(self) -> None:
        self.run_cli("demo")
        code, out, _ = self.run_cli("--json", "check")
        self.assertEqual(code, 0)
        self.assertFalse([item for item in json.loads(out) if item["severity"] == "error"])

    def test_error_triad_on_missing_quote(self) -> None:
        self.run_cli("research", "add", "Error case")
        code, _, err = self.run_cli(
            "claim", "add", "r_000001", "--text", "Empirical.", "--kind", "empirical",
            "--source", "s_000001",
        )
        self.assertEqual(code, 1)
        self.assertIn("Why:", err)
        self.assertIn("Fix:", err)

    def test_report_and_scorecard(self) -> None:
        self.run_cli("demo")
        code, out, _ = self.run_cli("report", "r_000001")
        self.assertEqual(code, 0)
        self.assertIn("Demo: mechanism inference", out)
        code, out, _ = self.run_cli("scorecard", "r_000001")
        self.assertEqual(code, 0)
        self.assertIn("Scorecard", out)

    def test_kill_test_verify_exit_code(self) -> None:
        script = self.dir / "ok.py"
        script.write_text("print('ok')\n", encoding="utf-8")
        self.run_cli("demo")
        command = f'"{sys.executable}" "{script}"'
        code, out, _ = self.run_cli(
            "test", "add", "r_000001", "--name", "CLI test", "--command", command,
            "--claim", "c_000001",
        )
        self.assertEqual(code, 0)
        test_id = out.split()[0]
        code, out, _ = self.run_cli("test", "verify", test_id)
        self.assertEqual(code, 0)
        self.assertIn("PASS", out)

    def test_export_writes_a_file(self) -> None:
        self.run_cli("demo")
        target = self.dir / "out.jsonl"
        code, out, _ = self.run_cli("export", str(target))
        self.assertEqual(code, 0)
        self.assertTrue(target.exists())
        self.assertIn("exported", out)

    def test_missing_database_record_exits_one(self) -> None:
        code, _, err = self.run_cli("report", "r_999999")
        self.assertEqual(code, 1)
        self.assertIn("not found", err)




    def test_report_check_ignores_reverification(self) -> None:
        target = self.dir / "report.md"
        code, _, _ = self.run_cli("demo")
        self.assertEqual(code, 0)
        code, _, _ = self.run_cli("report", "r_000001", "--out", str(target))
        self.assertEqual(code, 0)
        code, _, _ = self.run_cli("test", "verify", "t_000001")
        self.assertEqual(code, 0)
        code, out, _ = self.run_cli("report", "r_000001", "--check", str(target))
        self.assertEqual(code, 0, out)
        code, out, _ = self.run_cli("report", "r_000001", "--check", str(target), "--strict")
        self.assertEqual(code, 1, out)

    def test_source_status_and_retraction_from_the_cli(self) -> None:
        self.run_cli("demo")
        code, _, _ = self.run_cli(
            "source", "status", "s_000001", "--status", "expression_of_concern",
            "--note", "journal notice",
        )
        self.assertEqual(code, 0)
        code, out, _ = self.run_cli(
            "source", "retract", "s_000001", "--reason", "notice", "--evidence", "notice-2026"
        )
        self.assertEqual(code, 0)
        self.assertIn("RETRACTED", out)
        code, _, _ = self.run_cli("check")
        self.assertEqual(code, 0)

    def test_inventory_reports_provenance(self) -> None:
        self.run_cli("demo")
        code, out, _ = self.run_cli("inventory")
        self.assertEqual(code, 0)
        self.assertIn("engine code:", out)

    def test_verdict_group_flag_is_accepted(self) -> None:
        self.run_cli("demo")
        code, out, _ = self.run_cli(
            "claim", "verdict", "c_000001", "--status", "PROVEN",
            "--evidence", "a symbolic argument",
        )
        self.assertEqual(code, 0)
        self.assertIn("PROVEN", out)




    def test_outline_and_brief_respect_the_budget(self) -> None:
        self.run_cli("demo")
        code, out, _ = self.run_cli("outline", "r_000001", "--budget", "60")
        self.assertEqual(code, 0)
        self.assertIn("OMITTED:", out)
        code, out, _ = self.run_cli("--json", "brief", "r_000001")
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertIn("text", payload)
        self.assertIn("tokens", payload)

    def test_analysis_commands(self) -> None:
        self.run_cli("demo")
        code, out, _ = self.run_cli("analysis", "contradictions", "r_000001")
        self.assertEqual(code, 0)
        self.assertIn("c_000001", out)
        code, out, _ = self.run_cli("analysis", "matrix", "r_000001")
        self.assertEqual(code, 0)
        self.assertIn("q_000001", out)
        code, out, _ = self.run_cli("analysis", "keystone", "r_000001", "--limit", "2")
        self.assertEqual(code, 0)
        self.assertIn("weight", out)
        code, out, _ = self.run_cli("analysis", "expose", "c_000001")
        self.assertEqual(code, 0)
        self.assertIn("dependent", out)

    def test_diff_command_exit_codes(self) -> None:
        self.run_cli("demo")
        first = self.dir / "a.jsonl"
        second = self.dir / "b.jsonl"
        self.run_cli("export", str(first))
        self.run_cli("export", str(second))
        code, out, _ = self.run_cli("diff", str(first), str(second))
        self.assertEqual(code, 0)
        self.assertIn("no differences", out)
        self.run_cli("claim", "add", "r_000001", "--text", "Later claim.", "--kind", "assumption",
                     "--basis", "b")
        self.run_cli("export", str(second))
        code, out, _ = self.run_cli("diff", str(first), str(second))
        self.assertEqual(code, 1)
        self.assertIn("+ claim:", out)

    def test_claim_merge_and_context(self) -> None:
        self.run_cli("demo")
        self.run_cli("claim", "add", "r_000001", "--text", "Duplicate of c_000002.", "--kind",
                     "assumption", "--basis", "b")
        code, out, _ = self.run_cli("claim", "merge", "c_000002", "c_000006")
        self.assertEqual(code, 0)
        self.assertIn("retired c_000006", out)
        code, out, _ = self.run_cli("claim", "context", "c_000002")
        self.assertEqual(code, 0)
        self.assertIn("CLAIM c_000002", out)


    def test_screening_and_prisma(self) -> None:
        self.run_cli("demo")
        code, _, _ = self.run_cli("source", "screen", "s_000001", "--status", "included")
        self.assertEqual(code, 0)
        code, out, _ = self.run_cli("source", "prisma", "--research", "r_000001")
        self.assertEqual(code, 0)
        self.assertIn("included: 1", out)
        code, _, err = self.run_cli(
            "source", "screen", "s_000001", "--status", "excluded", "--reason", "because"
        )
        self.assertEqual(code, 1)
        self.assertIn("Why:", err)

    def test_events_are_listed(self) -> None:
        self.run_cli("demo")
        self.run_cli("source", "status", "s_000001", "--status", "expression_of_concern",
                     "--note", "notice")
        code, out, _ = self.run_cli("events", "--kind", "source.status")
        self.assertEqual(code, 0)
        self.assertIn("source.status", out)
        self.assertIn("s_000001", out)

    def test_db_integrity_and_backup(self) -> None:
        self.run_cli("demo")
        code, out, _ = self.run_cli("db", "integrity")
        self.assertEqual(code, 0)
        self.assertIn("integrity: ok", out)
        target = self.dir / "backup.db"
        code, out, _ = self.run_cli("db", "backup", str(target))
        self.assertEqual(code, 0)
        self.assertTrue(target.is_file())
        self.assertIn("verified", out)

    def test_negative_control_through_the_cli(self) -> None:
        self.run_cli("demo")
        main = self.dir / "m.py"
        control = self.dir / "c.py"
        main.write_text("print('value=1')\n", encoding="utf-8")
        control.write_text("import sys\nprint('diverged')\nsys.exit(2)\n", encoding="utf-8")
        code, out, _ = self.run_cli(
            "test", "add", "r_000001", "--name", "With control",
            "--command", f'"{sys.executable}" "{main}"',
            "--control", f'"{sys.executable}" "{control}"',
            "--claim", "c_000001",
        )
        self.assertEqual(code, 0)
        test_id = out.split()[0]
        code, out, _ = self.run_cli("test", "verify", test_id)
        self.assertEqual(code, 0)
        self.assertIn("control: falsified", out)


    def test_observations_and_statistics(self) -> None:
        self.run_cli("demo")
        for value in (1.2, 1.4, 1.1, 1.3):
            code, _, _ = self.run_cli(
                "observation", "add", "c_000003", "--group", "baseline", "--value", str(value)
            )
            self.assertEqual(code, 0)
        for value in (1.9, 2.1, 2.0, 2.2):
            self.run_cli("observation", "add", "c_000003", "--group", "treatment",
                         "--value", str(value))
        code, out, _ = self.run_cli("observation", "list", "c_000003", "--group", "baseline")
        self.assertEqual(code, 0)
        self.assertEqual(len(out.strip().splitlines()), 4)
        code, out, _ = self.run_cli("--json", "analysis", "stats", "c_000003",
                                    "--baseline", "baseline", "--treatment", "treatment",
                                    "--resamples", "100")
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertTrue(payload["significant"])
        self.assertEqual(payload["baseline"]["n"], 4)
        first = out.split('"claim"')[0]
        code, out, _ = self.run_cli("observation", "void", "ob_000001", "--reason", "typo")
        self.assertEqual(code, 0)
        self.assertIn("voided", out)

    def test_observation_errors_use_the_triad(self) -> None:
        self.run_cli("demo")
        code, _, err = self.run_cli(
            "observation", "add", "c_000003", "--group", "baseline", "--value", "nan"
        )
        self.assertEqual(code, 1)
        self.assertIn("Why:", err)
        self.assertIn("Fix:", err)


    def test_analysis_trend(self) -> None:
        self.run_cli("demo")
        for value in (1.0, 1.2, 1.4, 1.6):
            self.run_cli("observation", "add", "c_000003", "--group", "series",
                         "--value", str(value))
        code, out, _ = self.run_cli("analysis", "trend", "c_000003", "--group", "series")
        self.assertEqual(code, 0)
        self.assertIn("slope=+0.2", out)
        code, _, err = self.run_cli("analysis", "trend", "c_000003", "--group", "absent")
        self.assertEqual(code, 1)
        self.assertIn("Why:", err)


    def test_export_check_detects_tampering(self) -> None:
        self.run_cli("demo")
        target = self.dir / "snap.jsonl"
        self.run_cli("export", str(target))
        code, out, _ = self.run_cli("export", str(target), "--check")
        self.assertEqual(code, 0)
        self.assertIn("intact: True", out)
        lines = target.read_text(encoding="utf-8").splitlines()
        lines[1] = lines[1].replace("Demo", "Altered")
        target.write_text("\n".join(lines) + "\n", encoding="utf-8")
        code, out, _ = self.run_cli("export", str(target), "--check")
        self.assertEqual(code, 1)
        self.assertIn("intact: False", out)


    def test_export_check_refuses_a_research_filter(self) -> None:
        self.run_cli("demo")
        target = self.dir / "snap.jsonl"
        self.run_cli("export", str(target))
        code, _, err = self.run_cli("export", str(target), "--check", "--research", "r_000001")
        self.assertEqual(code, 1)
        self.assertIn("cannot be combined", err)


    def test_export_check_fails_on_an_unsupported_schema(self) -> None:
        self.run_cli("demo")
        target = self.dir / "snap.jsonl"
        self.run_cli("export", str(target))
        lines = target.read_text(encoding="utf-8").splitlines()
        meta = json.loads(lines[0])
        meta["schema"] = 99
        lines[0] = json.dumps(meta, sort_keys=True)
        target.write_text("\n".join(lines) + "\n", encoding="utf-8")
        code, out, _ = self.run_cli("export", str(target), "--check")
        self.assertEqual(code, 1)
        self.assertIn("unsupported", out)


if __name__ == "__main__":
    unittest.main()
