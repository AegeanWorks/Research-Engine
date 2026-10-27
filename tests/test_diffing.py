"""Snapshot diff: semantic by default, exact on request."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from engine.claims import add_claim
from engine.diffing import diff_files, diff_records, load_jsonl, render
from engine.bundle import export_jsonl
from engine.errors import EngineError
from engine.killtests import verify_test
from tests.support import DatabaseCase


class DiffTests(DatabaseCase):
    def setUp(self) -> None:
        super().setUp()
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.dir = Path(directory.name)

    def test_identical_exports_have_no_differences(self) -> None:
        from engine.demo import seed_demo

        demo = seed_demo(self.conn)
        first = self.dir / "a.jsonl"
        second = self.dir / "b.jsonl"
        export_jsonl(self.conn, first, demo["research"])
        export_jsonl(self.conn, second, demo["research"])
        result = diff_files(first, second)
        self.assertTrue(result["identical"], result)
        self.assertIn("no differences", render(result))

    def test_a_new_claim_is_added(self) -> None:
        from engine.demo import seed_demo

        demo = seed_demo(self.conn)
        first = self.dir / "a.jsonl"
        second = self.dir / "b.jsonl"
        export_jsonl(self.conn, first, demo["research"])
        added = add_claim(self.conn, demo["research"], "A new claim.", "assumption", basis="b")
        export_jsonl(self.conn, second, demo["research"])
        result = diff_files(first, second)
        self.assertEqual([item["id"] for item in result["added"]], [added.id])

    def test_semantic_mode_ignores_run_churn(self) -> None:
        from engine.demo import seed_demo

        demo = seed_demo(self.conn)
        first = self.dir / "a.jsonl"
        second = self.dir / "b.jsonl"
        export_jsonl(self.conn, first, demo["research"])
        verify_test(self.conn, demo["test"])
        export_jsonl(self.conn, second, demo["research"])
        self.assertTrue(diff_files(first, second)["identical"])
        exact = diff_files(first, second, semantic=False)
        self.assertFalse(exact["identical"])

    def test_a_changed_status_is_reported(self) -> None:
        from engine.demo import seed_demo

        demo = seed_demo(self.conn)
        first = self.dir / "a.jsonl"
        second = self.dir / "b.jsonl"
        export_jsonl(self.conn, first, demo["research"])
        self.conn.execute("UPDATE claim SET status = 'UNKNOWN' WHERE id = ?", (demo["opposing_claim"],))
        export_jsonl(self.conn, second, demo["research"])
        result = diff_files(first, second)
        self.assertEqual(
            [(item["type"], item["id"]) for item in result["changed"]], [("claim", demo["opposing_claim"])]
        )

    def test_missing_snapshot_is_reported(self) -> None:
        with self.assertRaises(EngineError):
            load_jsonl(self.dir / "absent.jsonl")

    def test_malformed_snapshot_is_reported(self) -> None:
        bad = self.dir / "bad.jsonl"
        bad.write_text("{not json}\n", encoding="utf-8")
        with self.assertRaises(EngineError):
            load_jsonl(bad)

    def test_render_lists_each_change(self) -> None:
        result = diff_records([{"type": "claim", "id": "c_1", "status": "X"}],
                              [{"type": "claim", "id": "c_2", "status": "Y"}])
        text = render(result)
        self.assertIn("+ claim:c_2", text)
        self.assertIn("- claim:c_1", text)


if __name__ == "__main__":
    unittest.main()
