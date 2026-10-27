"""Consensus weighting and generated reports."""

from __future__ import annotations

import unittest

from engine.claims import add_claim, link_to_question, set_verdict
from engine.questions import add_question
from engine.synthesis import claim_detail, consensus, inventory, report, scorecard
from tests.support import DatabaseCase, force_numeric


class SynthesisTests(DatabaseCase):
    def _question_with_opposition(self) -> tuple[str, str, str, str]:
        research = self.add_research()
        question = add_question(self.conn, research, "Does S drive O?")
        question_id = question.id
        support = add_claim(
            self.conn, research, "S drives O.", "assumption",
            confidence=0.8, kill_test="A cohort in which O stays flat.",
        )
        against = add_claim(
            self.conn, research, "S does not drive O.", "assumption",
            confidence=0.4, kill_test="A cohort in which S and O covary.",
        )
        link_to_question(self.conn, support.id, question_id, "supports")
        link_to_question(self.conn, against.id, question_id, "contradicts")
        force_numeric(self.conn, support.id)
        return research, question_id, support.id, against.id

    def test_consensus_weights_status_and_confidence(self) -> None:
        _, question, _, _ = self._question_with_opposition()
        self.assertAlmostEqual(consensus(self.conn, question), 0.6364, places=4)

    def test_report_contains_evidence_and_contradictions(self) -> None:
        research, question, support, against = self._question_with_opposition()
        text = report(self.conn, research)
        self.assertIn("Does S drive O?", text)
        self.assertIn(support, text)
        self.assertIn(against, text)
        self.assertIn("Contradictions", text)
        self.assertIn("consensus", text)

    def test_scorecard_orders_failed_claims_first(self) -> None:
        research, _, support, against = self._question_with_opposition()
        set_verdict(self.conn, against, "FALSIFIED", "the cohort rejected it")
        text = scorecard(self.conn, research)
        lines = [line for line in text.splitlines() if line.startswith("| c_")]
        self.assertTrue(lines[0].startswith(f"| {against}"))

    def test_claim_detail_shows_verdict_history(self) -> None:
        _, _, support, _ = self._question_with_opposition()
        text = claim_detail(self.conn, support)
        self.assertIn("Verdict history", text)
        self.assertIn("UNVERIFIED -> NUMERIC", text)

    def test_inventory_counts_every_table(self) -> None:
        self._question_with_opposition()
        counts = inventory(self.conn)
        self.assertEqual(counts["research"], 1)
        self.assertEqual(counts["claim"], 2)
        self.assertEqual(counts["question"], 1)


if __name__ == "__main__":
    unittest.main()
