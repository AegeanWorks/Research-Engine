"""Bibliographic sources: the only place literature text may enter the graph."""

from __future__ import annotations

import sqlite3
from typing import List, Optional

from engine.database import next_id, transaction
from engine.errors import EngineError, NotFound
from engine.models import SOURCE_KINDS, SOURCE_STATUSES, Source
from engine.researches import get_research
from engine.artifacts import utc_now


def _to_source(row: sqlite3.Row) -> Source:
    return Source(**{key: row[key] for key in Source.__dataclass_fields__})


def add_source(
    conn: sqlite3.Connection,
    research_ref: str,
    title: str,
    year: Optional[int] = None,
    doi: str = "",
    url: str = "",
    authors: str = "",
    kind: str = "paper",
) -> Source:
    """Register a source; claims cannot cite it before it exists."""
    research = get_research(conn, research_ref)
    title = title.strip()
    if not title:
        raise EngineError("source title is empty", "a source needs a title.", "pass --title.")
    if kind not in SOURCE_KINDS:
        raise EngineError(
            f"unknown source kind: {kind}",
            f"allowed kinds are {', '.join(SOURCE_KINDS)}.",
            "pass one of the listed kinds with --kind.",
        )
    if year is not None and not 1000 <= int(year) <= 9999:
        raise EngineError(
            f"implausible year: {year}",
            "the year must be a four-digit calendar year.",
            "pass the publication year, for example --year 2024.",
        )
    if not doi.strip() and not url.strip() and year is None:
        raise EngineError(
            "source has no identifier",
            "without a DOI, URL or year the source cannot be audited or found again.",
            "pass at least one of --doi, --url or --year.",
        )
    with transaction(conn):
        record = Source(
            id=next_id(conn, "s"),
            research_id=research.id,
            kind=kind,
            title=title,
            authors=authors.strip(),
            year=int(year) if year is not None else None,
            doi=doi.strip(),
            url=url.strip(),
            retrieved_at=utc_now(),
        )
        conn.execute(
            "INSERT INTO source(id, research_id, kind, title, authors, year, doi, url, retrieved_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                record.id,
                record.research_id,
                record.kind,
                record.title,
                record.authors,
                record.year,
                record.doi,
                record.url,
                record.retrieved_at,
            ),
        )
    return record


def get_source(conn: sqlite3.Connection, ref: str) -> Source:
    """Fetch one source by identifier."""
    row = conn.execute("SELECT * FROM source WHERE id = ?", (ref,)).fetchone()
    if row is None:
        raise NotFound("source", ref)
    return _to_source(row)


def list_sources(
    conn: sqlite3.Connection, research_ref: str | None = None
) -> List[Source]:
    """List sources, optionally filtered by program."""
    if research_ref:
        research = get_research(conn, research_ref)
        rows = conn.execute(
            "SELECT * FROM source WHERE research_id = ? ORDER BY id", (research.id,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM source ORDER BY id").fetchall()
    return [_to_source(row) for row in rows]


def set_source_status(
    conn: sqlite3.Connection,
    ref: str,
    status: str,
    note: str = "",
    actor: str = "agent",
) -> Source:
    """Change a source's evidence status without deleting the record."""
    source = get_source(conn, ref)
    if status not in SOURCE_STATUSES:
        raise EngineError(
            f"unknown source status: {status}",
            f"allowed statuses are {', '.join(SOURCE_STATUSES)}.",
            "pass one of the listed statuses with --status.",
        )
    if status == source.status:
        raise EngineError(
            f"source already has status {status}",
            "a status change must change the recorded state.",
            "choose a different status, or inspect the source.",
        )
    if not note.strip():
        raise EngineError(
            f"status {status} needs a note",
            "a source status change is only recorded with its reason and evidence.",
            "pass --note with the retraction notice, the concern, or the correction.",
        )
    with transaction(conn):
        conn.execute(
            "UPDATE source SET status = ?, status_note = ?, status_at = ? WHERE id = ?",
            (status, note.strip(), utc_now(), source.id),
        )
    return get_source(conn, source.id)
