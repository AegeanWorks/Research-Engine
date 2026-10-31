"""Negative controls: a test must be able to fail before its pass is evidence."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from engine.claims import add_claim
from engine.context import outline
from engine.evidence import binding, control_state
from engine.integrity import check
from engine.killtests import add_test, get_test, list_runs, verify_test
from tests.support import DatabaseCase


class ControlTests(DatabaseCase):
    def setUp(self) -> None:
        super().setUp()
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.dir = Path(directory.name)
        self.research = self.add_research()
        self.claim = add_claim(
            self.conn, self.research, "Measured value.", "assumption",
            kill_test="A measurement that differs.",
        )

    def _script(self, name: str, code: str) -> str:
        path = self.dir / name
        path.write_text(code, encoding="utf-8")
        return f'"{sys.executable}" "{path}"'

    def _test(self, control: str = "") -> str:
        main = self._script("main.py", "print('measured=1')\n")
        return add_test(
            self.conn, self.research, "Measure", main,
            claim_ref=self.claim.id, control_command=control,
        ).id

    def test_control_runs_are_stored_with_their_role(self) -> None:
        control = self._script("control.py", "import sys\nprint('diverged')\nsys.exit(2)\n")
        test_id = self._test(control)
        result = verify_test(self.conn, test_id)
        self.assertTrue(result["verification_complete"])
        self.assertTrue(result["control_declared"])
        self.assertTrue(result["control_falsified"])
        runs = list_runs(self.conn, test_id)
        roles = sorted(run.role for run in runs)
        self.assertEqual(roles, ["control", "control", "main", "main"])

    def test_a_control_that_passes_blocks_verification(self) -> None:
        control = self._script("control.py", "print('measured=1')\n")
        test_id = self._test(control)
        result = verify_test(self.conn, test_id)
        self.assertFalse(result["verification_complete"])
        self.assertFalse(result["control_falsified"])
        codes = {finding.code for finding in check(self.conn)}
        self.assertIn("EVID-009", codes)

    def test_an_irreproducible_control_blocks_verification(self) -> None:
        counter = self.dir / "count.txt"
        control = self._script(
            "noisy.py",
            "from pathlib import Path\n"
            f"path = Path(r'{counter}')\n"
            "previous = path.read_text() if path.exists() else ''\n"
            "path.write_text(previous + 'x')\n"
            "print(path.read_text())\n"
            "raise SystemExit(2)\n",
        )
        result = verify_test(self.conn, self._test(control))
        self.assertFalse(result["control_falsified"])
        self.assertFalse(result["verification_complete"])

    def test_absence_of_a_control_is_reported_but_not_blocking(self) -> None:
        test_id = self._test()
        result = verify_test(self.conn, test_id)
        self.assertTrue(result["verification_complete"])
        self.assertFalse(result["control_declared"])
        findings = [item for item in check(self.conn) if item.code == "EVID-008"]
        self.assertEqual([item.subject for item in findings], [test_id])
        self.assertEqual(findings[0].severity, "warning")

    def test_editing_the_control_retires_the_evidence(self) -> None:
        control = self._script("control.py", "raise SystemExit(2)\n")
        test_id = self._test(control)
        verify_test(self.conn, test_id)
        before = binding(get_test(self.conn, test_id))["command_sha256"]
        self.conn.execute(
            "UPDATE killtest SET control_command = ? WHERE id = ?",
            (self._script("control2.py", "raise SystemExit(3)\n"), test_id),
        )
        after = binding(get_test(self.conn, test_id))["command_sha256"]
        self.assertNotEqual(before, after)

    def test_control_state_reports_absence_explicitly(self) -> None:
        test_id = self._test()
        test = get_test(self.conn, test_id)
        state = control_state(self.conn, test, "g_000001")
        self.assertEqual(state["declared"], False)
        self.assertEqual(state["runs"], 0)

    def test_outline_counts_the_program_screening(self) -> None:
        view = outline(self.conn, self.research)
        self.assertIn("OUTLINE", view.text)


    def test_adding_a_control_later_clears_the_error(self) -> None:
        test_id = self._test()  # first verification has no control
        verify_test(self.conn, test_id)
        self.assertIn("EVID-008", {finding.code for finding in check(self.conn)})
        control = self._script("control.py", "import sys\nprint('diverged')\nsys.exit(2)\n")
        self.conn.execute(
            "UPDATE killtest SET control_command = ? WHERE id = ?", (control, test_id)
        )
        verify_test(self.conn, test_id)
        codes = {finding.code for finding in check(self.conn)}
        self.assertNotIn("EVID-009", codes)
        self.assertNotIn("EVID-008", codes)


if __name__ == "__main__":
    unittest.main()
