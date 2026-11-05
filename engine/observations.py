"""Recorded observations: the raw measurements a numeric claim is computed from."""

from __future__ import annotations

import csv
import math
import re
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional

from engine.artifacts import utc_now
from engine.claims import get_claim
from engine.database import next_id, transaction
from engine.errors import EngineError, NotFound
from engine.events import record as record_event
from engine.models import (
    AGGREGATIONS,
    INSTRUMENT_KINDS,
    PROVENANCE_CLASSES,
    RATER_KINDS,
    Observation,
)
from engine.protocols import get_protocol


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
    instrument_kind: str = "",
    instrument_id: str = "",
    instrument_digest: str = "",
    rater_kind: str = "",
    rater_id: str = "",
    rater_version: str = "",
    protocol_id: str = "",
    sample_size: int = 1,
    aggregation: str = "raw",
    unit: str = "",
    provenance_class: str = "unclassified",
    producer_path: str = "",
    producer_digest: str = "",
) -> Observation:
    """Record one measurement in a named group; non-finite values are refused.

    Provenance is all-or-nothing: pass the instrument, rater and protocol together, or none of
    them. An unprovenanced record is accepted for legacy data and warned by `OBS-002`.
    """
    claim = get_claim(conn, claim_ref)
    if claim.superseded_by:
        raise EngineError(
            f"claim {claim.id} is superseded by {claim.superseded_by}",
            "a measurement on history cannot support the live graph.",
            f"record the measurement on {claim.superseded_by}, the current head.",
        )
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
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise EngineError(
            f"observation value is not a number: {value!r}",
            "a measurement must parse as a finite number.",
            "pass a numeric value, or record the missing value as an observation note.",
        )
    if not math.isfinite(number):
        raise EngineError(
            f"observation value is not finite: {value}",
            "NaN and infinity cannot enter a mean or an interval.",
            "record the missing value as an observation note instead, or omit it.",
        )
    provenance = (
        instrument_kind,
        instrument_id,
        instrument_digest,
        rater_kind,
        rater_id,
        rater_version,
        protocol_id,
    )
    has_provenance = any(str(item).strip() for item in provenance)
    if has_provenance:
        missing = [
            name
            for name, item in zip(
                (
                    "instrument_kind",
                    "instrument_id",
                    "instrument_digest",
                    "rater_kind",
                    "rater_id",
                    "rater_version",
                    "protocol_id",
                ),
                provenance,
            )
            if not str(item).strip()
        ]
        if missing:
            raise EngineError(
                "measurement provenance is incomplete",
                "missing: " + ", ".join(missing) + ".",
                "pass the instrument, rater and protocol together, or none of them.",
            )
        instrument_kind = instrument_kind.strip().lower()
        rater_kind = rater_kind.strip().lower()
        if instrument_kind not in INSTRUMENT_KINDS:
            raise EngineError(
                f"unknown instrument kind: {instrument_kind}",
                f"allowed kinds are {', '.join(INSTRUMENT_KINDS)}.",
                "pass one of the listed kinds.",
            )
        if rater_kind not in RATER_KINDS:
            raise EngineError(
                f"unknown rater kind: {rater_kind}",
                f"allowed kinds are {', '.join(RATER_KINDS)}.",
                "pass one of the listed kinds.",
            )
        protocol_id = protocol_id.strip().lower()
        get_protocol(conn, protocol_id)
    else:
        instrument_kind = ""
        instrument_id = ""
        instrument_digest = ""
        rater_kind = ""
        rater_id = ""
        rater_version = ""
        protocol_id = ""
    try:
        size_number = float(sample_size)
    except (TypeError, ValueError):
        raise EngineError(
            f"sample size is not an integer: {sample_size}",
            "sample size is the number of observations behind an aggregate.",
            "pass --sample-size with a positive integer.",
        )
    if isinstance(sample_size, bool) or not size_number.is_integer():
        raise EngineError(
            f"sample size is not an integer: {sample_size}",
            "a fractional observation count would silently truncate.",
            "pass --sample-size with a positive integer.",
        )
    sample_size = int(size_number)
    if sample_size < 1:
        raise EngineError(
            f"sample size must be positive: {sample_size}",
            "an aggregate over zero observations has no value.",
            "pass --sample-size 1 or more.",
        )
    aggregation = aggregation.strip().lower() or "raw"
    if aggregation not in AGGREGATIONS:
        raise EngineError(
            f"unknown aggregation: {aggregation}",
            f"allowed aggregations are {', '.join(AGGREGATIONS)}.",
            "pass one of the listed aggregations.",
        )
    unit = unit.strip()
    provenance_class = provenance_class.strip().lower() or "unclassified"
    if provenance_class not in PROVENANCE_CLASSES:
        raise EngineError(
            f"unknown provenance class: {provenance_class}",
            f"allowed classes are {', '.join(PROVENANCE_CLASSES)}.",
            "pass independent, self_reported or unclassified.",
        )
    producer_path = producer_path.strip()
    producer_digest = producer_digest.strip()
    if provenance_class == "self_reported" and not producer_path:
        raise EngineError(
            "self-reported measurement has no producer path",
            "a self-reported number must name the component that produced it.",
            "pass --producer-path with the module or script that generated the value.",
        )
    if producer_digest and not re.fullmatch(r"[0-9a-f]{64}", producer_digest):
        raise EngineError(
            "producer digest is not a SHA-256 hex string",
            "a producer is pinned by a 64-character lowercase hex digest.",
            "pass the digest of the producer, or omit --producer-digest.",
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
            instrument_kind=instrument_kind,
            instrument_id=instrument_id.strip(),
            instrument_digest=instrument_digest.strip(),
            rater_kind=rater_kind,
            rater_id=rater_id.strip(),
            rater_version=rater_version.strip(),
            protocol_id=protocol_id,
            sample_size=sample_size,
            aggregation=aggregation,
            unit=unit,
            provenance_class=provenance_class,
            producer_path=producer_path,
            producer_digest=producer_digest,
        )
        conn.execute(
            "INSERT INTO observation(id, research_id, claim_id, group_label, value, note, at,"
            " voided, void_reason, instrument_kind, instrument_id, instrument_digest,"
            " rater_kind, rater_id, rater_version, protocol_id, sample_size, aggregation, unit,"
            " provenance_class, producer_path, producer_digest)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, 0, '', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                record.id,
                record.research_id,
                record.claim_id,
                record.group_label,
                record.value,
                record.note,
                record.at,
                record.instrument_kind,
                record.instrument_id,
                record.instrument_digest,
                record.rater_kind,
                record.rater_id,
                record.rater_version,
                record.protocol_id,
                record.sample_size,
                record.aggregation,
                record.unit,
                record.provenance_class,
                record.producer_path,
                record.producer_digest,
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


_CSV_GROUP_KEYS = ("group_label", "group")
_CSV_VALUE_KEYS = ("value",)

CSV_TEMPLATE_HEADER = (
    "group_label,value,note,instrument_kind,instrument_id,instrument_digest,"
    "rater_kind,rater_id,rater_version,protocol_id,sample_size,aggregation,"
    "unit,provenance_class,producer_path,producer_digest"
)
"""Canonical header for `observation import-csv`; required: group_label, value."""


def import_observations_csv(
    conn: sqlite3.Connection,
    claim_ref: str,
    path: str | Path,
    actor: str = "agent",
) -> dict:
    """Bulk-record measurements from a CSV file with per-row error isolation.

    Required columns: one group column (`group_label` or `group`) and `value`.
    Optional columns map one-to-one onto `add_observation`: note,
    instrument_kind/id/digest, rater_kind/id/version, protocol_id, sample_size,
    aggregation, unit, provenance_class, producer_path/digest. A bad row is
    skipped with its reason so one bad cell does not fail the whole file (N1
    `DataManager` pattern); a missing file or header is refused loudly.
    """
    claim = get_claim(conn, claim_ref)
    csv_path = Path(str(path)).expanduser()
    imported = 0
    skipped: List[dict] = []
    try:
        with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                raise EngineError(
                    f"observations CSV has no header: {csv_path}",
                    "a bulk import needs named columns to mean anything.",
                    "add a header row with group_label,value and retry.",
                )
            normalized = {str(name).strip().lower(): name for name in reader.fieldnames}
            group_key = next(
                (normalized[key] for key in _CSV_GROUP_KEYS if key in normalized), None
            )
            value_key = next(
                (normalized[key] for key in _CSV_VALUE_KEYS if key in normalized), None
            )
            if group_key is None or value_key is None:
                raise EngineError(
                    f"observations CSV must contain columns {list(_CSV_GROUP_KEYS)} and value",
                    "a measurement is only comparable inside a named group.",
                    "add group_label,value columns and retry.",
                )

            def _cell(row: dict, *names: str) -> str:
                for name in names:
                    if name in row and row[name] not in (None, ""):
                        return str(row[name])
                return ""

            for lineno, row in enumerate(reader, start=2):
                # Resolve the actual header spellings back to values.
                group_raw = row.get(group_key, "")
                value_raw = row.get(value_key, "")
                if (group_raw is None or str(group_raw).strip() == "") and (
                    value_raw is None or str(value_raw).strip() == ""
                ):
                    continue
                try:
                    add_observation(
                        conn,
                        claim.id,
                        str(group_raw or "").strip(),
                        float(str(value_raw).strip()),
                        _cell(row, "note"),
                        instrument_kind=_cell(row, "instrument_kind"),
                        instrument_id=_cell(row, "instrument_id"),
                        instrument_digest=_cell(row, "instrument_digest"),
                        rater_kind=_cell(row, "rater_kind"),
                        rater_id=_cell(row, "rater_id"),
                        rater_version=_cell(row, "rater_version"),
                        protocol_id=_cell(row, "protocol_id", "protocol"),
                        sample_size=_cell(row, "sample_size") or 1,
                        aggregation=_cell(row, "aggregation") or "raw",
                        unit=_cell(row, "unit"),
                        provenance_class=_cell(row, "provenance_class") or "unclassified",
                        producer_path=_cell(row, "producer_path"),
                        producer_digest=_cell(row, "producer_digest"),
                    )
                    imported += 1
                except (EngineError, ValueError, TypeError) as error:
                    skipped.append({"row": lineno, "reason": str(error).splitlines()[0]})
    except OSError as error:
        raise EngineError(
            f"cannot read observations CSV: {csv_path}",
            "a bulk import reads exact bytes from a file that exists.",
            "pass a path to a readable CSV file.",
        ) from error
    _ = actor
    return {
        "claim": claim.id,
        "path": str(csv_path),
        "imported": imported,
        "skipped": len(skipped),
        "skipped_rows": skipped,
    }
