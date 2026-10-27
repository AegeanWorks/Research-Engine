"""Pre-registered hypotheses and their outcomes (the K13 discipline)."""

from __future__ import annotations

import sqlite3
from typing import List, Optional

from engine.database import next_id, transaction
from engine.errors import EngineError, NotFound
from engine.models import HYPOTHESIS_OUTCOMES, Hypothesis
from engine.questions import get_question
from engine.researches import get_research
from engine.artifacts import utc_now


def _to_hypothesis(row: sqlite3.Row) -> Hypothesis:
    return Hypothesis(**{key: row[key] for key in Hypothesis.__dataclass_fields__})


def add_hypothesis(
    conn: sqlite3.Connection,
    research_ref: str,
    statement: str,
    criterion: str,
    confidence: float = 0.5,
    question_ref: Optional[str] = None,
) -> Hypothesis:
    """Pre-register a prediction before any outcome is known."""
    research = get_research(conn, research_ref)
    statement = statement.strip()
    criterion = criterion.strip()
    if not statement:
        raise EngineError("hypothesis statement is empty", "a prediction must be stated.", "pass --statement.")
    if not criterion:
        raise EngineError(
            "hypothesis has no verification criterion",
            "a prediction that cannot fail is not a hypothesis.",
            "pass --criterion with the observation that would refute it.",
        )
    confidence = float(confidence)
    if not 0.0 <= confidence <= 1.0:
        raise EngineError(
            f"confidence out of range: {confidence}",
            "confidence is a probability in the closed interval [0, 1].",
            "pass a value such as --confidence 0.7.",
        )
    question_id = None
    if question_ref:
        question = get_question(conn, question_ref)
        if question.research_id != research.id:
            raise EngineError(
                "question belongs to another research program",
                "a hypothesis is registered inside the program that asks the question.",
                "register the hypothesis in that program.",
            )
        question_id = question.id
    with transaction(conn):
        stamp = utc_now()
        record = Hypothesis(
            id=next_id(conn, "h"),
            research_id=research.id,
            question_id=question_id,
            statement=statement,
            criterion=criterion,
            confidence=confidence,
            registered_at=stamp,
            status="PREREGISTERED",
            outcome_note="",
            updated_at=stamp,
        )
        conn.execute(
            "INSERT INTO hypothesis(id, research_id, question_id, statement, criterion, confidence,"
            " registered_at, status, outcome_note, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                record.id,
                record.research_id,
                record.question_id,
                record.statement,
                record.criterion,
                record.confidence,
                record.registered_at,
                record.status,
                record.outcome_note,
                record.updated_at,
            ),
        )
    return record


def get_hypothesis(conn: sqlite3.Connection, ref: str) -> Hypothesis:
    """Fetch one hypothesis by identifier."""
    row = conn.execute("SELECT * FROM hypothesis WHERE id = ?", (ref,)).fetchone()
    if row is None:
        raise NotFound("hypothesis", ref)
    return _to_hypothesis(row)


def list_hypotheses(
    conn: sqlite3.Connection, research_ref: str | None = None
) -> List[Hypothesis]:
    """List hypotheses, optionally filtered by program."""
    if research_ref:
        research = get_research(conn, research_ref)
        rows = conn.execute(
            "SELECT * FROM hypothesis WHERE research_id = ? ORDER BY id", (research.id,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM hypothesis ORDER BY id").fetchall()
    return [_to_hypothesis(row) for row in rows]


def record_outcome(
    conn: sqlite3.Connection,
    hypothesis_ref: str,
    outcome: str,
    evidence: str,
    note: str = "",
    actor: str = "agent",
) -> Hypothesis:
    """Close a pre-registered hypothesis with an evidence-backed outcome."""
    hypothesis = get_hypothesis(conn, hypothesis_ref)
    if outcome not in HYPOTHESIS_OUTCOMES:
        raise EngineError(
            f"unknown outcome: {outcome}",
            f"allowed outcomes are {', '.join(HYPOTHESIS_OUTCOMES)}.",
            "pass one of the listed outcomes with --status.",
        )
    if not evidence.strip():
        raise EngineError(
            "outcome has no evidence",
            "an outcome without an evidence path cannot be audited.",
            "pass --evidence naming the test run or analysis.",
        )
    if hypothesis.status != "PREREGISTERED":
        raise EngineError(
            f"hypothesis already has outcome {hypothesis.status}",
            "outcomes are recorded once and then remain in the verdict history.",
            "inspect the hypothesis instead of overwriting its outcome.",
        )
    with transaction(conn):
        stamp = utc_now()
        conn.execute(
            "INSERT INTO verdict(id, subject_kind, subject_id, status, previous_status,"
            " evidence, note, actor, at) VALUES (?, 'hypothesis', ?, ?, ?, ?, ?, ?, ?)",
            (
                next_id(conn, "v"),
                hypothesis.id,
                outcome,
                hypothesis.status,
                evidence.strip(),
                note.strip(),
                actor,
                stamp,
            ),
        )
        conn.execute(
            "UPDATE hypothesis SET status = ?, outcome_note = ?, updated_at = ? WHERE id = ?",
            (outcome, note.strip(), stamp, hypothesis.id),
        )
    return get_hypothesis(conn, hypothesis.id)


def preregistration_card(conn: sqlite3.Connection, hypothesis_ref: str) -> str:
    """Render the pre-registration card an agent writes before searching."""
    hypothesis = get_hypothesis(conn, hypothesis_ref)
    return (
        f"# K13 Pre-registration: {hypothesis.id}\n\n"
        f"**Registered:** {hypothesis.registered_at}\n"
        f"**Statement:** {hypothesis.statement}\n"
        f"**Confidence:** {hypothesis.confidence:.2f}\n"
        f"**Verification criterion:** {hypothesis.criterion}\n"
        f"**Most likely to be wrong:** {hypothesis.criterion}\n"
        f"**Status:** {hypothesis.status}\n"
    )
