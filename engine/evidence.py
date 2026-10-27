"""Evidence identity: which verified run groups are valid for a test right now.

This module owns the binding arithmetic so that `claims`, `killtests` and `integrity` can share it
without importing each other in a cycle. It reads `killtest` and `test_run` rows and never touches
claims.
"""

from __future__ import annotations

import json
import sqlite3
from typing import Dict, List, Optional, Sequence, Tuple

from engine.artifacts import sha256_text
from engine.models import KillTest
from engine.provenance import fingerprint, resolve_inputs

MIN_BINDING_RUNS = 2
_VERIFIED_GROUPING = (
    " GROUP BY run_group HAVING COUNT(*) >= 2 AND SUM(passed) = COUNT(*)"
    " AND COUNT(DISTINCT exit_code || ':' || stdout_sha256 || ':' || stderr_sha256) = 1"
)


def test_inputs(test: KillTest) -> Tuple[str, ...]:
    """The canonical declared input names of a test."""
    try:
        parsed = json.loads(test.inputs_json or "[]")
    except ValueError:
        return ()
    if not isinstance(parsed, list):
        return ()
    return resolve_inputs([str(item) for item in parsed])


def binding(test: KillTest) -> Dict[str, str]:
    """The identity a run must carry to count as evidence now."""
    current = fingerprint(test_inputs(test))
    return {
        "command_sha256": sha256_text(test.command),
        "code_sha256": current.code_sha256,
        "inputs_sha256": current.inputs_sha256,
    }


def _groups(conn: sqlite3.Connection, test_id: str, exact: bool) -> List[str]:
    """Verified groups for one test, newest first, optionally filtered by binding."""
    sql = (
        "SELECT run_group FROM test_run WHERE test_id = ?"
        + (" AND command_sha256 = ? AND code_sha256 = ? AND inputs_sha256 = ?" if exact else "")
        + _VERIFIED_GROUPING
        + " ORDER BY MAX(id) DESC"
    )
    params: Sequence[object] = (test_id,)
    if exact:
        row = conn.execute("SELECT * FROM killtest WHERE id = ?", (test_id,)).fetchone()
        if row is None:
            return []
        current = binding(KillTest(**{key: row[key] for key in KillTest.__dataclass_fields__}))
        params = (
            test_id,
            current["command_sha256"],
            current["code_sha256"],
            current["inputs_sha256"],
        )
    return [str(item["run_group"]) for item in conn.execute(sql, params).fetchall()]


def verified_groups(conn: sqlite3.Connection, test_id: str) -> List[str]:
    """Every historical run group that passed twice with identical output."""
    return _groups(conn, test_id, exact=False)


def current_verified_groups(conn: sqlite3.Connection, test: KillTest) -> List[str]:
    """Every group valid for the current code, inputs and command, newest first."""
    return _groups(conn, test.id, exact=True)


def current_verified_group(conn: sqlite3.Connection, test: KillTest) -> Optional[str]:
    """The newest group valid for the current binding, if any."""
    groups = current_verified_groups(conn, test)
    return groups[0] if groups else None


def _claim_tests(conn: sqlite3.Connection, claim_id: str) -> List[KillTest]:
    rows = conn.execute(
        "SELECT * FROM killtest WHERE claim_id = ? ORDER BY id", (claim_id,)
    ).fetchall()
    return [
        KillTest(**{key: row[key] for key in KillTest.__dataclass_fields__}) for row in rows
    ]


def claim_groups(conn: sqlite3.Connection, claim_id: str) -> List[str]:
    """Current verified groups across every test bound to a claim."""
    groups: List[str] = []
    for test in _claim_tests(conn, claim_id):
        groups.extend(current_verified_groups(conn, test))
    return groups


def claim_has_historical_evidence(conn: sqlite3.Connection, claim_id: str) -> bool:
    """Whether any test bound to a claim ever produced a verified group."""
    return any(verified_groups(conn, test.id) for test in _claim_tests(conn, claim_id))
