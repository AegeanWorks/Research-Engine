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
from engine.database import SCHEMA_VERSION


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
        self.assertIn(f"schema {SCHEMA_VERSION}", out)
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

    def test_search_command(self) -> None:
        self.run_cli("demo")
        code, out, _ = self.run_cli("--json", "search", "synthetic cohort")
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertGreaterEqual(payload["counts"]["source"]["hits"], 1)
        self.assertGreaterEqual(payload["counts"]["claim"]["hits"], 1)
        code, out, _ = self.run_cli("search", "synthetic cohort", "--budget", "60")
        self.assertEqual(code, 0)
        self.assertIn("SEARCH", out)

    def test_source_duplicates_command(self) -> None:
        self.run_cli("demo")
        self.run_cli(
            "source", "add", "r_000001", "--title", "Paper A", "--year", "2024",
            "--doi", "https://doi.org/10.1/X",
        )
        self.run_cli(
            "source", "add", "r_000001", "--title", "paper a", "--year", "2024",
            "--doi", "doi:10.1/x",
        )
        code, out, _ = self.run_cli("--json", "source", "duplicates", "--research", "r_000001")
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["groups"][0]["reason"], "doi")
        code, out, _ = self.run_cli("source", "duplicates", "--research", "r_000001")
        self.assertEqual(code, 0)
        self.assertIn("[doi]", out)

    def test_calibration_command(self) -> None:
        self.run_cli("demo")
        code, _, err = self.run_cli(
            "hypothesis", "outcome", "h_000001", "--status", "SUPPORTED",
            "--evidence", "demo outcome",
        )
        self.assertEqual(code, 0, err)
        code, out, _ = self.run_cli("--json", "analysis", "calibration", "r_000001")
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual(payload["counts"]["resolved"], 1)
        self.assertAlmostEqual(payload["brier"], 0.16, places=4)
        code, out, _ = self.run_cli("analysis", "calibration", "r_000001")
        self.assertEqual(code, 0)
        self.assertIn("Brier", out)

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


    def test_claim_revision_commands(self) -> None:
        self.run_cli("demo")
        code, out, _ = self.run_cli(
            "claim", "revise", "c_000001", "--text", "Narrower claim.",
            "--reason", "narrowed to the tested subgroup", "--source", "s_000001",
            "--quote", "Narrower claim in the tested subgroup.", "--locator", "p.2",
        )
        self.assertEqual(code, 0)
        self.assertIn("revised", out)
        code, out, _ = self.run_cli("claim", "history", "c_000001")
        self.assertEqual(code, 0)
        self.assertIn("c_000001", out)
        self.assertIn("head", out)
        _, default_list, _ = self.run_cli("claim", "list", "--research", "r_000001")
        self.assertNotIn("c_000001", default_list)
        _, history_list, _ = self.run_cli(
            "claim", "list", "--research", "r_000001", "--history"
        )
        self.assertIn("c_000001", history_list)

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

    def test_event_tree_and_path(self) -> None:
        self.run_cli("demo")
        from engine.database import connect
        from engine.events import record

        conn = connect(self.db)
        self.addCleanup(conn.close)
        root = record(conn, "nested.root", "root", research_id="r_000001")
        child = record(conn, "nested.child", "child", research_id="r_000001",
                       parent_id=root.id)
        conn.close()
        code, out, _ = self.run_cli("events", "--tree", root.id)
        self.assertEqual(code, 0)
        self.assertIn("nested.child", out)
        code, out, _ = self.run_cli("events", "--path", child.id)
        self.assertEqual(code, 0)
        self.assertIn("nested.root", out)
        self.assertIn("nested.child", out)

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


    def test_closed_vocabularies_are_rejected_by_the_parser(self) -> None:
        with self.assertRaises(SystemExit):
            self.run_cli(
                "claim", "add", "r_000001", "--text", "X.", "--kind", "bogus",
            )
        with self.assertRaises(SystemExit):
            self.run_cli("claim", "link", "c_000001", "c_000002", "--rel", "bogus")

    def test_retracted_status_points_at_retract(self) -> None:
        self.run_cli("research", "add", "R")
        self.run_cli("source", "add", "r_000001", "--title", "T", "--year", "2024")
        code, _, err = self.run_cli("source", "status", "s_000001", "--status", "retracted")
        self.assertEqual(code, 1)
        self.assertIn("source retract", err)

    def test_non_positive_budgets_are_refused(self) -> None:
        self.run_cli("demo")
        for command in ("outline", "brief"):
            code, _, err = self.run_cli(command, "r_000001", "--budget", "0")
            self.assertEqual(code, 1)
            self.assertIn("Why:", err)
        code, _, err = self.run_cli("search", "signal", "--budget", "0")
        self.assertEqual(code, 1)
        self.assertIn("Why:", err)

    def test_demo_failure_reports_the_error_triad(self) -> None:
        import engine.demo as demo_mod
        from engine.errors import EngineError

        real = demo_mod.run_test
        demo_mod.run_test = lambda conn, ref, **kwargs: {
            "verification_complete": False,
            "run_group": "g_broken",
        }
        try:
            code, _, err = self.run_cli("demo")
        finally:
            demo_mod.run_test = real
        self.assertEqual(code, 1)
        self.assertIn("Why:", err)
        self.assertIn("Fix:", err)
        self.assertNotIn("Traceback", err)

    def test_events_tree_refuses_list_filters(self) -> None:
        self.run_cli("demo")
        code, _, err = self.run_cli("events", "--tree", "ev_000001", "--kind", "other")
        self.assertEqual(code, 1)
        self.assertIn("Why:", err)
        code, _, err = self.run_cli("events", "--path", "ev_000001", "--research", "r_000001")
        self.assertEqual(code, 1)

    def test_strict_needs_check(self) -> None:
        self.run_cli("demo")
        code, _, err = self.run_cli("report", "r_000001", "--strict")
        self.assertEqual(code, 1)
        self.assertIn("--check", err)

    def test_check_json_is_stable_machine_output(self) -> None:
        self.run_cli("demo")
        code, out, _ = self.run_cli("--json", "check")
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertIsInstance(payload, list)

    def test_report_scorecard_card_evaluate_once(self) -> None:
        self.run_cli("demo")
        import engine.cli as cli_mod

        for attr, argv in (
            ("report", ("report", "r_000001")),
            ("scorecard", ("scorecard", "r_000001")),
            ("preregistration_card", ("hypothesis", "card", "h_000001")),
        ):
            calls = []
            orig = getattr(cli_mod, attr)

            def wrap(*args, _orig=orig, _calls=calls, **kwargs):
                _calls.append(1)
                return _orig(*args, **kwargs)

            setattr(cli_mod, attr, wrap)
            try:
                self.run_cli(*argv)
            finally:
                setattr(cli_mod, attr, orig)
            self.assertEqual(len(calls), 1, attr)

    def test_protocol_add_doc_path_mismatch_is_refused(self) -> None:
        doc = self.dir / "protocol.md"
        doc.write_bytes(b"procedure v1")
        code, _, err = self.run_cli(
            "protocol", "add", "--id", "doc_pinned", "--measures", "pinned",
            "--doc-path", str(doc), "--doc-digest", "0" * 64,
        )
        self.assertEqual(code, 1)
        self.assertIn("does not match", err)
        self.assertIn("Why:", err)
        self.assertIn("Fix:", err)

    def test_bulk_invalidate_needs_allow_bulk(self) -> None:
        self.run_cli("demo")
        code, out, _ = self.run_cli("claim", "list")
        self.assertEqual(code, 0)
        root = out.splitlines()[0].split()[0]
        code, out, _ = self.run_cli("claim", "list", "--research", "r_000001")
        self.assertEqual(code, 0)
        research = "r_000001"
        for index in range(11):
            code, _, _ = self.run_cli(
                "claim", "add", research, "--text", f"Dependent {index}.",
                "--kind", "derived", "--basis", "from root", "--from", root,
            )
            self.assertEqual(code, 0)
        code, _, err = self.run_cli(
            "claim", "invalidate", root, "--status", "FALSIFIED",
            "--reason", "reason", "--evidence", "evidence",
        )
        self.assertEqual(code, 1)
        self.assertIn("--allow-bulk", err)
        code, _, _ = self.run_cli(
            "claim", "invalidate", root, "--status", "FALSIFIED",
            "--reason", "reason", "--evidence", "evidence", "--allow-bulk",
        )
        self.assertEqual(code, 0)

    def test_events_verify_reports_a_healthy_ledger(self) -> None:
        self.run_cli("demo")
        code, out, _ = self.run_cli("events", "--verify")
        self.assertEqual(code, 0)
        self.assertIn("ledger ok", out)

    def test_analysis_plan_is_cited_by_stats(self) -> None:
        self.run_cli("demo")
        for value in (1.2, 1.4, 1.1, 1.3):
            self.run_cli("observation", "add", "c_000003", "--group", "baseline",
                         "--value", str(value))
        for value in (1.9, 2.1, 2.0, 2.2):
            self.run_cli("observation", "add", "c_000003", "--group", "treatment",
                         "--value", str(value))
        code, out, _ = self.run_cli(
            "analysis", "plan", "c_000003", "--baseline", "baseline",
            "--treatment", "treatment", "--prediction", "treatment exceeds baseline",
        )
        self.assertEqual(code, 0)
        plan_id = out.split()[0]
        code, out, _ = self.run_cli(
            "analysis", "stats", "c_000003", "--baseline", "baseline",
            "--treatment", "treatment", "--plan", plan_id, "--resamples", "100",
        )
        self.assertEqual(code, 0)
        self.assertIn(f"plan: {plan_id}", out)

    def test_amend_commands_correct_live_records(self) -> None:
        self.run_cli("demo")
        code, _, _ = self.run_cli(
            "hypothesis", "amend", "h_000001", "--statement", "Revised S predicts O.",
            "--reason", "typo",
        )
        self.assertEqual(code, 0)
        code, _, _ = self.run_cli(
            "protocol", "add", "--id", "top_1", "--measures", "measures accuracy",
        )
        self.assertEqual(code, 0)
        code, _, _ = self.run_cli(
            "protocol", "amend", "top_1", "--measures", "measures top-1 accuracy",
            "--reason", "typo",
        )
        self.assertEqual(code, 0)

    def test_main_module_import_has_no_side_effects(self) -> None:
        import importlib.util

        spec = importlib.util.find_spec("engine.__main__")
        assert spec is not None and spec.origin is not None
        source = Path(spec.origin).read_text(encoding="utf-8")
        self.assertIn('__name__ == "__main__"', source)


if __name__ == "__main__":
    unittest.main()
