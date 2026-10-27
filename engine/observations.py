"""Recorded observations: the raw measurements a numeric claim is computed from."""

from __future__ import annotations

import math
import sqlite3
from typing import Dict, List, Optional

from engine.artifacts import utc_now
from engine.claims import get_claim
from engine.database import next_id, transaction
from engine.errors import EngineError, NotFound
from engine.events import record as record_event
from engine.models import Observation


def _to_observation(row: sqlite3.Row) -> Observation:
    values = {key: row[key] for key in Observation.__dataclass_fields__}
    values["voided"] = bool(values["voided"])
    return Observation(**values)


def add_observation(
    conn: sqlite3.Connection,
    claim_ref: str,
    group_label: str,
    value: float,
    note: str = "",
    at: Optional[str] = None,
) -> Observation:
    """Record one measurement in a named group; non-finite values are refused."""
    claim = get_claim(conn, claim_ref)
    label = group_label.strip().lower()
    if not label:
        raise EngineError(
            "observation has no group",
            "a measurement is only comparable inside a named group such as `baseline`.",
            "pass --group with a label.",
        )
    if not label.replace("-", "").replace("_", "").isalnum():
        raise EngineError(
            f"invalid group label: {group_label}",
            "group labels are letters, digits, hyphens and underscores.",
            "use a label such as `baseline` or `treatment-2`.",
        )
    number = float(value)
    if not math.isfinite(number):
        raise EngineError(
            f"observation value is not finite: {value}",
            "NaN and infinity cannot enter a mean or an interval.",
            "record the missing value as an observation note instead, or omit it.",
        )
    with transaction(conn):
        record = Observation(
            id=next_id(conn, "ob"),
            research_id=claim.research_id,
            claim_id=claim.id,
            group_label=label,
            value=number,
            note=note.strip(),
            at=(at or utc_now()).strip(),
            voided=False,
            void_reason="",
        )
        conn.execute(
            "INSERT INTO observation(id, research_id, claim_id, group_label, value, note, at,"
            " voided, void_reason) VALUES (?, ?, ?, ?, ?, ?, ?, 0, '')",
            (
                record.id,
                record.research_id,
                record.claim_id,
                record.group_label,
                record.value,
                record.note,
                record.at,
            ),
        )
    return record


def get_observation(conn: sqlite3.Connection, ref: str) -> Observation:
    """Fetch one observation by identifier."""
    row = conn.execute("SELECT * FROM observation WHERE id = ?", (ref,)).fetchone()
    if row is None:
        raise NotFound("observation", ref)
    return _to_observation(row)


def list_observations(
    conn: sqlite3.Connection,
    claim_ref: str,
    group_label: Optional[str] = None,
    include_voided: bool = False,
) -> List[Observation]:
    """Observations of a claim, oldest first, excluding voided rows by default."""
    claim = get_claim(conn, claim_ref)
    clauses = ["claim_id = ?"]
    params: List[object] = [claim.id]
    if group_label:
        clauses.append("group_label = ?")
        params.append(group_label.strip().lower())
    if not include_voided:
        clauses.append("voided = 0")
    rows = conn.execute(
        f"SELECT * FROM observation WHERE {' AND '.join(clauses)} ORDER BY id", params
    ).fetchall()
    return [_to_observation(row) for row in rows]


def void_observation(
    conn: sqlite3.Connection, ref: str, reason: str, actor: str = "agent"
) -> Observation:
    """Retire a measurement without deleting it; the reason stays in the record."""
    observation = get_observation(conn, ref)
    if observation.voided:
        raise EngineError(
            f"observation already voided: {ref}",
            "a void is recorded once and never rewritten.",
            "inspect the observation instead.",
        )
    if not reason.strip():
        raise EngineError(
            "void has no reason",
            "a measurement is only retired with a recorded reason.",
            "pass --reason with the transcription error or exclusion criterion.",
        )
    with transaction(conn):
        conn.execute(
            "UPDATE observation SET voided = 1, void_reason = ? WHERE id = ?",
            (reason.strip(), observation.id),
        )
        record_event(
            conn,
            "observation.void",
            observation.id,
            f"claim {observation.claim_id}: {reason.strip()}",
            research_id=observation.research_id,
            actor=actor,
        )
    return get_observation(conn, observation.id)


def group_values(conn: sqlite3.Connection, claim_ref: str) -> Dict[str, List[float]]:
    """Non-voided values per group, in insertion order."""
    claim = get_claim(conn, claim_ref)
    groups: Dict[str, List[float]] = {}
    for row in conn.execute(
        "SELECT group_label, value FROM observation WHERE claim_id = ? AND voided = 0"
        " ORDER BY id",
        (claim.id,),
    ):
        groups.setdefault(str(row["group_label"]), []).append(float(row["value"]))
    return groups
