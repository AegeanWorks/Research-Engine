"""Vocabularies are closed and records are immutable."""

from __future__ import annotations

import dataclasses
import unittest

from engine.models import (
    CLAIM_STATUSES,
    NON_SUPPORTING_STATUSES,
    DEPENDENCY_RELATIONS,
    FAILED_STATUSES,
    PROMOTED_STATUSES,
    Claim,
)


class ModelTests(unittest.TestCase):
    def test_status_vocabulary_is_closed(self) -> None:
        self.assertEqual(
            CLAIM_STATUSES,
            ("UNVERIFIED", "PROVEN", "NUMERIC", "UNKNOWN", "FALSIFIED", "RETRACTED", "INVALIDATED"),
        )
        self.assertTrue(set(FAILED_STATUSES).issubset(CLAIM_STATUSES))
        self.assertTrue(set(PROMOTED_STATUSES).issubset(CLAIM_STATUSES))
        self.assertIn("UNKNOWN", NON_SUPPORTING_STATUSES)
        self.assertNotIn("UNKNOWN", FAILED_STATUSES)

    def test_dependency_relations_are_explicit(self) -> None:
        self.assertEqual(DEPENDENCY_RELATIONS, ("derived_from", "depends_on"))

    def test_claim_is_frozen(self) -> None:
        claim = Claim(
            id="c_000001",
            research_id="r_000001",
            source_id=None,
            text="x",
            quote="",
            locator="",
            kind="assumption",
            basis="because",
            kill_test="",
            status="UNVERIFIED",
            confidence=0.5,
            created_at="2026-01-01T00:00:00+00:00",
            updated_at="2026-01-01T00:00:00+00:00",
        )
        with self.assertRaises(dataclasses.FrozenInstanceError):
            claim.status = "PROVEN"  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()
