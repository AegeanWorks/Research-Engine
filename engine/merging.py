"""Claim merging: one survivor, every edge repointed, duplicates retired."""

from __future__ import annotations

import sqlite3
from typing import Iterable, List

from engine.claims import get_claim, record_edge, set_verdict
from engine.database import transaction
from engine.errors import EngineError
from engine.events import record as record_event


def merge_claims(
    conn: sqlite3.Connection,
    keep_ref: str,
    drop_refs: Iterable[str],
    note: str = "",
    actor: str = "agent",
) -> dict:
    """Keep one claim, repoint edges from the duplicates, and retire the duplicates.

    The survivor keeps its own verdict history. A duplicate is not deleted: it is recorded as
    `RETRACTED` with evidence naming the survivor, so the merge stays auditable and the
    duplicate-text warning stops firing.
    """
    keep = get_claim(conn, keep_ref)
    drops = [get_claim(conn, ref) for ref in drop_refs]
    if not drops:
        raise EngineError(
            "merge needs at least one duplicate",
            "merging one claim into itself changes nothing.",
            "pass one or more claim identifiers to merge into the survivor.",
        )
    if keep.status in ("RETRACTED", "INVALIDATED"):
        raise EngineError(
            f"survivor {keep.id} is {keep.status}",
            "a merge must keep a live claim, not a retired one.",
            "choose the claim that remains part of the argument as the survivor.",
        )
    if keep.superseded_by:
        raise EngineError(
            f"survivor {keep.id} is superseded by {keep.superseded_by}",
            "a merge must keep the current revision head.",
            "choose the head of the revision chain as the survivor.",
        )
    for claim in drops:
        if claim.id == keep.id:
            raise EngineError(
                "a claim cannot be merged into itself",
                "the survivor and the duplicate must differ.",
                "remove the survivor from the duplicate list.",
            )
        if claim.research_id != keep.research_id:
            raise EngineError(
                "merge crosses research programs",
                "a program boundary is never rewritten by a merge.",
                "merge only claims from the same program.",
            )
        if claim.status in ("RETRACTED", "INVALIDATED"):
            raise EngineError(
                f"claim {claim.id} is already {claim.status}",
                "a retired claim has no live edges to repoint.",
                "choose a live duplicate.",
            )
        if claim.superseded_by:
            raise EngineError(
                f"claim {claim.id} is superseded by {claim.superseded_by}",
                "a superseded claim is already history; merge the current head instead.",
                "choose a live duplicate from the current revision chain.",
            )
    moved: List[str] = []
    retired: List[str] = []
    rebound: List[str] = []
    with transaction(conn):
        for claim in drops:
            rows = conn.execute(
                "SELECT * FROM edge WHERE (src_kind = 'claim' AND src_id = ?)"
                " OR (dst_kind = 'claim' AND dst_id = ?) ORDER BY id",
                (claim.id, claim.id),
            ).fetchall()
            for row in rows:
                src_id = keep.id if str(row["src_id"]) == claim.id else str(row["src_id"])
                dst_id = keep.id if str(row["dst_id"]) == claim.id else str(row["dst_id"])
                if src_id == dst_id:
                    continue
                record_edge(
                    conn,
                    str(row["src_kind"]),
                    src_id,
                    str(row["dst_kind"]),
                    dst_id,
                    str(row["rel"]),
                )
                moved.append(str(row["id"]))
            conn.execute(
                "DELETE FROM edge WHERE (src_kind = 'claim' AND src_id = ?)"
                " OR (dst_kind = 'claim' AND dst_id = ?)",
                (claim.id, claim.id),
            )
            touched = conn.execute(
                "UPDATE killtest SET claim_id = ? WHERE claim_id = ?", (keep.id, claim.id)
            )
            if touched.rowcount:
                rebound.append(claim.id)
        for claim in drops:
            set_verdict(
                conn,
                claim.id,
                "RETRACTED",
                note.strip() or f"merged into {keep.id}",
                note=note.strip(),
                actor=actor,
            )
            retired.append(claim.id)
        record_event(
            conn,
            "claim.merge",
            keep.id,
            "retired " + ", ".join(retired),
            research_id=keep.research_id,
            actor=actor,
        )
    return {
        "keep": keep.id,
        "retired": retired,
        "edges_repointed": moved,
        "tests_repointed_from": rebound,
    }
