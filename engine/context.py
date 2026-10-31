"""Token-budgeted views: the same graph, measured in tokens for an agent reader."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import List, Sequence, Tuple

from engine.integrity import findings_for_research
from engine.markdown import sanitize
from engine.screening import prisma_flow
from engine.killtests import list_runs
from engine.models import CLAIM_STATUSES
from engine.questions import list_questions
from engine.researches import get_research, research_counts
from engine.synthesis import consensus, stance_claims

CHARS_PER_TOKEN = 4
DEFAULT_BUDGET = 800
RESERVE_TOKENS = 40


@dataclass(frozen=True)
class View:
    """A rendered, bounded view of one program."""

    text: str
    tokens: int
    omitted: int

    def to_dict(self) -> dict:
        return {"text": self.text, "tokens": self.tokens, "omitted": self.omitted}


def estimate_tokens(text: str) -> int:
    """A stable, provider-agnostic estimate: roughly four characters per token."""
    return (len(text) + CHARS_PER_TOKEN - 1) // CHARS_PER_TOKEN


def _clip(text: str, width: int) -> str:
    """Shorten one safe line without exceeding the width."""
    return sanitize(text, width)


def pack(lines: Sequence[str], budget: int) -> Tuple[List[str], int, int]:
    """Fit lines into a budget, always keeping the first, and count what was dropped.

    The first line is the anchor: a reader that sees only one line still learns what the view is
    about. Everything after it is dropped from the end when the budget is exhausted, and the
    dropped count is returned so the reader knows the view is incomplete.
    """
    if budget <= 0:
        raise ValueError("budget must be positive")
    available = max(budget - RESERVE_TOKENS, 1)
    kept: List[str] = []
    used = 0
    for index, line in enumerate(lines):
        cost = estimate_tokens(line) + 1
        if index == 0:
            kept.append(line)
            used += cost
            continue
        if used + cost > available:
            break
        kept.append(line)
        used += cost
    omitted = len(lines) - len(kept)
    return kept, omitted, used


def _render(lines: Sequence[str], budget: int) -> View:
    kept, omitted, used = pack(lines, budget)
    body = list(kept)
    if omitted:
        body.append(f"OMITTED: {omitted} more line(s); raise --budget to see them")
    text = "\n".join(body) + "\n"
    return View(text=text, tokens=estimate_tokens(text), omitted=omitted)


def _status_counts(conn: sqlite3.Connection, research_id: str) -> List[str]:
    lines = []
    for status in CLAIM_STATUSES:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM claim WHERE research_id = ? AND status = ?"
            " AND superseded_by IS NULL",
            (research_id, status),
        ).fetchone()
        if row["n"]:
            lines.append(f"  claims {status}: {row['n']}")
    return lines


def outline(conn: sqlite3.Connection, research_ref: str, budget: int = DEFAULT_BUDGET) -> View:
    """One line per question, hypothesis and test, with counts instead of text."""
    research = get_research(conn, research_ref)
    counts = research_counts(conn, research.id)
    lines = [
        f"OUTLINE {research.id} {research.slug}: {_clip(research.title, 80)}",
        f"  sources {counts['source']} questions {counts['question']}"
        f" claims {counts['claim']} hypotheses {counts['hypothesis']} tests {counts['killtest']}",
    ]
    lines.extend(_status_counts(conn, research.id))
    flow = prisma_flow(conn, research.id)
    if flow["total"]:
        lines.append(
            f"  sources included {flow['included']}/{flow['total']}"
            f" ({flow['included_fraction']:.0%})"
        )
    for question in list_questions(conn, research.id):
        evidence = len(stance_claims(conn, question.id))
        lines.append(
            f"Q {question.id} [{question.status}] evidence={evidence}"
            f" consensus={consensus(conn, question.id):+.2f} {_clip(question.text, 90)}"
        )
    for row in conn.execute(
        "SELECT id, status, confidence, statement FROM hypothesis"
        " WHERE research_id = ? ORDER BY id",
        (research.id,),
    ):
        lines.append(
            f"H {row['id']} [{row['status']}] {float(row['confidence']):.2f}"
            f" {_clip(row['statement'], 80)}"
        )
    for row in conn.execute(
        "SELECT id, name, claim_id, hypothesis_id FROM killtest WHERE research_id = ? ORDER BY id",
        (research.id,),
    ):
        runs = list_runs(conn, str(row["id"]), limit=1)
        latest = "never run" if not runs else ("pass" if runs[0].passed else "fail")
        lines.append(
            f"T {row['id']} {latest} -> {row['claim_id'] or row['hypothesis_id']}"
            f" {_clip(row['name'], 60)}"
        )
    findings = findings_for_research(conn, research.id)
    errors = sum(item.severity == "error" for item in findings)
    warnings = sum(item.severity == "warning" for item in findings)
    lines.append(f"  audit errors {errors} warnings {warnings}")
    return _render(lines, budget)


def brief(conn: sqlite3.Connection, research_ref: str, budget: int = DEFAULT_BUDGET) -> View:
    """Per question: consensus, the strongest support, and the strongest contradiction."""
    research = get_research(conn, research_ref)
    lines = [f"BRIEF {research.id} {research.slug}"]
    for question in list_questions(conn, research.id):
        rows = stance_claims(conn, question.id)
        lines.append(
            f"Q {question.id} consensus={consensus(conn, question.id):+.2f}"
            f" evidence={len(rows)} {_clip(question.text, 80)}"
        )
        support = [row for _cid, rel, row in rows if rel in ("supports", "answers")]
        against = [row for _cid, rel, row in rows if rel == "contradicts"]
        for label, group in (("+", support), ("-", against)):
            if not group:
                continue
            best = max(group, key=lambda row: float(row["confidence"]))
            lines.append(
                f"  {label} {best['id']} [{best['status']}]"
                f" {float(best['confidence']):.2f} {_clip(best['text'], 90)}"
            )
        if not rows:
            lines.append("  no linked evidence")
    return _render(lines, budget)


def claim_brief(conn: sqlite3.Connection, claim_ref: str, budget: int = DEFAULT_BUDGET) -> View:
    """One claim, its provenance, its premises and its verdicts, bounded."""
    from engine.claims import get_claim, prerequisites

    claim = get_claim(conn, claim_ref)
    lines = [
        f"CLAIM {claim.id} [{claim.status}] confidence {claim.confidence:.2f}",
        f"  {_clip(claim.text, 160)}",
        f"  kind {claim.kind} source {claim.source_id or 'none'}",
    ]
    if claim.quote:
        lines.append(f"  quote {_clip(claim.quote, 120)}")
    if claim.locator:
        lines.append(f"  locator {_clip(claim.locator, 80)}")
    if claim.kill_test:
        lines.append(f"  kill test {_clip(claim.kill_test, 120)}")
    for prereq in prerequisites(conn, claim.id):
        lines.append(f"  premise {prereq.id} [{prereq.status}] {_clip(prereq.text, 90)}")
    for row in conn.execute(
        "SELECT status, evidence, at FROM verdict WHERE subject_kind = 'claim'"
        " AND subject_id = ? ORDER BY id",
        (claim.id,),
    ):
        lines.append(
            f"  verdict {row['status']} at {row['at']} evidence {_clip(row['evidence'], 90)}"
        )
    return _render(lines, budget)
