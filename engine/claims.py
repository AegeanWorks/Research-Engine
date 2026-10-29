"""Claims: the unit of knowledge, with provenance and an append-only verdict history."""

from __future__ import annotations

import sqlite3
from typing import Iterable, List, Optional, Sequence

from engine.database import next_id, transaction
from engine.errors import EngineError, NotFound
from engine.events import record as record_event
from engine.models import (
    CLAIM_CLAIM_RELATIONS,
    CLAIM_KINDS,
    CLAIM_STATUSES,
    DEPENDENCY_RELATIONS,
    FAILED_STATUSES,
    NON_SUPPORTING_STATUSES,
    PROMOTED_STATUSES,
    Claim,
)
from engine.researches import get_research
from engine.sources import get_source
from engine.artifacts import utc_now


def _to_claim(row: sqlite3.Row) -> Claim:
    return Claim(**{key: row[key] for key in Claim.__dataclass_fields__})


def _validate_confidence(value: float) -> float:
    value = float(value)
    if not 0.0 <= value <= 1.0:
        raise EngineError(
            f"confidence out of range: {value}",
            "confidence is a probability in the closed interval [0, 1].",
            "pass a value such as --confidence 0.7.",
        )
    return value


def add_claim(
    conn: sqlite3.Connection,
    research_ref: str,
    text: str,
    kind: str,
    source_ref: Optional[str] = None,
    quote: str = "",
    locator: str = "",
    confidence: float = 0.5,
    kill_test: str = "",
    basis: str = "",
    prerequisites: Sequence[str] = (),
    revision_of: Optional[str] = None,
    revision_reason: str = "",
) -> Claim:
    """Record a claim; empirical claims must carry a verbatim quote and a locator."""
    research = get_research(conn, research_ref)
    text = text.strip()
    if not text:
        raise EngineError("claim text is empty", "a claim is an assertion.", "pass --text.")
    if kind not in CLAIM_KINDS:
        raise EngineError(
            f"unknown claim kind: {kind}",
            f"allowed kinds are {', '.join(CLAIM_KINDS)}.",
            "pass one of the listed kinds with --kind.",
        )
    confidence = _validate_confidence(confidence)
    source_id = None
    if kind == "empirical":
        if not source_ref:
            raise EngineError(
                "empirical claim has no source",
                "every empirical claim needs a registered source for provenance.",
                "register the source with `source add`, then pass --source.",
            )
        source = get_source(conn, source_ref)
        if source.research_id != research.id:
            raise EngineError(
                "source belongs to another research program",
                "evidence cannot cross program boundaries in one claim.",
                "register the source in this program or use the program that owns it.",
            )
        source_id = source.id
        if not quote.strip() or not locator.strip():
            raise EngineError(
                "empirical claim has no quote or locator",
                "a claim without an exact quote and a locator cannot be audited.",
                "pass --quote with the source sentence and --locator with its section, page or line.",
            )
    elif quote.strip():
        raise EngineError(
            "quote supplied for a non-empirical claim",
            "quotes are evidence from a source; derived and assumed claims argue instead.",
            "remove --quote and use --basis for the derivation or assumption.",
        )
    if kind != "empirical" and source_ref:
        raise EngineError(
            "source supplied for a non-empirical claim",
            "only empirical claims cite a source; derived and assumed claims use a basis.",
            "remove --source or record the assertion as empirical.",
        )
    if kind == "derived" and not basis.strip() and not prerequisites:
        raise EngineError(
            "derived claim has no basis",
            "a derived claim must name its premises or its derivation.",
            "pass --basis with the argument or --from with one or more prerequisite claim IDs.",
        )
    prereq_claims = [get_claim(conn, ref) for ref in prerequisites]
    for prereq in prereq_claims:
        if prereq.research_id != research.id:
            raise EngineError(
                "prerequisite belongs to another research program",
                "dependency edges cannot cross program boundaries.",
                "link claims from the same program.",
            )
    with transaction(conn):
        stamp = utc_now()
        record = Claim(
            id=next_id(conn, "c"),
            research_id=research.id,
            source_id=source_id,
            text=text,
            quote=quote.strip(),
            locator=locator.strip(),
            kind=kind,
            basis=basis.strip(),
            kill_test=kill_test.strip(),
            status="UNVERIFIED",
            confidence=confidence,
            created_at=stamp,
            updated_at=stamp,
            revision_of=revision_of,
            revision_reason=revision_reason.strip(),
        )
        conn.execute(
            "INSERT INTO claim(id, research_id, source_id, text, quote, locator, kind, basis,"
            " kill_test, status, confidence, created_at, updated_at, revision_of,"
            " revision_reason) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                record.id,
                record.research_id,
                record.source_id,
                record.text,
                record.quote,
                record.locator,
                record.kind,
                record.basis,
                record.kill_test,
                record.status,
                record.confidence,
                record.created_at,
                record.updated_at,
                record.revision_of,
                record.revision_reason,
            ),
        )
        for prereq in prereq_claims:
            record_edge(conn, "claim", record.id, "claim", prereq.id, "derived_from")
    return record


def get_claim(conn: sqlite3.Connection, ref: str) -> Claim:
    """Fetch one claim by identifier."""
    row = conn.execute("SELECT * FROM claim WHERE id = ?", (ref,)).fetchone()
    if row is None:
        raise NotFound("claim", ref)
    return _to_claim(row)


def list_claims(
    conn: sqlite3.Connection,
    research_ref: str | None = None,
    status: str | None = None,
    include_superseded: bool = False,
) -> List[Claim]:
    """List claims, optionally filtered by program and verdict; hide superseded heads by default."""
    clauses: List[str] = []
    params: List[object] = []
    if research_ref:
        clauses.append("research_id = ?")
        params.append(get_research(conn, research_ref).id)
    if status:
        if status not in CLAIM_STATUSES:
            raise EngineError(
                f"unknown status: {status}",
                f"allowed statuses are {', '.join(CLAIM_STATUSES)}.",
                "pass one of the listed statuses.",
            )
        clauses.append("status = ?")
        params.append(status)
    if not include_superseded:
        clauses.append("superseded_by IS NULL")
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = conn.execute(f"SELECT * FROM claim{where} ORDER BY id", params).fetchall()
    return [_to_claim(row) for row in rows]


def revision_chain(conn: sqlite3.Connection, ref: str) -> List[Claim]:
    """The full revision chain, oldest first, with a cycle guard."""
    claim = get_claim(conn, ref)
    chain = [claim]
    seen = {claim.id}
    while chain[0].revision_of:
        parent = get_claim(conn, chain[0].revision_of)
        if parent.id in seen:
            raise EngineError(
                "claim revision cycle",
                f"the chain revisits {parent.id}, so it cannot be ordered.",
                "repair the revision links before rendering the history.",
            )
        chain.insert(0, parent)
        seen.add(parent.id)
    while chain[-1].superseded_by:
        child = get_claim(conn, chain[-1].superseded_by)
        if child.id in seen:
            raise EngineError(
                "claim revision cycle",
                f"the chain revisits {child.id}, so it cannot be ordered.",
                "repair the revision links before rendering the history.",
            )
        chain.append(child)
        seen.add(child.id)
    return chain


def revise_claim(
    conn: sqlite3.Connection,
    ref: str,
    text: str,
    reason: str,
    source_ref: Optional[str] = None,
    quote: str = "",
    locator: str = "",
    confidence: float = 0.5,
    kill_test: str = "",
    basis: str = "",
    prerequisites: Sequence[str] = (),
    actor: str = "agent",
) -> Claim:
    """Append a revised claim, mark the old one superseded, and move its edges to the head.

    The new claim starts UNVERIFIED: old verdicts stay on the old claim and are never inherited.
    Tests stay bound to the old claim and are reported by REV-002 until deliberately rebound.
    """
    old = get_claim(conn, ref)
    if old.superseded_by:
        raise EngineError(
            f"claim {old.id} is already superseded by {old.superseded_by}",
            "a revision chain has one head; revise the head instead.",
            f"run `claim revise {old.superseded_by}` or inspect `claim history {old.id}`.",
        )
    if not reason.strip():
        raise EngineError(
            "revision has no reason",
            "a later reader must know why the assertion changed.",
            "pass --reason with the new evidence or narrowing.",
        )
    with transaction(conn):
        new = add_claim(
            conn,
            old.research_id,
            text,
            old.kind,
            source_ref=source_ref,
            quote=quote,
            locator=locator,
            confidence=confidence,
            kill_test=kill_test,
            basis=basis,
            prerequisites=prerequisites,
            revision_of=old.id,
            revision_reason=reason,
        )
        rows = conn.execute(
            "SELECT * FROM edge WHERE (src_kind = 'claim' AND src_id = ?)"
            " OR (dst_kind = 'claim' AND dst_id = ?) ORDER BY id",
            (old.id, old.id),
        ).fetchall()
        for row in rows:
            src_id = new.id if str(row["src_id"]) == old.id else str(row["src_id"])
            dst_id = new.id if str(row["dst_id"]) == old.id else str(row["dst_id"])
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
        conn.execute(
            "DELETE FROM edge WHERE (src_kind = 'claim' AND src_id = ?)"
            " OR (dst_kind = 'claim' AND dst_id = ?)",
            (old.id, old.id),
        )
        conn.execute(
            "UPDATE claim SET superseded_by = ? WHERE id = ?", (new.id, old.id)
        )
        record_event(
            conn,
            "claim.revise",
            new.id,
            f"{old.id} -> {new.id}: {reason.strip()}",
            research_id=old.research_id,
            actor=actor,
        )
    return get_claim(conn, new.id)


def current_groups_for_claim(conn: sqlite3.Connection, claim_id: str) -> List[str]:
    """Verified run groups, bound to the current code and inputs, for a claim's tests."""
    from engine.evidence import claim_groups

    return claim_groups(conn, claim_id)


def set_verdict(
    conn: sqlite3.Connection,
    claim_ref: str,
    status: str,
    evidence: str,
    note: str = "",
    actor: str = "agent",
    evidence_group: str = "",
) -> Claim:
    """Append a verdict; promotion needs a kill test, evidence, and current numeric proof."""
    claim = get_claim(conn, claim_ref)
    if status not in CLAIM_STATUSES:
        raise EngineError(
            f"unknown status: {status}",
            f"allowed statuses are {', '.join(CLAIM_STATUSES)}.",
            "pass one of the listed statuses.",
        )
    if status == claim.status:
        raise EngineError(
            f"claim already has status {status}",
            "a verdict must change the recorded state.",
            "choose a different status, or inspect the claim's verdict history.",
        )
    if status in PROMOTED_STATUSES or status in ("FALSIFIED", "RETRACTED", "INVALIDATED"):
        if not evidence.strip():
            raise EngineError(
                f"status {status} has no evidence",
                "a verdict is only as good as the evidence path behind it.",
                "pass --evidence naming the test run, derivation, or analysis.",
            )
    if status in PROMOTED_STATUSES and not claim.kill_test.strip():
        raise EngineError(
            "promotion has no kill test",
            "every proven or numeric claim must name the test most likely to refute it.",
            "record the claim's kill test before promoting it.",
        )
    if status in PROMOTED_STATUSES:
        for prereq in prerequisites(conn, claim.id):
            if prereq.status in NON_SUPPORTING_STATUSES:
                raise EngineError(
                    f"prerequisite {prereq.id} is {prereq.status}",
                    "a claim cannot be promoted while a premise has collapsed.",
                    "replace the premise, or record this claim as INVALIDATED.",
                )
    bound_group = ""
    if status == "NUMERIC":
        groups = current_groups_for_claim(conn, claim.id)
        if not groups:
            from engine.evidence import claim_authority_blocked

            blocked = claim_authority_blocked(conn, claim.id)
            if blocked:
                raise EngineError(
                    "numeric promotion is blocked by an earlier attempt",
                    f"{blocked}; a later pass cannot displace the earliest non-replaceable attempt.",
                    "record a new test, or revise the claim and pre-register a new attempt.",
                )
            raise EngineError(
                "numeric promotion has no current verified run",
                "a NUMERIC verdict claims a measurement; without two agreeing runs bound to the"
                " current code, inputs and command there is no measurement to cite.",
                "bind a deterministic test with `test add`, run `test verify`, then promote.",
            )
        if evidence_group and evidence_group not in groups:
            raise EngineError(
                f"evidence group {evidence_group} is not authoritative for this claim",
                "the named run is not the earliest non-replaceable, currently verified attempt.",
                "pass one of: " + ", ".join(groups) + ".",
            )
        bound_group = evidence_group or groups[0]
    with transaction(conn):
        stamp = utc_now()
        conn.execute(
            "INSERT INTO verdict(id, subject_kind, subject_id, status, previous_status,"
            " evidence, note, actor, at, evidence_group)"
            " VALUES (?, 'claim', ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                next_id(conn, "v"),
                claim.id,
                status,
                claim.status,
                evidence.strip(),
                note.strip(),
                actor,
                stamp,
                bound_group,
            ),
        )
        conn.execute(
            "UPDATE claim SET status = ?, updated_at = ? WHERE id = ?",
            (status, stamp, claim.id),
        )
    return get_claim(conn, claim.id)


def prerequisites(conn: sqlite3.Connection, claim_id: str) -> List[Claim]:
    """Return the claims this claim structurally depends on."""
    marks = ",".join("?" for _ in DEPENDENCY_RELATIONS)
    rows = conn.execute(
        f"SELECT c.* FROM edge e JOIN claim c ON c.id = e.dst_id"
        f" WHERE e.src_kind = 'claim' AND e.src_id = ? AND e.dst_kind = 'claim'"
        f" AND e.rel IN ({marks}) ORDER BY c.id",
        (claim_id, *DEPENDENCY_RELATIONS),
    ).fetchall()
    return [_to_claim(row) for row in rows]


def link_claims(
    conn: sqlite3.Connection, src_ref: str, dst_ref: str, rel: str
) -> str:
    """Add a typed claim-to-claim edge; dependency edges make invalidation transitive."""
    if rel not in CLAIM_CLAIM_RELATIONS and rel not in DEPENDENCY_RELATIONS:
        raise EngineError(
            f"unknown relation: {rel}",
            f"allowed claim relations are {', '.join(CLAIM_CLAIM_RELATIONS + DEPENDENCY_RELATIONS)}.",
            "pass one of the listed relations with --rel.",
        )
    src = get_claim(conn, src_ref)
    dst = get_claim(conn, dst_ref)
    if src.id == dst.id:
        raise EngineError("self edge refused", "a claim cannot relate to itself.", "choose another target.")
    if src.research_id != dst.research_id:
        raise EngineError(
            "claims belong to different research programs",
            "the graph keeps program boundaries explicit.",
            "link claims from the same program.",
        )
    with transaction(conn):
        edge_id = record_edge(conn, "claim", src.id, "claim", dst.id, rel)
    return edge_id


def record_edge(
    conn: sqlite3.Connection,
    src_kind: str,
    src_id: str,
    dst_kind: str,
    dst_id: str,
    rel: str,
) -> str:
    """Insert one typed edge, returning the existing id when the edge is already present."""
    existing = conn.execute(
        "SELECT id FROM edge WHERE src_kind = ? AND src_id = ? AND dst_kind = ?"
        " AND dst_id = ? AND rel = ?",
        (src_kind, src_id, dst_kind, dst_id, rel),
    ).fetchone()
    if existing:
        return str(existing["id"])
    edge_id = next_id(conn, "e")
    conn.execute(
        "INSERT INTO edge(id, src_kind, src_id, dst_kind, dst_id, rel, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (edge_id, src_kind, src_id, dst_kind, dst_id, rel, utc_now()),
    )
    return edge_id


def list_edges(conn: sqlite3.Connection, subject_ref: str) -> List[sqlite3.Row]:
    """Return every edge touching a claim, in either direction."""
    claim = get_claim(conn, subject_ref)
    return conn.execute(
        "SELECT * FROM edge WHERE (src_kind = 'claim' AND src_id = ?)"
        " OR (dst_kind = 'claim' AND dst_id = ?) ORDER BY id",
        (claim.id, claim.id),
    ).fetchall()


def link_to_question(
    conn: sqlite3.Connection, claim_ref: str, question_ref: str, stance: str
) -> str:
    """Attach a claim to a question with a stance used by the consensus score."""
    from engine.models import CLAIM_QUESTION_RELATIONS
    from engine.questions import get_question

    if stance not in CLAIM_QUESTION_RELATIONS:
        raise EngineError(
            f"unknown stance: {stance}",
            f"allowed stances are {', '.join(CLAIM_QUESTION_RELATIONS)}.",
            "pass one of the listed stances with --stance.",
        )
    claim = get_claim(conn, claim_ref)
    question = get_question(conn, question_ref)
    if claim.research_id != question.research_id:
        raise EngineError(
            "claim and question belong to different research programs",
            "questions collect evidence only inside their own program.",
            "link within one program.",
        )
    with transaction(conn):
        return record_edge(conn, "claim", claim.id, "question", question.id, stance)


def iter_edges(conn: sqlite3.Connection) -> Iterable[sqlite3.Row]:
    """Yield every edge for audits that need the whole graph."""
    return conn.execute("SELECT * FROM edge ORDER BY id").fetchall()
