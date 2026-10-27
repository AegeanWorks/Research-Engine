"""Observations: raw values, their voiding, and the statistics projection over them."""

from __future__ import annotations

import unittest

from engine.analysis import claim_statistics, observation_summary
from engine.claims import add_claim
from engine.errors import EngineError
from engine.events import list_events
from engine.integrity import check
from engine.observations import (
    add_observation,
    get_observation,
    group_values,
    list_observations,
    void_observation,
)
from engine.synthesis import claim_detail
from tests.support import DatabaseCase


class ObservationTests(DatabaseCase):
    def setUp(self) -> None:
        super().setUp()
        self.research = self.add_research()
        self.claim = add_claim(
            self.conn, self.research, "Treatment raises the value.", "assumption", basis="p"
        ).id
        for value in (1.2, 1.4, 1.1, 1.3, 1.25, 1.35):
            add_observation(self.conn, self.claim, "baseline", value)
        for value in (1.9, 2.1, 2.0, 2.2, 1.95, 2.05):
            add_observation(self.conn, self.claim, "treatment", value)

    def test_values_are_recorded_in_order(self) -> None:
        values = [item.value for item in list_observations(self.conn, self.claim, "baseline")]
        self.assertEqual(values, [1.2, 1.4, 1.1, 1.3, 1.25, 1.35])

    def test_non_finite_values_are_refused(self) -> None:
        with self.assertRaises(EngineError):
            add_observation(self.conn, self.claim, "baseline", float("nan"))
        with self.assertRaises(EngineError):
            add_observation(self.conn, self.claim, "baseline", float("inf"))

    def test_invalid_group_is_refused(self) -> None:
        with self.assertRaises(EngineError):
            add_observation(self.conn, self.claim, "  ", 1.0)
        with self.assertRaises(EngineError):
            add_observation(self.conn, self.claim, "not a label", 1.0)

    def test_groups_are_lowercased(self) -> None:
        record = add_observation(self.conn, self.claim, "Baseline", 9.0)
        self.assertEqual(record.group_label, "baseline")

    def test_void_retires_without_deleting(self) -> None:
        record = add_observation(self.conn, self.claim, "baseline", 99.0)
        voided = void_observation(self.conn, record.id, "transcription error")
        self.assertTrue(voided.voided)
        self.assertEqual(voided.void_reason, "transcription error")
        self.assertNotIn(99.0, group_values(self.conn, self.claim)["baseline"])
        self.assertEqual(len(list_observations(self.conn, self.claim, "baseline", True)), 7)
        self.assertEqual(get_observation(self.conn, record.id).value, 99.0)

    def test_void_requires_a_reason_and_happens_once(self) -> None:
        record = add_observation(self.conn, self.claim, "baseline", 99.0)
        with self.assertRaises(EngineError):
            void_observation(self.conn, record.id, " ")
        void_observation(self.conn, record.id, "duplicate")
        with self.assertRaises(EngineError):
            void_observation(self.conn, record.id, "again")

    def test_void_is_logged(self) -> None:
        record = add_observation(self.conn, self.claim, "baseline", 99.0)
        void_observation(self.conn, record.id, "duplicate")
        kinds = [event.kind for event in list_events(self.conn)]
        self.assertIn("observation.void", kinds)

    def test_statistics_compare_the_groups(self) -> None:
        result = claim_statistics(self.conn, self.claim, "baseline", "treatment", resamples=200)
        self.assertEqual(result["baseline"]["n"], 6)
        self.assertEqual(result["treatment"]["n"], 6)
        self.assertAlmostEqual(result["difference"], 0.7666666666666666, places=12)
        self.assertTrue(result["significant"])

    def test_missing_group_lists_available_groups(self) -> None:
        with self.assertRaises(EngineError) as caught:
            claim_statistics(self.conn, self.claim, "control", "treatment")
        self.assertIn("baseline", caught.exception.fix)

    def test_statistics_are_logged_and_clear_the_warning(self) -> None:
        self.assertIn("OBS-001", {finding.code for finding in check(self.conn)})
        claim_statistics(self.conn, self.claim, "baseline", "treatment", resamples=50)
        self.assertNotIn("OBS-001", {finding.code for finding in check(self.conn)})
        kinds = [event.kind for event in list_events(self.conn)]
        self.assertIn("claim.stats", kinds)

    def test_summary_and_detail(self) -> None:
        summary = observation_summary(self.conn, self.claim)
        self.assertEqual([item["group"] for item in summary], ["baseline", "treatment"])
        self.assertEqual(summary[0]["n"], 6)
        detail = claim_detail(self.conn, self.claim)
        self.assertIn("## Observations", detail)
        self.assertIn("baseline: n=6", detail)

    def test_voided_values_are_excluded_from_statistics(self) -> None:
        outlier = add_observation(self.conn, self.claim, "baseline", 100.0)
        void_observation(self.conn, outlier.id, "outlier")
        result = claim_statistics(self.conn, self.claim, "baseline", "treatment", resamples=50)
        self.assertEqual(result["baseline"]["n"], 6)
        self.assertLess(result["baseline"]["mean"], 2.0)


if __name__ == "__main__":
    unittest.main()
