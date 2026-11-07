"""HTML report generation for N1 baseline-vs-intervention results."""

from __future__ import annotations

import html as html_lib
from pathlib import Path
from typing import Any, Dict


def _number(value, digits: int = 2) -> str:
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return "N/A"


def generate_html_report(
    results: Dict[str, Any],
    filepath: str | Path,
    intervention_name: str,
    metric_name: str,
) -> bool:
    """Write the source-style HTML report and return whether it was written."""
    intervention = html_lib.escape(str(intervention_name))
    metric = html_lib.escape(str(metric_name))
    analysis = results.get("analysis", {}) if isinstance(results, dict) else {}
    baseline = results.get("baseline_window", {})
    intervention_window = results.get("intervention_window", {})
    t_test = analysis.get("t_test", {}) or {}
    u_test = analysis.get("mann_whitney_u", {}) or {}
    ci = analysis.get("bootstrap_ci", {}) or {}
    warnings = list(results.get("warnings", [])) + list(analysis.get("warnings", []))
    t_stat = t_test.get("t", t_test.get("statistic"))
    u_stat = u_test.get("u", u_test.get("statistic"))
    ci_low = ci.get("low", ci.get("lower"))
    ci_high = ci.get("high", ci.get("upper"))
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Analysis Report: {intervention}</title>
    <style>
        body {{ font-family: sans-serif; margin: 20px; }}
        h1, h2, h3 {{ color: #333; }}
        .section {{ margin-bottom: 20px; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
        .warning {{ color: #d9534f; font-weight: bold; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <h1>Analysis Report</h1>
    <h2>Intervention: {intervention}</h2>
    <h3>Metric: {metric}</h3>
    <div class="section">
        <h3>Overview</h3>
        <p><b>Mean Difference:</b> {_number(analysis.get('mean_difference'))}</p>
        <p><b>Cohen's d:</b> {_number(analysis.get('cohens_d'))}</p>
        <p><b>Bootstrap 95% CI:</b> [{_number(ci_low)}, {_number(ci_high)}]</p>
    </div>
    <div class="section">
        <h3>Statistical Tests</h3>
        <table>
            <tr><th>Test</th><th>Statistic</th><th>p-value</th></tr>
            <tr><td>Welch's t-test</td><td>{_number(t_stat)}</td><td>{_number(t_test.get('p_value'), 4)}</td></tr>
            <tr><td>Mann-Whitney U</td><td>{_number(u_stat)}</td><td>{_number(u_test.get('p_value'), 4)}</td></tr>
        </table>
    </div>
    <div class="section">
        <h3>Windows</h3>
        <table>
            <tr><th>Period</th><th>Dates</th><th>Count</th><th>Mean</th><th>Std Dev</th></tr>
            <tr><td>Baseline</td><td>{baseline.get('start')} to {baseline.get('end')}</td>
                <td>{baseline.get('count', 0)}</td><td>{_number(baseline.get('mean'))}</td>
                <td>{_number(baseline.get('sd', baseline.get('std')))}</td></tr>
            <tr><td>Intervention</td><td>{intervention_window.get('start')} to {intervention_window.get('end')}</td>
                <td>{intervention_window.get('count', 0)}</td><td>{_number(intervention_window.get('mean'))}</td>
                <td>{_number(intervention_window.get('sd', intervention_window.get('std')))}</td></tr>
        </table>
    </div>
"""
    if warnings:
        html += "    <div class=\"section\">\n        <h3>Warnings</h3>\n        <ul>\n"
        html += "".join(f"            <li class='warning'>{html_lib.escape(str(item))}</li>\n" for item in warnings)
        html += "        </ul>\n    </div>\n"
    html += "</body>\n</html>\n"
    target = Path(filepath)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(html, encoding="utf-8")
    return True
