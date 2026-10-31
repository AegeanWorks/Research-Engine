"""Kill tests: binding, two-run agreement, expected exits and bounded teardown."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from engine.errors import EngineError
from engine.killtests import (
    add_test,
    current_verified_group,
    get_test,
    list_runs,
    run_test,
    verified_groups,
    verify_test,
)
from tests.support import DatabaseCase


class KillTestTests(DatabaseCase):
    def setUp(self) -> None:
        super().setUp()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.research = self.add_research()
        self.claim = self.add_empirical(self.research)

    def _script(self, name: str, body: str) -> str:
        path = self.dir / name
        path.write_text(body, encoding="utf-8")
        return f'"{sys.executable}" "{path}"'

    def test_test_must_be_bound_to_a_target(self) -> None:
        with self.assertRaises(EngineError):
            add_test(self.conn, self.research, "Unbound", 'python -c "print(1)"')

    def test_two_runs_agree_and_record_a_verified_group(self) -> None:
        command = self._script("stable.py", "print('kill-test:stable')\n")
        test = add_test(self.conn, self.research, "Stable", command, claim_ref=self.claim)
        result = verify_test(self.conn, test.id)
        self.assertTrue(result["passed"])
        self.assertTrue(result["reproducible"])
        self.assertTrue(result["verification_complete"])
        self.assertEqual(len(verified_groups(self.conn, test.id)), 1)
        self.assertEqual(len(list_runs(self.conn, test.id)), 2)

    def test_disagreeing_runs_fail_reproducibility(self) -> None:
        counter = self.dir / "counter.txt"
        body = (
            "from pathlib import Path\n"
            f"path = Path(r'{counter}')\n"
            "previous = path.read_text() if path.exists() else ''\n"
            "path.write_text(previous + 'x')\n"
            "print(path.read_text())\n"
        )
        command = self._script("drifting.py", body)
        test = add_test(self.conn, self.research, "Drifting", command, claim_ref=self.claim)
        result = verify_test(self.conn, test.id)
        self.assertFalse(result["passed"])
        self.assertFalse(result["reproducible"])
        self.assertEqual(verified_groups(self.conn, test.id), [])

    def test_expected_exit_code_is_honoured(self) -> None:
        command = self._script("exits.py", "raise SystemExit(3)\n")
        test = add_test(
            self.conn, self.research, "Expected failure", command,
            claim_ref=self.claim, expect_exit=3,
        )
        result = verify_test(self.conn, test.id)
        self.assertTrue(result["passed"])

    def test_ordinary_failure_is_reported(self) -> None:
        command = self._script("fails.py", "raise SystemExit(1)\n")
        test = add_test(self.conn, self.research, "Fails", command, claim_ref=self.claim)
        result = run_test(self.conn, test.id)
        self.assertFalse(result["passed"])
        self.assertFalse(result["verification_complete"])

    def test_timeout_kills_the_command_and_fails(self) -> None:
        command = self._script("slow.py", "import time\ntime.sleep(5)\n")
        test = add_test(
            self.conn, self.research, "Slow", command, claim_ref=self.claim, timeout_seconds=1,
        )
        result = run_test(self.conn, test.id)
        self.assertFalse(result["passed"])
        self.assertEqual(result["runs"][0]["exit_code"], -1)


    def test_binding_matches_after_verification(self) -> None:
        command = self._script("bound.py", "print('bound')\n")
        test = add_test(self.conn, self.research, "Bound", command, claim_ref=self.claim)
        result = verify_test(self.conn, test.id)
        self.assertIsNotNone(current_verified_group(self.conn, test))
        self.assertEqual(result["binding"]["command_sha256"], result["binding"]["command_sha256"])
        self.assertEqual(len(result["binding"]["code_sha256"]), 64)

    def test_editing_the_command_invalidates_the_binding(self) -> None:
        command = self._script("edit.py", "print('one')\n")
        test = add_test(self.conn, self.research, "Editable", command, claim_ref=self.claim)
        verify_test(self.conn, test.id)
        self.assertIsNotNone(current_verified_group(self.conn, test))
        self.conn.execute(
            "UPDATE killtest SET command = ? WHERE id = ?",
            (self._script("edited_command.py", "print('two')\n"), test.id),
        )
        refreshed = get_test(self.conn, test.id)
        self.assertIsNone(current_verified_group(self.conn, refreshed))
        self.assertEqual(len(verified_groups(self.conn, test.id)), 1)

    def test_changing_a_declared_input_invalidates_the_binding(self) -> None:
        data = self.dir / "data.txt"
        data.write_text("one", encoding="utf-8")
        command = self._script("read_input.py", "from pathlib import Path\n"
                               f"print(Path(r'{data}').read_text(encoding='utf-8'))\n")
        test = add_test(
            self.conn, self.research, "Reads input", command,
            claim_ref=self.claim, inputs=[str(data)],
        )
        verify_test(self.conn, test.id)
        self.assertIsNotNone(current_verified_group(self.conn, test))
        data.write_text("two", encoding="utf-8")
        self.assertIsNone(current_verified_group(self.conn, test))
        verify_test(self.conn, test.id)
        self.assertIsNotNone(current_verified_group(self.conn, test))

    def test_run_records_the_binding_and_git_state(self) -> None:
        command = self._script("recorded.py", "print('recorded')\n")
        test = add_test(self.conn, self.research, "Recorded", command, claim_ref=self.claim)
        verify_test(self.conn, test.id)
        runs = list_runs(self.conn, test.id)
        self.assertEqual(len(runs), 2)
        for run in runs:
            self.assertEqual(len(run.command_sha256), 64)
            self.assertEqual(len(run.code_sha256), 64)
            self.assertTrue(run.git_commit)
            self.assertTrue(run.python_version)


if __name__ == "__main__":
    unittest.main()
