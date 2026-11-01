"""Deterministic lexical search over the recorded graph.

The engine deliberately has no persistent full-text index: a scan cannot go stale, and SQLite FTS5
is not guaranteed on every Python 3.10 build. Ranking mirrors the phrase-first rule used by the
reference research graph: an exact phrase outranks scattered term hits, and a hit in the primary
field outranks a hit in supporting metadata.
"""

from __future__ import annotations

import re
import sqlite3
from typing import Dict, List, Sequence, Tuple

from engine.context import estimate_tokens, pack
from engine.errors import EngineError
from engine.markdown import sanitize
from engine.researches import get_research

KINDS = ("claim", "source", "question", "hypothesis")
_KIND_ORDER = {kind: index for index, kind in enumerate(KINDS)}
_WORD = re.compile(r"[^\W_]+", re.UNICODE)
_STOPWORDS = frozenset(
    "a an and are as at be but by for from has have if in into is it its of on or that the"
    " their then there these this to was were will with".split()
)
_SNIPPET_WIDTH = 120


def _terms(query: str) -> Tuple[str, ...]:
    """Case-folded query terms, de-duplicated and stripped of one-character noise."""
    words = [word.casefold() for word in _WORD.findall(query) if len(word) >= 2]
    unique = tuple(dict.fromkeys(words))
    content = tuple(word for word in unique if word not in _STOPWORDS)
    return content or unique


def _score(
    needle: str, terms: Sequence[str], blob: str, primary: str
) -> Tuple[int, List[str]]:
    """Phrase-first relevance: exact phrase, primary field, then matched terms."""
    score = 0
    if needle and needle in blob:
        score += 100
    if needle and needle in primary:
        score += 50
    matched = [term for term in terms if term in blob]
    if matched:
        score += sum(3 if term in primary else 1 for term in matched)
    return score, matched


def _snippet(text: str, needle: str, terms: Sequence[str], width: int = _SNIPPET_WIDTH) -> str:
    """A one-line window around the earliest match, with visible cut marks."""
    flat = " ".join(str(text).split())
    if not flat:
        return ""
    lower = flat.casefold()
    positions = []
    for candidate in (needle, *terms):
        if not candidate:
            continue
        found = lower.find(candidate)
        if found >= 0:
            positions.append(found)
    position = min(positions) if positions else 0
    start = max(0, position - width // 3)
    end = min(len(flat), start + width)
    if start:
        space = flat.rfind(" ", 0, start)
        if space >= 0 and start - space <= 20:
            start = space + 1
    if end < len(flat):
        space = flat.find(" ", end)
        if space >= 0 and space - end <= 20:
            end = space
    prefix = "\u2026" if start else ""
    suffix = "\u2026" if end < len(flat) else ""
    return sanitize(prefix + flat[start:end] + suffix, width + 2)


def _fields(kind: str, row: sqlite3.Row) -> List[Tuple[str, str]]:
    """Primary and supporting text for one record, in match-priority order."""
    if kind == "claim":
        return [
            ("text", str(row["text"])),
            ("quote", str(row["quote"])),
            ("basis", str(row["basis"])),
            ("kill_test", str(row["kill_test"])),
            ("locator", str(row["locator"])),
        ]
    if kind == "source":
        return [
            ("title", str(row["title"])),
            ("authors", str(row["authors"])),
            ("doi", str(row["doi"])),
            ("url", str(row["url"])),
            ("kind", str(row["kind"])),
        ]
    if kind == "question":
        return [("text", str(row["text"]))]
    return [
        ("statement", str(row["statement"])),
        ("criterion", str(row["criterion"])),
        ("outcome_note", str(row["outcome_note"])),
    ]


def _rows(
    conn: sqlite3.Connection, kind: str, research_id: str | None, include_superseded: bool
) -> List[sqlite3.Row]:
    """Program-scoped rows for one kind, in stable identifier order."""
    clauses: List[str] = []
    params: List[object] = []
    if research_id is not None:
        clauses.append("research_id = ?")
        params.append(research_id)
    if kind == "claim" and not include_superseded:
        clauses.append("superseded_by IS NULL")
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    return conn.execute(
        f"SELECT * FROM {kind}{where} ORDER BY id", params
    ).fetchall()


def search(
    conn: sqlite3.Connection,
    query: str,
    research_ref: str | None = None,
    kinds: Sequence[str] | None = None,
    limit: int = 5,
    include_superseded: bool = False,
    budget: int = 800,
) -> dict:
    """Rank one query across the graph and return matches with a matched-field snippet."""
    value = " ".join(str(query or "").split())
    if not value:
        raise EngineError(
            "search query is empty",
            "an empty query would match every record and rank nothing.",
            "pass a word or phrase.",
        )
    if int(limit) < 1:
        raise EngineError(
            f"result limit is {limit}",
            "a result set needs at least one row per kind.",
            "pass --limit 1 or more.",
        )
    if int(budget) < 1:
        raise EngineError(
            f"token budget is {budget}",
            "a text view needs a positive budget.",
            "pass --budget 100 or more.",
        )
    selected = tuple(kinds) if kinds else KINDS
    for kind in selected:
        if kind not in KINDS:
            raise EngineError(
                f"unknown search kind: {kind}",
                f"allowed kinds are {', '.join(KINDS)}.",
                "pass one of the listed kinds with --kind.",
            )
    research_id = get_research(conn, research_ref).id if research_ref else None
    needle = value.casefold()
    terms = _terms(value)

    found: List[dict] = []
    counts: Dict[str, dict] = {}
    for kind in selected:
        rows = _rows(conn, kind, research_id, include_superseded)
        hits: List[dict] = []
        for row in rows:
            fields = _fields(kind, row)
            blob = " ".join(item for _name, item in fields).casefold()
            primary = fields[0][1].casefold()
            score, matched = _score(needle, terms, blob, primary)
            if score <= 0:
                continue
            field, text = fields[0]
            for name, candidate in fields:
                lowered = candidate.casefold()
                if (needle and needle in lowered) or any(term in lowered for term in terms):
                    field, text = name, candidate
                    break
            status = str(row["status"]) if "status" in row.keys() else ""
            hits.append(
                {
                    "kind": kind,
                    "id": str(row["id"]),
                    "score": score,
                    "status": status,
                    "field": field,
                    "snippet": _snippet(text, needle, terms),
                    "matched": matched,
                }
            )
        hits.sort(key=lambda item: (-item["score"], item["id"]))
        counts[kind] = {"hits": len(hits), "returned": min(len(hits), int(limit))}
        found.extend(hits[: int(limit)])

    found.sort(key=lambda item: (-item["score"], _KIND_ORDER[item["kind"]], item["id"]))
    total_hits = sum(item["hits"] for item in counts.values())
    returned = len(found)
    lines = [
        f'SEARCH "{sanitize(value, 80)}": {total_hits} hit(s), {returned} result(s)'
    ]
    for item in found:
        lines.append(
            f"  {item['kind']} {item['id']} [{item['status'] or '-'}]"
            f" score={item['score']} {item['field']}: {item['snippet']}"
        )
    kept, omitted, _used = pack(lines, int(budget))
    if omitted:
        kept.append(f"OMITTED: {omitted} more line(s); raise --budget to see them")
    text = "\n".join(kept) + "\n"
    return {
        "query": value,
        "research": research_id or "all",
        "budget_tokens": int(budget),
        "tokens": estimate_tokens(text),
        "counts": counts,
        "results": found,
        "omitted": total_hits - returned,
        "budget_omitted": omitted,
        "text": text,
    }
