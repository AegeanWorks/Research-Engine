"""JSONL export is complete, scoped and deterministic in order."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from engine.bundle import export_jsonl
from engine.claims import add_claim
from engine.researches import create_research
from tests.support import DatabaseCase


class BundleTests(DatabaseCase):
    def setUp(self) -> None:
        super().setUp()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "bundle.jsonl"

    def test_export_writes_meta_first_and_every_record(self) -> None:
        research = self.add_research()
        add_claim(self.conn, research, "A claim.", "assumption", basis="a")
        counts = export_jsonl(self.conn, self.path)
        lines = [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(lines[0]["type"], "meta")
        types = [line["type"] for line in lines]
        self.assertIn("research", types)
        self.assertIn("claim", types)
        self.assertEqual(counts["claim"], 1)

    def test_scoped_export_excludes_other_programs(self) -> None:
        first = create_research(self.conn, "First")
        second = create_research(self.conn, "Second")
        add_claim(self.conn, first.id, "First claim.", "assumption", basis="a")
        add_claim(self.conn, second.id, "Second claim.", "assumption", basis="b")
        export_jsonl(self.conn, self.path, first.slug)
        text = self.path.read_text(encoding="utf-8")
        self.assertIn("First claim.", text)
        self.assertNotIn("Second claim.", text)

    def test_export_replaces_the_file_atomically(self) -> None:
        self.path.write_text("stale", encoding="utf-8")
        export_jsonl(self.conn, self.path)
        self.assertNotEqual(self.path.read_text(encoding="utf-8"), "stale")


if __name__ == "__main__":
    unittest.main()
