"""N1 experiment records and baseline-vs-intervention analysis."""

from experiments.analysis import (
    analyze_baseline_vs_intervention,
    analyze_multiple_metrics,
    bootstrap_ci,
    calculate_trend,
    correlation_matrix,
)
from experiments.models import (
    EventEntry,
    Intervention,
    MetricDefinition,
    MetricEntry,
    add_event,
    add_intervention,
    add_metric,
    add_metric_definition,
    close_intervention,
    delete_metric_definition,
    get_intervention,
    get_metric_definition,
    intervention_status,
    list_events,
    list_interventions,
    list_metric_definitions,
    list_metrics,
    update_intervention,
    update_metric_definition,
)
from experiments.settings import SettingsManager
from experiments.reporting import generate_html_report, save_report_json
from experiments.summary import render_summary_html, summarize_period

__all__ = [
    "EventEntry",
    "Intervention",
    "MetricDefinition",
    "MetricEntry",
    "SettingsManager",
    "add_event",
    "add_intervention",
    "add_metric",
    "add_metric_definition",
    "close_intervention",
    "delete_metric_definition",
    "get_intervention",
    "get_metric_definition",
    "intervention_status",
    "list_events",
    "list_interventions",
    "list_metric_definitions",
    "list_metrics",
    "update_intervention",
    "update_metric_definition",
    "render_summary_html",
    "save_report_json",
    "summarize_period",
    "analyze_baseline_vs_intervention",
    "analyze_multiple_metrics",
    "bootstrap_ci",
    "calculate_trend",
    "correlation_matrix",
]
