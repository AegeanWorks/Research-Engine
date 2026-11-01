"""Duplicate sources: DOI and title normalization, scope, and the integrity warning."""

from __future__ import annotations

import unittest

from engine.duplicates import duplicate_sources, normalize_doi, normalize_title
from engine.integrity import check
from engine.sources import add_source
from tests.support import DatabaseCase


class NormalizationTests(unittest.TestCase):
    def test_doi_resolver_prefix_and_case_are_folded(self) -> None:
        self.assertEqual(normalize_doi("https://doi.org/10.1000/ABC"), "10.1000/abc")
        self.assertEqual(normalize_doi("doi:10.1000/abc"), "10.1000/abc")
        self.assertEqual(normalize_doi("HTTP://DX.DOI.ORG/10.1000/Abc"), "10.1000/abc")
        self.assertEqual(normalize_doi("   "), "")

    def test_title_folds_accents_case_and_punctuation(self) -> None:
        self.assertEqual(normalize_title("Café: Signal, S!"), "cafe signal s")
        self.assertEqual(normalize_title("  CAFE   signal s  "), "cafe signal s")


class DuplicateSourceTests(DatabaseCase):
    def test_doi_duplicates_are_grouped_with_the_lowest_id_kept(self) -> None:
        research = self.add_research()
        first = add_source(
            self.conn, research, "Café Signal", year=2024,
            doi="https://doi.org/10.1000/ABC",
        ).id
        second = add_source(
            self.conn, research, "cafe signal", year=2024, doi="doi:10.1000/abc"
        ).id
        result = duplicate_sources(self.conn, research)
        self.assertEqual(result["total"], 1)
        group = result["groups"][0]
        self.assertEqual(group["reason"], "doi")
        self.assertEqual(group["keep"], first)
        self.assertEqual([item["id"] for item in group["sources"]], [first, second])

    def test_title_year_duplicates_are_grouped(self) -> None:
        research = self.add_research()
        first = add_source(self.conn, research, "A Study of S", year=2020).id
        second = add_source(self.conn, research, "A study of S!", year=2020).id
        group = duplicate_sources(self.conn, research)["groups"][0]
        self.assertEqual(group["reason"], "title_year")
        self.assertEqual(group["keep"], first)
        self.assertEqual({item["id"] for item in group["sources"]}, {first, second})

    def test_same_title_different_year_is_only_a_variant(self) -> None:
        research = self.add_research()
        add_source(self.conn, research, "Same Title", year=2019)
        add_source(self.conn, research, "Same Title", year=2020)
        group = duplicate_sources(self.conn, research)["groups"][0]
        self.assertEqual(group["reason"], "title_variant")

    def test_programs_are_never_grouped_together(self) -> None:
        first = self.add_research("First")
        second = self.add_research("Second")
        add_source(self.conn, first, "Shared Title", year=2024, doi="10.1/same")
        add_source(self.conn, second, "Shared Title", year=2024, doi="10.1/same")
        result = duplicate_sources(self.conn)
        self.assertEqual(result["groups"], [])

    def test_limit_keeps_the_total_visible(self) -> None:
        research = self.add_research()
        for index in range(3):
            add_source(self.conn, research, f"Title {index}", year=2024, doi=f"10.1/{index}")
            add_source(self.conn, research, f"Title {index}", year=2024, doi=f"DOI:10.1/{index}")
        result = duplicate_sources(self.conn, research, limit=1)
        self.assertEqual(result["total"], 3)
        self.assertEqual(result["returned"], 1)
        self.assertEqual(len(result["groups"]), 1)

    def test_integrity_warns_on_doi_and_title_year_but_not_variants(self) -> None:
        research = self.add_research()
        add_source(self.conn, research, "A Study", year=2024, doi="10.1/a")
        add_source(self.conn, research, "a study", year=2024, doi="doi:10.1/a")
        findings = [item for item in check(self.conn) if item.code == "DUP-002"]
        self.assertEqual(len(findings), 1)
        self.assertIn("share DOI", findings[0].message)

        other = self.add_research("Variants")
        add_source(self.conn, other, "Same Title", year=2019)
        add_source(self.conn, other, "Same Title", year=2020)
        codes = [item.code for item in check(self.conn)]
        self.assertEqual(codes.count("DUP-002"), 1)


if __name__ == "__main__":
    unittest.main()
