"""Evidence identity: which verified run groups are valid for a test right now.

This module owns the binding arithmetic so that `claims`, `killtests` and `integrity` can share it
without importing each other in a cycle. It reads `killtest` and `test_run` rows and never touches
claims.
"""

from __future__ import annotations

import json
import sqlite3
from typing import Dict, List, Optional, Sequence, Tuple

from engine import attempts
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
    """The identity a run must carry to count as evidence now.

    The negative control is part of the command identity: changing it changes what the test
    proves, so old runs must stop counting.
    """
    current = fingerprint(test_inputs(test))
    return {
        "command_sha256": sha256_text(test.command + "\n--control--\n" + test.control_command),
        "code_sha256": current.code_sha256,
        "inputs_sha256": current.inputs_sha256,
    }


def _groups(
    conn: sqlite3.Connection,
    test_id: str,
    exact: bool,
    current: Optional[Dict[str, str]] = None,
) -> List[str]:
    """Verified main-role groups for one test, newest first, optionally binding-filtered."""
    sql = (
        "SELECT run_group FROM test_run WHERE test_id = ? AND role = 'main'"
        + (" AND command_sha256 = ? AND code_sha256 = ? AND inputs_sha256 = ?" if exact else "")
        + _VERIFIED_GROUPING
        + " ORDER BY MAX(id) DESC"
    )
    params: Sequence[object] = (test_id,)
    if exact:
        if current is None:
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
    """Every historical main-role group that passed twice with identical output."""
    return _groups(conn, test_id, exact=False)


def current_verified_groups(
    conn: sqlite3.Connection, test: KillTest, current: Optional[Dict[str, str]] = None
) -> List[str]:
    """Every main-role group valid for the current code, inputs and command, newest first."""
    return _groups(conn, test.id, exact=True, current=current)


def current_verified_group(conn: sqlite3.Connection, test: KillTest) -> Optional[str]:
    """The newest group valid for the current binding, if any."""
    groups = current_verified_groups(conn, test)
    return groups[0] if groups else None


def control_state(conn: sqlite3.Connection, test: KillTest, group: str) -> dict:
    """Whether the declared control was falsified in one run group.

    `absent` means the test declares no control. `falsified` requires two or more control runs
    that all fail the expectation and agree on their output.
    """
    if not test.control_command:
        return {"declared": False, "group": group, "runs": 0, "falsified": False, "reproducible": False}
    rows = conn.execute(
        "SELECT exit_code, passed, stdout_sha256, stderr_sha256 FROM test_run"
        " WHERE test_id = ? AND run_group = ? AND role = 'control' ORDER BY id",
        (test.id, group),
    ).fetchall()
    fingerprints = {
        (row["exit_code"], row["stdout_sha256"], row["stderr_sha256"]) for row in rows
    }
    return {
        "declared": True,
        "group": group,
        "runs": len(rows),
        "falsified": len(rows) >= MIN_BINDING_RUNS
        and all(not bool(row["passed"]) for row in rows)
        and len(fingerprints) == 1,
        "reproducible": len(fingerprints) == 1,
    }


def authoritative_attempt(conn: sqlite3.Connection, test: KillTest) -> Optional[sqlite3.Row]:
    """The earliest non-replaceable attempt bound to the test's current identity."""
    current = binding(test)
    return attempts.authoritative(
        conn,
        test.id,
        current["command_sha256"],
        current["code_sha256"],
        current["inputs_sha256"],
    )


def authoritative_group(conn: sqlite3.Connection, test: KillTest) -> Optional[str]:
    """The authoritative group when that attempt is also a currently verified group."""
    current = binding(test)
    row = attempts.authoritative(
        conn,
        test.id,
        current["command_sha256"],
        current["code_sha256"],
        current["inputs_sha256"],
    )
    if row is None or str(row["outcome"]) != "completed":
        return None
    group = str(row["run_group"])
    if group not in _groups(conn, test.id, exact=True, current=current):
        return None
    return group


def authority_blocked(conn: sqlite3.Connection, test: KillTest) -> Optional[str]:
    """The reason a later pass cannot be promoted, when the authority is a subject failure."""
    row = authoritative_attempt(conn, test)
    if row is None or str(row["outcome"]) != "subject_failed":
        return None
    reason = str(row["reason"]) or "no reason recorded"
    return f"attempt {row['attempt_no']} was subject_failed ({reason})"


def _claim_tests(conn: sqlite3.Connection, claim_id: str) -> List[KillTest]:
    rows = conn.execute(
        "SELECT * FROM killtest WHERE claim_id = ? ORDER BY id", (claim_id,)
    ).fetchall()
    return [
        KillTest(**{key: row[key] for key in KillTest.__dataclass_fields__}) for row in rows
    ]


def claim_groups(conn: sqlite3.Connection, claim_id: str) -> List[str]:
    """Current verified groups across every test bound to a claim.

    A test with recorded attempts contributes only its authoritative group. A legacy test with
    no attempt rows keeps the pre-v6 any-current-group behaviour.
    """
    groups: List[str] = []
    for test in _claim_tests(conn, claim_id):
        current = binding(test)
        row = attempts.authoritative(
            conn,
            test.id,
            current["command_sha256"],
            current["code_sha256"],
            current["inputs_sha256"],
        )
        if row is None:
            groups.extend(_groups(conn, test.id, exact=True, current=current))
        elif str(row["outcome"]) == "completed":
            group = str(row["run_group"])
            if group in _groups(conn, test.id, exact=True, current=current):
                groups.append(group)
    return groups


def claim_authority_blocked(conn: sqlite3.Connection, claim_id: str) -> Optional[str]:
    """The first subject-failure authority across a claim's tests, if any."""
    for test in _claim_tests(conn, claim_id):
        reason = authority_blocked(conn, test)
        if reason:
            return reason
    return None


def claim_has_historical_evidence(conn: sqlite3.Connection, claim_id: str) -> bool:
    """Whether any test bound to a claim ever produced a verified group."""
    return any(verified_groups(conn, test.id) for test in _claim_tests(conn, claim_id))


def claim_tests(conn: sqlite3.Connection, claim_id: str) -> List[KillTest]:
    """Every test bound to a claim."""
    return _claim_tests(conn, claim_id)
