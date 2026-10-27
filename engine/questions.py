"""Research questions that collect supporting and contradicting claims."""

from __future__ import annotations

import sqlite3
from typing import List

from engine.database import next_id, transaction
from engine.errors import EngineError, NotFound
from engine.models import Question
from engine.researches import get_research
from engine.artifacts import utc_now


def _to_question(row: sqlite3.Row) -> Question:
    return Question(**{key: row[key] for key in Question.__dataclass_fields__})


def add_question(conn: sqlite3.Connection, research_ref: str, text: str) -> Question:
    """Add an open question to a program."""
    research = get_research(conn, research_ref)
    text = text.strip()
    if not text:
        raise EngineError("question text is empty", "a question needs a sentence.", "pass the question text.")
    with transaction(conn):
        record = Question(
            id=next_id(conn, "q"),
            research_id=research.id,
            text=text,
            status="open",
            created_at=utc_now(),
        )
        conn.execute(
            "INSERT INTO question(id, research_id, text, status, created_at) VALUES (?, ?, ?, ?, ?)",
            (record.id, record.research_id, record.text, record.status, record.created_at),
        )
    return record


def get_question(conn: sqlite3.Connection, ref: str) -> Question:
    """Fetch one question by identifier."""
    row = conn.execute("SELECT * FROM question WHERE id = ?", (ref,)).fetchone()
    if row is None:
        raise NotFound("question", ref)
    return _to_question(row)


def list_questions(
    conn: sqlite3.Connection, research_ref: str | None = None
) -> List[Question]:
    """List questions, optionally filtered by program."""
    if research_ref:
        research = get_research(conn, research_ref)
        rows = conn.execute(
            "SELECT * FROM question WHERE research_id = ? ORDER BY id", (research.id,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM question ORDER BY id").fetchall()
    return [_to_question(row) for row in rows]


def close_question(conn: sqlite3.Connection, ref: str) -> Question:
    """Mark a question resolved without deleting its evidence."""
    question = get_question(conn, ref)
    with transaction(conn):
        conn.execute("UPDATE question SET status = 'closed' WHERE id = ?", (question.id,))
    return Question(**{**question.__dict__, "status": "closed"})
