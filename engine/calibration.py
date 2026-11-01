"""Hypothesis calibration: score preregistered confidence against recorded outcomes.

Brier and log loss are proper scoring rules over the probabilities the researcher recorded before
the outcome. They describe this program's forecasting record; they are not a posterior, they never
change a hypothesis, and a small resolved set is reported as descriptive rather than decisive.
"""

from __future__ import annotations

import math
import sqlite3
from typing import Dict, List, Optional, Tuple

from engine.database import transaction
from engine.events import record as record_event
from engine.errors import EngineError
from engine.researches import get_research

MIN_RESOLVED = 10
BIN_EDGES = ((0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.0))
_OUTCOME = {"SUPPORTED": 1.0, "REFUTED": 0.0}
_EPS = 1.0e-12


def _clip(probability: float) -> float:
    """Keep log loss finite without turning a certain prediction into a free pass."""
    return min(max(probability, _EPS), 1.0 - _EPS)


def _bin_index(probability: float) -> int:
    """Return the fixed reliability bin for one probability, including exactly 1.0."""
    for index, (low, high) in enumerate(BIN_EDGES):
        if low <= probability < high:
            return index
    return len(BIN_EDGES) - 1


def summary(
    conn: sqlite3.Connection,
    research_ref: str,
    min_resolved: int = MIN_RESOLVED,
) -> dict:
    """Compute the calibration scorecard for one program without writing anything."""
    research = get_research(conn, research_ref)
    if int(min_resolved) < 1:
        raise EngineError(
            f"minimum resolved set is {min_resolved}",
            "a calibration sample needs at least one resolved hypothesis.",
            "pass --min-n 1 or more.",
        )
    rows = conn.execute(
        "SELECT id, confidence, status FROM hypothesis WHERE research_id = ? ORDER BY id",
        (research.id,),
    ).fetchall()

    counts = {
        "total": len(rows),
        "resolved": 0,
        "supported": 0,
        "refuted": 0,
        "inconclusive": 0,
        "preregistered": 0,
    }
    pairs: List[Tuple[str, float, float]] = []
    for row in rows:
        status = str(row["status"])
        if status in _OUTCOME:
            counts["resolved"] += 1
            counts["supported" if status == "SUPPORTED" else "refuted"] += 1
            pairs.append((str(row["id"]), float(row["confidence"]), _OUTCOME[status]))
        elif status == "INCONCLUSIVE":
            counts["inconclusive"] += 1
        else:
            counts["preregistered"] += 1

    resolved = counts["resolved"]
    coverage = round(resolved / counts["total"], 4) if counts["total"] else 0.0
    brier: Optional[float] = None
    log_loss: Optional[float] = None
    base_rate: Optional[float] = None
    brier_baseline: Optional[float] = None
    skill: Optional[float] = None
    if resolved:
        brier = sum((probability - outcome) ** 2 for _id, probability, outcome in pairs) / resolved
        log_loss = -sum(
            outcome * math.log(_clip(probability))
            + (1.0 - outcome) * math.log(_clip(1.0 - probability))
            for _id, probability, outcome in pairs
        ) / resolved
        base_rate = sum(outcome for _id, _probability, outcome in pairs) / resolved
        brier_baseline = sum(
            (base_rate - outcome) ** 2 for _id, _probability, outcome in pairs
        ) / resolved
        skill = 1.0 - brier / brier_baseline if brier_baseline > 0 else None

    bins = []
    for index, (low, high) in enumerate(BIN_EDGES):
        members = [(probability, outcome) for _id, probability, outcome in pairs
                   if _bin_index(probability) == index]
        if members:
            mean_confidence = sum(probability for probability, _outcome in members) / len(members)
            observed = sum(outcome for _probability, outcome in members) / len(members)
            gap = observed - mean_confidence
        else:
            mean_confidence = observed = gap = None
        bins.append(
            {
                "low": low,
                "high": high,
                "n": len(members),
                "mean_confidence": None if mean_confidence is None else round(mean_confidence, 4),
                "observed": None if observed is None else round(observed, 4),
                "gap": None if gap is None else round(gap, 4),
            }
        )

    warnings: List[str] = []
    if resolved == 0:
        warnings.append("no hypothesis has a recorded outcome; calibration is undefined")
    elif resolved < int(min_resolved):
        warnings.append(
            f"{resolved} resolved hypothesis(es); scores are descriptive below {int(min_resolved)}"
        )
    if resolved and base_rate in (0.0, 1.0):
        warnings.append(
            "every resolved outcome has the same label; discrimination cannot be measured"
        )
    for item in bins:
        if item["n"] and item["gap"] is not None and abs(item["gap"]) >= 0.2:
            direction = "overconfident" if item["gap"] < 0 else "underconfident"
            warnings.append(
                f"bin {item['low']:.1f}-{item['high']:.1f} is {direction} by"
                f" {abs(item['gap']):.2f}"
            )

    return {
        "research": research.id,
        "counts": counts,
        "coverage": coverage,
        "min_resolved": int(min_resolved),
        "brier": None if brier is None else round(brier, 6),
        "log_loss": None if log_loss is None else round(log_loss, 6),
        "base_rate": None if base_rate is None else round(base_rate, 6),
        "brier_baseline": None if brier_baseline is None else round(brier_baseline, 6),
        "skill": None if skill is None else round(skill, 6),
        "bins": bins,
        "warnings": warnings,
    }


def score(
    conn: sqlite3.Connection,
    research_ref: str,
    min_resolved: int = MIN_RESOLVED,
    actor: str = "agent",
) -> dict:
    """Score one program and append the calibration run to the event log."""
    result = summary(conn, research_ref, min_resolved)
    counts = result["counts"]
    if result["brier"] is None:
        detail = f"n=0 coverage={result['coverage']:.4f} no resolved outcome"
    else:
        detail = (
            f"n={counts['resolved']} brier={result['brier']:.4f}"
            f" log_loss={result['log_loss']:.4f} coverage={result['coverage']:.4f}"
        )
    with transaction(conn):
        record_event(
            conn,
            "hypothesis.calibration",
            result["research"],
            detail,
            research_id=result["research"],
            actor=actor,
        )
    return result
