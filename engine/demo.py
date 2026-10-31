"""A self-contained demonstration of every engine mechanic in under ten seconds."""

from __future__ import annotations

import sqlite3
import sys

from engine.cascade import invalidate
from engine.claims import add_claim, link_claims, link_to_question, set_verdict
from engine.hypotheses import add_hypothesis
from engine.killtests import add_test, run_test
from engine.questions import add_question
from engine.researches import create_research, research_counts
from engine.sources import add_source


def seed_demo(conn: sqlite3.Connection) -> dict:
    """Create one synthetic program that exercises provenance, tests, and cascade."""
    research = create_research(
        conn,
        "Demo: mechanism inference",
        scope="Synthetic data only; this program demonstrates mechanics, not a scientific claim.",
    )
    source = add_source(
        conn,
        research.id,
        title="Synthetic cohort study (demonstration data, not a real publication)",
        year=2026,
        kind="dataset",
        authors="Research Engine demo",
        url="https://example.invalid/synthetic-cohort",
    )
    question = add_question(conn, research.id, "Does signal S drive outcome O in the synthetic cohort?")
    claim = add_claim(
        conn,
        research.id,
        "In the synthetic cohort, signal S rose with outcome O.",
        kind="empirical",
        source_ref=source.id,
        quote="In the synthetic cohort, signal S rose with outcome O.",
        locator="Abstract, sentence 1",
        confidence=0.8,
        kill_test="t1: the consistency probe must print the same line twice.",
    )
    derived = add_claim(
        conn,
        research.id,
        "Raising S should raise O if the synthetic association is causal.",
        kind="derived",
        basis="If S rises with O, a causal reading predicts raising S raises O.",
        prerequisites=[claim.id],
        confidence=0.5,
        kill_test="A randomized synthetic run that raises S without raising O.",
    )
    opposing = add_claim(
        conn,
        research.id,
        "The synthetic cohort showed no association between S and O.",
        kind="empirical",
        source_ref=source.id,
        quote="The synthetic cohort showed no association between S and O.",
        locator="Abstract, sentence 2",
        confidence=0.4,
        kill_test="t1: the consistency probe must disagree with the positive finding.",
    )
    link_to_question(conn, claim.id, question.id, "supports")
    link_to_question(conn, derived.id, question.id, "supports")
    link_to_question(conn, opposing.id, question.id, "contradicts")
    link_claims(conn, derived.id, claim.id, "supports")

    hypothesis = add_hypothesis(
        conn,
        research.id,
        "A randomized synthetic intervention on S will raise O.",
        "O fails to rise when S is raised in the randomized synthetic run.",
        confidence=0.6,
        question_ref=question.id,
    )

    test = add_test(
        conn,
        research.id,
        "Synthetic consistency probe",
        'python -c "print(\'kill-test:signal-consistent\')"',
        claim_ref=claim.id,
        timeout_seconds=30,
        control_command=(
            '"' + sys.executable + '" -c "import sys; print(\'kill-test:control-diverged\');'
            ' sys.exit(2)"'
        ),
    )
    run = run_test(conn, test.id, runs=2)
    if not run["verification_complete"]:
        raise RuntimeError("demo kill test did not pass twice")

    set_verdict(
        conn,
        claim.id,
        "NUMERIC",
        f"{test.id} two-run verification",
        evidence_group=run["run_group"],
    )

    withdrawn = add_claim(
        conn,
        research.id,
        "Signal S is stable across the synthetic cohort.",
        kind="empirical",
        source_ref=source.id,
        quote="Signal S is stable across the synthetic cohort.",
        locator="Methods, paragraph 3",
        confidence=0.5,
        kill_test="A synthetic replicate in which S drifts by more than 10%.",
    )
    dependent = add_claim(
        conn,
        research.id,
        "S can therefore be treated as a fixed input in the synthetic model.",
        kind="derived",
        basis="A stable S is a fixed input by definition.",
        prerequisites=[withdrawn.id],
        confidence=0.5,
        kill_test="A replicate with non-negligible drift in S.",
    )
    link_to_question(conn, withdrawn.id, question.id, "supports")
    link_to_question(conn, dependent.id, question.id, "supports")
    collapse = invalidate(
        conn,
        withdrawn.id,
        "FALSIFIED",
        "A later synthetic replicate drifted by 42%, contradicting stability.",
        "demo: synthetic replicate drift",
    )

    return {
        "research": research.id,
        "question": question.id,
        "claim": claim.id,
        "derived_claim": derived.id,
        "opposing_claim": opposing.id,
        "hypothesis": hypothesis.id,
        "test": test.id,
        "run_group": run["run_group"],
        "cascade_root": withdrawn.id,
        "cascade_affected": [item["id"] for item in collapse["affected"]],
        "dependent": dependent.id,
        "counts": research_counts(conn, research.id),
    }
