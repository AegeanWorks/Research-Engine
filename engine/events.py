"""Append-only event log for actions that are not verdicts.

Verdicts and invalidations already record themselves. Everything else that changes the meaning of
the record — a source losing its status, a duplicate being merged, a report being generated, a
schema being migrated — needs one place a reviewer can scan in order.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import List, Optional

from engine.artifacts import utc_now
from engine.database import next_id, transaction


@dataclass(frozen=True)
class Event:
    id: str
    at: str
    research_id: str
    kind: str
    subject: str
    detail: str
    actor: str


def _to_event(row: sqlite3.Row) -> Event:
    return Event(**{key: row[key] for key in Event.__dataclass_fields__})


def record(
    conn: sqlite3.Connection,
    kind: str,
    subject: str,
    detail: str = "",
    research_id: str = "",
    actor: str = "agent",
) -> Event:
    """Append one event. Callers run inside their own write transaction."""
    with transaction(conn):
        event = Event(
            id=next_id(conn, "ev"),
            at=utc_now(),
            research_id=research_id,
            kind=kind.strip(),
            subject=subject.strip(),
            detail="".join(
                character if character.isprintable() or character == " " else " "
                for character in detail
            ).strip()[:2000],
            actor=actor,
        )
        conn.execute(
            "INSERT INTO event(id, at, research_id, kind, subject, detail, actor)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                event.id,
                event.at,
                event.research_id,
                event.kind,
                event.subject,
                event.detail,
                event.actor,
            ),
        )
    return event


def list_events(
    conn: sqlite3.Connection,
    research_ref: Optional[str] = None,
    kind: Optional[str] = None,
    limit: int = 50,
) -> List[Event]:
    """Recent events, newest first, optionally filtered by program and kind."""
    from engine.researches import get_research

    clauses: List[str] = []
    params: List[object] = []
    if research_ref:
        clauses.append("research_id = ?")
        params.append(get_research(conn, research_ref).id)
    if kind:
        clauses.append("kind = ?")
        params.append(kind.strip())
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = conn.execute(
        f"SELECT * FROM event{where} ORDER BY id DESC LIMIT ?", (*params, max(int(limit), 1))
    ).fetchall()
    return [_to_event(row) for row in rows]


def count(conn: sqlite3.Connection) -> int:
    """Total recorded events."""
    return int(conn.execute("SELECT COUNT(*) AS n FROM event").fetchone()["n"])
