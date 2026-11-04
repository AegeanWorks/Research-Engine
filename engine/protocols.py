"""Measurement protocol registry.

A protocol names what a measurement covers end to end. Two numbers with different protocol ids
are not the same quantity, so `analysis stats` refuses to compare them unless the operator
explicitly allows an incomparable comparison with a caveat.
"""

from __future__ import annotations

import hashlib
import re
import sqlite3
from pathlib import Path
from typing import List

from engine.amendments import record_amendment
from engine.artifacts import utc_now
from engine.database import transaction
from engine.errors import EngineError, NotFound
from engine.events import record as record_event
from engine.models import Protocol

_ID = re.compile(r"[a-z0-9][a-z0-9_-]*")


def _to_protocol(row: sqlite3.Row) -> Protocol:
    values = {key: row[key] for key in Protocol.__dataclass_fields__}
    values["includes_generation"] = bool(values["includes_generation"])
    values["includes_judge"] = bool(values["includes_judge"])
    return Protocol(**values)


def register_protocol(
    conn: sqlite3.Connection,
    protocol_id: str,
    measures: str,
    includes_generation: bool = False,
    includes_judge: bool = False,
    doc_digest: str = "",
    doc_path: str = "",
    actor: str = "agent",
) -> Protocol:
    """Register an immutable protocol id; re-registering the same id is refused."""
    protocol_id = protocol_id.strip().lower()
    if not _ID.fullmatch(protocol_id):
        raise EngineError(
            f"invalid protocol id: {protocol_id}",
            "a protocol id is lowercase letters, digits, hyphens and underscores.",
            "use an id such as `accuracy_at_1` or `end_to_end_judge`.",
        )
    measures = measures.strip()
    if not measures:
        raise EngineError(
            "protocol has no measures text",
            "a protocol must state what it measures end to end.",
            "pass --measures with a short description.",
        )
    doc_digest = doc_digest.strip()
    doc_path = doc_path.strip()
    if doc_path:
        try:
            document = Path(doc_path).read_bytes()
        except OSError:
            raise EngineError(
                "protocol document cannot be read",
                "the --doc-path file is missing or unreadable, so no digest"
                " can be computed for the pin.",
                "pass a readable document path, or omit --doc-path.",
            )
        computed = hashlib.sha256(document).hexdigest()
        if doc_digest and doc_digest != computed:
            raise EngineError(
                "protocol doc digest does not match document",
                "the pinned digest differs from the SHA-256 of the document at"
                " --doc-path, so the pin does not describe that document.",
                "recompute the digest from the current document, or pin the"
                " document the digest was taken from.",
            )
        doc_digest = computed
    if doc_digest and not re.fullmatch(r"[0-9a-f]{64}", doc_digest):
        raise EngineError(
            "protocol doc digest is not a SHA-256 hex string",
            "a protocol definition is pinned by a 64-character lowercase hex digest.",
            "pass the digest of the protocol document, or omit --doc-digest.",
        )
    with transaction(conn):
        existing = conn.execute(
            "SELECT id FROM protocol WHERE id = ?", (protocol_id,)
        ).fetchone()
        if existing is not None:
            raise EngineError(
                f"protocol already registered: {protocol_id}",
                "a protocol id is immutable so old measurements keep their meaning.",
                "register a new id for a changed procedure.",
            )
        record = Protocol(
            id=protocol_id,
            measures=measures,
            includes_generation=bool(includes_generation),
            includes_judge=bool(includes_judge),
            doc_digest=doc_digest,
            registered_at=utc_now(),
        )
        conn.execute(
            "INSERT INTO protocol(id, measures, includes_generation, includes_judge,"
            " doc_digest, registered_at) VALUES (?, ?, ?, ?, ?, ?)",
            (
                record.id,
                record.measures,
                int(record.includes_generation),
                int(record.includes_judge),
                record.doc_digest,
                record.registered_at,
            ),
        )
        record_event(
            conn,
            "protocol.register",
            record.id,
            record.measures,
            actor=actor,
        )
    return record


def get_protocol(conn: sqlite3.Connection, ref: str) -> Protocol:
    """Fetch one registered protocol by id."""
    row = conn.execute("SELECT * FROM protocol WHERE id = ?", (ref.strip().lower(),)).fetchone()
    if row is None:
        raise NotFound("protocol", ref)
    return _to_protocol(row)


def amend_protocol(
    conn: sqlite3.Connection,
    ref: str,
    measures: str,
    reason: str,
    actor: str = "agent",
) -> Protocol:
    """Correct a protocol's measures text; the pin and digest never move.

    The document digest keeps pinning the registered document, so a measures
    correction cannot smuggle in a different document. The before and after go to
    the amendment ledger with the stated reason.
    """
    record = get_protocol(conn, ref)
    measures = measures.strip()
    if not measures:
        raise EngineError(
            "amended measures text is empty",
            "a correction cannot blank the text it fixes.",
            "pass a non-empty --measures value.",
        )
    reason = reason.strip()
    if not reason:
        raise EngineError(
            "amendment has no reason",
            "a correction without a stated reason cannot be audited.",
            "pass --reason naming the error being fixed.",
        )
    if measures == record.measures:
        raise EngineError(
            "amendment changes nothing",
            "the supplied measures already match the record.",
            "pass different text, or leave the record alone.",
        )
    with transaction(conn):
        record_amendment(
            conn, "protocol", record.id, "measures", record.measures, measures,
            reason, actor,
        )
        conn.execute(
            "UPDATE protocol SET measures = ? WHERE id = ?", (measures, record.id)
        )
        record_event(
            conn, "protocol.amend", record.id, f"measures corrected: {reason}",
            actor=actor,
        )
    return get_protocol(conn, record.id)


def list_protocols(conn: sqlite3.Connection) -> List[Protocol]:
    """Every registered protocol, oldest id first."""
    return [
        _to_protocol(row)
        for row in conn.execute("SELECT * FROM protocol ORDER BY id").fetchall()
    ]
