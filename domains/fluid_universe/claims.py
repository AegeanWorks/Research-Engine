"""Fluid-universe claim ledger and scorecard compatibility.

The fluid project records its claims in Markdown tables. The host keeps the same status
vocabulary, so a table can be mapped into host claim records without a second ontology. This
module parses the two documents and reports disagreements between them; it does not rewrite
either source.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple

from engine.models import CLAIM_STATUSES


@dataclass(frozen=True)
class ClaimRecord:
    claim_id: str
    statement: str
    label: str
    status: str
    qualifier: str
    evidence: str
    kill_test: str


@dataclass(frozen=True)
class ScorecardRow:
    claim_id: str
    status: str
    result: str


def _cells(line: str) -> List[str]:
    """Split a Markdown table row on unescaped pipes."""
    body = line.strip()
    if not body.startswith("|"):
        return []
    cells: List[str] = []
    current: List[str] = []
    escaped = False
    for character in body[1:]:
        if escaped:
            current.append(character)
            escaped = False
        elif character == "\\":
            escaped = True
        elif character == "|":
            cells.append("".join(current).strip())
            current = []
        else:
            current.append(character)
    if current:
        cells.append("".join(current).strip())
    return cells


def _clean(value: str) -> str:
    return value.replace("**", "").replace("`", "").strip()


def split_status(value: str) -> Tuple[str, str]:
    """Return the base status and the parenthesised qualifier, if any."""
    text = _clean(value)
    base, _, rest = text.partition("(")
    status = base.strip().upper()
    qualifier = rest.rstrip(")").strip() if rest else ""
    if status not in CLAIM_STATUSES:
        raise ValueError(f"unknown claim status: {value!r}")
    return status, qualifier


def _is_separator(cells: List[str]) -> bool:
    return bool(cells) and all(set(cell) <= {"-", ":"} for cell in cells)


def parse_claim_table(text: str) -> List[ClaimRecord]:
    """Parse the six-column claim ledger table."""
    records: List[ClaimRecord] = []
    for line in text.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = _cells(line)
        if len(cells) < 6 or cells[0].lower() == "id" or _is_separator(cells):
            continue
        status, qualifier = split_status(cells[3])
        records.append(
            ClaimRecord(
                claim_id=_clean(cells[0]),
                statement=_clean(cells[1]),
                label=_clean(cells[2]),
                status=status,
                qualifier=qualifier,
                evidence=_clean(cells[4]),
                kill_test=_clean(cells[5]),
            )
        )
    return records


def parse_scorecard(text: str) -> List[ScorecardRow]:
    """Parse the three-column one-line scorecard table."""
    rows: List[ScorecardRow] = []
    for line in text.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = _cells(line)
        if len(cells) < 3 or cells[0].lower() == "id" or _is_separator(cells):
            continue
        status, _qualifier = split_status(cells[1])
        rows.append(
            ScorecardRow(
                claim_id=_clean(cells[0]),
                status=status,
                result=_clean(cells[2]),
            )
        )
    return rows


def compare_ledger_and_scorecard(
    claims: Iterable[ClaimRecord], rows: Iterable[ScorecardRow]
) -> List[dict]:
    """Report claims whose ledger and scorecard statuses disagree or are missing."""
    ledger = {claim.claim_id: claim.status for claim in claims}
    scorecard = {row.claim_id: row.status for row in rows}
    problems: List[dict] = []
    for claim_id in sorted(set(ledger) | set(scorecard)):
        left = ledger.get(claim_id)
        right = scorecard.get(claim_id)
        if left != right:
            problems.append(
                {
                    "claim_id": claim_id,
                    "ledger": left,
                    "scorecard": right,
                    "reason": "missing" if left is None or right is None else "status mismatch",
                }
            )
    return problems


def load_claims(root: Path) -> List[ClaimRecord]:
    """Read the external claims.md; the file is referenced, never copied."""
    return parse_claim_table((Path(root) / "claims.md").read_text(encoding="utf-8"))


def load_scorecard(root: Path) -> List[ScorecardRow]:
    """Read the external SCORECARD.md."""
    return parse_scorecard((Path(root) / "SCORECARD.md").read_text(encoding="utf-8"))
