"""Append-only amendment ledger: every correction keeps its before and after."""

from __future__ import annotations

import sqlite3
from typing import List, Optional

from engine.artifacts import utc_now
from engine.database import next_id, transaction
from engine.errors import EngineError
from engine.models import Amendment


def _to_amendment(row: sqlite3.Row) -> Amendment:
    return Amendment(
        id=str(row["id"]),
        subject_kind=str(row["subject_kind"]),
        subject_id=str(row["subject_id"]),
        field=str(row["field"]),
        before=str(row["before_value"]),
        after=str(row["after_value"]),
        reason=str(row["reason"]),
        actor=str(row["actor"]),
        at=str(row["at"]),
    )


def record_amendment(
    conn: sqlite3.Connection,
    subject_kind: str,
    subject_id: str,
    field: str,
    before: str,
    after: str,
    reason: str,
    actor: str = "agent",
) -> Amendment:
    """Append one correction; the reason is mandatory and the past is kept."""
    reason = reason.strip()
    if not reason:
        raise EngineError(
            "amendment has no reason",
            "a correction without a stated reason cannot be audited.",
            "pass --reason naming the error being fixed.",
        )
    if before == after:
        raise EngineError(
            "amendment changes nothing",
            "the corrected value is identical to the recorded one.",
            "pass a different value, or leave the record alone.",
        )
    with transaction(conn):
        record = Amendment(
            id=next_id(conn, "am"),
            subject_kind=subject_kind.strip(),
            subject_id=subject_id.strip(),
            field=field.strip(),
            before=before,
            after=after,
            reason=reason,
            actor=actor,
            at=utc_now(),
        )
        conn.execute(
            "INSERT INTO amendment(id, subject_kind, subject_id, field, before_value,"
            " after_value, reason, actor, at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                record.id,
                record.subject_kind,
                record.subject_id,
                record.field,
                record.before,
                record.after,
                record.reason,
                record.actor,
                record.at,
            ),
        )
    return record


def list_amendments(
    conn: sqlite3.Connection,
    subject_kind: Optional[str] = None,
    subject_id: Optional[str] = None,
) -> List[Amendment]:
    """Amendments in record order, optionally filtered to one corrected record."""
    clauses: List[str] = []
    params: List[object] = []
    if subject_kind:
        clauses.append("subject_kind = ?")
        params.append(subject_kind.strip())
    if subject_id:
        clauses.append("subject_id = ?")
        params.append(subject_id.strip())
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = conn.execute(
        f"SELECT * FROM amendment{where} ORDER BY id", tuple(params)
    ).fetchall()
    return [_to_amendment(row) for row in rows]
