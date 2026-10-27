"""Research programs: the top-level containers the engine is asked to investigate."""

from __future__ import annotations

import re
import sqlite3
from typing import List, Optional

from engine.database import next_id, transaction
from engine.errors import EngineError, NotFound
from engine.models import Research
from engine.artifacts import utc_now


def _slugify(conn: sqlite3.Connection, title: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "research"
    candidate = base
    suffix = 2
    while conn.execute("SELECT 1 FROM research WHERE slug = ?", (candidate,)).fetchone():
        candidate = f"{base}-{suffix}"
        suffix += 1
    return candidate


def _to_research(row: sqlite3.Row) -> Research:
    return Research(**{key: row[key] for key in Research.__dataclass_fields__})


def create_research(
    conn: sqlite3.Connection, title: str, scope: str = "", slug: Optional[str] = None
) -> Research:
    """Create a research program with a stable, unique slug."""
    title = title.strip()
    if not title:
        raise EngineError("research title is empty", "a program needs a name.", "pass a non-empty title.")
    with transaction(conn):
        chosen = slug.strip() if slug else _slugify(conn, title)
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", chosen):
            raise EngineError(
                f"invalid research slug: {chosen}",
                "slugs are lowercase letters, digits and hyphens, and start with a letter or digit.",
                "use a slug such as `fluid-universe`.",
            )
        if conn.execute("SELECT 1 FROM research WHERE slug = ?", (chosen,)).fetchone():
            raise EngineError(
                f"research slug already exists: {chosen}",
                "two programs cannot share a slug.",
                "choose another slug or use `research show` on the existing program.",
            )
        record = Research(
            id=next_id(conn, "r"),
            slug=chosen,
            title=title,
            scope=scope.strip(),
            created_at=utc_now(),
        )
        conn.execute(
            "INSERT INTO research(id, slug, title, scope, created_at) VALUES (?, ?, ?, ?, ?)",
            (record.id, record.slug, record.title, record.scope, record.created_at),
        )
    return record


def get_research(conn: sqlite3.Connection, ref: str) -> Research:
    """Resolve a program by identifier or slug."""
    row = conn.execute(
        "SELECT * FROM research WHERE id = ? OR slug = ?", (ref, ref)
    ).fetchone()
    if row is None:
        raise NotFound("research", ref)
    return _to_research(row)


def list_researches(conn: sqlite3.Connection) -> List[Research]:
    """List programs in creation order."""
    rows = conn.execute("SELECT * FROM research ORDER BY id").fetchall()
    return [_to_research(row) for row in rows]


def research_counts(conn: sqlite3.Connection, research_id: str) -> dict:
    """Return the record counts that summarise a program."""
    counts = {}
    for table in ("source", "question", "claim", "hypothesis", "killtest"):
        counts[table] = conn.execute(
            f"SELECT COUNT(*) AS n FROM {table} WHERE research_id = ?", (research_id,)
        ).fetchone()["n"]
    counts["open_questions"] = conn.execute(
        "SELECT COUNT(*) AS n FROM question WHERE research_id = ? AND status = 'open'",
        (research_id,),
    ).fetchone()["n"]
    return counts
