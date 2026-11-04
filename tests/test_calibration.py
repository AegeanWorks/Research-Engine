"""Hypothesis calibration: recorded confidence is scored against recorded outcomes."""

from __future__ import annotations

import unittest

from engine.calibration import score, summary
from engine.errors import EngineError
from engine.events import list_events
from engine.hypotheses import add_hypothesis, record_outcome
from engine.synthesis import report
from tests.support import DatabaseCase


class CalibrationTests(DatabaseCase):
    def add_outcome(self, research: str, confidence: float, status: str, text: str = "Prediction") -> str:
        hypothesis = add_hypothesis(
            self.conn, research, text, "The observation that would refute it.", confidence=confidence
        )
        record_outcome(self.conn, hypothesis.id, status, "recorded test evidence")
        return hypothesis.id

    def test_min_resolved_must_be_a_positive_integer(self) -> None:
        research = self.add_research()
        with self.assertRaises(EngineError):
            summary(self.conn, research, min_resolved="abc")
        with self.assertRaises(EngineError):
            summary(self.conn, research, min_resolved=2.5)
        with self.assertRaises(EngineError):
            summary(self.conn, research, min_resolved=True)
        with self.assertRaises(EngineError):
            summary(self.conn, research, min_resolved=0)

    def test_brier_log_loss_and_coverage(self) -> None:
        research = self.add_research()
        self.add_outcome(research, 0.9, "SUPPORTED", "A")
        self.add_outcome(research, 0.8, "REFUTED", "B")
        self.add_outcome(research, 0.6, "SUPPORTED", "C")
        self.add_outcome(research, 0.5, "INCONCLUSIVE", "D")
        result = summary(self.conn, research)
        self.assertEqual(
            result["counts"],
            {
                "total": 4,
                "resolved": 3,
                "supported": 2,
                "refuted": 1,
                "inconclusive": 1,
                "preregistered": 0,
            },
        )
        self.assertAlmostEqual(result["coverage"], 0.75, places=6)
        self.assertAlmostEqual(result["brier"], 0.27, places=6)
        self.assertAlmostEqual(result["log_loss"], 0.741875, places=6)
        self.assertAlmostEqual(result["base_rate"], 0.666667, places=6)
        self.assertAlmostEqual(result["brier_baseline"], 0.222222, places=6)
        self.assertAlmostEqual(result["skill"], -0.215, places=6)

    def test_reliability_bins_separate_direction(self) -> None:
        research = self.add_research()
        self.add_outcome(research, 0.9, "SUPPORTED", "A")
        self.add_outcome(research, 0.8, "REFUTED", "B")
        self.add_outcome(research, 0.6, "SUPPORTED", "C")
        result = summary(self.conn, research)
        bins = {item["low"]: item for item in result["bins"]}
        self.assertEqual(bins[0.8]["n"], 2)
        self.assertAlmostEqual(bins[0.8]["mean_confidence"], 0.85, places=4)
        self.assertAlmostEqual(bins[0.8]["observed"], 0.5, places=4)
        self.assertAlmostEqual(bins[0.8]["gap"], -0.35, places=4)
        self.assertEqual(bins[0.6]["n"], 1)
        self.assertAlmostEqual(bins[0.6]["gap"], 0.4, places=4)
        self.assertEqual(bins[0.0]["n"], 0)
        self.assertIsNone(bins[0.0]["gap"])
        self.assertTrue(any("overconfident" in warning for warning in result["warnings"]))
        self.assertTrue(any("underconfident" in warning for warning in result["warnings"]))

    def test_empty_program_is_undefined_not_zero(self) -> None:
        research = self.add_research()
        result = summary(self.conn, research)
        self.assertEqual(result["counts"]["total"], 0)
        self.assertIsNone(result["brier"])
        self.assertIsNone(result["log_loss"])
        self.assertEqual(result["coverage"], 0.0)
        self.assertIn("calibration is undefined", result["warnings"][0])

    def test_small_resolved_set_is_flagged(self) -> None:
        research = self.add_research()
        self.add_outcome(research, 0.7, "SUPPORTED")
        result = summary(self.conn, research, min_resolved=4)
        self.assertTrue(any("descriptive below 4" in warning for warning in result["warnings"]))
        quiet = summary(self.conn, research, min_resolved=1)
        self.assertFalse(any("descriptive" in warning for warning in quiet["warnings"]))

    def test_one_sided_outcomes_cannot_measure_discrimination(self) -> None:
        research = self.add_research()
        self.add_outcome(research, 0.7, "SUPPORTED", "A")
        self.add_outcome(research, 0.8, "SUPPORTED", "B")
        result = summary(self.conn, research)
        self.assertTrue(any("same label" in warning for warning in result["warnings"]))
        self.assertIsNone(result["skill"])

    def test_score_appends_an_event_and_report_shows_the_score(self) -> None:
        research = self.add_research()
        self.add_outcome(research, 0.6, "SUPPORTED", "A")
        result = score(self.conn, research)
        self.assertEqual(result["counts"]["resolved"], 1)
        events = [item for item in list_events(self.conn) if item.kind == "hypothesis.calibration"]
        self.assertEqual(len(events), 1)
        self.assertIn("brier=", events[0].detail)
        rendered = report(self.conn, research)
        self.assertIn("Hypothesis calibration", rendered)
        self.assertIn("Brier:", rendered)

    def test_minimum_resolved_set_must_be_positive(self) -> None:
        research = self.add_research()
        with self.assertRaises(EngineError):
            summary(self.conn, research, min_resolved=0)


if __name__ == "__main__":
    unittest.main()
