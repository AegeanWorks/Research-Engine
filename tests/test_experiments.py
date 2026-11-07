"""N1 experiment records and baseline-vs-intervention analysis on the host core."""

from __future__ import annotations

import unittest

from engine.errors import EngineError
from experiments.analysis import (
    analyze_baseline_vs_intervention,
    analyze_multiple_metrics,
)
from experiments.models import (
    add_event,
    add_intervention,
    add_metric,
    add_metric_definition,
    list_events,
    list_interventions,
    list_metric_definitions,
    list_metrics,
)
from tests.support import DatabaseCase


class ExperimentModelTests(DatabaseCase):
    def test_intervention_round_trip(self) -> None:
        research = self.add_research()
        intervention = add_intervention(
            self.conn,
            research,
            "Sleep extension",
            "2026-01-01",
            projected_end_date="2026-02-01",
            dosage="+1 h",
            notes="pilot",
        )
        self.assertEqual(intervention.name, "Sleep extension")
        self.assertEqual([row.id for row in list_interventions(self.conn, research)], [intervention.id])

    def test_metric_definition_is_unique_per_program(self) -> None:
        research = self.add_research()
        add_metric_definition(self.conn, research, "weight", unit="kg")
        self.assertRaises(
            EngineError,
            add_metric_definition,
            self.conn,
            research,
            "weight",
            unit="kg",
        )
        self.assertEqual(len(list_metric_definitions(self.conn, research)), 1)

    def test_metric_entry_links_intervention_and_validates_finite_value(self) -> None:
        research = self.add_research()
        intervention = add_intervention(self.conn, research, "Run-in", "2026-01-01")
        add_metric(
            self.conn,
            research,
            "weight",
            "2026-01-02",
            81.5,
            intervention_ref=intervention.id,
        )
        rows = list_metrics(self.conn, research)
        self.assertEqual(rows[0].value, 81.5)
        self.assertEqual(rows[0].intervention_id, intervention.id)
        self.assertRaises(
            EngineError,
            add_metric,
            self.conn,
            research,
            "weight",
            "2026-01-03",
            float("nan"),
        )

    def test_event_severity_is_bounded(self) -> None:
        research = self.add_research()
        add_event(self.conn, research, "headache", "2026-01-02T10:00:00+00:00", severity=3)
        self.assertEqual(list_events(self.conn, research)[0].severity, 3)
        self.assertRaises(
            EngineError,
            add_event,
            self.conn,
            research,
            "headache",
            "2026-01-02T11:00:00+00:00",
            severity=6,
        )

    def test_intervention_from_another_program_is_refused(self) -> None:
        first = self.add_research("First")
        second = self.add_research("Second")
        intervention = add_intervention(self.conn, first, "Only here", "2026-01-01")
        self.assertRaises(
            EngineError,
            add_metric,
            self.conn,
            second,
            "weight",
            "2026-01-02",
            80.0,
            intervention_ref=intervention.id,
        )


class ExperimentAnalysisTests(DatabaseCase):
    def _rows(self, research: str, values: list[float], start_day: int = 1,
              metric: str = "weight") -> None:
        for offset, value in enumerate(values):
            day = start_day + offset
            add_metric(self.conn, research, metric, f"2026-01-{day:02d}", value)

    def test_baseline_and_intervention_windows(self) -> None:
        research = self.add_research()
        baseline = [80.0, 80.4, 79.6, 80.2, 79.8]
        treatment = [78.0, 77.6, 78.2, 77.8, 78.1]
        self._rows(research, baseline, start_day=1)
        self._rows(research, treatment, start_day=10)
        result = analyze_baseline_vs_intervention(
            self.conn,
            research,
            "weight",
            "2026-01-10",
            baseline_days=9,
            intervention_days=9,
        )
        self.assertEqual(result["baseline_window"]["count"], 5)
        self.assertEqual(result["intervention_window"]["count"], 5)
        self.assertAlmostEqual(result["analysis"]["mean_difference"], -2.06, places=6)
        self.assertIn("cohens_d", result["analysis"])
        self.assertIsNotNone(result["analysis"]["t_test"]["p_value"])
        self.assertIsNotNone(result["analysis"]["mann_whitney_u"]["p_value"])

    def test_insufficient_data_returns_counts_not_an_exception(self) -> None:
        research = self.add_research()
        self._rows(research, [80.0, 80.2], start_day=1)
        self._rows(research, [79.0, 79.2], start_day=10)
        result = analyze_baseline_vs_intervention(
            self.conn,
            research,
            "weight",
            "2026-01-10",
            baseline_days=9,
            intervention_days=9,
        )
        self.assertIn("error", result)
        self.assertEqual(result["baseline_count"], 2)
        self.assertEqual(result["intervention_count"], 2)

    def test_multiple_metric_warning_above_three(self) -> None:
        research = self.add_research()
        for metric in ("a", "b", "c", "d"):
            self._rows(research, [1.0, 2.0, 3.0], start_day=1, metric=metric)
            self._rows(research, [2.0, 3.0, 4.0], start_day=10, metric=metric)
        result = analyze_multiple_metrics(
            self.conn,
            research,
            ["a", "b", "c", "d"],
            "2026-01-10",
            baseline_days=9,
            intervention_days=9,
        )
        self.assertTrue(any("Multiple Comparison Risk" in text for text in result["global_warnings"]))
        self.assertEqual(set(result["results"]), {"a", "b", "c", "d"})
