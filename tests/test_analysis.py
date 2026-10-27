"""Discovery: contradictions, coverage matrix, keystone ranking, exposure."""

from __future__ import annotations

import unittest

from engine.analysis import (
    contradictions,
    evidence_matrix,
    expose,
    keystone_claims,
    keywords,
    overlap,
    unlinked_contradictions,
)
from engine.claims import add_claim, link_claims, link_to_question
from engine.questions import add_question
from tests.support import DatabaseCase


class KeywordTests(unittest.TestCase):
    def test_stopwords_are_removed(self) -> None:
        self.assertEqual(keywords("the signal and the outcome"), {"signal", "outcome"})

    def test_overlap_is_jaccard(self) -> None:
        self.assertAlmostEqual(overlap("alpha beta", "beta gamma"), 1 / 3, places=4)
        self.assertEqual(overlap("alpha", ""), 0.0)


class AnalysisTests(DatabaseCase):
    def setUp(self) -> None:
        super().setUp()
        from engine.demo import seed_demo

        self.demo = seed_demo(self.conn)

    def test_contradictions_pair_within_a_question(self) -> None:
        pairs = contradictions(self.conn, self.demo["research"])
        keys = {(item["support"], item["contradicts"], item["question"]) for item in pairs}
        self.assertIn((self.demo["claim"], self.demo["opposing_claim"], self.demo["question"]), keys)
        self.assertTrue(all(item["score"] >= 0 for item in pairs))

    def test_contradictions_are_ranked_by_score(self) -> None:
        scores = [item["score"] for item in contradictions(self.conn, self.demo["research"])]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_min_score_filters(self) -> None:
        pairs = contradictions(self.conn, self.demo["research"], min_score=0.99)
        self.assertEqual(pairs, [])

    def test_claims_on_different_questions_are_not_paired(self) -> None:
        research = self.add_research()
        first = add_question(self.conn, research, "Does A hold?")
        second = add_question(self.conn, research, "Does B hold?")
        support = add_claim(self.conn, research, "A holds.", "assumption", basis="a")
        against = add_claim(self.conn, research, "A does not hold.", "assumption", basis="b")
        link_to_question(self.conn, support.id, first.id, "supports")
        link_to_question(self.conn, against.id, second.id, "contradicts")
        self.assertEqual(contradictions(self.conn, research), [])

    def test_unlinked_contradictions_skip_recorded_edges(self) -> None:
        research = self.add_research()
        left = add_claim(self.conn, research, "Signal S rises with outcome O.", "assumption",
                         basis="a", confidence=0.8)
        right = add_claim(self.conn, research, "Signal S falls with outcome O.", "assumption",
                          basis="b", confidence=0.8)
        proposals = unlinked_contradictions(self.conn, research)
        self.assertEqual(len(proposals), 1)
        link_claims(self.conn, left.id, right.id, "contradicts")
        self.assertEqual(unlinked_contradictions(self.conn, research), [])

    def test_matrix_counts_claims_per_source_and_question(self) -> None:
        matrix = evidence_matrix(self.conn, self.demo["research"])
        self.assertEqual(matrix["questions"], [self.demo["question"]])
        self.assertEqual(len(matrix["rows"]), 1)
        self.assertGreaterEqual(matrix["rows"][0]["total"], 1)
        self.assertEqual(matrix["gaps"][0]["question"], self.demo["question"])

    def test_matrix_ignores_assumed_claims(self) -> None:
        research = self.add_research()
        question = add_question(self.conn, research, "Anything?")
        claim = add_claim(self.conn, research, "Assumed.", "assumption", basis="a")
        link_to_question(self.conn, claim.id, question.id, "supports")
        matrix = evidence_matrix(self.conn, research)
        self.assertEqual(matrix["rows"], [])
        self.assertEqual(matrix["gaps"][0]["covered"], 0)

    def test_keystone_ranks_by_downstream_and_inbound(self) -> None:
        ranked = keystone_claims(self.conn, self.demo["research"], limit=3)
        self.assertEqual(len(ranked), 3)
        self.assertEqual(ranked[0]["claim"], self.demo["claim"])
        self.assertEqual(ranked[0]["dependents"], 1)

    def test_expose_lists_dependents_and_inbound(self) -> None:
        exposed = expose(self.conn, self.demo["claim"])
        self.assertEqual([item["id"] for item in exposed["dependents"]],
                         [self.demo["derived_claim"]])
        self.assertTrue(any(item["rel"] == "supports" for item in exposed["inbound"]))


if __name__ == "__main__":
    unittest.main()
