"""Attempt authority: the earliest non-replaceable attempt wins."""

from __future__ import annotations

import unittest

from engine import attempts
from engine.attempts import list_attempts
from engine.claims import add_claim, set_verdict
from engine.database import next_id, transaction
from engine.errors import EngineError
from engine.evidence import (
    authoritative_group,
    binding,
    claim_authority_blocked,
    claim_groups,
)
from engine.integrity import check
from engine.killtests import add_test, run_test, verify_test
from tests.support import DatabaseCase


class AttemptAuthorityTests(DatabaseCase):
    def setUp(self) -> None:
        super().setUp()
        self.research = self.add_research()
        self.claim = add_claim(
            self.conn,
            self.research,
            "Measured.",
            "assumption",
            kill_test="A counterexample.",
        )
        self.test = add_test(
            self.conn,
            self.research,
            "Probe",
            'python -c "print(1)"',
            claim_ref=self.claim.id,
        )

    def _insert_group(
        self,
        group: str,
        passed: bool = True,
        values: dict | None = None,
        outputs: tuple[str, str] | None = None,
    ) -> None:
        current = values or binding(self.test)
        output_pair = outputs or (f"{group}-out", f"{group}-out")
        with transaction(self.conn):
            for tag, output in zip(("run1", "run2"), output_pair):
                self.conn.execute(
                    "INSERT INTO test_run(id, test_id, run_group, run_tag, started_at,"
                    " duration_ms, exit_code, passed, stdout_sha256, stderr_sha256,"
                    " command_sha256, code_sha256, inputs_sha256, role)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'main')",
                    (
                        next_id(self.conn, "u"),
                        self.test.id,
                        group,
                        tag,
                        "2026-01-01T00:00:00+00:00",
                        1,
                        0 if passed else 1,
                        int(passed),
                        output,
                        "err",
                        current["command_sha256"],
                        current["code_sha256"],
                        current["inputs_sha256"],
                    ),
                )

    def _record(self, group: str, outcome: str, reason: str = ""):
        return attempts.record(self.conn, self.test.id, group, outcome, reason)

    def test_earliest_completed_attempt_wins(self) -> None:
        self._insert_group("g_000001")
        self._record("g_000001", "completed")
        self._insert_group("g_000002")
        self._record("g_000002", "completed")
        self.assertEqual(authoritative_group(self.conn, self.test), "g_000001")
        self.assertEqual(claim_groups(self.conn, self.claim.id), ["g_000001"])

    def test_infra_failure_is_replaceable(self) -> None:
        self._insert_group("g_000001", passed=False)
        self._record("g_000001", "infra_failed", "timeout")
        self._insert_group("g_000002")
        self._record("g_000002", "completed")
        self.assertEqual(authoritative_group(self.conn, self.test), "g_000002")

    def test_subject_failure_blocks_a_later_pass(self) -> None:
        self._insert_group("g_000001", passed=False)
        self._record("g_000001", "subject_failed", "expected_exit_mismatch")
        self._insert_group("g_000002")
        self._record("g_000002", "completed")
        self.assertIsNone(authoritative_group(self.conn, self.test))
        self.assertIn("subject_failed", claim_authority_blocked(self.conn, self.claim.id))
        with self.assertRaises(EngineError) as caught:
            set_verdict(self.conn, self.claim.id, "NUMERIC", "two runs")
        self.assertIn("earlier attempt", str(caught.exception))

    def test_indeterminate_is_replaceable(self) -> None:
        self._insert_group("g_000001", outputs=("one", "two"))
        self._record("g_000001", "indeterminate", "non_reproducible")
        self._insert_group("g_000002")
        self._record("g_000002", "completed")
        self.assertEqual(authoritative_group(self.conn, self.test), "g_000002")

    def test_stale_binding_is_ignored(self) -> None:
        old = dict(binding(self.test))
        old["command_sha256"] = "old-command"
        self._insert_group("g_000001", values=old)
        self._record("g_000001", "completed")
        self._insert_group("g_000002")
        self._record("g_000002", "completed")
        self.assertEqual(authoritative_group(self.conn, self.test), "g_000002")

    def test_legacy_group_without_an_attempt_still_counts(self) -> None:
        self._insert_group("g_000001")
        self.assertEqual(claim_groups(self.conn, self.claim.id), ["g_000001"])

    def test_replaceable_outcome_requires_a_reason(self) -> None:
        with self.assertRaises(EngineError):
            self._record("g_000001", "infra_failed")

    def test_attempts_are_sequenced_and_listed(self) -> None:
        self._insert_group("g_000001")
        self._insert_group("g_000002")
        self._record("g_000001", "completed")
        self._record("g_000002", "infra_failed", "runner_crash")
        records = list_attempts(self.conn, self.test.id)
        self.assertEqual([item.attempt_no for item in records], [2, 1])
        self.assertEqual(attempts.for_group(self.conn, self.test.id, "g_000001").attempt_no, 1)

    def test_completed_attempt_promotes(self) -> None:
        self._insert_group("g_000001")
        self._record("g_000001", "completed")
        claim = set_verdict(self.conn, self.claim.id, "NUMERIC", "two runs")
        self.assertEqual(claim.status, "NUMERIC")
        self.assertEqual(
            self.conn.execute(
                "SELECT evidence_group FROM verdict WHERE subject_id = ?"
                " AND status = 'NUMERIC'",
                (self.claim.id,),
            ).fetchone()["evidence_group"],
            "g_000001",
        )

    def test_real_subject_failure_records_an_attempt_and_blocks(self) -> None:
        test = add_test(
            self.conn,
            self.research,
            "Fails twice",
            'python -c "raise SystemExit(3)"',
            claim_ref=self.claim.id,
        )
        result = verify_test(self.conn, test.id)
        self.assertEqual(result["attempt"]["outcome"], "subject_failed")
        with self.assertRaises(EngineError) as caught:
            set_verdict(self.conn, self.claim.id, "NUMERIC", "two runs")
        self.assertIn("earlier attempt", str(caught.exception))

    def test_single_run_is_indeterminate(self) -> None:
        result = run_test(self.conn, self.test.id, runs=1)
        self.assertEqual(result["attempt"]["outcome"], "indeterminate")
        self.assertEqual(result["attempt"]["reason"], "insufficient_runs")

    def test_control_that_does_not_fail_is_indeterminate(self) -> None:
        test = add_test(
            self.conn,
            self.research,
            "Vacuity",
            'python -c "print(1)"',
            claim_ref=self.claim.id,
            control_command='python -c "print(1)"',
        )
        result = verify_test(self.conn, test.id)
        self.assertEqual(result["attempt"]["outcome"], "indeterminate")
        self.assertEqual(result["attempt"]["reason"], "control_not_falsified")

    def test_a_new_test_after_a_subject_failure_warns(self) -> None:
        failed = add_test(
            self.conn,
            self.research,
            "Fails twice",
            'python -c "raise SystemExit(3)"',
            claim_ref=self.claim.id,
        )
        verify_test(self.conn, failed.id)
        later = add_test(
            self.conn,
            self.research,
            "Later probe",
            'python -c "print(1)"',
            claim_ref=self.claim.id,
        )
        with transaction(self.conn):
            self.conn.execute(
                "UPDATE killtest SET created_at = ? WHERE id = ?",
                ("2099-01-01T00:00:00+00:00", later.id),
            )
        findings = [item for item in check(self.conn) if item.code == "TEST-002"]
        self.assertEqual([item.subject for item in findings], [later.id])


if __name__ == "__main__":
    unittest.main()
