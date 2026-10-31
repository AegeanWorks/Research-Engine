"""Provenance requirements and the append-only verdict lifecycle."""

from __future__ import annotations

import unittest

from engine.claims import (
    add_claim,
    get_claim,
    link_claims,
    list_claims,
    prerequisites,
    set_verdict,
)
from engine.errors import EngineError
from tests.support import DatabaseCase


class ClaimTests(DatabaseCase):
    def test_empirical_claim_needs_source_quote_and_locator(self) -> None:
        research = self.add_research()
        source = self.add_source(research)
        with self.assertRaises(EngineError):
            add_claim(self.conn, research, "No source.", "empirical")
        with self.assertRaises(EngineError):
            add_claim(self.conn, research, "No quote.", "empirical", source_ref=source, locator="p. 1")
        with self.assertRaises(EngineError):
            add_claim(self.conn, research, "No locator.", "empirical", source_ref=source, quote="q")

    def test_derived_claim_needs_a_basis_or_premise(self) -> None:
        research = self.add_research()
        with self.assertRaises(EngineError):
            add_claim(self.conn, research, "Derived from nothing.", "derived")

    def test_quote_is_refused_for_non_empirical_claims(self) -> None:
        research = self.add_research()
        with self.assertRaises(EngineError):
            add_claim(self.conn, research, "Assumed.", "assumption", quote="a quote")

    def test_confidence_bounds_are_enforced(self) -> None:
        research = self.add_research()
        with self.assertRaises(EngineError):
            add_claim(self.conn, research, "Too sure.", "assumption", confidence=1.5)

    def test_source_must_share_the_program(self) -> None:
        first = self.add_research("First")
        second = self.add_research("Second")
        foreign = self.add_source(second)
        with self.assertRaises(EngineError):
            add_claim(
                self.conn,
                first,
                "Cross-program evidence.",
                "empirical",
                source_ref=foreign,
                quote="q",
                locator="p. 1",
            )

    def test_prerequisites_create_dependency_edges(self) -> None:
        research = self.add_research()
        root = self.add_empirical(research)
        derived = add_claim(
            self.conn,
            research,
            "Therefore O follows S.",
            "derived",
            basis="modus ponens over the association",
            prerequisites=[root],
        )
        self.assertEqual([claim.id for claim in prerequisites(self.conn, derived.id)], [root])

    def test_verdict_requires_evidence(self) -> None:
        research = self.add_research()
        claim = add_claim(self.conn, research, "Assumed.", "assumption", kill_test="A failing observation.")
        with self.assertRaises(EngineError):
            set_verdict(self.conn, claim.id, "PROVEN", "")

    def test_promotion_requires_a_kill_test(self) -> None:
        research = self.add_research()
        claim = add_claim(self.conn, research, "Assumed.", "assumption")
        with self.assertRaises(EngineError):
            set_verdict(self.conn, claim.id, "PROVEN", "a derivation")

    def test_verdict_history_preserves_previous_status(self) -> None:
        research = self.add_research()
        claim = add_claim(self.conn, research, "Assumed.", "assumption", kill_test="A failing observation.")
        set_verdict(self.conn, claim.id, "PROVEN", "symbolic proof in notes")
        updated = get_claim(self.conn, claim.id)
        self.assertEqual(updated.status, "PROVEN")
        rows = self.conn.execute(
            "SELECT * FROM verdict WHERE subject_kind = 'claim' AND subject_id = ?", (claim.id,)
        ).fetchall()
        self.assertEqual(rows[0]["previous_status"], "UNVERIFIED")
        self.assertEqual(rows[0]["status"], "PROVEN")

    def test_same_status_is_refused(self) -> None:
        research = self.add_research()
        claim = add_claim(self.conn, research, "Assumed.", "assumption", kill_test="A failing observation.")
        set_verdict(self.conn, claim.id, "PROVEN", "proof")
        with self.assertRaises(EngineError):
            set_verdict(self.conn, claim.id, "PROVEN", "proof again")

    def test_promotion_blocked_by_failed_premise(self) -> None:
        research = self.add_research()
        root = self.add_empirical(research)
        set_verdict(self.conn, root, "FALSIFIED", "the cohort failed to replicate")
        derived = add_claim(
            self.conn,
            research,
            "Therefore O follows S.",
            "derived",
            basis="from the failed premise",
            prerequisites=[root],
            kill_test="An intervention that does not move O.",
        )
        with self.assertRaises(EngineError):
            set_verdict(self.conn, derived.id, "PROVEN", "a proof")

    def test_links_are_typed_and_directional(self) -> None:
        research = self.add_research()
        first = self.add_empirical(research, "First assertion.")
        second = self.add_empirical(research, "Second assertion.")
        link_claims(self.conn, first, second, "supports")
        with self.assertRaises(EngineError):
            link_claims(self.conn, first, second, "invented_relation")
        with self.assertRaises(EngineError):
            link_claims(self.conn, first, first, "supports")

    def test_list_filters_by_status(self) -> None:
        research = self.add_research()
        claim = self.add_empirical(research)
        self.assertEqual(len(list_claims(self.conn, research, "UNVERIFIED")), 1)
        set_verdict(self.conn, claim, "FALSIFIED", "replicate failed")
        self.assertEqual(len(list_claims(self.conn, research, "UNVERIFIED")), 0)

    def test_failed_claim_cannot_be_promoted_in_place(self) -> None:
        research = self.add_research()
        claim = add_claim(
            self.conn, research, "Signal S rose.", "assumption",
            kill_test="A replicate in which S falls.",
        )
        set_verdict(self.conn, claim.id, "PROVEN", "a proof")
        set_verdict(self.conn, claim.id, "FALSIFIED", "the replicate failed")
        with self.assertRaises(EngineError) as caught:
            set_verdict(self.conn, claim.id, "PROVEN", "a new proof")
        self.assertIn("cannot be revived", str(caught.exception))
        self.assertEqual(get_claim(self.conn, claim.id).status, "FALSIFIED")

    def test_failed_claim_can_move_to_another_failed_status(self) -> None:
        research = self.add_research()
        claim = add_claim(
            self.conn, research, "Signal S rose.", "assumption",
            kill_test="A replicate in which S falls.",
        )
        set_verdict(self.conn, claim.id, "FALSIFIED", "the replicate failed")
        retired = set_verdict(self.conn, claim.id, "RETRACTED", "withdrawn after the failure")
        self.assertEqual(retired.status, "RETRACTED")


if __name__ == "__main__":
    unittest.main()
