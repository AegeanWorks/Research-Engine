"""CSV import for N1 metric entries, using the host experiment model."""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path
from typing import Optional

from engine.errors import EngineError
from experiments.models import add_metric


def import_metrics_csv(
    conn: sqlite3.Connection,
    research_ref: str,
    path: Path | str,
    intervention_ref: Optional[str] = None,
) -> dict:
    """Import ``date,metric_name,value[,note]`` rows; bad rows are counted, not fatal."""
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
        required = {"date", "metric_name", "value"}
        if not required <= fields:
            raise EngineError(
                f"CSV is missing columns: {', '.join(sorted(required - fields))}",
                "metric import needs date, metric_name and value.",
                "add the missing columns and retry.",
            )
        imported = 0
        skipped = 0
        reasons: list[str] = []
        for line_no, row in enumerate(reader, start=2):
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
    return {"imported": imported, "skipped": skipped, "reasons": reasons}
