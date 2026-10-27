"""A collapsed premise invalidates every dependent transitively."""

from __future__ import annotations

import unittest

from engine.cascade import dependents, invalidate, preview
from engine.claims import add_claim, get_claim
from tests.support import DatabaseCase


class CascadeTests(DatabaseCase):
    def _chain(self) -> tuple[str, str, str]:
        research = self.add_research()
        root = self.add_empirical(research)
        middle = add_claim(
            self.conn, research, "Middle depends on root.", "derived",
            basis="from root", prerequisites=[root],
        ).id
        leaf = add_claim(
            self.conn, research, "Leaf depends on middle.", "derived",
            basis="from middle", prerequisites=[middle],
        ).id
        return root, middle, leaf

    def test_dependents_are_transitive_and_ordered_by_depth(self) -> None:
        root, middle, leaf = self._chain()
        self.assertEqual(dependents(self.conn, root), [(middle, 1), (leaf, 2)])

    def test_preview_writes_nothing(self) -> None:
        root, middle, leaf = self._chain()
        result = preview(self.conn, root)
        self.assertEqual([item["id"] for item in result["affected"]], [middle, leaf])
        self.assertTrue(all(item["would_invalidate"] for item in result["affected"]))
        self.assertEqual(get_claim(self.conn, root).status, "UNVERIFIED")

    def test_collapse_invalidates_every_dependent(self) -> None:
        root, middle, leaf = self._chain()
        result = invalidate(
            self.conn, root, "FALSIFIED", "the primary cohort failed", "replicate run 2"
        )
        self.assertEqual(get_claim(self.conn, root).status, "FALSIFIED")
        self.assertEqual(get_claim(self.conn, middle).status, "INVALIDATED")
        self.assertEqual(get_claim(self.conn, leaf).status, "INVALIDATED")
        self.assertEqual([item["id"] for item in result["affected"]], [middle, leaf])
        row = self.conn.execute("SELECT * FROM invalidation").fetchone()
        self.assertIn(root, row["root_id"])

    def test_retracted_dependent_is_not_rewritten(self) -> None:
        root, middle, leaf = self._chain()
        from engine.claims import set_verdict

        set_verdict(self.conn, middle, "RETRACTED", "withdrawn by the author")
        result = invalidate(self.conn, root, "FALSIFIED", "primary failed", "replicate run 2")
        self.assertEqual(get_claim(self.conn, middle).status, "RETRACTED")
        self.assertEqual(get_claim(self.conn, leaf).status, "INVALIDATED")
        self.assertEqual([item["id"] for item in result["affected"]], [leaf])

    def test_collapse_requires_reason_and_failed_status(self) -> None:
        root, _, _ = self._chain()
        with self.assertRaises(Exception):
            invalidate(self.conn, root, "UNVERIFIED", "no reason", "evidence")
        with self.assertRaises(Exception):
            invalidate(self.conn, root, "FALSIFIED", "  ", "evidence")


if __name__ == "__main__":
    unittest.main()
