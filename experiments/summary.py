"""Daily/weekly N1 summary, extracted from the source SummarizerWidget."""

from __future__ import annotations

import html as html_lib
import sqlite3
from datetime import date

from engine.errors import EngineError
from engine.researches import get_research
from experiments.models import (
    get_intervention,
    intervention_status,
    list_events,
    list_interventions,
    list_metric_definitions,
    list_metrics,
)


def _date(value: str, field: str) -> str:
    try:
        return date.fromisoformat(str(value).strip()).isoformat()
    except ValueError as exc:
        raise EngineError(
            f"{field} is not an ISO date: {value!r}",
            "a summary window compares calendar dates exactly.",
            f"pass {field} as YYYY-MM-DD.",
        ) from exc


def summarize_period(
    conn: sqlite3.Connection,
    research_ref: str,
    start_date: str,
    end_date: str,
    intervention_ref: str | None = None,
) -> dict:
    """Collect interventions, metrics and events for a date range or one intervention."""
    research = get_research(conn, research_ref)
    start = _date(start_date, "start_date")
    end = _date(end_date, "end_date")
    if start > end:
        raise EngineError(
            "start_date is after end_date",
            "a summary window cannot run backwards.",
            "reverse the dates.",
        )
    selected_name = None
    units = {row.name: row.unit for row in list_metric_definitions(conn, research.id)}
    if intervention_ref:
        chosen = get_intervention(conn, intervention_ref)
        if chosen.research_id != research.id:
            raise EngineError(
                "intervention belongs to another research program",
                "a summary cannot cross a program boundary.",
                "use an intervention from this program.",
            )
        interventions = [chosen]
        selected_name = chosen.name
        metrics = list_metrics(conn, research.id, intervention_ref=chosen.id)
        events = [
            row for row in list_events(conn, research.id)
            if row.intervention_id == chosen.id
        ]
    else:
        interventions = [
            row
            for row in list_interventions(conn, research.id)
            if row.start_date <= end and (row.end_date is None or row.end_date >= start)
        ]
        metrics = [
            row for row in list_metrics(conn, research.id) if start <= row.date <= end
        ]
        events = [
            row for row in list_events(conn, research.id)
            if start <= row.timestamp[:10] <= end
        ]
    return {
        "start": start,
        "end": end,
        "intervention_name": selected_name,
        "interventions": [
            {
                "id": row.id,
                "name": row.name,
                "start_date": row.start_date,
                "end_date": row.end_date,
                "projected_end_date": row.projected_end_date,
                "status": intervention_status(row),
            }
            for row in interventions
        ],
        "metrics": [
            {
                "id": row.id,
                "date": row.date,
                "metric_name": row.metric_name,
                "value": row.value,
                "unit": units.get(row.metric_name, ""),
                "note": row.note,
            }
            for row in metrics
        ],
        "events": [
            {
                "id": row.id,
                "timestamp": row.timestamp,
                "event_name": row.event_name,
                "severity": row.severity,
                "notes": row.notes,
            }
            for row in events
        ],
    }


def render_summary_html(summary: dict) -> str:
    """Format a summary the way the source widget displayed it, with escaping."""
    if summary.get("intervention_name"):
        title = f"Summary for Intervention: {html_lib.escape(summary['intervention_name'])}"
        heading = "Intervention Details"
    else:
        title = f"Summary for {summary['start']} to {summary['end']}"
        heading = "Interventions in Period"
    parts = [f"<h1>{title}</h1>", f"<h3>{heading}</h3>"]
    if summary["interventions"]:
        parts.append("<ul>")
        for item in summary["interventions"]:
            parts.append(
                f"<li><b>{html_lib.escape(item['name'])}</b>"
                f" (Started: {item['start_date']}, Status: {html_lib.escape(item['status'])})</li>"
            )
        parts.append("</ul>")
    else:
        parts.append("<p>No active interventions in this period.</p>")
    parts.append("<h3>Logged Metrics</h3>")
    if summary["metrics"]:
        parts.append("<ul>")
        for item in summary["metrics"]:
            parts.append(
                f"<li>{item['date']}: <b>{html_lib.escape(item['metric_name'])}</b>"
                f" = {item['value']}</li>"
            )
        parts.append("</ul>")
    else:
        parts.append("<p>No metrics logged in this period.</p>")
    parts.append("<h3>Logged Events</h3>")
    if summary["events"]:
        parts.append("<ul>")
        for item in summary["events"]:
            parts.append(
                f"<li>{item['timestamp'][:16].replace('T', ' ')}:"
                f" <b>{html_lib.escape(item['event_name'])}</b>"
                f" (Severity: {item['severity']})</li>"
            )
        parts.append("</ul>")
    else:
        parts.append("<p>No events logged in this period.</p>")
    return "".join(parts)
