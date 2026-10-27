"""Graph integrity: provenance, evidence paths, dependency acyclicity and stale dependents."""

from __future__ import annotations

import json
import sqlite3
from typing import Dict, Iterable, List

from engine.evidence import (
    control_state,
    current_verified_groups,
    verified_groups,
)
from engine.killtests import get_test
from engine.models import (
    BROKEN_SOURCE_STATUSES,
    DEPENDENCY_RELATIONS,
    FAILED_STATUSES,
    Finding,
)

_KIND_TABLES = {"claim": "claim", "question": "question", "hypothesis": "hypothesis", "source": "source"}
_FAILED = tuple(FAILED_STATUSES)
_BROKEN_SOURCES = tuple(BROKEN_SOURCE_STATUSES)


def _finding(code: str, severity: str, subject: str, message: str, fix: str) -> Finding:
    return Finding(code=code, severity=severity, subject=subject, message=message, fix=fix)


def _entity(conn: sqlite3.Connection, kind: str, ref: str) -> sqlite3.Row | None:
    table = _KIND_TABLES.get(kind)
    if not table:
        return None
    return conn.execute(f"SELECT * FROM {table} WHERE id = ?", (ref,)).fetchone()


def _cycles(conn: sqlite3.Connection) -> List[List[str]]:
    marks = ",".join("?" for _ in DEPENDENCY_RELATIONS)
    rows = conn.execute(
        f"SELECT src_id, dst_id FROM edge WHERE src_kind = 'claim' AND dst_kind = 'claim'"
        f" AND rel IN ({marks}) ORDER BY src_id, dst_id",
        DEPENDENCY_RELATIONS,
    ).fetchall()
    graph: Dict[str, List[str]] = {}
    for row in rows:
        graph.setdefault(str(row["src_id"]), []).append(str(row["dst_id"]))
    state: Dict[str, int] = {}
    stack: List[str] = []
    found: List[List[str]] = []
    seen_cycles = set()

    def visit(node: str) -> None:
        state[node] = 1
        stack.append(node)
        for neighbour in graph.get(node, []):
            if state.get(neighbour, 0) == 0:
                visit(neighbour)
            elif state.get(neighbour) == 1:
                start = stack.index(neighbour)
                cycle = stack[start:] + [neighbour]
                key = frozenset(cycle)
                if key not in seen_cycles:
                    seen_cycles.add(key)
                    found.append(cycle)
        stack.pop()
        state[node] = 2

    for node in sorted(graph):
        if state.get(node, 0) == 0:
            visit(node)
    return found


def check(conn: sqlite3.Connection) -> List[Finding]:
    """Return every integrity finding; an empty list means the graph is coherent."""
    findings: List[Finding] = []

    for row in conn.execute(
        "SELECT * FROM claim WHERE kind = 'empirical'"
        " AND (source_id IS NULL OR trim(quote) = '' OR trim(locator) = '')"
    ):
        findings.append(
            _finding(
                "PROV-001",
                "error",
                row["id"],
                "empirical claim lacks a source, exact quote, or locator",
                "record the missing provenance, or reclassify the claim as derived/assumption.",
            )
        )

    for row in conn.execute(
        "SELECT * FROM source WHERE year IS NULL AND trim(doi) = '' AND trim(url) = ''"
    ):
        findings.append(
            _finding(
                "PROV-002",
                "error",
                row["id"],
                "source has no year, DOI or URL",
                "add an identifier so the source can be found again.",
            )
        )

    for row in conn.execute(
        "SELECT * FROM claim WHERE status IN ('PROVEN', 'NUMERIC')"
        " AND (trim(kill_test) = '' OR NOT EXISTS ("
        " SELECT 1 FROM verdict v WHERE v.subject_kind = 'claim' AND v.subject_id = claim.id"
        " AND v.status = claim.status AND trim(v.evidence) <> ''))"
    ):
        findings.append(
            _finding(
                "EVID-001",
                "error",
                row["id"],
                "promoted claim has no kill test or no evidence-backed verdict",
                "record the kill test and the evidence path, or downgrade the claim.",
            )
        )

    for row in conn.execute(
        "SELECT c.* FROM claim c WHERE c.status = 'NUMERIC' AND NOT EXISTS ("
        " SELECT 1 FROM killtest t WHERE t.claim_id = c.id AND EXISTS ("
        "  SELECT 1 FROM (SELECT run_group FROM test_run WHERE test_id = t.id"
        "   AND role = 'main' GROUP BY run_group HAVING COUNT(*) >= 2 AND SUM(passed) = COUNT(*)"
        "   AND COUNT(DISTINCT exit_code || ':' || stdout_sha256 || ':' || stderr_sha256) = 1)))"
    ):
        findings.append(
            _finding(
                "EVID-002",
                "error",
                row["id"],
                "numeric claim has no test that passed twice with identical output",
                "bind a deterministic test and run `test verify`, or relabel the claim.",
            )
        )

    for row in conn.execute(
        "SELECT c.* FROM claim c WHERE c.status = 'UNKNOWN' AND NOT EXISTS ("
        " SELECT 1 FROM verdict v WHERE v.subject_kind = 'claim' AND v.subject_id = c.id"
        " AND v.status = 'UNKNOWN' AND trim(v.evidence) <> '')"
    ):
        findings.append(
            _finding(
                "EVID-007",
                "warning",
                row["id"],
                "UNKNOWN claim has no recorded reason for the missing evidence",
                "record what is missing with `claim verdict --status UNKNOWN --evidence ...`,"
                " or leave the claim UNVERIFIED.",
            )
        )

    for row in conn.execute(
        "SELECT * FROM claim WHERE status = 'NUMERIC' ORDER BY id"
    ):
        tests = [
            get_test(conn, str(test_row["id"]))
            for test_row in conn.execute(
                "SELECT id FROM killtest WHERE claim_id = ? ORDER BY id", (row["id"],)
            ).fetchall()
        ]
        if not tests:
            continue
        if not any(verified_groups(conn, test.id) for test in tests):
            continue
        current = [
            group for test in tests for group in current_verified_groups(conn, test)
        ]
        if not current:
            findings.append(
                _finding(
                    "EVID-005",
                    "error",
                    row["id"],
                    "numeric evidence is stale: no verified run matches the current code,"
                    " inputs and command",
                    "re-run `test verify` for the claim's test, or downgrade the claim.",
                )
            )
            continue
        promotion = conn.execute(
            "SELECT evidence_group FROM verdict WHERE subject_kind = 'claim'"
            " AND subject_id = ? AND status = 'NUMERIC' ORDER BY id DESC LIMIT 1",
            (row["id"],),
        ).fetchone()
        bound = str(promotion["evidence_group"]) if promotion is not None else ""
        if bound not in current:
            findings.append(
                _finding(
                    "EVID-006",
                    "error",
                    row["id"],
                    "the promotion verdict is not tied to a current verified run"
                    f" (bound: {bound or 'none'}; current: {', '.join(current)})",
                    "re-record the verdict against a current group with `claim verdict --group`.",
                )
            )

    # A test that has produced verified evidence is the unit that must be able to fail.
    for row in conn.execute("SELECT id FROM killtest ORDER BY id"):
        groups = verified_groups(conn, str(row["id"]))
        if not groups:
            continue
        test = get_test(conn, str(row["id"]))
        if not test.control_command:
            findings.append(
                _finding(
                    "EVID-008",
                    "warning",
                    test.id,
                    "test produces verified evidence but declares no negative control,"
                    " so vacuity is not excluded",
                    "add `--control CMD` with a command that must fail, then re-verify.",
                )
            )
            continue
        state = control_state(conn, test, groups[0])
        if not state["falsified"]:
            findings.append(
                _finding(
                    "EVID-009",
                    "error",
                    test.id,
                    "the declared negative control never failed reproducibly,"
                    " so the test has not shown it can fail",
                    "make the control fail deterministically twice, then re-verify the test.",
                )
            )

    for row in conn.execute(
        "SELECT c.id, s.id AS source_id, s.screening AS screening"
        " FROM claim c JOIN source s ON s.id = c.source_id"
        " WHERE s.screening IN ('screened_out', 'excluded') AND c.status NOT IN"
        f" ({','.join('?' for _ in _FAILED)}) ORDER BY c.id",
        _FAILED,
    ):
        findings.append(
            _finding(
                "SCREEN-001",
                "warning",
                str(row["id"]),
                f"claim cites source {row['source_id']} screened out of the review"
                f" ({row['screening']})",
                "justify the inclusion, or replace the source and re-record the claim.",
            )
        )

    for row in conn.execute(
        "SELECT c.id, c.status, s.id AS source_id, s.status AS source_status"
        " FROM claim c JOIN source s ON s.id = c.source_id"
        f" WHERE s.status IN ({','.join('?' for _ in _BROKEN_SOURCES)})"
        f" AND c.status NOT IN ({','.join('?' for _ in _FAILED)}) ORDER BY c.id",
        (*_BROKEN_SOURCES, *_FAILED),
    ):
        findings.append(
            _finding(
                "PROV-003",
                "error",
                str(row["id"]),
                f"claim cites retracted source {row['source_id']}",
                "retract the claim (`source retract` does this) or replace the source.",
            )
        )

    for row in conn.execute(
        "SELECT c.id, s.id AS source_id FROM claim c JOIN source s ON s.id = c.source_id"
        " WHERE s.status = 'expression_of_concern' AND c.status NOT IN"
        f" ({','.join('?' for _ in _FAILED)}) ORDER BY c.id",
        _FAILED,
    ):
        findings.append(
            _finding(
                "PROV-004",
                "warning",
                str(row["id"]),
                f"claim cites source {row['source_id']} under an expression of concern",
                "record the concern in the claim note, or replace the source.",
            )
        )

    for row in conn.execute(
        "SELECT c.* FROM claim c WHERE c.status IN ('FALSIFIED', 'RETRACTED', 'INVALIDATED')"
        " AND NOT EXISTS (SELECT 1 FROM verdict v WHERE v.subject_kind = 'claim'"
        " AND v.subject_id = c.id AND v.status = c.status AND trim(v.evidence) <> '')"
    ):
        findings.append(
            _finding(
                "EVID-003",
                "error",
                row["id"],
                f"claim status {row['status']} has no verdict evidence",
                "record the failing evidence, or return the claim to UNVERIFIED.",
            )
        )

    for row in conn.execute(
        "SELECT h.* FROM hypothesis h WHERE h.status IN ('SUPPORTED', 'REFUTED', 'INCONCLUSIVE')"
        " AND NOT EXISTS (SELECT 1 FROM verdict v WHERE v.subject_kind = 'hypothesis'"
        " AND v.subject_id = h.id AND v.status = h.status AND trim(v.evidence) <> '')"
    ):
        findings.append(
            _finding(
                "EVID-004",
                "error",
                row["id"],
                "hypothesis outcome has no evidence-backed verdict",
                "record the outcome evidence, or leave the hypothesis pre-registered.",
            )
        )

    for cycle in _cycles(conn):
        findings.append(
            _finding(
                "GRAPH-001",
                "error",
                cycle[0],
                "dependency cycle: " + " -> ".join(cycle),
                "remove one dependency edge so premises form a DAG.",
            )
        )

    for row in conn.execute("SELECT * FROM edge ORDER BY id"):
        for kind_key, id_key in (("src_kind", "src_id"), ("dst_kind", "dst_id")):
            kind = str(row[kind_key])
            ref = str(row[id_key])
            if _entity(conn, kind, ref) is None:
                findings.append(
                    _finding(
                        "GRAPH-002",
                        "error",
                        str(row["id"]),
                        f"edge points to missing {kind} {ref}",
                        "delete the dangling edge or restore the record.",
                    )
                )

    for row in conn.execute("SELECT * FROM edge ORDER BY id"):
        if row["src_kind"] == row["dst_kind"] and row["src_id"] == row["dst_id"]:
            findings.append(
                _finding(
                    "GRAPH-003",
                    "error",
                    str(row["id"]),
                    "self edge",
                    "delete the edge: a record cannot relate to itself.",
                )
            )
        src = _entity(conn, row["src_kind"], row["src_id"])
        dst = _entity(conn, row["dst_kind"], row["dst_id"])
        if src is None or dst is None:
            continue
        if "research_id" in src.keys() and "research_id" in dst.keys():
            if src["research_id"] != dst["research_id"]:
                findings.append(
                    _finding(
                        "SCOPE-001",
                        "error",
                        str(row["id"]),
                        "edge crosses research programs",
                        "remove the edge or move both records into one program.",
                    )
                )

    marks = ",".join("?" for _ in _FAILED)
    for row in conn.execute(
        f"SELECT e.id, e.src_id, e.dst_id, src.status AS src_status, dst.status AS dst_status"
        f" FROM edge e JOIN claim src ON src.id = e.src_id JOIN claim dst ON dst.id = e.dst_id"
        f" WHERE e.src_kind = 'claim' AND e.dst_kind = 'claim'"
        f" AND e.rel IN ('derived_from', 'depends_on') AND dst.status IN ({marks})"
        f" AND src.status NOT IN ('INVALIDATED', 'RETRACTED')",
        _FAILED,
    ):
        findings.append(
            _finding(
                "CASCADE-001",
                "error",
                str(row["src_id"]),
                f"dependent is {row['src_status']} while premise {row['dst_id']} is {row['dst_status']}",
                "run `claim invalidate` on the premise, or replace the failed premise.",
            )
        )

    for row in conn.execute(
        "SELECT t.id, t.claim_id, c.status FROM killtest t JOIN claim c ON c.id = t.claim_id"
        " WHERE c.status IN ('RETRACTED', 'INVALIDATED') ORDER BY t.id"
    ):
        findings.append(
            _finding(
                "TEST-001",
                "warning",
                str(row["id"]),
                f"test targets retired claim {row['claim_id']} ({row['status']})",
                "bind a test to the surviving claim, or record why the test is kept for history.",
            )
        )

    for row in conn.execute(
        "SELECT q.* FROM question q WHERE q.status = 'open' AND NOT EXISTS ("
        " SELECT 1 FROM edge e WHERE e.dst_kind = 'question' AND e.dst_id = q.id"
        " AND e.src_kind = 'claim' AND e.rel IN ('supports', 'contradicts', 'answers'))"
    ):
        findings.append(
            _finding(
                "GAP-001",
                "warning",
                row["id"],
                "open question has no supporting or contradicting claim",
                "collect evidence, or close the question as out of scope.",
            )
        )

    for row in conn.execute(
        "SELECT c.* FROM claim c WHERE NOT EXISTS ("
        " SELECT 1 FROM edge e WHERE e.src_kind = 'claim' AND e.src_id = c.id"
        " AND e.dst_kind = 'question')"
    ):
        findings.append(
            _finding(
                "GAP-002",
                "warning",
                row["id"],
                "claim is not linked to any question",
                "link it with `claim link-question`, or record why it is standalone.",
            )
        )

    for row in conn.execute(
        "SELECT research_id, text, COUNT(*) AS n FROM claim"
        " WHERE status NOT IN ('RETRACTED', 'INVALIDATED')"
        " GROUP BY research_id, text HAVING n > 1"
    ):
        findings.append(
            _finding(
                "DUP-001",
                "warning",
                str(row["research_id"]),
                f"duplicate claim text appears {row['n']} times",
                "merge duplicates, or differentiate the assertions.",
            )
        )

    for row in conn.execute(
        "SELECT v.id, v.at, h.registered_at FROM verdict v JOIN hypothesis h"
        " ON h.id = v.subject_id WHERE v.subject_kind = 'hypothesis' AND v.at < h.registered_at"
    ):
        findings.append(
            _finding(
                "PRE-001",
                "error",
                str(row["id"]),
                "hypothesis outcome is dated before its registration",
                "restore the chronological record; pre-registration must precede the outcome.",
            )
        )

    for row in conn.execute(
        "SELECT claim_id, MAX(at) AS data_at FROM observation GROUP BY claim_id ORDER BY claim_id"
    ):
        claim_id = str(row["claim_id"])
        analysis = conn.execute(
            "SELECT MAX(at) AS last FROM event WHERE subject = ?"
            " AND kind IN ('claim.stats', 'claim.trend')",
            (claim_id,),
        ).fetchone()["last"]
        observation_ids = [
            str(item["id"])
            for item in conn.execute(
                "SELECT id FROM observation WHERE claim_id = ? ORDER BY id", (claim_id,)
            )
        ]
        voided_at = None
        if observation_ids:
            marks = ",".join("?" for _ in observation_ids)
            voided_at = conn.execute(
                f"SELECT MAX(at) AS last FROM event WHERE kind = 'observation.void'"
                f" AND subject IN ({marks})",
                observation_ids,
            ).fetchone()["last"]
        live = int(
            conn.execute(
                "SELECT COUNT(*) AS n FROM observation WHERE claim_id = ? AND voided = 0",
                (claim_id,),
            ).fetchone()["n"]
        )
        data_at = max(str(row["data_at"]), str(voided_at or ""))
        if analysis is not None and str(analysis) >= data_at:
            continue
        if analysis is None and live == 0:
            continue
        message = (
            "claim has recorded observations but no statistics run"
            if analysis is None
            else "observations changed after the last statistics run"
        )
        findings.append(
            _finding(
                "OBS-001",
                "warning",
                claim_id,
                message,
                "re-run `analysis stats CLAIM --baseline ... --treatment ...` before citing numbers.",
            )
        )

    for row in conn.execute(
        "SELECT r.id FROM research r WHERE NOT EXISTS ("
        " SELECT 1 FROM claim c WHERE c.research_id = r.id)"
    ):
        findings.append(
            _finding(
                "EMPTY-001",
                "warning",
                row["id"],
                "research program has no claims yet",
                "add a claim, or remove the unused program.",
            )
        )

    return findings


def has_errors(findings: Iterable[Finding]) -> bool:
    """Return True when at least one finding blocks a verdict."""
    return any(item.severity == "error" for item in findings)


def render_markdown(findings: Iterable[Finding]) -> str:
    """Render findings as a compact audit table."""
    items = list(findings)
    if not items:
        return "Integrity check: no findings.\n"
    lines = ["# Integrity check", "", f"{sum(i.severity == 'error' for i in items)} error(s), "
             f"{sum(i.severity == 'warning' for i in items)} warning(s).", "",
             "| Severity | Code | Subject | Finding | Fix |", "|---|---|---|---|---|"]
    for item in items:
        lines.append(
            f"| {item.severity} | {item.code} | {item.subject} | "
            f"{item.message.replace('|', '/')} | {item.fix.replace('|', '/')} |"
        )
    return "\n".join(lines) + "\n"


def render_json(findings: Iterable[Finding]) -> str:
    """Render findings as stable machine-readable JSON."""
    payload = [
        {
            "code": item.code,
            "severity": item.severity,
            "subject": item.subject,
            "message": item.message,
            "fix": item.fix,
        }
        for item in findings
    ]
    return json.dumps(payload, indent=2, sort_keys=True)


def findings_for_research(conn: sqlite3.Connection, research_id: str) -> List[Finding]:
    """Findings attributable to one program: its own records, edges and the program itself."""
    ids = {research_id}
    for table in ("claim", "question", "hypothesis", "source", "killtest"):
        for row in conn.execute(f"SELECT id FROM {table} WHERE research_id = ?", (research_id,)):
            ids.add(str(row["id"]))
    members = tuple(ids)
    marks = ",".join("?" for _ in members)
    for row in conn.execute(
        f"SELECT id FROM edge WHERE src_id IN ({marks}) OR dst_id IN ({marks})",
        (*members, *members),
    ):
        ids.add(str(row["id"]))
    return [finding for finding in check(conn) if finding.subject in ids]
