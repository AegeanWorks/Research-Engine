"""Merging duplicates: survivor, repointed edges, retired duplicates, history kept."""

from __future__ import annotations

import unittest

from engine.claims import add_claim, get_claim, link_claims, link_to_question, prerequisites
from engine.errors import EngineError
from engine.integrity import check
from engine.merging import merge_claims
from engine.questions import add_question
from tests.support import DatabaseCase


class MergeTests(DatabaseCase):
    def setUp(self) -> None:
        super().setUp()
        self.research = self.add_research()
        self.question = add_question(self.conn, self.research, "Does S drive O?")
        self.keep = add_claim(
            self.conn, self.research, "Signal S drives O.", "assumption", basis="a", confidence=0.7
        )
        self.duplicate = add_claim(
            self.conn, self.research, "Signal S drives O.", "assumption", basis="b", confidence=0.5
        )
        link_to_question(self.conn, self.duplicate.id, self.question.id, "supports")

    def test_merge_retires_the_duplicate_and_keeps_history(self) -> None:
        result = merge_claims(self.conn, self.keep.id, [self.duplicate.id])
        self.assertEqual(result["keep"], self.keep.id)
        self.assertEqual(result["retired"], [self.duplicate.id])
        self.assertEqual(get_claim(self.conn, self.duplicate.id).status, "RETRACTED")
        rows = self.conn.execute(
            "SELECT * FROM verdict WHERE subject_id = ?", (self.duplicate.id,)
        ).fetchall()
        self.assertEqual(len(rows), 1)
        self.assertIn(self.keep.id, rows[0]["evidence"])

    def test_edges_are_repointed_to_the_survivor(self) -> None:
        merge_claims(self.conn, self.keep.id, [self.duplicate.id])
        attached = self.conn.execute(
            "SELECT * FROM edge WHERE src_kind = 'claim' AND dst_kind = 'question'"
            " AND dst_id = ?",
            (self.question.id,),
        ).fetchall()
        self.assertEqual([row["src_id"] for row in attached], [self.keep.id])

    def test_dependency_edges_survive_and_feed_the_survivor(self) -> None:
        derived = add_claim(
            self.conn, self.research, "Therefore O follows S.", "derived", basis="from dup",
            prerequisites=[self.duplicate.id],
        )
        merge_claims(self.conn, self.keep.id, [self.duplicate.id])
        self.assertEqual(
            [claim.id for claim in prerequisites(self.conn, derived.id)], [self.keep.id]
        )

    def test_merge_clears_the_duplicate_warning(self) -> None:
        self.assertIn("DUP-001", {finding.code for finding in check(self.conn)})
        merge_claims(self.conn, self.keep.id, [self.duplicate.id])
        self.assertNotIn("DUP-001", {finding.code for finding in check(self.conn)})

    def test_self_merge_is_refused(self) -> None:
        with self.assertRaises(EngineError):
            merge_claims(self.conn, self.keep.id, [self.keep.id])

    def test_empty_duplicate_list_is_refused(self) -> None:
        with self.assertRaises(EngineError):
            merge_claims(self.conn, self.keep.id, [])

    def test_retired_duplicate_is_refused(self) -> None:
        merge_claims(self.conn, self.keep.id, [self.duplicate.id])
        with self.assertRaises(EngineError):
            merge_claims(self.conn, self.keep.id, [self.duplicate.id])

    def test_cross_program_merge_is_refused(self) -> None:
        other = self.add_research("Other")
        foreign = add_claim(self.conn, other, "Elsewhere.", "assumption", basis="a")
        with self.assertRaises(EngineError):
            merge_claims(self.conn, self.keep.id, [foreign.id])

    def test_linking_two_merged_claims_does_not_leave_a_self_edge(self) -> None:
        related = add_claim(self.conn, self.research, "Related claim.", "assumption", basis="c")
        link_claims(self.conn, related.id, self.duplicate.id, "supports")
        merge_claims(self.conn, self.keep.id, [self.duplicate.id])
        self_edges = self.conn.execute(
            "SELECT * FROM edge WHERE src_id = dst_id"
        ).fetchall()
        self.assertEqual(self_edges, [])


if __name__ == "__main__":
    unittest.main()
