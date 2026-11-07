"""CSV export for N1 experiment rows, mirroring the import headers."""

from __future__ import annotations

import csv
import io
import sqlite3
from pathlib import Path

from engine.errors import EngineError
from experiments.models import list_events, list_interventions, list_metrics

METRIC_FIELDS = ["date", "metric_name", "value", "note"]
INTERVENTION_FIELDS = [
    "name",
    "start_date",
    "projected_end_date",
    "end_date",
    "dosage",
    "notes",
]
EVENT_FIELDS = ["timestamp", "event_name", "severity", "notes", "intervention_ref"]


def _write(path: Path | str, fields: list[str], rows: list[dict]) -> dict:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(buffer.getvalue(), encoding="utf-8")
    return {"rows": len(rows), "path": str(target)}


def export_metrics_csv(
    conn: sqlite3.Connection, research_ref: str, path: Path | str
) -> dict:
    rows = [
        {
            "date": row.date,
            "metric_name": row.metric_name,
            "value": row.value,
            "note": row.note,
        }
        for row in list_metrics(conn, research_ref)
    ]
    return _write(path, METRIC_FIELDS, rows)


def export_interventions_csv(
    conn: sqlite3.Connection, research_ref: str, path: Path | str
) -> dict:
    rows = [
        {
            "name": row.name,
            "start_date": row.start_date,
            "projected_end_date": row.projected_end_date or "",
            "end_date": row.end_date or "",
            "dosage": row.dosage,
            "notes": row.notes,
        }
        for row in list_interventions(conn, research_ref)
    ]
    return _write(path, INTERVENTION_FIELDS, rows)


def export_events_csv(
    conn: sqlite3.Connection, research_ref: str, path: Path | str
) -> dict:
    rows = [
        {
            "timestamp": row.timestamp,
            "event_name": row.event_name,
            "severity": "" if row.severity is None else row.severity,
            "notes": row.notes,
            "intervention_ref": row.intervention_id or "",
        }
        for row in list_events(conn, research_ref)
    ]
    return _write(path, EVENT_FIELDS, rows)


def export_csv(
    conn: sqlite3.Connection,
    research_ref: str,
    path: Path | str,
    data_type: str = "metrics",
) -> dict:
    """Dispatch the source ``DataManager.export_to_csv`` data types."""
    kind = str(data_type).strip().lower()
    if kind == "metrics":
        return export_metrics_csv(conn, research_ref, path)
    if kind == "interventions":
        return export_interventions_csv(conn, research_ref, path)
    if kind == "events":
        return export_events_csv(conn, research_ref, path)
    raise EngineError(
        f"unknown CSV data type: {data_type!r}",
        "the source exporter supports metrics, interventions and events.",
        "pass one of metrics, interventions or events.",
    )
