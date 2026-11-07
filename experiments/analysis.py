"""Baseline-vs-intervention analysis for N1 experiment records.

The module reads host experiment rows, splits them at the declared intervention start into a
baseline and a treatment window, and delegates the inference to :mod:`engine.stats`. It never
imports a domain pack: the N1 behaviour is part of the host experiment module.
"""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from statistics import mean
from typing import Dict, List, Optional, Sequence, Tuple

from engine import stats
from engine.errors import EngineError
from experiments.models import (
    MAX_SAFE_METRICS,
    MIN_BASELINE_DAYS,
    MIN_DATA_POINTS,
    MIN_INTERVENTION_DAYS,
    list_metrics,
)

def _start_date(value: str) -> date:
    try:
        return date.fromisoformat(str(value).strip())
    except ValueError as exc:
        raise EngineError(
            f"intervention start is not an ISO date: {value!r}",
            "analysis windows are calendar-date ranges.",
            "pass the start date as YYYY-MM-DD.",
        ) from exc


def _days(value: int, field: str) -> int:
    if type(value) is not int or value < 1:
        raise EngineError(
            f"{field} must be a positive integer: {value!r}",
            "a window needs at least one calendar day.",
            f"pass {field} as an integer of one or more days.",
        )
    return value


def _summary(rows: Sequence) -> dict:
    values = [float(row.value) for row in rows]
    days = [row.date for row in rows]
    return {
        "start": min(days) if days else None,
        "end": max(days) if days else None,
        "count": len(values),
        "mean": mean(values) if values else 0.0,
        "sd": stats.sample_sd(values),
    }


def _trend(rows: Sequence) -> dict:
    values = [float(row.value) for row in rows]
    xs = [date.fromisoformat(row.date).toordinal() for row in rows]
    result = stats.linregress(xs, values)
    return {"slope": result["slope"], "r": result["r"], "p_value": result["p"]}


def _window_warnings(
    baseline: Sequence,
    intervention: Sequence,
    baseline_days: int,
    intervention_days: int,
) -> List[str]:
    warnings: List[str] = []
    baseline_span = len({row.date for row in baseline})
    intervention_span = len({row.date for row in intervention})
    if baseline_span < MIN_BASELINE_DAYS:
        warnings.append(
            f"Insufficient baseline duration: {baseline_span} days"
            f" (recommended >= {MIN_BASELINE_DAYS})"
        )
    if intervention_span < MIN_INTERVENTION_DAYS:
        warnings.append(
            f"Insufficient intervention duration: {intervention_span} days"
            f" (recommended >= {MIN_INTERVENTION_DAYS})"
        )
    if intervention_days < baseline_days:
        warnings.append(
            f"Intervention duration ({intervention_days} days) is shorter than baseline"
            f" ({baseline_days} days). Power may be reduced."
        )
    if not baseline or not intervention:
        warnings.append("a window has no observations")
    if baseline and intervention:
        both_flat = stats.sample_sd([float(row.value) for row in baseline]) == 0
        both_flat = both_flat and stats.sample_sd(
            [float(row.value) for row in intervention]
        ) == 0
        if both_flat:
            warnings.append("Zero variance in both baseline and intervention data.")
    return warnings


def analyze_baseline_vs_intervention(
    conn: sqlite3.Connection,
    research_ref: str,
    metric_name: str,
    start_date: str,
    baseline_days: int = 14,
    intervention_days: int = 14,
) -> dict:
    """Compare one metric before and after the declared intervention start.

    The baseline window is ``[start - baseline_days, start)``; the intervention window is
    ``[start, start + intervention_days)``. Fewer than ``MIN_DATA_POINTS`` observations in either
    window is reported as counts, not raised: a sparse record is a finding, not a crash.
    """
    metric_name = str(metric_name).strip()
    if not metric_name:
        raise EngineError(
            "metric name is empty",
            "an analysis needs the metric it compares.",
            "pass the metric name.",
        )
    start = _start_date(start_date)
    baseline_days = _days(baseline_days, "baseline_days")
    intervention_days = _days(intervention_days, "intervention_days")
    baseline_start = start - timedelta(days=baseline_days)
    intervention_end = start + timedelta(days=intervention_days)

    rows = list_metrics(conn, research_ref, metric_name=metric_name)
    baseline = [
        row for row in rows
        if baseline_start <= date.fromisoformat(row.date) < start
    ]
    intervention = [
        row for row in rows
        if start <= date.fromisoformat(row.date) < intervention_end
    ]
    if len(baseline) < MIN_DATA_POINTS or len(intervention) < MIN_DATA_POINTS:
        return {
            "error": f"Insufficient data points (minimum {MIN_DATA_POINTS} required)",
            "metric": metric_name,
            "baseline_count": len(baseline),
            "intervention_count": len(intervention),
            "baseline_window": {
                "start": baseline_start.isoformat(),
                "end": start.isoformat(),
            },
            "intervention_window": {
                "start": start.isoformat(),
                "end": intervention_end.isoformat(),
            },
        }

    baseline_values = [float(row.value) for row in baseline]
    intervention_values = [float(row.value) for row in intervention]
    compared = stats.compare_groups(baseline_values, intervention_values)
    warnings = _window_warnings(
        baseline, intervention, baseline_days, intervention_days
    )
    warnings.extend(compared["warnings"])
    return {
        "metric": metric_name,
        "baseline_window": {
            "start": baseline_start.isoformat(),
            "end": start.isoformat(),
            **_summary(baseline),
        },
        "intervention_window": {
            "start": start.isoformat(),
            "end": intervention_end.isoformat(),
            **_summary(intervention),
        },
        "analysis": {
            "mean_difference": compared["difference"],
            "cohens_d": compared["cohens_d"],
            "t_test": {
                "t": compared["welch"]["t"],
                "df": compared["welch"]["df"],
                "p_value": compared["welch"]["p"],
            },
            "mann_whitney_u": {
                "u": compared["mann_whitney"]["u"],
                "z": compared["mann_whitney"]["z"],
                "p_value": compared["mann_whitney"]["p"],
                "method": compared["mann_whitney"]["method"],
            },
            "bootstrap_ci": compared["bootstrap"],
            "baseline_trend": _trend(baseline),
            "intervention_trend": _trend(intervention),
            "alpha": compared["alpha"],
            "tests_agree": compared["tests_agree"],
            "significant": compared["significant"],
            "warnings": warnings,
        },
    }


def correlation_matrix(
    conn: sqlite3.Connection,
    research_ref: str,
    metric_names: Optional[Sequence[str]] = None,
) -> dict:
    """Pairwise Pearson correlation for metrics observed on the same dates.

    A date with repeated values is averaged, mirroring the source pivot table. A pair with fewer
    than three shared dates reports ``r=0.0`` and its actual ``n``, never a fabricated value.
    """
    rows = list_metrics(conn, research_ref)
    available = sorted({row.metric_name for row in rows})
    if metric_names:
        selected = [str(name).strip() for name in metric_names if str(name).strip()]
        unknown = sorted(set(selected) - set(available))
        if unknown:
            raise EngineError(
                f"unknown metrics: {', '.join(unknown)}",
                "a correlation needs recorded metrics.",
                "use a metric name from this program, or record it first.",
            )
        metrics = list(dict.fromkeys(selected))
    else:
        metrics = available
    by_metric: Dict[str, Dict[str, float]] = {name: {} for name in metrics}
    totals: Dict[Tuple[str, str], list] = {}
    for row in rows:
        if row.metric_name not in by_metric:
            continue
        totals.setdefault((row.metric_name, row.date), []).append(float(row.value))
    for (name, day), values in totals.items():
        by_metric[name][day] = mean(values)
    matrix: Dict[str, Dict[str, dict]] = {}
    for left in metrics:
        matrix[left] = {}
        for right in metrics:
            shared = sorted(set(by_metric[left]) & set(by_metric[right]))
            pairs = [(by_metric[left][day], by_metric[right][day]) for day in shared]
            result = stats.pearson([pair[0] for pair in pairs], [pair[1] for pair in pairs])
            matrix[left][right] = {"r": result["r"], "n": result["n"]}
    return {"metrics": metrics, "matrix": matrix}


def analyze_multiple_metrics(
    conn: sqlite3.Connection,
    research_ref: str,
    metric_names: Sequence[str],
    start_date: str,
    baseline_days: int = 14,
    intervention_days: int = 14,
) -> dict:
    """Analyze several metrics and report the multiple-comparison risk as a global warning."""
    names = [str(name).strip() for name in metric_names if str(name).strip()]
    if not names:
        raise EngineError(
            "no metrics selected",
            "a multi-metric analysis needs at least one metric.",
            "pass one or more metric names.",
        )
    if len(set(names)) != len(names):
        raise EngineError(
            "duplicate metric selected",
            "each metric is analyzed once per request.",
            "remove the duplicate metric name.",
        )
    results: Dict[str, dict] = {}
    for name in names:
        results[name] = analyze_baseline_vs_intervention(
            conn,
            research_ref,
            name,
            start_date,
            baseline_days=baseline_days,
            intervention_days=intervention_days,
        )
    global_warnings: List[str] = []
    if len(names) > MAX_SAFE_METRICS:
        global_warnings.append(
            f"Multiple Comparison Risk: {len(names)} metrics exceed the safe limit of"
            f" {MAX_SAFE_METRICS}; treat isolated significant results as exploratory."
        )
    p_values: List[float] = []
    for name in names:
        analysis = results[name].get("analysis")
        if analysis:
            p_values.append(float(analysis["t_test"]["p_value"]))
    adjusted: Optional[List[dict]] = None
    if p_values:
        adjusted = stats.holm_adjust(p_values)
    return {
        "metrics": names,
        "results": results,
        "global_warnings": global_warnings,
        "holm_adjustment": adjusted,
    }
