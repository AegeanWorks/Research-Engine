"""Portable JSONL export of the evidence graph, and a digest of its content."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import List, Set, Tuple

from engine.artifacts import atomic_write_text, utc_now
from engine.database import SCHEMA_VERSION
from engine.researches import get_research

_ORDER = (
    "research",
    "source",
    "question",
    "claim",
    "hypothesis",
    "killtest",
    "edge",
    "test_run",
    "verdict",
    "invalidation",
)


def _rows(conn: sqlite3.Connection, table: str, research_id: str | None) -> List[sqlite3.Row]:
    if research_id is None:
        return conn.execute(f"SELECT * FROM {table} ORDER BY id").fetchall()
    if table == "research":
        return conn.execute("SELECT * FROM research WHERE id = ?", (research_id,)).fetchall()
    if table in ("source", "question", "claim", "hypothesis", "killtest"):
        return conn.execute(
            f"SELECT * FROM {table} WHERE research_id = ? ORDER BY id", (research_id,)
        ).fetchall()
    if table == "edge":
        members = set()
        for entity in ("claim", "question", "hypothesis"):
            for row in conn.execute(
                f"SELECT id FROM {entity} WHERE research_id = ?", (research_id,)
            ):
                members.add(str(row["id"]))
        return [
            row
            for row in conn.execute("SELECT * FROM edge ORDER BY id")
            if str(row["src_id"]) in members or str(row["dst_id"]) in members
        ]
    if table == "test_run":
        return conn.execute(
            "SELECT u.* FROM test_run u JOIN killtest t ON t.id = u.test_id"
            " WHERE t.research_id = ? ORDER BY u.id",
            (research_id,),
        ).fetchall()
    if table == "verdict":
        members: Set[str] = set()
        for entity in ("claim", "hypothesis"):
            for row in conn.execute(
                f"SELECT id FROM {entity} WHERE research_id = ?", (research_id,)
            ):
                members.add(str(row["id"]))
        return [
            row
            for row in conn.execute("SELECT * FROM verdict ORDER BY id")
            if str(row["subject_id"]) in members
        ]
    if table == "invalidation":
        members = {
            str(row["id"])
            for row in conn.execute(
                "SELECT id FROM claim WHERE research_id = ?", (research_id,)
            )
        }
        return [
            row
            for row in conn.execute("SELECT * FROM invalidation ORDER BY id")
            if str(row["root_id"]) in members
        ]
    raise ValueError(f"unknown bundle table: {table}")


def export_records(
    conn: sqlite3.Connection, research_ref: str | None = None
) -> Tuple[List[dict], dict]:
    """Return the ordered graph records and their per-table counts."""
    research_id = None
    if research_ref:
        research_id = get_research(conn, research_ref).id
    records: List[dict] = []
    counts = {}
    for table in _ORDER:
        rows = _rows(conn, table, research_id)
        counts[table] = len(rows)
        for row in rows:
            payload = {"type": table}
            payload.update({key: row[key] for key in row.keys()})
            records.append(payload)
    return records, counts


_VOLATILE_RUN_FIELDS = frozenset(
    {"id", "run_group", "started_at", "duration_ms", "output_tail"}
)


def content_records(records: List[dict]) -> List[dict]:
    """Semantic projection of a record set: run allocation artefacts are dropped.

    Re-running an unchanged test allocates new run ids, a new group label and new timings, so an
    exact record digest changes even though no claim, verdict or piece of evidence changed. The
    projection keeps the binding hashes and the pass flag, de-duplicates identical runs, and
    therefore tracks content rather than bookkeeping.
    """
    runs = set()
    kept: List[dict] = []
    for record in records:
        if record.get("type") == "test_run":
            runs.add(
                tuple(
                    sorted(
                        (key, str(value))
                        for key, value in record.items()
                        if key not in _VOLATILE_RUN_FIELDS
                    )
                )
            )
            continue
        kept.append(record)
    for run in sorted(runs):
        fields = dict(run)
        identity = f"run:{fields.get('test_id', '')}:{fields.get('run_tag', '')}"
        kept.append({"type": "test_run", "id": identity, "projection": list(run)})
    return kept


def _digest(records: List[dict]) -> str:
    blob = "\n".join(json.dumps(record, sort_keys=True) for record in records)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def graph_sha256(conn: sqlite3.Connection, research_ref: str | None = None) -> str:
    """Exact digest of every exported record, including run bookkeeping."""
    records, _ = export_records(conn, research_ref)
    return _digest(records)


def content_sha256(conn: sqlite3.Connection, research_ref: str | None = None) -> str:
    """Digest of the graph's content, stable across a pure re-verification."""
    records, _ = export_records(conn, research_ref)
    return _digest(content_records(records))


def export_jsonl(
    conn: sqlite3.Connection, path: Path, research_ref: str | None = None
) -> dict:
    """Write the graph as deterministic JSONL lines, atomically."""
    records, counts = export_records(conn, research_ref)
    lines = [
        json.dumps(
            {
                "type": "meta",
                "schema": SCHEMA_VERSION,
                "engine": "research-engine",
                "exported_at": utc_now(),
                "research": research_ref or "all",
            },
            sort_keys=True,
        )
    ]
    lines.extend(json.dumps(record, sort_keys=True) for record in records)
    atomic_write_text(Path(path), "\n".join(lines) + "\n")
    return counts
