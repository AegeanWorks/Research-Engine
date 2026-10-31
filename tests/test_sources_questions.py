"""Source identifiers and question lifecycle."""

from __future__ import annotations

import unittest

from engine.errors import EngineError
from engine.questions import add_question, close_question, list_questions
from engine.sources import add_source, list_sources
from tests.support import DatabaseCase


class SourceQuestionTests(DatabaseCase):
    def test_source_requires_an_identifier(self) -> None:
        research = self.add_research()
        with self.assertRaises(EngineError):
            add_source(self.conn, research, "No identifier")

    def test_source_accepts_doi_or_url(self) -> None:
        research = self.add_research()
        doi_source = add_source(self.conn, research, "With DOI", doi="10.1000/example")
        url_source = add_source(self.conn, research, "With URL", url="https://example.org/x")
        self.assertEqual(doi_source.doi, "10.1000/example")
        self.assertEqual(url_source.url, "https://example.org/x")
        self.assertEqual(len(list_sources(self.conn, research)), 2)

    def test_source_rejects_bad_kind_and_year(self) -> None:
        research = self.add_research()
        with self.assertRaises(EngineError):
            add_source(self.conn, research, "Bad kind", year=2024, kind="tweet")
        with self.assertRaises(EngineError):
            add_source(self.conn, research, "Bad year", year=24)

    def test_question_closes_without_deleting(self) -> None:
        research = self.add_research()
        question = add_question(self.conn, research, "Does S drive O?")
        closed = close_question(self.conn, question.id)
        self.assertEqual(closed.status, "closed")
        self.assertEqual(len(list_questions(self.conn, research)), 1)

    def test_empty_question_is_refused(self) -> None:
        research = self.add_research()
        with self.assertRaises(EngineError):
            add_question(self.conn, research, "   ")


if __name__ == "__main__":
    unittest.main()
