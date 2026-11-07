"""Experiment records: N1 interventions, metric definitions, measurements and events.

The records are stdlib-only host rows. They never import a domain pack and they keep the N1
semantics: an intervention is a dated episode, a metric definition names what was measured, a
metric entry is one dated value, and an event is a dated observation with a bounded severity.
"""

from __future__ import annotations

import math
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime
from typing import List, Optional

from engine.artifacts import utc_now
from engine.database import next_id, transaction
from engine.errors import EngineError, NotFound
from engine.researches import get_research

MAX_SAFE_METRICS = 3
MIN_BASELINE_DAYS = 7
MIN_INTERVENTION_DAYS = 7
MIN_DATA_POINTS = 3


@dataclass(frozen=True)
class Intervention:
    id: str
    research_id: str
    name: str
    start_date: str
    projected_end_date: Optional[str]
    end_date: Optional[str]
    dosage: str
    notes: str
    created_at: str


@dataclass(frozen=True)
class MetricDefinition:
    id: str
    research_id: str
    name: str
    description: str
    unit: str
    created_at: str


@dataclass(frozen=True)
class MetricEntry:
    id: str
    research_id: str
    intervention_id: Optional[str]
    metric_name: str
    date: str
    value: float
    note: str
    created_at: str


@dataclass(frozen=True)
class EventEntry:
    id: str
    research_id: str
    intervention_id: Optional[str]
    timestamp: str
    event_name: str
    severity: Optional[int]
    notes: str
    created_at: str


def _date(value: str, field: str) -> str:
    text = str(value).strip()
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError as exc:
        raise EngineError(
            f"{field} is not an ISO date: {value!r}",
            "experiment windows compare calendar dates exactly.",
            f"pass {field} as YYYY-MM-DD.",
        ) from exc


def _timestamp(value: str) -> str:
    text = str(value).strip()
    try:
        datetime.fromisoformat(text)
    except ValueError as exc:
        raise EngineError(
            f"timestamp is not ISO-8601: {value!r}",
            "an event needs an exact time so its order is auditable.",
            "pass an ISO-8601 timestamp such as 2026-01-01T09:00:00+00:00.",
        ) from exc
    return text


def _finite(value: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise EngineError(
            f"metric value is not a number: {value!r}",
            "a measurement must be numeric.",
            "pass a finite number.",
        ) from exc
    if not math.isfinite(number):
        raise EngineError(
            f"metric value is not finite: {value!r}",
            "NaN and infinity cannot be compared or summarised.",
            "record the measurement as a finite number.",
        )
    return number


def _intervention(conn: sqlite3.Connection, research_id: str, ref: Optional[str]) -> Optional[str]:
    if ref is None or not str(ref).strip():
        return None
    row = conn.execute(
        "SELECT id, research_id FROM experiment_intervention WHERE id = ?", (str(ref),)
    ).fetchone()
    if row is None:
        raise NotFound("intervention", ref)
    if row["research_id"] != research_id:
        raise EngineError(
            "intervention belongs to another research program",
            "an experiment record cannot cross a program boundary.",
            "use the intervention from this program, or record it in its own program.",
        )
    return row["id"]


def add_intervention(
    conn: sqlite3.Connection,
    research_ref: str,
    name: str,
    start_date: str,
    projected_end_date: Optional[str] = None,
    end_date: Optional[str] = None,
    dosage: str = "",
    notes: str = "",
) -> Intervention:
    research = get_research(conn, research_ref)
    name = str(name).strip()
    if not name:
        raise EngineError(
            "intervention name is empty",
            "an intervention needs a stable name.",
            "pass the intervention name.",
        )
    start = _date(start_date, "start_date")
    projected = _date(projected_end_date, "projected_end_date") if projected_end_date else None
    ended = _date(end_date, "end_date") if end_date else None
    if projected and projected < start:
        raise EngineError(
            "projected_end_date precedes start_date",
            "an intervention cannot end before it starts.",
            "correct the dates.",
        )
    if ended and ended < start:
        raise EngineError(
            "end_date precedes start_date",
            "an intervention cannot end before it starts.",
            "correct the dates.",
        )
    with transaction(conn):
        record = Intervention(
            id=next_id(conn, "iv"),
            research_id=research.id,
            name=name,
            start_date=start,
            projected_end_date=projected,
            end_date=ended,
            dosage=str(dosage).strip(),
            notes=str(notes).strip(),
            created_at=utc_now(),
        )
        conn.execute(
            "INSERT INTO experiment_intervention(id, research_id, name, start_date,"
            " projected_end_date, end_date, dosage, notes, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                record.id,
                record.research_id,
                record.name,
                record.start_date,
                record.projected_end_date,
                record.end_date,
                record.dosage,
                record.notes,
                record.created_at,
            ),
        )
    return record


def add_metric_definition(
    conn: sqlite3.Connection,
    research_ref: str,
    name: str,
    description: str = "",
    unit: str = "",
) -> MetricDefinition:
    research = get_research(conn, research_ref)
    name = str(name).strip()
    if not name:
        raise EngineError(
            "metric name is empty",
            "a metric definition needs a stable name.",
            "pass the metric name.",
        )
    with transaction(conn):
        record = MetricDefinition(
            id=next_id(conn, "md"),
            research_id=research.id,
            name=name,
            description=str(description).strip(),
            unit=str(unit).strip(),
            created_at=utc_now(),
        )
        try:
            conn.execute(
                "INSERT INTO experiment_metric_definition(id, research_id, name, description,"
                " unit, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    record.id,
                    record.research_id,
                    record.name,
                    record.description,
                    record.unit,
                    record.created_at,
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise EngineError(
                f"metric already defined in this program: {name}",
                "one metric name has one definition per program.",
                "reuse the existing definition, or choose a distinct name.",
            ) from exc
    return record


def add_metric(
    conn: sqlite3.Connection,
    research_ref: str,
    metric_name: str,
    date_value: str,
    value: float,
    intervention_ref: Optional[str] = None,
    note: str = "",
) -> MetricEntry:
    research = get_research(conn, research_ref)
    metric_name = str(metric_name).strip()
    if not metric_name:
        raise EngineError(
            "metric name is empty",
            "a measurement needs the metric it belongs to.",
            "pass the metric name.",
        )
    intervention_id = _intervention(conn, research.id, intervention_ref)
    measured = _date(date_value, "date")
    number = _finite(value)
    with transaction(conn):
        record = MetricEntry(
            id=next_id(conn, "me"),
            research_id=research.id,
            intervention_id=intervention_id,
            metric_name=metric_name,
            date=measured,
            value=number,
            note=str(note).strip(),
            created_at=utc_now(),
        )
        conn.execute(
            "INSERT INTO experiment_metric(id, research_id, intervention_id, metric_name,"
            " date, value, note, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                record.id,
                record.research_id,
                record.intervention_id,
                record.metric_name,
                record.date,
                record.value,
                record.note,
                record.created_at,
            ),
        )
    return record


def add_event(
    conn: sqlite3.Connection,
    research_ref: str,
    event_name: str,
    timestamp: str,
    severity: Optional[int] = None,
    notes: str = "",
    intervention_ref: Optional[str] = None,
) -> EventEntry:
    research = get_research(conn, research_ref)
    event_name = str(event_name).strip()
    if not event_name:
        raise EngineError(
            "event name is empty",
            "an event needs a stable name.",
            "pass the event name.",
        )
    if severity is not None:
        if type(severity) is not int or not 1 <= severity <= 5:
            raise EngineError(
                f"event severity out of range: {severity!r}",
                "severity is an integer from 1 (mild) to 5 (severe).",
                "pass a severity between 1 and 5, or omit it.",
            )
    with transaction(conn):
        record = EventEntry(
            id=next_id(conn, "ee"),
            research_id=research.id,
            intervention_id=_intervention(conn, research.id, intervention_ref),
            timestamp=_timestamp(timestamp),
            event_name=event_name,
            severity=severity,
            notes=str(notes).strip(),
            created_at=utc_now(),
        )
        conn.execute(
            "INSERT INTO experiment_event(id, research_id, intervention_id, timestamp,"
            " event_name, severity, notes, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                record.id,
                record.research_id,
                record.intervention_id,
                record.timestamp,
                record.event_name,
                record.severity,
                record.notes,
                record.created_at,
            ),
        )
    return record


def _rows(conn: sqlite3.Connection, sql: str, params: tuple) -> list:
    return conn.execute(sql, params).fetchall()


def list_interventions(
    conn: sqlite3.Connection, research_ref: str | None = None
) -> List[Intervention]:
    if research_ref:
        research = get_research(conn, research_ref)
        rows = _rows(
            conn,
            "SELECT * FROM experiment_intervention WHERE research_id = ? ORDER BY start_date, id",
            (research.id,),
        )
    else:
        rows = _rows(conn, "SELECT * FROM experiment_intervention ORDER BY start_date, id", ())
    return [Intervention(**{key: row[key] for key in Intervention.__dataclass_fields__}) for row in rows]


def list_metric_definitions(
    conn: sqlite3.Connection, research_ref: str | None = None
) -> List[MetricDefinition]:
    if research_ref:
        research = get_research(conn, research_ref)
        rows = _rows(
            conn,
            "SELECT * FROM experiment_metric_definition WHERE research_id = ? ORDER BY name",
            (research.id,),
        )
    else:
        rows = _rows(conn, "SELECT * FROM experiment_metric_definition ORDER BY name", ())
    return [MetricDefinition(**{key: row[key] for key in MetricDefinition.__dataclass_fields__}) for row in rows]


def list_metrics(
    conn: sqlite3.Connection,
    research_ref: str | None = None,
    metric_name: str | None = None,
    intervention_ref: str | None = None,
) -> List[MetricEntry]:
    clauses: list[str] = []
    params: list[object] = []
    if research_ref:
        research = get_research(conn, research_ref)
        clauses.append("research_id = ?")
        params.append(research.id)
    if metric_name:
        clauses.append("metric_name = ?")
        params.append(metric_name)
    if intervention_ref:
        clauses.append("intervention_id = ?")
        params.append(intervention_ref)
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = _rows(conn, f"SELECT * FROM experiment_metric{where} ORDER BY date, id", tuple(params))
    return [MetricEntry(**{key: row[key] for key in MetricEntry.__dataclass_fields__}) for row in rows]


def list_events(
    conn: sqlite3.Connection, research_ref: str | None = None
) -> List[EventEntry]:
    if research_ref:
        research = get_research(conn, research_ref)
        rows = _rows(
            conn,
            "SELECT * FROM experiment_event WHERE research_id = ? ORDER BY timestamp, id",
            (research.id,),
        )
    else:
        rows = _rows(conn, "SELECT * FROM experiment_event ORDER BY timestamp, id", ())
    return [EventEntry(**{key: row[key] for key in EventEntry.__dataclass_fields__}) for row in rows]


def get_intervention(conn: sqlite3.Connection, ref: str) -> Intervention:
    row = conn.execute(
        "SELECT * FROM experiment_intervention WHERE id = ?", (str(ref),)
    ).fetchone()
    if row is None:
        raise NotFound("intervention", ref)
    return Intervention(**{key: row[key] for key in Intervention.__dataclass_fields__})


def get_metric_definition(conn: sqlite3.Connection, ref: str) -> MetricDefinition:
    row = conn.execute(
        "SELECT * FROM experiment_metric_definition WHERE id = ?", (str(ref),)
    ).fetchone()
    if row is None:
        raise NotFound("metric definition", ref)
    return MetricDefinition(**{key: row[key] for key in MetricDefinition.__dataclass_fields__})


def update_intervention(
    conn: sqlite3.Connection,
    research_ref: str,
    ref: str,
    name: str,
    start_date: str,
    projected_end_date: Optional[str] = None,
    end_date: Optional[str] = None,
    dosage: str = "",
    notes: str = "",
) -> Intervention:
    """Replace an intervention's editable fields; the source dialog's edit path."""
    research = get_research(conn, research_ref)
    record = get_intervention(conn, ref)
    if record.research_id != research.id:
        raise EngineError(
            "intervention belongs to another research program",
            "an edit cannot cross a program boundary.",
            "edit the intervention from the program that owns it.",
        )
    name = str(name).strip()
    if not name:
        raise EngineError(
            "intervention name is empty",
            "an intervention needs a stable name.",
            "pass the intervention name.",
        )
    start = _date(start_date, "start_date")
    projected = _date(projected_end_date, "projected_end_date") if projected_end_date else None
    ended = _date(end_date, "end_date") if end_date else None
    for value, field in ((projected, "projected_end_date"), (ended, "end_date")):
        if value is not None and value < start:
            raise EngineError(
                f"{field} precedes start_date",
                "an intervention cannot end before it starts.",
                "correct the dates.",
            )
    with transaction(conn):
        conn.execute(
            "UPDATE experiment_intervention SET name = ?, start_date = ?,"
            " projected_end_date = ?, end_date = ?, dosage = ?, notes = ? WHERE id = ?",
            (
                name,
                start,
                projected,
                ended,
                str(dosage).strip(),
                str(notes).strip(),
                record.id,
            ),
        )
    return get_intervention(conn, record.id)


def close_intervention(
    conn: sqlite3.Connection, ref: str, end_date: Optional[str] = None
) -> Intervention:
    """Close an open intervention, defaulting to today like the source GUI."""
    record = get_intervention(conn, ref)
    if record.end_date:
        raise EngineError(
            f"intervention already closed on {record.end_date}",
            "closing twice would hide the real end date.",
            "edit the intervention if the end date is wrong.",
        )
    ended = _date(end_date, "end_date") if end_date else date.today().isoformat()
    if ended < record.start_date:
        raise EngineError(
            "end_date precedes start_date",
            "an intervention cannot end before it starts.",
            "pass a later end date.",
        )
    with transaction(conn):
        conn.execute(
            "UPDATE experiment_intervention SET end_date = ? WHERE id = ?",
            (ended, record.id),
        )
    return get_intervention(conn, record.id)


def intervention_status(record: Intervention, today: Optional[str] = None) -> str:
    """Return the source GUI's display status for one intervention."""
    current = today or date.today().isoformat()
    if record.end_date and record.end_date <= current:
        return f"Ended {record.end_date}"
    if record.projected_end_date:
        return f"Ongoing (Projected end: {record.projected_end_date})"
    return "Ongoing"


def update_metric_definition(
    conn: sqlite3.Connection,
    research_ref: str,
    ref: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    unit: Optional[str] = None,
) -> MetricDefinition:
    """Edit a metric definition and rename its existing entries in one transaction."""
    research = get_research(conn, research_ref)
    record = get_metric_definition(conn, ref)
    if record.research_id != research.id:
        raise EngineError(
            "metric definition belongs to another research program",
            "an edit cannot cross a program boundary.",
            "edit the definition from the program that owns it.",
        )
    new_name = str(name).strip() if name is not None else record.name
    if not new_name:
        raise EngineError(
            "metric name is empty",
            "a metric definition needs a stable name.",
            "pass the metric name.",
        )
    with transaction(conn):
        try:
            if new_name != record.name:
                conn.execute(
                    "UPDATE experiment_metric SET metric_name = ?"
                    " WHERE research_id = ? AND metric_name = ?",
                    (new_name, research.id, record.name),
                )
            conn.execute(
                "UPDATE experiment_metric_definition SET name = ?, description = ?, unit = ?"
                " WHERE id = ?",
                (
                    new_name,
                    record.description if description is None else str(description).strip(),
                    record.unit if unit is None else str(unit).strip(),
                    record.id,
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise EngineError(
                f"metric already defined in this program: {new_name}",
                "one metric name has one definition per program.",
                "choose a distinct name.",
            ) from exc
    return get_metric_definition(conn, record.id)


def delete_metric_definition(conn: sqlite3.Connection, ref: str) -> None:
    """Delete a metric definition; recorded metric entries keep their name."""
    record = get_metric_definition(conn, ref)
    with transaction(conn):
        conn.execute("DELETE FROM experiment_metric_definition WHERE id = ?", (record.id,))
