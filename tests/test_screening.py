"""Screening decisions and the PRISMA flow."""

from __future__ import annotations

import unittest

from engine.claims import add_claim
from engine.errors import EngineError
from engine.integrity import check
from engine.models import SCREENING_REASONS, SCREENING_STATUSES
from engine.screening import prisma_flow, set_screening, unscreened_sources
from engine.sources import get_source
from tests.support import DatabaseCase


class ScreeningTests(DatabaseCase):
    def setUp(self) -> None:
        super().setUp()
        self.research = self.add_research()
        self.source = self.add_source(self.research)

    def test_new_sources_are_identified(self) -> None:
        self.assertEqual(get_source(self.conn, self.source).screening, "identified")
        self.assertEqual(len(unscreened_sources(self.conn, self.research)), 1)

    def test_vocabularies_are_closed(self) -> None:
        self.assertIn("included", SCREENING_STATUSES)
        self.assertIn("not_relevant", SCREENING_REASONS)

    def test_out_status_defaults_to_other_reason(self) -> None:
        record = set_screening(self.conn, self.source, "excluded")
        self.assertEqual(record.screening, "excluded")
        self.assertEqual(record.screening_reason, "other")

    def test_reason_is_required_to_be_known(self) -> None:
        with self.assertRaises(EngineError):
            set_screening(self.conn, self.source, "screened_out", "because")

    def test_reason_is_cleared_for_an_in_status(self) -> None:
        record = set_screening(self.conn, self.source, "included", "duplicate")
        self.assertEqual(record.screening, "included")
        self.assertEqual(record.screening_reason, "")

    def test_unknown_status_and_repeat_are_refused(self) -> None:
        with self.assertRaises(EngineError):
            set_screening(self.conn, self.source, "maybe")
        set_screening(self.conn, self.source, "included")
        with self.assertRaises(EngineError):
            set_screening(self.conn, self.source, "included")

    def test_prisma_counts_and_fraction(self) -> None:
        second = self.add_source(self.research)
        third = self.add_source(self.research)
        set_screening(self.conn, self.source, "included")
        set_screening(self.conn, second, "excluded", "wrong_outcome")
        set_screening(self.conn, third, "screened_out", "duplicate")
        flow = prisma_flow(self.conn, self.research)
        self.assertEqual(flow["counts"]["included"], 1)
        self.assertEqual(flow["counts"]["excluded"], 1)
        self.assertEqual(flow["reasons"], {"duplicate": 1, "wrong_outcome": 1})
        self.assertEqual(flow["total"], 3)
        self.assertAlmostEqual(flow["included_fraction"], 0.3333, places=4)

    def test_excluded_source_citing_claim_warns(self) -> None:
        claim = add_claim(
            self.conn, self.research, "S rose with O.", "empirical",
            source_ref=self.source, quote="S rose with O.", locator="p.1",
            kill_test="A replicate.",
        )
        set_screening(self.conn, self.source, "excluded", "not_relevant")
        findings = [item for item in check(self.conn) if item.code == "SCREEN-001"]
        self.assertEqual([item.subject for item in findings], [claim.id])
        self.assertEqual(findings[0].severity, "warning")

    def test_included_source_does_not_warn(self) -> None:
        add_claim(
            self.conn, self.research, "S rose with O.", "empirical",
            source_ref=self.source, quote="S rose with O.", locator="p.1", kill_test="A replicate.",
        )
        set_screening(self.conn, self.source, "included")
        self.assertNotIn("SCREEN-001", {item.code for item in check(self.conn)})


if __name__ == "__main__":
    unittest.main()
