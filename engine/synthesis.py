"""Evidence synthesis: weighted consensus, contradiction pairs, and generated reports."""

from __future__ import annotations

import sqlite3
from typing import Dict, List, Tuple

from engine.claims import get_claim
from engine.integrity import findings_for_research
from engine.markdown import bullet, cell, code, sanitize
from engine.questions import list_questions
from engine.researches import get_research, research_counts
from engine.screening import prisma_flow

_STATUS_WEIGHT = {
    "PROVEN": 1.0,
    "NUMERIC": 0.9,
    "UNKNOWN": 0.0,
    "UNVERIFIED": 0.4,
    "FALSIFIED": 0.0,
    "RETRACTED": 0.0,
    "INVALIDATED": 0.0,
}

LIMITS = (
    "PROVEN records an evidence path and a named kill test; it is not a machine-checked proof.",
    "Consensus is a display heuristic over recorded stances; it never changes a verdict.",
    "Numeric evidence is current only while its verified run matches the engine code, declared"
    " inputs and command.",
    "UNKNOWN records that the evidence is missing; it never counts as support.",
    "A numeric test without a negative control has not shown that it can fail.",
    "Sources are registered explicitly; the engine performs no literature crawling.",
    "Single-writer SQLite; concurrent authorship is out of scope.",
)


def stance_claims(conn: sqlite3.Connection, question_id: str) -> List[Tuple[str, str, sqlite3.Row]]:
    rows = conn.execute(
        "SELECT e.rel, c.* FROM edge e JOIN claim c ON c.id = e.src_id"
        " WHERE e.src_kind = 'claim' AND e.dst_kind = 'question' AND e.dst_id = ?"
        " AND e.rel IN ('supports', 'contradicts', 'answers', 'mentions') ORDER BY c.id",
        (question_id,),
    ).fetchall()
    return [(str(row["id"]), str(row["rel"]), row) for row in rows]


def consensus(conn: sqlite3.Connection, question_ref: str) -> float:
    """Confidence-weighted support minus contradiction in [-1, 1]."""
    support = 0.0
    against = 0.0
    for _claim_id, rel, row in stance_claims(conn, question_ref):
        weight = _STATUS_WEIGHT.get(str(row["status"]), 0.0) * float(row["confidence"])
        if rel in ("supports", "answers"):
            support += weight
        elif rel == "contradicts":
            against += weight
    total = support + against
    return 0.0 if total == 0 else round((support - against) / total, 4)


def _contradictions(conn: sqlite3.Connection, question_id: str) -> List[Tuple[str, str]]:
    supports = [cid for cid, rel, _ in stance_claims(conn, question_id) if rel == "supports"]
    against = [cid for cid, rel, _ in stance_claims(conn, question_id) if rel == "contradicts"]
    return [(left, right) for left in supports for right in against]


def _provenance_cell(conn: sqlite3.Connection, row: sqlite3.Row) -> str:
    if row["kind"] == "empirical":
        return f"quote at {row['locator']}"
    if row["basis"]:
        return str(row["basis"])
    if row["source_id"]:
        return f"source {row['source_id']}"
    return "-"


def report(conn: sqlite3.Connection, research_ref: str) -> str:
    """Render a full, reproducible research report from the graph."""
    research = get_research(conn, research_ref)
    counts = research_counts(conn, research.id)
    findings = findings_for_research(conn, research.id)
    lines = [
        f"# {sanitize(research.title, 200)}",
        "",
        f"**Program:** `{research.id}` (`{research.slug}`)  ",
        f"**Scope:** {sanitize(research.scope, 400) or 'not stated'}  ",
        "**Generated from:** the engine database (no hand-written numbers)",
        "",
        "## Inventory",
        "",
        f"- sources: {counts['source']}",
        f"- questions: {counts['question']} ({counts['open_questions']} open)",
        f"- claims: {counts['claim']}",
        f"- hypotheses: {counts['hypothesis']}",
        f"- kill tests: {counts['killtest']}",
        f"- integrity: {sum(f.severity == 'error' for f in findings)} error(s), "
        f"{sum(f.severity == 'warning' for f in findings)} warning(s)",
        "",
    ]

    screening = prisma_flow(conn, research.id)
    if screening["total"]:
        lines.extend(["## Source screening", ""])
        lines.append(
            "| " + " | ".join(screening["counts"]) + " | included fraction |"
        )
        lines.append("|" + "---|" * (len(screening["counts"]) + 1))
        lines.append(
            "| "
            + " | ".join(str(value) for value in screening["counts"].values())
            + f" | {screening['included_fraction']:.2%} |"
        )
        lines.append("")
        if screening["reasons"]:
            lines.append(
                "Exclusions: "
                + ", ".join(f"{cell(name)} ({count})" for name, count in screening["reasons"].items())
            )
            lines.append("")

    lines.extend(["## Questions", ""])
    questions = list_questions(conn, research.id)
    if not questions:
        lines.append("_No questions recorded._")
    for question in questions:
        stance_rows = stance_claims(conn, question.id)
        lines.extend(
            [
                f"### {question.id}: {bullet(question.text, 160)}",
                "",
                f"- status: {question.status}",
                f"- consensus: {consensus(conn, question.id):+.4f} (support vs contradiction, weighted)",
                f"- evidence: {len(stance_rows)} claim(s)",
                "",
            ]
        )
        if not stance_rows:
            lines.append("_No claim is linked to this question._")
        else:
            lines.extend(
                [
                    "| Claim | Stance | Status | Confidence | Assertion | Provenance |",
                    "|---|---|---|---|---|---|",
                ]
            )
            for claim_id, rel, row in stance_rows:
                lines.append(
                    f"| {claim_id} | {rel} | {row['status']} | {float(row['confidence']):.2f} | "
                    f"{cell(row['text'])} | {cell(_provenance_cell(conn, row))} |"
                )
            lines.append("")
        pairs = _contradictions(conn, question.id)
        if pairs:
            lines.append("**Contradictions:** " + ", ".join(f"{a} vs {b}" for a, b in pairs))
            lines.append("")

    lines.extend(["## Hypotheses", ""])
    hypotheses = conn.execute(
        "SELECT * FROM hypothesis WHERE research_id = ? ORDER BY id", (research.id,)
    ).fetchall()
    if not hypotheses:
        lines.append("_No hypotheses pre-registered._")
    for row in hypotheses:
        lines.extend(
            [
                f"### {row['id']}: {bullet(row['statement'], 160)}",
                "",
                f"- status: {row['status']}",
                f"- confidence: {float(row['confidence']):.2f}",
                f"- registered: {row['registered_at']}",
                f"- verification criterion: {bullet(row['criterion'], 400)}",
                f"- outcome note: {bullet(row['outcome_note'], 400) or '-'}",
                "",
            ]
        )

    lines.extend(["## Kill tests", ""])
    tests = conn.execute(
        "SELECT * FROM killtest WHERE research_id = ? ORDER BY id", (research.id,)
    ).fetchall()
    if not tests:
        lines.append("_No executable kill tests._")
    else:
        lines.extend(
            ["| Test | Target | Command | Control | Latest run |", "|---|---|---|---|---|"]
        )
        for row in tests:
            latest = conn.execute(
                "SELECT * FROM test_run WHERE test_id = ? AND role = 'main'"
                " ORDER BY id DESC LIMIT 1",
                (row["id"],),
            ).fetchone()
            outcome = "never run" if latest is None else (
                f"{'PASS' if latest['passed'] else 'FAIL'} (exit {latest['exit_code']})"
            )
            target = row["claim_id"] or row["hypothesis_id"]
            control = "declared" if row["control_command"] else "none"
            lines.append(
                f"| {row['id']} | {target} | `{code(row['command'])}` | {control} | {outcome} |"
            )
        lines.append("")

    lines.extend(["## Measurements", ""])
    measured = conn.execute(
        "SELECT claim_id, group_label, COUNT(*) AS n, AVG(value) AS mean,"
        " MIN(value) AS low, MAX(value) AS high FROM observation"
        " WHERE research_id = ? AND voided = 0"
        " GROUP BY claim_id, group_label ORDER BY claim_id, group_label",
        (research.id,),
    ).fetchall()
    if not measured:
        lines.append("_No observations recorded._")
    else:
        lines.extend(["| Claim | Group | n | min | mean | max |", "|---|---|---|---|---|---|"])
        for row in measured:
            lines.append(
                f"| {row['claim_id']} | {cell(row['group_label'], 40)} | {row['n']} | "
                f"{float(row['low']):.4g} | {float(row['mean']):.4g} | {float(row['high']):.4g} |"
            )
        latest_runs = conn.execute(
            "SELECT subject, kind, at, detail FROM event"
            " WHERE research_id = ? AND kind IN ('claim.stats', 'claim.trend') ORDER BY id",
            (research.id,),
        ).fetchall()
        seen = {}
        for row in latest_runs:
            seen[str(row["subject"])] = row
        for claim_id, row in sorted(seen.items()):
            lines.append(
                f"- {claim_id} last {row['kind']} at {row['at']}: {bullet(row['detail'], 200)}"
            )
        lines.append("")

    lines.extend(["## Audit", ""])
    if not findings:
        lines.append("_No integrity findings._")
    for finding in findings:
        lines.append(
            f"- **{finding.severity.upper()} {finding.code}** `{finding.subject}`: "
            f"{sanitize(finding.message, 400)}"
        )

    lines.extend(["", "## Limits", ""])
    for limit in LIMITS:
        lines.append(f"- {limit}")
    return "\n".join(lines) + "\n"


def scorecard(conn: sqlite3.Connection, research_ref: str) -> str:
    """Render one line per claim, ordered by status then identifier."""
    research = get_research(conn, research_ref)
    order = {status: index for index, status in enumerate(
        ("FALSIFIED", "INVALIDATED", "RETRACTED", "UNVERIFIED", "UNKNOWN", "NUMERIC", "PROVEN")
    )}
    rows = conn.execute(
        "SELECT * FROM claim WHERE research_id = ? ORDER BY id", (research.id,)
    ).fetchall()
    ranked = sorted(rows, key=lambda row: (order.get(str(row["status"]), 99), str(row["id"])))
    lines = [
        f"# Scorecard: {sanitize(research.title, 200)}",
        "",
        "| Claim | Status | Confidence | Assertion |",
        "|---|---|---|---|",
    ]
    for row in ranked:
        lines.append(
            f"| {row['id']} | {row['status']} | {float(row['confidence']):.2f} | "
            f"{cell(row['text'])} |"
        )
    if not ranked:
        lines.append("| - | - | - | no claims |")
    return "\n".join(lines) + "\n"


def claim_detail(conn: sqlite3.Connection, claim_ref: str) -> str:
    """Render one claim with provenance, dependencies, verdicts and linked tests."""
    claim = get_claim(conn, claim_ref)
    lines = [
        f"# {claim.id}: {bullet(claim.text, 240)}",
        "",
        f"- research: {claim.research_id}",
        f"- kind: {claim.kind}",
        f"- status: {claim.status}",
        f"- confidence: {claim.confidence:.2f}",
        f"- kill test: {bullet(claim.kill_test, 300) or '-'}",
        f"- source: {claim.source_id or '-'}",
        f"- quote: {bullet(claim.quote, 300) or '-'}",
        f"- locator: {bullet(claim.locator, 200) or '-'}",
        f"- basis: {bullet(claim.basis, 300) or '-'}",
        "",
        "## Verdict history",
        "",
    ]
    verdicts = conn.execute(
        "SELECT * FROM verdict WHERE subject_kind = 'claim' AND subject_id = ? ORDER BY id",
        (claim.id,),
    ).fetchall()
    if not verdicts:
        lines.append("_No verdict recorded._")
    for row in verdicts:
        bound = f" [{row['evidence_group']}]" if row["evidence_group"] else ""
        lines.append(
            f"- {row['at']} {row['previous_status']} -> {row['status']}{bound}: "
            f"{bullet(row['evidence'], 300)}"
        )
    lines.extend(["", "## Observations", ""])
    groups = conn.execute(
        "SELECT group_label, COUNT(*) AS n, MIN(value) AS low, MAX(value) AS high,"
        " AVG(value) AS mean FROM observation WHERE claim_id = ? AND voided = 0"
        " GROUP BY group_label ORDER BY group_label",
        (claim.id,),
    ).fetchall()
    if not groups:
        lines.append("_No observations recorded._")
    for group in groups:
        lines.append(
            f"- {cell(group['group_label'])}: n={group['n']} min={group['low']:.4g}"
            f" max={group['high']:.4g} mean={group['mean']:.4g}"
        )
    stats_runs = conn.execute(
        "SELECT at, detail FROM event WHERE kind = 'claim.stats' AND subject = ? ORDER BY id DESC",
        (claim.id,),
    ).fetchall()
    for row in stats_runs[:1]:
        lines.append(f"- last statistics run {row['at']}: {bullet(row['detail'], 200)}")

    lines.extend(["", "## Edges", ""])
    edges = conn.execute(
        "SELECT * FROM edge WHERE (src_kind = 'claim' AND src_id = ?)"
        " OR (dst_kind = 'claim' AND dst_id = ?) ORDER BY id",
        (claim.id, claim.id),
    ).fetchall()
    if not edges:
        lines.append("_No edges._")
    for row in edges:
        lines.append(
            f"- {row['src_kind']}:{row['src_id']} --{row['rel']}--> {row['dst_kind']}:{row['dst_id']}"
        )
    return "\n".join(lines) + "\n"


def inventory(conn: sqlite3.Connection) -> Dict[str, int]:
    """Return engine-wide counts used by the CLI overview."""
    tables = (
        "research", "source", "question", "claim", "hypothesis",
        "killtest", "test_run", "verdict", "observation", "event",
    )
    return {table: conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"] for table in tables}
