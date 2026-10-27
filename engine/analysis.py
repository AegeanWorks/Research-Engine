"""Discovery and ranking over the graph: contradictions, coverage, keystones."""

from __future__ import annotations

import re
import sqlite3
from typing import Dict, List, Sequence, Tuple

from engine.cascade import dependents
from engine.claims import get_claim
from engine.questions import list_questions
from engine.researches import get_research
from engine.synthesis import stance_claims

_STOPWORDS = frozenset(
    "a an the and or of in on for to with by from as is are was were be been being that this"
    " these those it its at into over under than then so such not no but if while because"
    " we our they their he she his her which who whom what when where how can cannot may might"
    " will would should could do does did done have has had more most less least also".split()
)
_WORD = re.compile(r"[A-Za-z][A-Za-z'\-]+")


def keywords(text: str) -> frozenset:
    """Content words of an assertion, lowercased and de-duplicated."""
    return frozenset(
        word.lower() for word in _WORD.findall(str(text)) if word.lower() not in _STOPWORDS
    )


def overlap(left: str, right: str) -> float:
    """Jaccard overlap of two keyword sets, 0.0 when either is empty."""
    first = keywords(left)
    second = keywords(right)
    if not first or not second:
        return 0.0
    return len(first & second) / len(first | second)


def _pair_score(first: sqlite3.Row, second: sqlite3.Row) -> float:
    confidence = (float(first["confidence"]) + float(second["confidence"])) / 2.0
    return round(0.6 * confidence + 0.4 * overlap(str(first["text"]), str(second["text"])), 4)


def contradictions(
    conn: sqlite3.Connection, research_ref: str, min_score: float = 0.0
) -> List[dict]:
    """Pairs of supporting and contradicting claims attached to the same question.

    Scoping to one question is deliberate: two claims about different questions are not in
    conflict, however similar their wording. The score ranks pairs so the most confident and most
    topical disagreement is read first.
    """
    research = get_research(conn, research_ref)
    found: List[dict] = []
    seen = set()
    for question in list_questions(conn, research.id):
        rows = stance_claims(conn, question.id)
        support = [row for _cid, rel, row in rows if rel in ("supports", "answers")]
        against = [row for _cid, rel, row in rows if rel == "contradicts"]
        for left in support:
            for right in against:
                key = (question.id, *sorted((str(left["id"]), str(right["id"]))))
                if key in seen:
                    continue
                score = _pair_score(left, right)
                if score < min_score:
                    continue
                seen.add(key)
                found.append(
                    {
                        "question": question.id,
                        "support": str(left["id"]),
                        "contradicts": str(right["id"]),
                        "score": score,
                        "overlap": round(overlap(str(left["text"]), str(right["text"])), 4),
                        "support_text": str(left["text"]),
                        "contradicts_text": str(right["text"]),
                    }
                )
    return sorted(found, key=lambda item: (-item["score"], item["support"], item["contradicts"]))


def unlinked_contradictions(
    conn: sqlite3.Connection, research_ref: str, min_score: float = 0.35
) -> List[dict]:
    """Claims that contradict each other by keyword overlap but have no `contradicts` edge.

    This is advisory: it proposes a link, it does not create one.
    """
    research = get_research(conn, research_ref)
    claims = conn.execute(
        "SELECT * FROM claim WHERE research_id = ? AND status NOT IN"
        " ('RETRACTED', 'INVALIDATED') ORDER BY id",
        (research.id,),
    ).fetchall()
    existing = {
        tuple(sorted((str(row["src_id"]), str(row["dst_id"]))))
        for row in conn.execute(
            "SELECT src_id, dst_id FROM edge WHERE src_kind = 'claim' AND dst_kind = 'claim'"
            " AND rel = 'contradicts'"
        )
    }
    proposals = []
    for index, left in enumerate(claims):
        for right in claims[index + 1 :]:
            key = tuple(sorted((str(left["id"]), str(right["id"]))))
            if key in existing:
                continue
            score = round(0.4 * float(left["confidence"]) + 0.6 * overlap(
                str(left["text"]), str(right["text"])
            ), 4)
            if score < min_score:
                continue
            proposals.append(
                {
                    "left": str(left["id"]),
                    "right": str(right["id"]),
                    "score": score,
                    "left_text": str(left["text"]),
                    "right_text": str(right["text"]),
                }
            )
    return sorted(proposals, key=lambda item: (-item["score"], item["left"], item["right"]))


def evidence_matrix(conn: sqlite3.Connection, research_ref: str) -> dict:
    """Sources x questions: how many claims each source contributes to each question."""
    research = get_research(conn, research_ref)
    questions = list_questions(conn, research.id)
    sources = conn.execute(
        "SELECT id, title, year FROM source WHERE research_id = ? ORDER BY id", (research.id,)
    ).fetchall()
    counts: Dict[Tuple[str, str], int] = {}
    for row in conn.execute(
        "SELECT c.id, c.source_id, e.dst_id AS question_id FROM claim c"
        " JOIN edge e ON e.src_kind = 'claim' AND e.src_id = c.id AND e.dst_kind = 'question'"
        " WHERE c.research_id = ? AND c.source_id IS NOT NULL",
        (research.id,),
    ):
        key = (str(row["source_id"]), str(row["question_id"]))
        counts[key] = counts.get(key, 0) + 1
    columns = [question.id for question in questions]
    rows = []
    for source in sources:
        cells = [counts.get((str(source["id"]), column), 0) for column in columns]
        rows.append(
            {
                "source": str(source["id"]),
                "title": str(source["title"]),
                "year": source["year"],
                "cells": cells,
                "total": sum(cells),
            }
        )
    gaps = [
        {
            "question": column,
            "covered": sum(1 for row in rows if counts.get((row["source"], column), 0)),
        }
        for column in columns
    ]
    return {"questions": columns, "rows": rows, "gaps": gaps}


def keystone_claims(conn: sqlite3.Connection, research_ref: str, limit: int = 10) -> List[dict]:
    """Claims that the rest of the graph leans on, by transitive dependents and inbound edges."""
    research = get_research(conn, research_ref)
    rows = conn.execute(
        "SELECT id, status, confidence, text FROM claim WHERE research_id = ? ORDER BY id",
        (research.id,),
    ).fetchall()
    inbound: Dict[str, int] = {}
    for row in conn.execute("SELECT dst_id, COUNT(*) AS n FROM edge WHERE dst_kind = 'claim'"
                            " GROUP BY dst_id"):
        inbound[str(row["dst_id"])] = int(row["n"])
    ranked = []
    for row in rows:
        claim_id = str(row["id"])
        downstream = dependents(conn, claim_id)
        ranked.append(
            {
                "claim": claim_id,
                "status": str(row["status"]),
                "confidence": float(row["confidence"]),
                "dependents": len(downstream),
                "max_depth": max((depth for _id, depth in downstream), default=0),
                "inbound": inbound.get(claim_id, 0),
                "text": str(row["text"]),
                "weight": len(downstream) + inbound.get(claim_id, 0),
            }
        )
    ranked.sort(key=lambda item: (-item["weight"], -item["dependents"], item["claim"]))
    return ranked[: max(limit, 1)]


def expose(conn: sqlite3.Connection, claim_ref: str) -> dict:
    """What a claim would take down with it, plus what cites it."""
    claim = get_claim(conn, claim_ref)
    downstream = dependents(conn, claim.id)
    inbound = conn.execute(
        "SELECT rel, src_kind, src_id FROM edge WHERE dst_kind = 'claim' AND dst_id = ?"
        " ORDER BY rel, src_id",
        (claim.id,),
    ).fetchall()
    return {
        "claim": claim.id,
        "status": claim.status,
        "dependents": [{"id": item, "depth": depth} for item, depth in downstream],
        "inbound": [dict(row) for row in inbound],
    }
