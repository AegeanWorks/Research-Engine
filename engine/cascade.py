"""Transitive invalidation: when a premise collapses, everything built on it collapses too."""

from __future__ import annotations

import json
import sqlite3
from typing import List, Tuple

from engine.claims import get_claim, set_verdict
from engine.database import next_id, transaction
from engine.errors import EngineError
from engine.models import DEPENDENCY_RELATIONS, FAILED_STATUSES
from engine.artifacts import utc_now


def dependents(conn: sqlite3.Connection, claim_id: str) -> List[Tuple[str, int]]:
    """Return every claim that structurally depends on this claim, by depth."""
    seen = {claim_id}
    frontier = [claim_id]
    found: List[Tuple[str, int]] = []
    depth = 0
    marks = ",".join("?" for _ in DEPENDENCY_RELATIONS)
    while frontier:
        depth += 1
        next_frontier: List[str] = []
        for current in frontier:
            rows = conn.execute(
                f"SELECT src_id FROM edge WHERE src_kind = 'claim' AND dst_kind = 'claim'"
                f" AND dst_id = ? AND rel IN ({marks}) ORDER BY src_id",
                (current, *DEPENDENCY_RELATIONS),
            ).fetchall()
            for row in rows:
                candidate = str(row["src_id"])
                if candidate in seen:
                    continue
                seen.add(candidate)
                found.append((candidate, depth))
                next_frontier.append(candidate)
        frontier = next_frontier
    return found


def preview(conn: sqlite3.Connection, claim_ref: str) -> dict:
    """Show what a collapse would invalidate without writing anything."""
    claim = get_claim(conn, claim_ref)
    affected = []
    for dependent_id, depth in dependents(conn, claim.id):
        dependent = get_claim(conn, dependent_id)
        affected.append(
            {
                "id": dependent.id,
                "depth": depth,
                "status": dependent.status,
                "would_invalidate": dependent.status not in ("RETRACTED", "INVALIDATED"),
                "text": dependent.text,
            }
        )
    return {"root": claim.id, "root_status": claim.status, "affected": affected}


def invalidate(
    conn: sqlite3.Connection,
    claim_ref: str,
    status: str,
    reason: str,
    evidence: str,
    actor: str = "agent",
) -> dict:
    """Record a failed root claim, then invalidate every dependent in one transaction."""
    if status not in ("FALSIFIED", "RETRACTED"):
        raise EngineError(
            f"invalid status for a collapse: {status}",
            "a collapse must record the root claim as FALSIFIED or RETRACTED.",
            "pass --status FALSIFIED or --status RETRACTED.",
        )
    if not reason.strip():
        raise EngineError(
            "collapse has no reason",
            "a dependent claim is only invalidated with an explicit reason.",
            "pass --reason with the failed premise.",
        )
    root = get_claim(conn, claim_ref)
    planned = dependents(conn, root.id)
    affected = []
    with transaction(conn):
        set_verdict(conn, root.id, status, evidence, note=reason, actor=actor)
        for dependent_id, depth in planned:
            dependent = get_claim(conn, dependent_id)
            if dependent.status in ("RETRACTED", "INVALIDATED"):
                continue
            previous = dependent.status
            set_verdict(
                conn,
                dependent.id,
                "INVALIDATED",
                f"cascade:{root.id}",
                note=f"premise {root.id} became {status}: {reason}",
                actor=actor,
            )
            affected.append(
                {"id": dependent.id, "depth": depth, "previous_status": previous}
            )
        conn.execute(
            "INSERT INTO invalidation(id, root_kind, root_id, reason, actor, at, affected_json)"
            " VALUES (?, 'claim', ?, ?, ?, ?, ?)",
            (
                next_id(conn, "x"),
                root.id,
                reason.strip(),
                actor,
                utc_now(),
                json.dumps(affected, sort_keys=True),
            ),
        )
    return {
        "root": root.id,
        "status": status,
        "affected": affected,
        "failed_states": list(FAILED_STATUSES),
    }

def retract_source(
    conn: sqlite3.Connection,
    ref: str,
    reason: str,
    evidence: str,
    actor: str = "agent",
) -> dict:
    """Retract a source and retire every empirical claim that cites it."""
    from engine.sources import get_source, set_source_status

    if not reason.strip():
        raise EngineError(
            "retraction has no reason",
            "claims are only retired with a recorded reason.",
            "pass --reason with the retraction notice.",
        )
    source = get_source(conn, ref)
    if source.status == "retracted":
        raise EngineError(
            "source is already retracted",
            "a retraction is recorded once and then remains in the record.",
            "inspect the source and its affected claims.",
        )
    affected: list = []
    with transaction(conn):
        set_source_status(conn, source.id, "retracted", reason, actor)
        rows = conn.execute(
            "SELECT id, status FROM claim WHERE source_id = ? ORDER BY id", (source.id,)
        ).fetchall()
        for row in rows:
            if str(row["status"]) in FAILED_STATUSES:
                continue
            result = invalidate(
                conn,
                str(row["id"]),
                "RETRACTED",
                f"source {source.id} retracted: {reason}",
                evidence,
                actor=actor,
            )
            affected.append(
                {
                    "id": str(row["id"]),
                    "previous_status": str(row["status"]),
                    "cascade": [item["id"] for item in result["affected"]],
                }
            )
    return {"source": source.id, "status": "retracted", "affected": affected}
