"""N1 surfaces that were missing after the first merge: correlation, CSV, report."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from engine.errors import EngineError
from experiments.analysis import analyze_baseline_vs_intervention, correlation_matrix
from experiments.exporter import export_csv
from experiments.importer import import_csv, import_events_csv, import_interventions_csv
from experiments.models import add_intervention, add_metric, list_events, list_interventions
from experiments.reporting import generate_html_report
from tests.support import DatabaseCase


class ExperimentSurfaceTests(DatabaseCase):
    def setUp(self) -> None:
        super().setUp()
        self.directory = Path(tempfile.mkdtemp())
        self.addCleanup(
            lambda: __import__("shutil").rmtree(self.directory, ignore_errors=True)
        )

    def test_correlation_matrix_aligns_pairs_by_date(self) -> None:
        research = self.add_research()
        for offset, (first, second) in enumerate(((1, 2), (2, 4), (3, 6), (4, 8))):
            add_metric(self.conn, research, "a", f"2026-01-0{offset + 1}", first)
            add_metric(self.conn, research, "b", f"2026-01-0{offset + 1}", second)
        result = correlation_matrix(self.conn, research, ["a", "b"])
        self.assertEqual(result["metrics"], ["a", "b"])
        self.assertAlmostEqual(result["matrix"]["a"]["b"]["r"], 1.0, places=10)
        self.assertAlmostEqual(result["matrix"]["b"]["a"]["r"], 1.0, places=10)
        self.assertEqual(result["matrix"]["a"]["b"]["n"], 4)

    def test_correlation_refuses_unknown_metric(self) -> None:
        research = self.add_research()
        with self.assertRaises(EngineError):
            correlation_matrix(self.conn, research, ["missing"])

    def test_csv_import_and_export_round_trip_all_three_types(self) -> None:
        research = self.add_research()
        interventions = self.directory / "interventions.csv"
        interventions.write_text(
            "name,start_date,projected_end_date,end_date,dosage,notes\n"
            "Sleep extension,2026-01-01,2026-02-01,,+1 h,pilot\n",
            encoding="utf-8",
        )
        self.assertEqual(import_csv(self.conn, research, interventions, "interventions")["imported"], 1)
        intervention = list_interventions(self.conn, research)[0]

        events = self.directory / "events.csv"
        events.write_text(
            "timestamp,event_name,severity,notes,intervention_ref\n"
            f"2026-01-02T10:00:00+00:00,headache,3,reported,{intervention.id}\n",
            encoding="utf-8",
        )
        self.assertEqual(import_events_csv(self.conn, research, events)["imported"], 1)
        self.assertEqual(list_events(self.conn, research)[0].severity, 3)

        metrics = self.directory / "metrics.csv"
        metrics.write_text(
            "date,metric_name,value,note\n"
            "2026-01-02,weight,81.5,baseline\n",
            encoding="utf-8",
        )
        self.assertEqual(import_csv(self.conn, research, metrics, "metrics")["imported"], 1)
        for data_type, name in (
            ("metrics", "metrics-out.csv"),
            ("interventions", "interventions-out.csv"),
            ("events", "events-out.csv"),
        ):
            result = export_csv(self.conn, research, self.directory / name, data_type)
            self.assertEqual(result["rows"], 1)
            self.assertTrue((self.directory / name).is_file())

    def test_unknown_csv_type_is_refused(self) -> None:
        research = self.add_research()
        path = self.directory / "x.csv"
        path.write_text("a,b\n1,2\n", encoding="utf-8")
        with self.assertRaises(EngineError):
            import_csv(self.conn, research, path, "unknown")

    def test_html_report_writes_escape_safe_summary(self) -> None:
        research = self.add_research()
        intervention = add_intervention(self.conn, research, "Run <in>", "2026-01-01")
        for offset, value in enumerate((80.0, 80.2, 79.8)):
            add_metric(self.conn, research, "weight", f"2026-01-0{offset + 1}", value)
        for offset, value in enumerate((78.0, 78.2, 77.8)):
            add_metric(self.conn, research, "weight", f"2026-01-1{offset}", value)
        result = analyze_baseline_vs_intervention(
            self.conn, research, "weight", "2026-01-10", baseline_days=9, intervention_days=9
        )
        output = self.directory / "report.html"
        self.assertTrue(generate_html_report(result, output, intervention.name, "weight"))
        text = output.read_text(encoding="utf-8")
        self.assertIn("<html>", text)
        self.assertIn("Run &lt;in&gt;", text)
        self.assertIn("Welch", text)
        self.assertIn("Bootstrap", text)
