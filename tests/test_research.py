"""Program creation, slug resolution and counts."""

from __future__ import annotations

import unittest

from engine.errors import EngineError, NotFound
from engine.researches import create_research, get_research, list_researches, research_counts
from tests.support import DatabaseCase


class ResearchTests(DatabaseCase):
    def test_create_and_resolve_by_slug(self) -> None:
        record = create_research(self.conn, "Fluid Universe", "Nematic UV track")
        self.assertEqual(record.slug, "fluid-universe")
        self.assertEqual(get_research(self.conn, "fluid-universe").id, record.id)
        self.assertEqual(get_research(self.conn, record.id).title, "Fluid Universe")

    def test_duplicate_slug_is_suffixed(self) -> None:
        first = create_research(self.conn, "Same Title")
        second = create_research(self.conn, "Same Title")
        self.assertNotEqual(first.slug, second.slug)
        self.assertEqual(second.slug, "same-title-2")

    def test_invalid_slug_is_refused(self) -> None:
        with self.assertRaises(EngineError):
            create_research(self.conn, "Title", slug="Not A Slug")

    def test_missing_program_is_reported(self) -> None:
        with self.assertRaises(NotFound):
            get_research(self.conn, "r_999999")

    def test_counts_include_open_questions(self) -> None:
        research = create_research(self.conn, "Counted")
        self.assertEqual(research_counts(self.conn, research.id)["question"], 0)
        self.assertEqual(len(list_researches(self.conn)), 1)


if __name__ == "__main__":
    unittest.main()
