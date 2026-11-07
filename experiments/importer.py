"""CSV import for N1 experiment rows, using the host experiment model."""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path
from typing import Optional

from engine.errors import EngineError
from experiments.models import add_event, add_intervention, add_metric


def _rows(path: Path | str, required: set[str]) -> list[dict]:
    source = Path(path)
    if not source.is_file():
        raise EngineError(
            f"CSV file does not exist: {source}",
            "the importer reads a committed export or a user file.",
            "pass the path of an existing CSV file.",
        )
    with source.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = {name.strip().lower() for name in (reader.fieldnames or [])}
        if not required <= fields:
            raise EngineError(
                f"CSV is missing columns: {', '.join(sorted(required - fields))}",
                f"this import needs {', '.join(sorted(required))}.",
                "add the missing columns and retry.",
            )
        return list(reader)


def _result(imported: int, skipped: int, reasons: list[str]) -> dict:
    return {"imported": imported, "skipped": skipped, "reasons": reasons}


def import_metrics_csv(
    conn: sqlite3.Connection,
    research_ref: str,
    path: Path | str,
    intervention_ref: Optional[str] = None,
) -> dict:
    """Import ``date,metric_name,value[,note]`` rows; bad rows are counted, not fatal."""
    imported = 0
    skipped = 0
    reasons: list[str] = []
    for line_no, row in enumerate(_rows(path, {"date", "metric_name", "value"}), start=2):
        try:
            add_metric(
                conn,
                research_ref,
                str(row.get("metric_name") or ""),
                str(row.get("date") or ""),
                float(str(row.get("value") or "").strip()),
                intervention_ref=intervention_ref,
                note=str(row.get("note") or ""),
            )
        except (EngineError, TypeError, ValueError) as exc:
            skipped += 1
            if len(reasons) < 10:
                reasons.append(f"line {line_no}: {exc}")
        else:
            imported += 1
    return _result(imported, skipped, reasons)


def import_interventions_csv(
    conn: sqlite3.Connection,
    research_ref: str,
    path: Path | str,
) -> dict:
    """Import ``name,start_date[,projected_end_date,end_date,dosage,notes]`` rows."""
    imported = 0
    skipped = 0
    reasons: list[str] = []
    for line_no, row in enumerate(_rows(path, {"name", "start_date"}), start=2):
        try:
            add_intervention(
                conn,
                research_ref,
                str(row.get("name") or ""),
                str(row.get("start_date") or ""),
                projected_end_date=str(row.get("projected_end_date") or "").strip() or None,
                end_date=str(row.get("end_date") or "").strip() or None,
                dosage=str(row.get("dosage") or ""),
                notes=str(row.get("notes") or ""),
            )
        except (EngineError, TypeError, ValueError) as exc:
            skipped += 1
            if len(reasons) < 10:
                reasons.append(f"line {line_no}: {exc}")
        else:
            imported += 1
    return _result(imported, skipped, reasons)


def import_events_csv(
    conn: sqlite3.Connection,
    research_ref: str,
    path: Path | str,
) -> dict:
    """Import ``timestamp,event_name[,severity,notes,intervention_ref]`` rows."""
    imported = 0
    skipped = 0
    reasons: list[str] = []
    for line_no, row in enumerate(_rows(path, {"timestamp", "event_name"}), start=2):
        raw_severity = str(row.get("severity") or "").strip()
        intervention = str(row.get("intervention_ref") or "").strip() or None
        try:
            severity = int(raw_severity) if raw_severity else None
            add_event(
                conn,
                research_ref,
                str(row.get("event_name") or ""),
                str(row.get("timestamp") or ""),
                severity=severity,
                notes=str(row.get("notes") or ""),
                intervention_ref=intervention,
            )
        except (EngineError, TypeError, ValueError) as exc:
            skipped += 1
            if len(reasons) < 10:
                reasons.append(f"line {line_no}: {exc}")
        else:
            imported += 1
    return _result(imported, skipped, reasons)


def import_csv(
    conn: sqlite3.Connection,
    research_ref: str,
    path: Path | str,
    data_type: str = "metrics",
) -> dict:
    """Dispatch the source ``DataManager.import_from_csv`` data types."""
    kind = str(data_type).strip().lower()
    if kind == "metrics":
        return import_metrics_csv(conn, research_ref, path)
    if kind == "interventions":
        return import_interventions_csv(conn, research_ref, path)
    if kind == "events":
        return import_events_csv(conn, research_ref, path)
    raise EngineError(
        f"unknown CSV data type: {data_type!r}",
        "the source importer supports metrics, interventions and events.",
        "pass one of metrics, interventions or events.",
    )
