"""Source status and retraction cascade."""

from __future__ import annotations

import unittest

from engine.claims import add_claim, get_claim
from engine.cascade import retract_source
from engine.errors import EngineError
from engine.integrity import check
from engine.cascade import retract_source
from engine.sources import get_source, set_source_status
from tests.support import DatabaseCase


class SourceStatusTests(DatabaseCase):
    def test_downgrade_requires_a_note(self) -> None:
        research = self.add_research()
        source = self.add_source(research)
        with self.assertRaises(EngineError):
            set_source_status(self.conn, source, "expression_of_concern", "")
        updated = set_source_status(
            self.conn, source, "expression_of_concern", "journal notice 2026-10"
        )
        self.assertEqual(updated.status, "expression_of_concern")
        self.assertTrue(updated.status_at)

    def test_unknown_status_and_repeat_are_refused(self) -> None:
        research = self.add_research()
        source = self.add_source(research)
        with self.assertRaises(EngineError):
            set_source_status(self.conn, source, "dubious", "note")
        with self.assertRaises(EngineError):
            set_source_status(self.conn, source, "active", "note")

    def test_direct_retracted_status_routes_through_retraction(self) -> None:
        research = self.add_research()
        source = self.add_source(research)
        with self.assertRaises(EngineError):
            set_source_status(self.conn, source, "retracted", "notice")

    def test_retraction_path_retires_and_refuses_repeats(self) -> None:
        research = self.add_research()
        source = self.add_source(research)
        retract_source(self.conn, source, "notice", "evidence")
        self.assertEqual(get_source(self.conn, source).status, "retracted")
        with self.assertRaises(EngineError):
            retract_source(self.conn, source, "notice", "evidence")

    def test_retraction_requires_a_reason(self) -> None:
        research = self.add_research()
        source = self.add_source(research)
        with self.assertRaises(EngineError):
            retract_source(self.conn, source, "  ", "evidence")

    def test_retraction_requires_evidence(self) -> None:
        research = self.add_research()
        source = self.add_source(research)
        with self.assertRaises(EngineError):
            retract_source(self.conn, source, "notice", "   ")

    def test_retraction_ignores_superseded_claims(self) -> None:
        from engine.claims import revise_claim

        research = self.add_research()
        source = self.add_source(research)
        claim = add_claim(
            self.conn, research, "S rose with O.", "empirical",
            source_ref=source, quote="S rose with O.", locator="p.1",
            kill_test="A replicate.",
        )
        head = revise_claim(
            self.conn, claim.id, "S rose with O, narrowly.", "narrower scope",
            source_ref=source, quote="S rose with O.", locator="p.1",
            kill_test="A replicate.",
        )
        result = retract_source(self.conn, source, "notice", "evidence")
        self.assertEqual(get_source(self.conn, source).status, "retracted")
        self.assertEqual(get_claim(self.conn, claim.id).status, "UNVERIFIED")
        self.assertEqual(get_claim(self.conn, head.id).status, "RETRACTED")
        self.assertEqual([item["id"] for item in result["affected"]], [head.id])

    def test_retraction_retires_claims_and_dependents(self) -> None:
        research = self.add_research()
        source = self.add_source(research)
        claim = add_claim(
            self.conn, research, "S rose with O.", "empirical",
            source_ref=source, quote="S rose with O.", locator="p.1",
            kill_test="A replicate where S rises and O falls.",
        )
        derived = add_claim(
            self.conn, research, "Therefore S drives O.", "derived",
            basis="from the association", prerequisites=[claim.id],
        )
        result = retract_source(
            self.conn, source, "journal retraction notice", "retraction notice 2026-10"
        )
        self.assertEqual(result["status"], "retracted")
        self.assertEqual(get_source(self.conn, source).status, "retracted")
        self.assertEqual(get_claim(self.conn, claim.id).status, "RETRACTED")
        self.assertEqual(get_claim(self.conn, derived.id).status, "INVALIDATED")
        self.assertEqual([item["id"] for item in result["affected"]], [claim.id])
        self.assertIn(derived.id, result["affected"][0]["cascade"])

    def test_retracting_twice_is_refused(self) -> None:
        research = self.add_research()
        source = self.add_source(research)
        retract_source(self.conn, source, "notice", "evidence")
        with self.assertRaises(EngineError):
            retract_source(self.conn, source, "notice", "evidence")

    def test_claims_are_left_alone_when_already_failed(self) -> None:
        research = self.add_research()
        source = self.add_source(research)
        claim = add_claim(
            self.conn, research, "S rose with O.", "empirical",
            source_ref=source, quote="S rose with O.", locator="p.1",
            kill_test="A replicate.",
        )
        from engine.claims import set_verdict

        set_verdict(self.conn, claim.id, "FALSIFIED", "replicate failed")
        result = retract_source(self.conn, source, "notice", "evidence")
        self.assertEqual(result["affected"], [])
        self.assertEqual(get_claim(self.conn, claim.id).status, "FALSIFIED")

    def test_retracted_source_is_clean_after_cascade(self) -> None:
        research = self.add_research()
        source = self.add_source(research)
        add_claim(
            self.conn, research, "S rose with O.", "empirical",
            source_ref=source, quote="S rose with O.", locator="p.1",
            kill_test="A replicate.",
        )
        retract_source(self.conn, source, "notice", "evidence")
        codes = [finding.code for finding in check(self.conn)]
        self.assertNotIn("PROV-003", codes)



    def test_retraction_covers_twin_doi_rows(self) -> None:
        research = self.add_research()
        first = self.add_source(research)
        self.conn.execute(
            "UPDATE source SET doi = ? WHERE id = ?",
            ("https://doi.org/10.1000/abc", first),
        )
        from engine.sources import add_source

        twin = add_source(
            self.conn, research, "Twin record", year=2024, doi="doi:10.1000/ABC",
        ).id
        for source, text in ((first, "S rose with O."), (twin, "S rose with O too.")):
            add_claim(
                self.conn, research, text, "empirical",
                source_ref=source, quote=text, locator="p.1",
                kill_test="A replicate.",
            )
        result = retract_source(self.conn, first, "notice", "evidence")
        self.assertEqual(get_source(self.conn, first).status, "retracted")
        self.assertEqual(get_source(self.conn, twin).status, "retracted")
        self.assertIn(twin, result["siblings"])
        live_retracted = [
            item for item in check(self.conn) if item.code == "PROV-003"
        ]
        self.assertEqual(live_retracted, [])

    def test_reinstatement_requires_a_note_and_keeps_claim_verdicts(self) -> None:
        research = self.add_research()
        source = self.add_source(research)
        claim = add_claim(
            self.conn, research, "Cites the source.", "empirical",
            source_ref=source, quote="Cites the source.", locator="p.1", kill_test="A replicate.",
        )
        retract_source(self.conn, source, "notice", "evidence")
        with self.assertRaises(EngineError):
            set_source_status(self.conn, source, "active", "")
        reinstated = set_source_status(
            self.conn, source, "active", "retraction was itself withdrawn"
        )
        self.assertEqual(reinstated.status, "active")
        self.assertEqual(get_claim(self.conn, claim.id).status, "RETRACTED")


if __name__ == "__main__":
    unittest.main()
