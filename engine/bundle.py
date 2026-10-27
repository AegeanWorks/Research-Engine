"""Portable JSONL export of the evidence graph, and a digest of its content."""

from __future__ import annotations

import hashlib
import hmac
import json
import sqlite3
from pathlib import Path
from typing import List, Set, Tuple

from engine.artifacts import atomic_write_text, digest, utc_now
from engine.database import SCHEMA_VERSION
from engine.errors import EngineError
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
    "observation",
    "event",
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
    if table in ("observation", "event"):
        return conn.execute(
            f"SELECT * FROM {table} WHERE research_id = ? ORDER BY id", (research_id,)
        ).fetchall()
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


def evidence_records(records: List[dict]) -> List[dict]:
    """Drop the audit log from the digest input.

    Events are consequences of state changes that are already hashed, and `report.write` is created
    while a manifest is being produced; hashing it would make the manifest reference itself and
    would make every regeneration look like a content change. Events stay in the export.
    """
    return [record for record in records if record.get("type") != "event"]


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


def _digest(records: List[dict], kind: str) -> str:
    blob = "\n".join(json.dumps(record, sort_keys=True) for record in records)
    return digest(kind, blob)


def graph_sha256(conn: sqlite3.Connection, research_ref: str | None = None) -> str:
    """Exact digest of every evidence record, including run bookkeeping; excludes the audit log."""
    records, _ = export_records(conn, research_ref)
    return _digest(evidence_records(records), "graph/1")


def content_sha256(conn: sqlite3.Connection, research_ref: str | None = None) -> str:
    """Digest of the graph's content, stable across a pure re-verification."""
    records, _ = export_records(conn, research_ref)
    return _digest(content_records(evidence_records(records)), "content/1")


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
                "records": sum(counts.values()),
                "export_digest": _digest(records, "export/1"),
            },
            sort_keys=True,
        )
    ]
    lines.extend(json.dumps(record, sort_keys=True) for record in records)
    atomic_write_text(Path(path), "\n".join(lines) + "\n")
    return counts


def verify_export(path: Path) -> dict:
    """Check a snapshot against the digest it carries in its own meta line.

    The export digest covers every record, including the audit log: it answers "is this file
    intact?", while the manifest's content digest answers "has the evidence changed?". A legacy
    export without a digest is refused rather than trusted.
    """
    source = Path(path)
    if not source.is_file():
        raise EngineError(
            f"snapshot not found: {source}",
            "there is no file to verify.",
            "create one with `export PATH --research REF`.",
        )
    records = []
    meta = None
    for number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except ValueError as error:
            raise EngineError(
                f"snapshot line {number} is not valid JSON: {source}",
                f"{error}",
                "re-export the snapshot with this engine version.",
            ) from error
        if record.get("type") == "meta":
            meta = record
            continue
        records.append(record)
    if meta is None:
        raise EngineError(
            f"snapshot has no meta line: {source}",
            "a verifiable export starts with a meta record.",
            "re-export the snapshot with this engine version.",
        )
    recorded = str(meta.get("export_digest") or "")
    if not recorded:
        raise EngineError(
            f"snapshot carries no digest: {source}",
            "this export predates self-verification, so its contents cannot be proven intact.",
            "re-export the snapshot with this engine version.",
        )
    actual = _digest(records, "export/1")
    recorded_count = meta.get("records")
    try:
        counts_match = recorded_count is None or int(recorded_count) == len(records)
    except (TypeError, ValueError):
        counts_match = False
    schema = meta.get("schema")
    return {
        "path": str(source),
        "ok": hmac.compare_digest(recorded, actual),
        "digest": actual,
        "recorded_digest": recorded,
        "records": len(records),
        "recorded_records": recorded_count,
        "counts_match": counts_match,
        "schema": schema,
        "schema_supported": schema == SCHEMA_VERSION,
        "research": meta.get("research"),
        "exported_at": meta.get("exported_at"),
    }
