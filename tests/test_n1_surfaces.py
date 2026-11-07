"""N1 surfaces that were missing after the first merge: correlation, CSV, report."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from engine.errors import EngineError
from experiments.analysis import (
    analyze_baseline_vs_intervention,
    bootstrap_ci,
    calculate_trend,
    correlation_matrix,
)
from experiments.compat import AnalysisEngine, DataManager, ReportGenerator
from experiments.exporter import export_csv
from experiments.importer import import_csv, import_events_csv, import_interventions_csv
from experiments.models import (
    add_event,
    add_intervention,
    add_metric,
    add_metric_definition,
    close_intervention,
    delete_metric_definition,
    get_metric_definition,
    intervention_status,
    list_events,
    list_interventions,
    list_metrics,
    update_intervention,
    update_metric_definition,
)
from experiments.reporting import generate_html_report, save_report_json
from experiments.settings import SettingsManager
from experiments.summary import render_summary_html, summarize_period
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
            "date,metric_name,value,note,intervention_ref\n"
            f"2026-01-02,weight,81.5,baseline,{intervention.id}\n",
            encoding="utf-8",
        )
        self.assertEqual(import_csv(self.conn, research, metrics, "metrics")["imported"], 1)
        self.assertEqual(list_metrics(self.conn, research)[0].intervention_id, intervention.id)
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

    def test_out_of_range_severity_is_coerced_not_fatal(self) -> None:
        research = self.add_research()
        path = self.directory / "events.csv"
        path.write_text(
            "timestamp,event_name,severity\n"
            "2026-01-02T10:00:00+00:00,headache,9\n",
            encoding="utf-8",
        )
        result = import_events_csv(self.conn, research, path)
        self.assertTrue(result["success"])
        self.assertEqual(result["imported"], 1)
        self.assertIsNone(list_events(self.conn, research)[0].severity)

    def test_all_bad_rows_report_failure(self) -> None:
        research = self.add_research()
        path = self.directory / "bad.csv"
        path.write_text(
            "date,metric_name,value\nnot-a-date,weight,80.0\n",
            encoding="utf-8",
        )
        result = import_csv(self.conn, research, path, "metrics")
        self.assertFalse(result["success"])
        self.assertEqual(result["imported"], 0)
        self.assertEqual(result["skipped"], 1)

    def test_settings_round_trip_and_custom_minimum(self) -> None:
        settings_file = self.directory / "settings.json"
        settings = SettingsManager(settings_file)
        self.assertEqual(settings.get("min_data_points"), 3)
        settings.set("min_data_points", 2)
        self.assertTrue(settings.save_settings())
        self.assertEqual(SettingsManager(settings_file).get("min_data_points"), 2)

        research = self.add_research()
        for offset, value in enumerate((80.0, 80.2)):
            add_metric(self.conn, research, "weight", f"2026-01-0{offset + 1}", value)
        for offset, value in enumerate((78.0, 78.2)):
            add_metric(self.conn, research, "weight", f"2026-01-1{offset}", value)
        default_result = analyze_baseline_vs_intervention(
            self.conn, research, "weight", "2026-01-10", baseline_days=9, intervention_days=9
        )
        self.assertIn("error", default_result)
        custom_result = analyze_baseline_vs_intervention(
            self.conn,
            research,
            "weight",
            "2026-01-10",
            baseline_days=9,
            intervention_days=9,
            settings=settings,
        )
        self.assertIn("analysis", custom_result)
        self.assertEqual(custom_result["analysis"]["t_test"]["statistic"],
                         custom_result["analysis"]["t_test"]["t"])
        self.assertIn("lower", custom_result["analysis"]["bootstrap_ci"])

    def test_compatibility_names_cover_trend_bootstrap_and_data_manager(self) -> None:
        trend = calculate_trend([1.0, 2.0, 3.0, 4.0])
        self.assertGreater(trend["slope"], 0)
        self.assertLess(trend["p_value"], 0.05)
        engine = AnalysisEngine()
        self.assertEqual(engine.calculate_trend([1.0, 2.0, 3.0])["slope"], 1.0)

        interval = bootstrap_ci([80.0, 80.2, 79.8], [78.0, 78.2, 77.8], resamples=100)
        self.assertIn("lower", interval)
        self.assertIn("upper", interval)

        research = self.add_research()
        manager = DataManager(self.conn, research)
        path = self.directory / "manager.csv"
        path.write_text(
            "date,metric_name,value\n2026-01-02,weight,81.5\n", encoding="utf-8"
        )
        self.assertTrue(manager.import_from_csv(path, "metrics")["success"])
        exported = manager.export_to_csv(self.directory / "manager-out.csv", "metrics")
        self.assertEqual(exported["rows"], 1)
        self.assertTrue(ReportGenerator.generate_html_report(
            {"analysis": {}, "baseline_window": {}, "intervention_window": {}},
            self.directory / "compat.html",
            "I",
            "M",
        ))

    def test_intervention_edit_close_and_status(self) -> None:
        research = self.add_research()
        intervention = add_intervention(self.conn, research, "Run-in", "2026-01-01")
        updated = update_intervention(
            self.conn,
            research,
            intervention.id,
            "Sleep extension",
            "2026-01-02",
            projected_end_date="2026-02-01",
            notes="edited",
        )
        self.assertEqual(updated.name, "Sleep extension")
        self.assertEqual(intervention_status(updated, today="2026-01-15"),
                         "Ongoing (Projected end: 2026-02-01)")
        closed = close_intervention(self.conn, updated.id, end_date="2026-01-20")
        self.assertEqual(closed.end_date, "2026-01-20")
        self.assertEqual(intervention_status(closed, today="2026-01-21"),
                         "Ended 2026-01-20")
        with self.assertRaises(EngineError):
            close_intervention(self.conn, closed.id)

    def test_metric_definition_rename_updates_entries_and_delete(self) -> None:
        research = self.add_research()
        definition = add_metric_definition(self.conn, research, "weight", unit="kg")
        add_metric(self.conn, research, "weight", "2026-01-02", 81.5)
        renamed = update_metric_definition(
            self.conn, research, definition.id, name="body mass", unit="kg"
        )
        self.assertEqual(renamed.name, "body mass")
        self.assertEqual(list_metrics(self.conn, research)[0].metric_name, "body mass")
        delete_metric_definition(self.conn, definition.id)
        with self.assertRaises(Exception):
            get_metric_definition(self.conn, definition.id)

    def test_summary_period_and_html(self) -> None:
        research = self.add_research()
        intervention = add_intervention(self.conn, research, "Sleep", "2026-01-01")
        add_metric(self.conn, research, "weight", "2026-01-02", 81.5,
                   intervention_ref=intervention.id)
        add_metric(self.conn, research, "weight", "2026-02-01", 79.0,
                   intervention_ref=intervention.id)
        add_event(
            self.conn,
            research,
            "headache",
            "2026-01-02T10:00:00+00:00",
            severity=2,
            intervention_ref=intervention.id,
        )
        summary = summarize_period(
            self.conn,
            research,
            "2026-01-01",
            "2026-01-31",
            intervention_ref=intervention.id,
        )
        self.assertEqual(summary["intervention_name"], "Sleep")
        self.assertEqual(len(summary["metrics"]), 2)
        self.assertEqual(len(summary["events"]), 1)
        text = render_summary_html(summary)
        self.assertIn("Summary for Intervention: Sleep", text)
        self.assertIn("headache", text)

    def test_report_json_save(self) -> None:
        output = self.directory / "result.json"
        self.assertTrue(save_report_json({"a": 1, "when": "2026-01-01"}, output))
        self.assertIn('"a": 1', output.read_text(encoding="utf-8"))

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
