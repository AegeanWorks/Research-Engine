"""Claim revisions: the head carries the edges, the old claim stays as history."""

from __future__ import annotations

import unittest

from engine.claims import (
    add_claim,
    get_claim,
    link_claims,
    link_to_question,
    list_claims,
    list_edges,
    revise_claim,
    revision_chain,
    set_verdict,
)
from engine.errors import EngineError
from engine.integrity import check
from engine.killtests import add_test
from engine.observations import add_observation
from engine.questions import add_question
from tests.support import DatabaseCase


class RevisionTests(DatabaseCase):
    def setUp(self) -> None:
        super().setUp()
        self.research = self.add_research()
        self.source = self.add_source(self.research)
        self.question = add_question(self.conn, self.research, "Does the mechanism hold?")
        self.old = add_claim(
            self.conn,
            self.research,
            "The mechanism holds.",
            "empirical",
            source_ref=self.source,
            quote="The mechanism holds in the tested cohort.",
            locator="Results, p.1",
            kill_test="A cohort where it fails.",
        )
        link_to_question(self.conn, self.old.id, self.question.id, "supports")

    def _revise(self, **overrides):
        reason = overrides.pop("reason", "Narrowed to the tested subgroup.")
        values = {
            "source_ref": self.source,
            "quote": "The mechanism holds in sleep-deprived adults.",
            "locator": "Results, p.2",
        }
        values.update(overrides)
        return revise_claim(
            self.conn,
            self.old.id,
            "The mechanism holds in sleep-deprived adults.",
            reason,
            **values,
        )

    def test_revision_marks_the_old_claim_and_starts_unverified(self) -> None:
        new = self._revise()
        old = get_claim(self.conn, self.old.id)
        self.assertNotEqual(new.id, old.id)
        self.assertEqual(old.superseded_by, new.id)
        self.assertEqual(new.revision_of, old.id)
        self.assertEqual(new.revision_reason, "Narrowed to the tested subgroup.")
        self.assertEqual(new.status, "UNVERIFIED")
        self.assertEqual(old.status, "UNVERIFIED")

    def test_default_list_hides_superseded_and_history_includes_it(self) -> None:
        new = self._revise()
        heads = [claim.id for claim in list_claims(self.conn, self.research)]
        history = [
            claim.id
            for claim in list_claims(self.conn, self.research, include_superseded=True)
        ]
        self.assertIn(new.id, heads)
        self.assertNotIn(self.old.id, heads)
        self.assertIn(self.old.id, history)

    def test_revision_chain_is_oldest_first(self) -> None:
        new = self._revise()
        self.assertEqual([claim.id for claim in revision_chain(self.conn, new.id)],
                         [self.old.id, new.id])

    def test_edges_move_to_the_head(self) -> None:
        new = self._revise()
        self.assertEqual(list_edges(self.conn, self.old.id), [])
        targets = [
            (row["dst_kind"], row["dst_id"], row["rel"])
            for row in list_edges(self.conn, new.id)
        ]
        self.assertIn(("question", self.question.id, "supports"), targets)

    def test_an_empirical_revision_still_needs_a_quote(self) -> None:
        with self.assertRaises(EngineError):
            revise_claim(
                self.conn,
                self.old.id,
                "Narrower.",
                "Narrowed.",
                source_ref=self.source,
                locator="Results, p.2",
            )

    def test_a_revision_needs_a_reason(self) -> None:
        with self.assertRaises(EngineError):
            self._revise(reason=" ")

    def test_a_superseded_claim_cannot_be_revised_again(self) -> None:
        self._revise()
        with self.assertRaises(EngineError):
            self._revise()

    def test_a_test_on_a_superseded_claim_warns(self) -> None:
        test = add_test(
            self.conn,
            self.research,
            "Old probe",
            'python -c "print(1)"',
            claim_ref=self.old.id,
        )
        self._revise()
        findings = [item for item in check(self.conn) if item.code == "REV-002"]
        self.assertEqual([item.subject for item in findings], [test.id])

    def test_a_superseded_claim_refuses_a_new_verdict(self) -> None:
        new = self._revise()
        with self.assertRaises(EngineError):
            set_verdict(self.conn, self.old.id, "PROVEN", "a proof")
        self.assertEqual(get_claim(self.conn, self.old.id).status, "UNVERIFIED")
        self.assertEqual(new.status, "UNVERIFIED")

    def test_a_superseded_claim_refuses_a_new_observation(self) -> None:
        self._revise()
        with self.assertRaises(EngineError):
            add_observation(self.conn, self.old.id, "baseline", 1.0)

    def test_a_superseded_claim_refuses_a_new_test(self) -> None:
        self._revise()
        with self.assertRaises(EngineError):
            add_test(
                self.conn,
                self.research,
                "Late probe",
                'python -c "print(1)"',
                claim_ref=self.old.id,
            )

    def test_a_superseded_claim_refuses_a_new_prerequisite(self) -> None:
        self._revise()
        with self.assertRaises(EngineError):
            add_claim(
                self.conn,
                self.research,
                "Derived from history.",
                "derived",
                basis="a",
                prerequisites=[self.old.id],
            )

    def test_a_superseded_claim_refuses_new_links(self) -> None:
        new = self._revise()
        with self.assertRaises(EngineError):
            link_claims(self.conn, self.old.id, new.id, "related")
        with self.assertRaises(EngineError):
            link_to_question(self.conn, self.old.id, self.question.id, "supports")


if __name__ == "__main__":
    unittest.main()
