"""Golden run: the whole command surface, end to end, in a fresh database.

This is the operational dogfooding gate. It does not test an individual module; it checks that the
commands compose: a program is created, screened, evidenced, measured, tested, adjudicated,
reported, compared, collapsed, merged, backed up and audited in one sequence.
"""

from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from engine.cli import main


class GoldenRunTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.dir = Path(directory.name)
        self.db = self.dir / "golden.db"
        self.scripts = self.dir / "scripts"
        self.scripts.mkdir()
        self.main_py = self.scripts / "measure.py"
        self.control_py = self.scripts / "control.py"
        self.main_py.write_text("print('value=2')\n", encoding="utf-8")
        self.control_py.write_text(
            "import sys\nprint('control-diverged')\nsys.exit(2)\n", encoding="utf-8"
        )

    def run_cli(self, *args: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(["--db", str(self.db), *args])
        return code, out.getvalue(), err.getvalue()

    def must(self, *args: str) -> str:
        code, out, err = self.run_cli(*args)
        self.assertEqual(code, 0, f"{args} failed: {out}{err}")
        return out

    def test_every_command_composes(self) -> None:
        self.assertIn("schema 7", self.must("init"))

        # 1. Program, question, source and screening.
        self.assertIn("r_000001", self.must("research", "add", "Golden program", "--scope", "end to end"))
        self.must("question", "add", "r_000001", "Does the treatment raise the value?")
        self.must("source", "add", "r_000001", "--title", "Cohort", "--year", "2026",
                  "--doi", "10.1000/golden")
        self.must("source", "screen", "s_000001", "--status", "included")
        prisma = self.must("source", "prisma", "--research", "r_000001")
        self.assertIn("included: 1", prisma)

        # 2. Claims with provenance, a premise edge and question links.
        self.must(
            "claim", "add", "r_000001", "--kind", "empirical", "--text", "The value rose.",
            "--source", "s_000001", "--quote", "The value rose.", "--locator", "Results p.1",
            "--kill-test", "A run where the value does not rise.",
        )
        self.must(
            "claim", "add", "r_000001", "--kind", "derived", "--text", "The treatment causes the rise.",
            "--basis", "association plus design", "--from", "c_000001",
            "--kill-test", "A randomized run with no rise.",
        )
        self.must(
            "claim", "add", "r_000001", "--kind", "empirical", "--text",
            "The value did not rise.", "--source", "s_000001",
            "--quote", "The value did not rise.", "--locator", "Results p.2",
            "--kill-test", "A run where the value rises.",
        )
        self.must("claim", "link-question", "c_000001", "q_000001", "--stance", "supports")
        self.must("claim", "link-question", "c_000002", "q_000001", "--stance", "supports")
        self.must("claim", "link-question", "c_000003", "q_000001", "--stance", "contradicts")
        self.must("claim", "link", "c_000002", "c_000001", "--rel", "supports")

        # 3. Pre-registration.
        hypothesis = self.must(
            "hypothesis", "add", "r_000001", "--statement", "Raising the treatment raises the value.",
            "--criterion", "The value stays flat.", "--confidence", "0.7", "--question", "q_000001",
        )
        self.assertIn("PREREGISTERED", hypothesis)
        self.assertIn("Verification criterion", self.must("hypothesis", "card", "h_000001"))

        # 4. Observations, statistics and a trend.
        for value in (1.2, 1.4, 1.1, 1.3):
            self.must("observation", "add", "c_000001", "--group", "baseline", "--value", str(value))
        for value in (1.9, 2.1, 2.0, 2.2):
            self.must("observation", "add", "c_000001", "--group", "treatment", "--value", str(value))
        stats = json.loads(self.must(
            "--json", "analysis", "stats", "c_000001", "--baseline", "baseline",
            "--treatment", "treatment", "--seed", "7", "--resamples", "200",
        ))
        self.assertTrue(stats["significant"])
        self.assertEqual(stats["bootstrap"]["seed"], 7)
        self.assertIn("slope=", self.must("analysis", "trend", "c_000001", "--group", "baseline"))

        # 5. Kill test with a negative control, then the numeric verdict.
        self.must(
            "test", "add", "r_000001", "--name", "Measure", "--claim", "c_000001",
            "--command", f'"{sys.executable}" "{self.main_py}"',
            "--control", f'"{sys.executable}" "{self.control_py}"',
        )
        verified = self.must("test", "verify", "t_000001")
        self.assertIn("control: falsified", verified)
        self.must("claim", "verdict", "c_000001", "--status", "NUMERIC", "--evidence",
                  "two-run measurement")

        # 6. Views and discovery.
        self.assertIn("OUTLINE", self.must("outline", "r_000001"))
        self.assertIn("BRIEF", self.must("brief", "r_000001"))
        self.assertIn("CLAIM c_000001", self.must("claim", "context", "c_000001"))
        contradictions = self.must("analysis", "contradictions", "r_000001")
        self.assertIn("q_000001", contradictions)
        self.assertIn("c_000003", contradictions)
        self.assertIn("c_000001", self.must("analysis", "keystone", "r_000001"))
        self.assertIn("q_000001", self.must("analysis", "matrix", "r_000001"))
        self.assertIn("dependent", self.must("analysis", "expose", "c_000001"))

        # 7. Report, manifest, drift check.
        report_path = self.dir / "report.md"
        self.must("report", "r_000001", "--out", str(report_path))
        manifest = json.loads((self.dir / "report.md.manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["license"]["id"], "ASL-1.1")
        self.assertIn("clean: True", self.must("report", "r_000001", "--check", str(report_path)))

        # 8. Snapshots.
        first, second = self.dir / "a.jsonl", self.dir / "b.jsonl"
        self.must("export", str(first))
        self.must("export", str(second))
        self.assertIn("no differences", self.must("diff", str(first), str(second)))

        # 9. Maintenance and the audit trail.
        self.assertIn("integrity: ok", self.must("db", "integrity"))
        self.assertIn("verified", self.must("db", "backup", str(self.dir / "backup.db")))
        self.assertIn("report.write", self.must("events", "--kind", "report.write"))

        # 10. The gate is clean for this program.
        code, out, _ = self.run_cli("check")
        self.assertEqual(code, 0, out)
        self.assertNotIn("| error |", out)

        # 11. Collapse a premise: the dependent must be invalidated.
        self.must("claim", "invalidate", "c_000001", "--status", "FALSIFIED",
                  "--reason", "the replicate failed", "--evidence", "replicate run 2")
        invalidated = self.must("claim", "list", "--status", "INVALIDATED")
        self.assertIn("c_000002", invalidated)

        # 12. Merge a duplicate into the surviving claim.
        self.must("claim", "add", "r_000001", "--kind", "assumption", "--text",
                  "Duplicate assertion.", "--basis", "a")
        self.must("claim", "add", "r_000001", "--kind", "assumption", "--text",
                  "Duplicate assertion.", "--basis", "b")
        merged = self.must("claim", "merge", "c_000004", "c_000005")
        self.assertIn("retired c_000005", merged)
        self.assertIn("Scorecard", self.must("scorecard", "r_000001"))


if __name__ == "__main__":
    unittest.main()
