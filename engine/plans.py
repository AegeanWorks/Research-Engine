"""Pre-registered analysis plans: comparisons declare their prediction first."""

from __future__ import annotations

import sqlite3
from typing import List, Optional

from engine.artifacts import utc_now
from engine.claims import get_claim
from engine.database import next_id, transaction
from engine.errors import EngineError, NotFound
from engine.events import record as record_event
from engine.models import AnalysisPlan
from engine.researches import get_research


def _to_plan(row: sqlite3.Row) -> AnalysisPlan:
    return AnalysisPlan(**{key: row[key] for key in AnalysisPlan.__dataclass_fields__})


def add_plan(
    conn: sqlite3.Connection,
    claim_ref: str,
    baseline: str,
    treatment: str,
    prediction: str,
    actor: str = "agent",
) -> AnalysisPlan:
    """Pre-register what a comparison is expected to show, before it runs."""
    claim = get_claim(conn, claim_ref)
    baseline = baseline.strip().lower()
    treatment = treatment.strip().lower()
    prediction = prediction.strip()
    if not prediction:
        raise EngineError(
            "analysis plan has no prediction",
            "a plan that predicts nothing cannot be confirmed or surprised.",
            "pass --prediction stating the expected direction or effect.",
        )
    if not baseline or not treatment:
        raise EngineError(
            "analysis plan needs two group labels",
            "a comparison needs a baseline and a treatment to mean anything.",
            "pass --baseline and --treatment with the planned group labels.",
        )
    if baseline == treatment:
        raise EngineError(
            f"cannot plan group {baseline!r} against itself",
            "a comparison needs two different groups for a difference to mean anything.",
            "choose a different baseline or treatment label.",
        )
    with transaction(conn):
        record = AnalysisPlan(
            id=next_id(conn, "ap"),
            research_id=claim.research_id,
            claim_id=claim.id,
            baseline=baseline,
            treatment=treatment,
            prediction=prediction,
            status="PREREGISTERED",
            registered_at=utc_now(),
        )
        conn.execute(
            "INSERT INTO analysis_plan(id, research_id, claim_id, baseline, treatment,"
            " prediction, status, registered_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                record.id,
                record.research_id,
                record.claim_id,
                record.baseline,
                record.treatment,
                record.prediction,
                record.status,
                record.registered_at,
            ),
        )
        record_event(
            conn,
            "analysis.plan",
            record.id,
            f"{baseline}->{treatment}: {prediction}",
            research_id=claim.research_id,
            actor=actor,
        )
    return record


def get_plan(conn: sqlite3.Connection, ref: str) -> AnalysisPlan:
    """Fetch one analysis plan by identifier."""
    row = conn.execute("SELECT * FROM analysis_plan WHERE id = ?", (ref,)).fetchone()
    if row is None:
        raise NotFound("analysis_plan", ref)
    return _to_plan(row)


def list_plans(
    conn: sqlite3.Connection, claim_ref: Optional[str] = None
) -> List[AnalysisPlan]:
    """Plans in record order, optionally filtered to one claim."""
    if claim_ref:
        claim = get_claim(conn, claim_ref)
        rows = conn.execute(
            "SELECT * FROM analysis_plan WHERE claim_id = ? ORDER BY id", (claim.id,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM analysis_plan ORDER BY id").fetchall()
    return [_to_plan(row) for row in rows]


def match_plan(
    conn: sqlite3.Connection, claim_id: str, baseline: str, treatment: str
) -> List[AnalysisPlan]:
    """Plans preregistered for exactly this claim and group pair."""
    rows = conn.execute(
        "SELECT * FROM analysis_plan WHERE claim_id = ? AND baseline = ?"
        " AND treatment = ? ORDER BY id",
        (claim_id, baseline.strip().lower(), treatment.strip().lower()),
    ).fetchall()
    return [_to_plan(row) for row in rows]
