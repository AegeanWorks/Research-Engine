"""Promotion gate: a NUMERIC verdict must cite a current, verified run group."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from engine.claims import add_claim, get_claim, set_verdict
from engine.errors import EngineError
from engine.integrity import check
from engine.killtests import add_test, current_verified_group, verify_test
from tests.support import DatabaseCase


class PromotionTests(DatabaseCase):
    def setUp(self) -> None:
        super().setUp()
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.dir = Path(directory.name)
        self.research = self.add_research()
        self.claim = add_claim(
            self.conn, self.research, "Measured value.", "assumption",
            kill_test="A run that prints another value.",
        )
        self.script = self.dir / "measure.py"
        self.script.write_text("print('value=1')\n", encoding="utf-8")
        self.command = f'"{sys.executable}" "{self.script}"'

    def _verified_test(self) -> str:
        test = add_test(self.conn, self.research, "Measure", self.command, claim_ref=self.claim.id)
        result = verify_test(self.conn, test.id)
        self.assertTrue(result["verification_complete"])
        return test.id

    def test_numeric_without_a_test_is_refused(self) -> None:
        with self.assertRaises(EngineError) as caught:
            set_verdict(self.conn, self.claim.id, "NUMERIC", "asserted")
        self.assertIn("no current verified run", str(caught.exception))
        self.assertEqual(get_claim(self.conn, self.claim.id).status, "UNVERIFIED")

    def test_numeric_derives_the_current_group(self) -> None:
        test_id = self._verified_test()
        set_verdict(self.conn, self.claim.id, "NUMERIC", f"{test_id} two-run verification")
        stored = self.conn.execute(
            "SELECT evidence_group FROM verdict WHERE subject_kind = 'claim'"
            " AND subject_id = ? AND status = 'NUMERIC'",
            (self.claim.id,),
        ).fetchone()["evidence_group"]
        self.assertTrue(stored)
        self.assertEqual([f.code for f in check(self.conn) if f.severity == "error"], [])

    def test_explicit_group_is_recorded(self) -> None:
        test_id = self._verified_test()
        from engine.killtests import get_test

        group = current_verified_group(self.conn, get_test(self.conn, test_id))
        set_verdict(self.conn, self.claim.id, "NUMERIC", "measured", evidence_group=group)
        stored = self.conn.execute(
            "SELECT evidence_group FROM verdict WHERE subject_id = ? AND status = 'NUMERIC'",
            (self.claim.id,),
        ).fetchone()["evidence_group"]
        self.assertEqual(stored, group)

    def test_unknown_group_is_refused(self) -> None:
        self._verified_test()
        with self.assertRaises(EngineError):
            set_verdict(self.conn, self.claim.id, "NUMERIC", "measured", evidence_group="g_999999")
        self.assertEqual(get_claim(self.conn, self.claim.id).status, "UNVERIFIED")

    def test_promotion_on_a_changed_command_is_detected(self) -> None:
        test_id = self._verified_test()
        set_verdict(self.conn, self.claim.id, "NUMERIC", "measured")
        self.script.write_text("print('value=2')\n", encoding="utf-8")
        self.conn.execute("UPDATE killtest SET command = ? WHERE id = ?",
                          (self.command + " ", test_id))
        verify_test(self.conn, test_id)
        codes = {finding.code for finding in check(self.conn) if finding.severity == "error"}
        self.assertIn("EVID-006", codes)

    def test_proven_promotion_needs_no_group(self) -> None:
        set_verdict(self.conn, self.claim.id, "PROVEN", "a symbolic argument")
        self.assertEqual(get_claim(self.conn, self.claim.id).status, "PROVEN")
        stored = self.conn.execute(
            "SELECT evidence_group FROM verdict WHERE subject_id = ? AND status = 'PROVEN'",
            (self.claim.id,),
        ).fetchone()["evidence_group"]
        self.assertEqual(stored, "")


if __name__ == "__main__":
    unittest.main()
