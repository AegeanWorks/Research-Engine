"""Regression tests for defects found in the T-004 audit."""

from __future__ import annotations

import unittest

from engine.analysis import contradictions
from engine.bundle import content_records, export_records
from engine.claims import add_claim, link_to_question, set_verdict
from engine.context import outline
from engine.database import transaction
from engine.diffing import _index, diff_records
from engine.integrity import check, findings_for_research
from engine.killtests import add_test
from engine.merging import merge_claims
from engine.questions import add_question
from engine.researches import create_research
from tests.support import DatabaseCase


class RunIdentityTests(DatabaseCase):
    def test_projected_runs_carry_distinct_stable_ids(self) -> None:
        from engine.demo import seed_demo

        demo = seed_demo(self.conn)
        records, _ = export_records(self.conn, demo["research"])
        projected = [item for item in content_records(records) if item["type"] == "test_run"]
        ids = [item["id"] for item in projected]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(identifier.startswith("run:") for identifier in ids))

    def test_semantic_index_does_not_collapse_runs(self) -> None:
        from engine.demo import seed_demo

        demo = seed_demo(self.conn)
        records, _ = export_records(self.conn, demo["research"])
        index = _index(records, semantic=True)
        run_keys = [key for key in index if key[0] == "test_run"]
        self.assertGreaterEqual(len(run_keys), 2)
        self.assertEqual(len({key[1] for key in run_keys}), len(run_keys))
        self.assertTrue(all(key[1] for key in run_keys))

    def test_a_changed_run_is_reported_by_identity(self) -> None:
        from engine.demo import seed_demo

        demo = seed_demo(self.conn)
        before, _ = export_records(self.conn, demo["research"])
        after = []
        for record in before:
            copy = dict(record)
            if copy["type"] == "test_run" and copy.get("run_tag") == "run2":
                copy["exit_code"] = 1
                copy["passed"] = 0
            after.append(copy)
        result = diff_records(before, after, semantic=True)
        self.assertEqual(result["counts"]["changed"], 1)
        self.assertNotEqual(result["changed"][0]["id"], "")
        self.assertTrue(result["changed"][0]["id"].startswith("run:"))


class ContradictionScopeTests(DatabaseCase):
    def test_the_same_pair_on_two_questions_is_reported_twice(self) -> None:
        research = create_research(self.conn, "Pair scope")
        first = add_question(self.conn, research.id, "First question?")
        second = add_question(self.conn, research.id, "Second question?")
        support = add_claim(self.conn, research.id, "Signal S rises.", "assumption", basis="a")
        against = add_claim(self.conn, research.id, "Signal S falls.", "assumption", basis="b")
        for question in (first, second):
            link_to_question(self.conn, support.id, question.id, "supports")
            link_to_question(self.conn, against.id, question.id, "contradicts")
        pairs = [item for item in contradictions(self.conn, research.id)
                 if item["support"] == support.id]
        self.assertEqual(sorted(item["question"] for item in pairs),
                         sorted([first.id, second.id]))


class MergeFollowThroughTests(DatabaseCase):
    def setUp(self) -> None:
        super().setUp()
        self.research = self.add_research()
        self.keep = add_claim(self.conn, self.research, "Signal S drives O.", "assumption", basis="a")
        self.duplicate = add_claim(self.conn, self.research, "Signal S drives O.", "assumption", basis="b")

    def test_tests_follow_the_survivor(self) -> None:
        test = add_test(
            self.conn, self.research, "Probe", 'python -c "print(1)"',
            claim_ref=self.duplicate.id,
        )
        result = merge_claims(self.conn, self.keep.id, [self.duplicate.id])
        self.assertEqual(result["tests_repointed_from"], [self.duplicate.id])
        row = self.conn.execute("SELECT claim_id FROM killtest WHERE id = ?", (test.id,)).fetchone()
        self.assertEqual(row["claim_id"], self.keep.id)

    def test_merging_into_a_retired_survivor_is_refused(self) -> None:
        set_verdict(self.conn, self.keep.id, "RETRACTED", "withdrawn")
        with self.assertRaises(Exception):
            merge_claims(self.conn, self.keep.id, [self.duplicate.id])

    def test_a_test_left_on_a_retired_claim_warns(self) -> None:
        add_test(
            self.conn, self.research, "Orphan", 'python -c "print(1)"',
            claim_ref=self.duplicate.id,
        )
        set_verdict(self.conn, self.duplicate.id, "INVALIDATED", "premise collapsed")
        findings = [item for item in check(self.conn) if item.code == "TEST-001"]
        self.assertEqual([item.severity for item in findings], ["warning"])
        self.assertEqual(findings[0].subject, "t_000001")


class ScopedAuditTests(DatabaseCase):
    def test_outline_counts_only_its_own_program(self) -> None:
        from engine.demo import seed_demo

        demo = seed_demo(self.conn)
        other = create_research(self.conn, "Broken elsewhere")
        broken = add_claim(self.conn, other.id, "No provenance.", "assumption", basis="a")
        with transaction(self.conn):
            self.conn.execute("UPDATE claim SET kind = 'empirical' WHERE id = ?", (broken.id,))
        self.assertTrue([f for f in findings_for_research(self.conn, other.id)
                         if f.severity == "error"])
        view = outline(self.conn, demo["research"])
        self.assertIn("audit errors 0 warnings", view.text)


if __name__ == "__main__":
    unittest.main()
