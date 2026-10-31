"""Append-only attempt ledger for kill-test executions.

An attempt is one verification invocation for a test. Its sequence is allocated inside the
writer's transaction, and only `infra_failed` and `indeterminate` attempts are replaceable.
The earliest non-replaceable attempt is authoritative, so a later pass cannot displace an
earlier subject failure.
"""

from __future__ import annotations

import sqlite3
from typing import List, Optional

from engine.artifacts import utc_now
from engine.database import next_id, transaction
from engine.errors import EngineError
from engine.models import (
    ATTEMPT_OUTCOMES,
    REPLACEABLE_ATTEMPT_OUTCOMES,
    Attempt,
)


def _to_attempt(row: sqlite3.Row) -> Attempt:
    return Attempt(**{key: row[key] for key in Attempt.__dataclass_fields__})


def record(
    conn: sqlite3.Connection,
    test_id: str,
    run_group: str,
    outcome: str,
    reason: str = "",
) -> Attempt:
    """Append one attempt; a replaceable outcome requires a recorded reason."""
    if outcome not in ATTEMPT_OUTCOMES:
        raise EngineError(
            f"unknown attempt outcome: {outcome}",
            f"allowed outcomes are {', '.join(ATTEMPT_OUTCOMES)}.",
            "pass one of the listed outcomes.",
        )
    reason = reason.strip()
    if outcome in REPLACEABLE_ATTEMPT_OUTCOMES and not reason:
        raise EngineError(
            f"attempt outcome {outcome} has no reason",
            "a replaceable attempt is only replaceable for a recorded reason.",
            "pass the timeout, crash, drift or non-reproducibility reason.",
        )
    with transaction(conn):
        row = conn.execute(
            "SELECT COALESCE(MAX(attempt_no), 0) + 1 AS next_no"
            " FROM test_attempt WHERE test_id = ?",
            (test_id,),
        ).fetchone()
        attempt = Attempt(
            id=next_id(conn, "a"),
            test_id=test_id,
            attempt_no=int(row["next_no"]),
            run_group=run_group,
            outcome=outcome,
            reason=reason,
            created_at=utc_now(),
        )
        conn.execute(
            "INSERT INTO test_attempt(id, test_id, attempt_no, run_group, outcome, reason,"
            " created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                attempt.id,
                attempt.test_id,
                attempt.attempt_no,
                attempt.run_group,
                attempt.outcome,
                attempt.reason,
                attempt.created_at,
            ),
        )
    return attempt


def authoritative(
    conn: sqlite3.Connection,
    test_id: str,
    command_sha256: str,
    code_sha256: str,
    inputs_sha256: str,
) -> Optional[sqlite3.Row]:
    """The earliest non-replaceable attempt bound to the current command, code and inputs."""
    return conn.execute(
        "SELECT a.* FROM test_attempt a WHERE a.test_id = ?"
        " AND a.outcome IN ('completed', 'subject_failed')"
        " AND EXISTS (SELECT 1 FROM test_run u WHERE u.test_id = a.test_id"
        " AND u.run_group = a.run_group AND u.role = 'main'"
        " AND u.command_sha256 = ? AND u.code_sha256 = ? AND u.inputs_sha256 = ?)"
        " ORDER BY a.attempt_no LIMIT 1",
        (test_id, command_sha256, code_sha256, inputs_sha256),
    ).fetchone()


def for_group(conn: sqlite3.Connection, test_id: str, run_group: str) -> Optional[Attempt]:
    """The attempt recorded for one run group, if any."""
    row = conn.execute(
        "SELECT * FROM test_attempt WHERE test_id = ? AND run_group = ?",
        (test_id, run_group),
    ).fetchone()
    return _to_attempt(row) if row is not None else None


def list_attempts(
    conn: sqlite3.Connection, test_ref: Optional[str] = None, limit: int = 50
) -> List[Attempt]:
    """Attempts for one test or all tests, newest sequence first."""
    if test_ref:
        rows = conn.execute(
            "SELECT * FROM test_attempt WHERE test_id = ? ORDER BY attempt_no DESC LIMIT ?",
            (test_ref, max(int(limit), 1)),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM test_attempt ORDER BY id DESC LIMIT ?", (max(int(limit), 1),)
        ).fetchall()
    return [_to_attempt(row) for row in rows]
