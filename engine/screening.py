"""Source screening and the PRISMA flow.

A source is identified, then screened in or out, then included or excluded from the synthesis. The
reason is part of the record: an exclusion without a reason is indistinguishable from an oversight.
"""

from __future__ import annotations

import sqlite3
from typing import Dict, List, Optional

from engine.artifacts import utc_now
from engine.database import transaction
from engine.errors import EngineError
from engine.events import record as record_event
from engine.models import SCREENING_REASONS, SCREENING_STATUSES, Source
from engine.researches import get_research
from engine.sources import get_source

TERMINAL_OUT = ("screened_out", "excluded")


def set_screening(
    conn: sqlite3.Connection,
    ref: str,
    status: str,
    reason: str = "",
    actor: str = "agent",
) -> Source:
    """Record one screening decision; an out-status always carries a reason."""
    source = get_source(conn, ref)
    status = status.strip().lower()
    if status not in SCREENING_STATUSES:
        raise EngineError(
            f"unknown screening status: {status}",
            f"allowed statuses are {', '.join(SCREENING_STATUSES)}.",
            "pass one of the listed statuses with --status.",
        )
    reason = reason.strip().lower()
    if status in TERMINAL_OUT and not reason:
        reason = "other"
    if reason and reason not in SCREENING_REASONS:
        raise EngineError(
            f"unknown exclusion reason: {reason}",
            f"allowed reasons are {', '.join(SCREENING_REASONS)}.",
            "pass one of the listed reasons with --reason.",
        )
    if status not in TERMINAL_OUT:
        reason = ""
    if status == source.screening and reason == source.screening_reason:
        raise EngineError(
            f"source already has screening {status}" + (f" ({reason})" if reason else ""),
            "a screening decision must change the recorded state.",
            "choose a different status or reason, or inspect the source.",
        )
    with transaction(conn):
        conn.execute(
            "UPDATE source SET screening = ?, screening_reason = ?, screening_at = ? WHERE id = ?",
            (status, reason, utc_now(), source.id),
        )
        record_event(
            conn,
            "source.screening",
            source.id,
            f"{source.screening} -> {status}" + (f" ({reason})" if reason else ""),
            research_id=source.research_id,
            actor=actor,
        )
    return get_source(conn, source.id)


def prisma_flow(conn: sqlite3.Connection, research_ref: Optional[str] = None) -> dict:
    """Counts and exclusion reasons across the review phases."""
    research_id = get_research(conn, research_ref).id if research_ref else None
    where = " WHERE research_id = ?" if research_id else ""
    params = (research_id,) if research_id else ()
    counts: Dict[str, int] = {
        status: int(
            conn.execute(
                f"SELECT COUNT(*) AS n FROM source{where}"
                + (" AND " if where else " WHERE ")
                + "screening = ?",
                (*params, status),
            ).fetchone()["n"]
        )
        for status in SCREENING_STATUSES
    }
    reasons: Dict[str, int] = {}
    for row in conn.execute(
        f"SELECT screening_reason AS reason, COUNT(*) AS n FROM source{where}"
        + (" AND " if where else " WHERE ")
        + "screening IN ('screened_out', 'excluded') GROUP BY screening_reason ORDER BY reason",
        params,
    ):
        reasons[str(row["reason"] or "other")] = int(row["n"])
    total = sum(counts.values())
    included = counts["included"]
    return {
        "counts": counts,
        "reasons": reasons,
        "total": total,
        "included": included,
        "included_fraction": round(included / total, 4) if total else 0.0,
    }


def unscreened_sources(conn: sqlite3.Connection, research_ref: str) -> List[Source]:
    """Sources still in the identified state, oldest first."""
    research = get_research(conn, research_ref)
    rows = conn.execute(
        "SELECT * FROM source WHERE research_id = ? AND screening = 'identified' ORDER BY id",
        (research.id,),
    ).fetchall()
    return [Source(**{key: row[key] for key in Source.__dataclass_fields__}) for row in rows]
