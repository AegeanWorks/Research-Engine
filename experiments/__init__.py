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
    list_events,
    list_interventions,
    list_metric_definitions,
    list_metrics,
)
from experiments.settings import SettingsManager

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
    "list_events",
    "list_interventions",
    "list_metric_definitions",
    "list_metrics",
    "analyze_baseline_vs_intervention",
    "analyze_multiple_metrics",
    "bootstrap_ci",
    "calculate_trend",
    "correlation_matrix",
]
