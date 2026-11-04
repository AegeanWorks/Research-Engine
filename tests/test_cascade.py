"""A collapsed premise invalidates every dependent transitively."""

from __future__ import annotations

import unittest

from engine.cascade import dependents, invalidate, preview
from engine.claims import add_claim, get_claim, link_claims, set_verdict
from engine.errors import EngineError
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

    def test_collapse_traverses_depends_on_edges(self) -> None:
        research = self.add_research()
        root = add_claim(self.conn, research, "Root.", "assumption", basis="a")
        middle = add_claim(self.conn, research, "Middle.", "derived", basis="b")
        link_claims(self.conn, middle.id, root.id, "depends_on")
        self.assertEqual(dependents(self.conn, root.id), [(middle.id, 1)])
        result = invalidate(self.conn, root.id, "FALSIFIED", "reason", "evidence")
        self.assertEqual(get_claim(self.conn, middle.id).status, "INVALIDATED")
        self.assertEqual([item["id"] for item in result["affected"]], [middle.id])

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

    def test_falsified_dependent_keeps_its_primary_failure(self) -> None:
        root, middle, leaf = self._chain()
        from engine.claims import set_verdict

        set_verdict(self.conn, middle, "FALSIFIED", "direct replicate failed")
        previewed = preview(self.conn, root)
        self.assertFalse(
            [item for item in previewed["affected"] if item["id"] == middle][0][
                "would_invalidate"
            ]
        )
        result = invalidate(
            self.conn, root, "FALSIFIED", "the primary cohort failed", "replicate run 2"
        )
        self.assertEqual(get_claim(self.conn, middle).status, "FALSIFIED")
        self.assertEqual(get_claim(self.conn, leaf).status, "INVALIDATED")
        self.assertEqual([item["id"] for item in result["affected"]], [leaf])

    def test_bulk_collapse_is_refused_without_override(self) -> None:
        research = self.add_research()
        root = add_claim(self.conn, research, "Root.", "assumption", basis="a")
        for index in range(11):
            add_claim(
                self.conn, research, f"Dependent {index}.", "derived",
                basis="from root", prerequisites=[root.id],
            )
        with self.assertRaises(EngineError) as caught:
            invalidate(self.conn, root.id, "FALSIFIED", "reason", "evidence")
        self.assertIn("--allow-bulk", str(caught.exception.fix))
        self.assertEqual(get_claim(self.conn, root.id).status, "UNVERIFIED")
        result = invalidate(
            self.conn, root.id, "FALSIFIED", "reason", "evidence", allow_bulk=True,
        )
        self.assertEqual(len(result["affected"]), 11)

    def test_collapse_requires_evidence(self) -> None:
        root, _, _ = self._chain()
        with self.assertRaises(Exception):
            invalidate(self.conn, root, "FALSIFIED", "a reason", "   ")

    def test_collapse_requires_reason_and_failed_status(self) -> None:
        root, _, _ = self._chain()
        with self.assertRaises(Exception):
            invalidate(self.conn, root, "UNVERIFIED", "no reason", "evidence")
        with self.assertRaises(Exception):
            invalidate(self.conn, root, "FALSIFIED", "  ", "evidence")

    def test_stale_preview_digest_is_refused(self) -> None:
        root, _, leaf = self._chain()
        digest = preview(self.conn, root)["digest"]
        set_verdict(self.conn, leaf, "FALSIFIED", "the leaf failed first")
        with self.assertRaises(EngineError) as caught:
            invalidate(
                self.conn, root, "FALSIFIED", "reason", "evidence",
                preview_digest=digest,
            )
        self.assertIn("preview", str(caught.exception.fix))
        self.assertEqual(get_claim(self.conn, root).status, "UNVERIFIED")

    def test_current_preview_digest_allows_collapse(self) -> None:
        root, mid, leaf = self._chain()
        digest = preview(self.conn, root)["digest"]
        result = invalidate(
            self.conn, root, "FALSIFIED", "reason", "evidence",
            preview_digest=digest,
        )
        self.assertEqual(
            [item["id"] for item in result["affected"]], [mid, leaf]
        )

    def test_preview_digest_binds_new_dependents(self) -> None:
        root, _, _ = self._chain()
        digest = preview(self.conn, root)["digest"]
        add_claim(
            self.conn, get_claim(self.conn, root).research_id, "Late dependent.",
            "derived", basis="from root", prerequisites=[root],
        )
        with self.assertRaises(EngineError):
            invalidate(
                self.conn, root, "FALSIFIED", "reason", "evidence",
                preview_digest=digest,
            )


if __name__ == "__main__":
    unittest.main()
