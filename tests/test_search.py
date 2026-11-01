"""Deterministic lexical search: phrase ranking, snippets, scope and budget."""

from __future__ import annotations

import unittest

from engine.claims import add_claim, revise_claim
from engine.errors import EngineError
from engine.hypotheses import add_hypothesis
from engine.questions import add_question
from engine.search import search
from engine.sources import add_source
from tests.support import DatabaseCase


class SearchTests(DatabaseCase):
    def add_assumption(self, research: str, text: str, basis: str = "because") -> str:
        return add_claim(self.conn, research, text, "assumption", basis=basis).id

    def test_phrase_beats_scattered_terms(self) -> None:
        research = self.add_research()
        phrase = self.add_assumption(research, "alpha beta gamma")
        scattered = self.add_assumption(research, "alpha appears, then beta appears later")
        result = search(self.conn, "alpha beta", kinds=("claim",))
        ids = [item["id"] for item in result["results"]]
        self.assertEqual(ids[0], phrase)
        scores = {item["id"]: item["score"] for item in result["results"]}
        self.assertGreater(scores[phrase], scores[scattered])

    def test_case_and_punctuation_are_folded(self) -> None:
        research = self.add_research()
        claim = self.add_assumption(research, "Signal S rose with outcome O.")
        result = search(self.conn, "SIGNAL, S", kinds=("claim",))
        self.assertEqual(result["results"][0]["id"], claim)

    def test_all_four_kinds_are_searched(self) -> None:
        research = self.add_research()
        source = add_source(self.conn, research, "Cohort study of signal S", year=2026).id
        question = add_question(self.conn, research, "Does signal S drive outcome O?").id
        hypothesis = add_hypothesis(
            self.conn, research, "Signal S raises O.", "O does not rise when S rises."
        ).id
        claim = self.add_assumption(research, "Signal S rose with O.")
        result = search(self.conn, "signal")
        kinds = {item["kind"] for item in result["results"]}
        self.assertEqual(kinds, {"claim", "source", "question", "hypothesis"})
        self.assertEqual(
            {item["id"] for item in result["results"]},
            {source, question, hypothesis, claim},
        )
        self.assertEqual(result["counts"]["claim"]["hits"], 1)

    def test_research_filter_excludes_other_programs(self) -> None:
        first = self.add_research("First")
        second = self.add_research("Second")
        mine = self.add_assumption(first, "alpha beta")
        self.add_assumption(second, "alpha beta")
        result = search(self.conn, "alpha beta", research_ref=first)
        self.assertEqual([item["id"] for item in result["results"]], [mine])
        self.assertEqual(result["research"], first)

    def test_superseded_claims_are_hidden_unless_requested(self) -> None:
        research = self.add_research()
        old = self.add_assumption(research, "alpha beta original")
        new = revise_claim(
            self.conn, old, "alpha beta refined", "clarify the assertion", basis="refined"
        ).id
        hidden = search(self.conn, "alpha beta", kinds=("claim",))
        self.assertEqual([item["id"] for item in hidden["results"]], [new])
        shown = search(self.conn, "alpha beta", kinds=("claim",), include_superseded=True)
        self.assertEqual({item["id"] for item in shown["results"]}, {old, new})

    def test_snippet_reports_the_matching_field(self) -> None:
        research = self.add_research()
        source = add_source(self.conn, research, "Unrelated title", year=2026).id
        claim = add_claim(
            self.conn,
            research,
            "The assertion itself is about something else.",
            "empirical",
            source_ref=source,
            quote="The exact quoted phrase mentions a hidden signal.",
            locator="Results, paragraph 2",
        ).id
        result = search(self.conn, "hidden signal", kinds=("claim",))
        item = result["results"][0]
        self.assertEqual(item["id"], claim)
        self.assertEqual(item["field"], "quote")
        self.assertIn("hidden signal", item["snippet"])

    def test_budget_reports_omitted_lines(self) -> None:
        research = self.add_research()
        for index in range(8):
            self.add_assumption(research, f"alpha beta claim number {index}")
        result = search(self.conn, "alpha beta", kinds=("claim",), limit=8, budget=60)
        self.assertIn("OMITTED:", result["text"])
        self.assertGreater(result["budget_omitted"], 0)

    def test_result_limit_is_per_kind(self) -> None:
        research = self.add_research()
        for index in range(4):
            self.add_assumption(research, f"alpha beta claim {index}")
        result = search(self.conn, "alpha beta", kinds=("claim",), limit=2)
        self.assertEqual(len(result["results"]), 2)
        self.assertEqual(result["counts"]["claim"], {"hits": 4, "returned": 2})
        self.assertEqual(result["omitted"], 2)

    def test_repeat_is_deterministic(self) -> None:
        research = self.add_research()
        self.add_assumption(research, "alpha beta one")
        self.add_assumption(research, "alpha beta two")
        first = search(self.conn, "alpha beta", kinds=("claim",))
        second = search(self.conn, "alpha beta", kinds=("claim",))
        self.assertEqual(first, second)

    def test_invalid_inputs_are_refused(self) -> None:
        with self.assertRaises(EngineError):
            search(self.conn, "   ")
        research = self.add_research()
        with self.assertRaises(EngineError):
            search(self.conn, "alpha", kinds=("paper",), research_ref=research)
        with self.assertRaises(EngineError):
            search(self.conn, "alpha", limit=0)
        with self.assertRaises(EngineError):
            search(self.conn, "alpha", budget=0)


if __name__ == "__main__":
    unittest.main()
