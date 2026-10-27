"""Pre-registration precedes outcomes and cards carry the falsification criterion."""

from __future__ import annotations

import unittest

from engine.errors import EngineError
from engine.hypotheses import (
    add_hypothesis,
    get_hypothesis,
    list_hypotheses,
    preregistration_card,
    record_outcome,
)
from engine.questions import add_question
from tests.support import DatabaseCase


class HypothesisTests(DatabaseCase):
    def test_criterion_is_required(self) -> None:
        research = self.add_research()
        with self.assertRaises(EngineError):
            add_hypothesis(self.conn, research, "S predicts O.", "  ")

    def test_registration_is_immediate_and_card_is_rendered(self) -> None:
        research = self.add_research()
        question = add_question(self.conn, research, "Does S drive O?")
        hypothesis = add_hypothesis(
            self.conn, research, "Raising S raises O.", "O stays flat when S is raised.",
            confidence=0.6, question_ref=question.id,
        )
        self.assertEqual(hypothesis.status, "PREREGISTERED")
        card = preregistration_card(self.conn, hypothesis.id)
        self.assertIn("Verification criterion", card)
        self.assertIn("Most likely to be wrong", card)

    def test_outcome_requires_evidence_and_closes_once(self) -> None:
        research = self.add_research()
        hypothesis = add_hypothesis(self.conn, research, "S predicts O.", "O stays flat.")
        with self.assertRaises(EngineError):
            record_outcome(self.conn, hypothesis.id, "REFUTED", "")
        closed = record_outcome(self.conn, hypothesis.id, "REFUTED", "trial 2", "O stayed flat")
        self.assertEqual(closed.status, "REFUTED")
        with self.assertRaises(EngineError):
            record_outcome(self.conn, hypothesis.id, "SUPPORTED", "another analysis")

    def test_unknown_outcome_is_refused(self) -> None:
        research = self.add_research()
        hypothesis = add_hypothesis(self.conn, research, "S predicts O.", "O stays flat.")
        with self.assertRaises(EngineError):
            record_outcome(self.conn, hypothesis.id, "MAYBE", "some analysis")
        self.assertEqual(get_hypothesis(self.conn, hypothesis.id).status, "PREREGISTERED")
        self.assertEqual(len(list_hypotheses(self.conn, research)), 1)


if __name__ == "__main__":
    unittest.main()
