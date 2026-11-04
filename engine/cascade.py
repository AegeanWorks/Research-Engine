"""Transitive invalidation: when a premise collapses, everything built on it collapses too."""

from __future__ import annotations

import json
import sqlite3
from typing import List, Tuple

from engine.claims import get_claim, set_verdict
from engine.database import next_id, transaction
from engine.errors import EngineError, NotFound
from engine.models import DEPENDENCY_RELATIONS, FAILED_STATUSES
from engine.artifacts import sha256_text, utc_now

CASCADE_BULK_LIMIT = 10
"""Collapse tripwire: retiring more than this many records needs an explicit opt-in.

Ten is a tripwire, not a safety proof: it catches the fat-fingered program-wide
collapse while staying out of the way of ordinary small cascades.
"""


def _plan_digest(
    conn: sqlite3.Connection, claim_ids: List[str], source_ids: List[str]
) -> str:
    """Bind exactly the rows an action will retire: any change breaks the digest.

    Claims contribute id, status and supersession; sources contribute id and
    status. The canonical form is sorted, so row order never affects the digest.
    """
    entries = []
    for claim_id in claim_ids:
        row = conn.execute(
            "SELECT status, superseded_by FROM claim WHERE id = ?", (claim_id,)
        ).fetchone()
        entries.append(
            ("claim", claim_id, str(row["status"]), str(row["superseded_by"] or ""))
        )
    for source_id in source_ids:
        row = conn.execute(
            "SELECT status FROM source WHERE id = ?", (source_id,)
        ).fetchone()
        entries.append(("source", source_id, str(row["status"]), ""))
    canonical = "\n".join("|".join(entry) for entry in sorted(entries))
    return sha256_text(canonical)


def _retraction_targets(conn: sqlite3.Connection, source) -> Tuple[list, list]:
    """The source plus every live twin row sharing its normalized DOI work."""
    from engine.duplicates import normalize_doi
    from engine.sources import get_source

    targets = [source]
    siblings: list = []
    work = normalize_doi(source.doi)
    if work:
        rows = conn.execute(
            "SELECT id, doi, status FROM source WHERE research_id = ? AND id != ? ORDER BY id",
            (source.research_id, source.id),
        ).fetchall()
        for row in rows:
            if normalize_doi(str(row["doi"] or "")) != work:
                continue
            if str(row["status"]) == "retracted":
                continue
            targets.append(get_source(conn, str(row["id"])))
            siblings.append(str(row["id"]))
    return targets, siblings


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


def preview(conn: sqlite3.Connection, ref: str) -> dict:
    """Show what a collapse or retraction would retire without writing anything.

    A claim ref previews the transitive collapse; a source ref previews the
    retraction across the work's twin rows. Either way the result carries a
    digest binding exactly the rows the action would read.
    """
    try:
        claim = get_claim(conn, ref)
    except NotFound:
        return _preview_retraction(conn, ref)
    affected = []
    planned = dependents(conn, claim.id)
    for dependent_id, depth in planned:
        dependent = get_claim(conn, dependent_id)
        affected.append(
            {
                "id": dependent.id,
                "depth": depth,
                "status": dependent.status,
                "would_invalidate": dependent.status not in FAILED_STATUSES,
                "text": dependent.text,
            }
        )
    digest = _plan_digest(
        conn, [claim.id] + [dependent_id for dependent_id, _ in planned], []
    )
    return {
        "root": claim.id,
        "root_status": claim.status,
        "affected": affected,
        "digest": digest,
    }


def _preview_retraction(conn: sqlite3.Connection, ref: str) -> dict:
    from engine.sources import get_source

    source = get_source(conn, ref)
    targets, _siblings = _retraction_targets(conn, source)
    claim_ids, affected = _retraction_plan(conn, targets)
    digest = _plan_digest(conn, claim_ids, [target.id for target in targets])
    return {
        "root": source.id,
        "root_status": source.status,
        "affected": affected,
        "digest": digest,
    }


def _retraction_plan(conn: sqlite3.Connection, targets: list) -> Tuple[list, list]:
    """Claim ids plus display entries a retraction would read.

    The digest covers every citing row (whatever its status) and the transitive
    dependents of the live ones: exactly the rows the action re-reads at
    execution, so any drift between preview and action breaks the digest.
    """
    affected = []
    seen: dict = {}
    for target in targets:
        rows = conn.execute(
            "SELECT * FROM claim WHERE source_id = ? AND superseded_by IS NULL ORDER BY id",
            (target.id,),
        ).fetchall()
        for row in rows:
            if str(row["id"]) in seen:
                continue
            seen[str(row["id"])] = 0
            affected.append(
                {
                    "id": str(row["id"]),
                    "depth": 0,
                    "status": str(row["status"]),
                    "would_retire": str(row["status"]) not in FAILED_STATUSES,
                    "text": str(row["text"]),
                }
            )
    for target in targets:
        rows = conn.execute(
            "SELECT id, status FROM claim WHERE source_id = ? AND superseded_by IS NULL ORDER BY id",
            (target.id,),
        ).fetchall()
        for row in rows:
            if str(row["status"]) in FAILED_STATUSES:
                continue
            for dependent_id, depth in dependents(conn, str(row["id"])):
                if dependent_id in seen and seen[dependent_id] <= depth + 1:
                    continue
                seen[dependent_id] = depth + 1
                dependent = get_claim(conn, dependent_id)
                affected.append(
                    {
                        "id": dependent.id,
                        "depth": depth + 1,
                        "status": dependent.status,
                        "would_retire": dependent.status not in FAILED_STATUSES,
                        "text": dependent.text,
                    }
                )
    affected.sort(key=lambda item: (item["depth"], item["id"]))
    return sorted(seen), affected


def invalidate(
    conn: sqlite3.Connection,
    claim_ref: str,
    status: str,
    reason: str,
    evidence: str,
    actor: str = "agent",
    allow_bulk: bool = False,
    preview_digest: str = "",
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
    if not evidence.strip():
        raise EngineError(
            "collapse has no evidence",
            "a collapse records the root verdict with an evidence path.",
            "pass --evidence naming the test run, derivation, or analysis.",
        )
    root = get_claim(conn, claim_ref)
    planned = dependents(conn, root.id)
    if len(planned) > CASCADE_BULK_LIMIT and not allow_bulk:
        raise EngineError(
            f"collapse would retire {len(planned)} records",
            "a collapse this wide is usually a wrong root, not a real cascade.",
            "run `cascade preview` to inspect the blast radius, then repeat with"
            " --allow-bulk when every dependent really falls.",
        )
    if preview_digest:
        current = _plan_digest(
            conn, [root.id] + [dependent_id for dependent_id, _ in planned], []
        )
        if current != preview_digest:
            raise EngineError(
                "the graph changed since the preview",
                "a status, edge or claim changed after `cascade preview` ran, so the"
                " preview no longer describes this collapse.",
                "re-run `cascade preview` and repeat with the fresh digest.",
            )
    affected = []
    with transaction(conn):
        set_verdict(conn, root.id, status, evidence, note=reason, actor=actor)
        for dependent_id, depth in planned:
            dependent = get_claim(conn, dependent_id)
            if dependent.status in FAILED_STATUSES:
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
    allow_bulk: bool = False,
    preview_digest: str = "",
) -> dict:
    """Retract a source and retire every empirical claim that cites it."""
    from engine.events import record as record_event
    from engine.sources import get_source

    if not reason.strip():
        raise EngineError(
            "retraction has no reason",
            "claims are only retired with a recorded reason.",
            "pass --reason with the retraction notice.",
        )
    if not evidence.strip():
        raise EngineError(
            "retraction has no evidence",
            "a retraction records each retired claim with an evidence path.",
            "pass --evidence naming the retraction notice or review.",
        )
    source = get_source(conn, ref)
    if source.status == "retracted":
        raise EngineError(
            "source is already retracted",
            "a retraction is recorded once and then remains in the record.",
            "inspect the source and its affected claims.",
        )
    targets, siblings = _retraction_targets(conn, source)
    plan: list = []
    for target in targets:
        rows = conn.execute(
            "SELECT id, status FROM claim WHERE source_id = ? AND superseded_by IS NULL ORDER BY id", (target.id,)
        ).fetchall()
        plan.append((target, rows))
    claim_ids, entries = _retraction_plan(conn, targets)
    retiring = sum(1 for entry in entries if entry["would_retire"])
    if retiring > CASCADE_BULK_LIMIT and not allow_bulk:
        raise EngineError(
            f"retraction would retire {retiring} claims",
            "a retraction this wide is usually a wrong source, not a real withdrawal.",
            "run `source duplicates` to inspect twin rows, then repeat with"
            " --allow-bulk when every citing claim really falls.",
        )
    if preview_digest:
        current = _plan_digest(conn, claim_ids, [target.id for target in targets])
        if current != preview_digest:
            raise EngineError(
                "the graph changed since the preview",
                "a status, edge or claim changed after the retraction preview ran, so"
                " the preview no longer describes this retraction.",
                "re-run `cascade preview` on the source and repeat with the fresh digest.",
            )
    affected: list = []
    with transaction(conn):
        for target, rows in plan:
            conn.execute(
                "UPDATE source SET status = 'retracted', status_note = ?, status_at = ? WHERE id = ?",
                (reason.strip(), utc_now(), target.id),
            )
            record_event(
                conn,
                "source.status",
                target.id,
                f"{target.status} -> retracted: {reason.strip()}",
                research_id=target.research_id,
                actor=actor,
            )
            for row in rows:
                if str(row["status"]) in FAILED_STATUSES:
                    continue
                result = invalidate(
                    conn,
                    str(row["id"]),
                    "RETRACTED",
                    f"source {target.id} retracted: {reason}",
                    evidence,
                    actor=actor,
                    allow_bulk=allow_bulk,
                )
                affected.append(
                    {
                        "id": str(row["id"]),
                        "previous_status": str(row["status"]),
                        "cascade": [item["id"] for item in result["affected"]],
                    }
                )
    return {"source": source.id, "status": "retracted", "siblings": siblings, "affected": affected}
