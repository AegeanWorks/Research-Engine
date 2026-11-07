"""Obezite claim-ledger tooling: parsing, buckets and projections on a fixture."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from domains.obezite.sentez import (
    generate,
    grade_bucket,
    macro_bucket,
    parse_claims,
    summarize,
)
from domains.obezite.uret import bol, chunk_adi, govde_dogrula, uret
from domains.obezite.split import split_lines
from domains.obezite.dedup import deduplicate
from domains.obezite.claim_index import build_index
from domains.obezite.backfill import backfill
from domains.obezite.cokus import analyze, marker_present
from domains.obezite.split_range import split_ledger

_LEDGER = """\
| **1** | First claim | L1 | D1 | up | none | **kan\u0131tl\u0131** | PMID:123 |
| **2** | Second claim | L2 | D? | down | q1 | **backfill-bekliyor** | none |
"""


class LedgerParsingTests(unittest.TestCase):
    def test_claims_are_parsed_with_buckets_and_source_identity(self) -> None:
        claims = parse_claims(_LEDGER)
        self.assertEqual([claim["id"] for claim in claims], [1, 2])
        self.assertEqual(claims[0]["bucket"], "kan\u0131tl\u0131")
        self.assertEqual(claims[0]["source_identity"], "yes")
        self.assertEqual(claims[1]["source_identity"], "no")
        self.assertEqual(claims[0]["range"], "1-481")

    def test_summary_separates_verified_and_backfill(self) -> None:
        summary = summarize(parse_claims(_LEDGER))
        self.assertEqual(summary["rows"], 2)
        self.assertEqual(summary["verified"], 1)
        self.assertEqual(summary["backfill"], 1)

    def test_bucket_helpers_are_stable(self) -> None:
        self.assertEqual(macro_bucket("**backfill-bekliyor**"), "backfill-bekliyor")
        self.assertEqual(grade_bucket("D1/E1 - human"), "D1/E1")
        self.assertEqual(grade_bucket("D?"), "belirsiz")

    def test_projections_are_generated_from_an_external_root(self) -> None:
        root = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(root, ignore_errors=True))
        literature = root / "02_LITERATUR"
        literature.mkdir(parents=True)
        (literature / "iddia-defteri.md").write_text(_LEDGER, encoding="utf-8")
        outputs = generate(root)
        self.assertEqual(set(outputs), {"iddia-register.csv", "kanit-ozeti.csv"})
        self.assertIn("First claim", outputs["iddia-register.csv"])
        self.assertIn("defter_satiri,2", outputs["kanit-ozeti.csv"])


class LedgerChunkingTests(unittest.TestCase):
    def test_chunk_names_follow_the_500_claim_window(self) -> None:
        self.assertEqual(chunk_adi(1), ("iddia-defteri-0001-0500.md", 1, 500))
        self.assertEqual(chunk_adi(501), ("iddia-defteri-0501-1000.md", 501, 1000))

    def test_split_is_lossless_and_routes_by_claim_number(self) -> None:
        lines = ["onsoz", "| **1** | a |", "| **2** | b |", "| **501** | c |"]
        onsoz, boxes, order = bol(lines)
        self.assertEqual(onsoz, ["onsoz"])
        self.assertEqual(order, ["iddia-defteri-0001-0500.md", "iddia-defteri-0501-1000.md"])
        self.assertEqual(boxes[order[0]]["ids"], [1, 2])
        self.assertEqual(boxes[order[1]]["ids"], [501])

    def test_generated_chunks_keep_every_line(self) -> None:
        lines = ["intro", "| **1** | a |", "note", "| **2** | b |"]
        onsoz, boxes, order = bol(lines)
        outputs, generated_boxes, generated_order, generated_intro = uret(lines)
        self.assertEqual(generated_order, order)
        self.assertEqual(generated_intro, onsoz)
        self.assertTrue(govde_dogrula(lines, generated_boxes, generated_order, generated_intro))
        self.assertTrue(set(order) <= set(outputs))
        self.assertIn("iddia-defteri-index.md", outputs)
        self.assertIn("claim-index.md", outputs)

    def test_quarantine_split_is_import_safe_and_keeps_headers(self) -> None:
        lines = [
            "header\n",
            "| **1** | active | L1 | D1 | up | none | kanitli | PMID:1 |\n",
            "| **2** | dead | L2 | D3 | down | none | falsified | PMID:2 |\n",
        ]
        active, quarantine = split_lines(lines)
        self.assertIn("header\n", active)
        self.assertIn("| **1** | active", "".join(active))
        self.assertIn("| **2** | dead", "".join(quarantine))
        self.assertNotIn("| **2** | dead", "".join(active))


class LedgerOperatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(self.root, ignore_errors=True))
        self.literature = self.root / "02_LITERATUR"
        self.literature.mkdir(parents=True)

    def test_dedup_writes_only_a_copy_and_archives_duplicates(self) -> None:
        first = self.literature / "iddia-defteri-0001-0500.md"
        second = self.literature / "iddia-defteri-0501-1000.md"
        retracted = self.literature / "iddia-defteri-CURUTULMUS.md"
        first.write_text("| **1** | one |\n", encoding="utf-8")
        second.write_text("| **2** | two |\n", encoding="utf-8")
        retracted.write_text("| **2** | two again |\n| **3** | three |\n", encoding="utf-8")
        before = retracted.read_bytes()
        output = self.root / "generated"
        result = deduplicate(
            [first, second],
            retracted,
            output / "archive.md",
            output / "CURUTULMUS.md",
        )
        self.assertEqual(result["duplicates"], 1)
        self.assertIn("| 2 |", (output / "archive.md").read_text(encoding="utf-8"))
        updated = (output / "CURUTULMUS.md").read_text(encoding="utf-8")
        self.assertNotIn("two again", updated)
        self.assertIn("three", updated)
        self.assertEqual(retracted.read_bytes(), before)

    def test_claim_index_classifies_references(self) -> None:
        chunk = self.literature / "iddia-defteri-0001-0500.md"
        chunk.write_text(
            "| **1** | c | L1 | D1 | dir | no | ok | S00.1, H3 |\n",
            encoding="utf-8",
        )
        output = self.root / "index.md"
        result = build_index([chunk], self.literature / "missing.md", output)
        self.assertEqual(result["claims"], 1)
        text = output.read_text(encoding="utf-8")
        self.assertIn("S00.1", text)
        self.assertIn("H3", text)

    def test_backfill_builds_missing_rows_without_touching_the_source(self) -> None:
        ledger = self.literature / "iddia-defteri.md"
        ledger.write_text("| **1** | one |\n", encoding="utf-8")
        questions = self.root / "01_SORULAR"
        questions.mkdir()
        (questions / "tur-85-example.md").write_text("İddia 3 burada.", encoding="utf-8")
        before = ledger.read_bytes()
        output = self.root / "backfilled.md"
        result = backfill(ledger, questions, output, start=3, end=4, tours=[85])
        self.assertEqual(result["missing"], [3, 4])
        text = output.read_text(encoding="utf-8")
        self.assertIn("| **3** |", text)
        self.assertIn("| **4** |", text)
        self.assertEqual(ledger.read_bytes(), before)

    def test_collapse_audit_flags_unmarked_dependents(self) -> None:
        ledger = self.literature / "iddia-defteri.md"
        ledger.write_text(
            "| **1** | bad | L1 | D3 | dir | no | çürütüldü | x |\n"
            "| **2** | safe | L1 | D1 | dir | ~~ | ok | 1 |\n"
            "| **3** | blind | L1 | D1 | dir | no | ok | 1 |\n",
            encoding="utf-8",
        )
        result = analyze(ledger)
        self.assertEqual(result["invalid"], [1])
        self.assertIn((1, 3), result["missing"])
        self.assertNotIn((1, 2), result["missing"])
        self.assertTrue(marker_present(ledger.read_text(encoding="utf-8").splitlines()[1]))

    def test_range_split_writes_chunks_and_index(self) -> None:
        source = self.literature / "iddia-defteri.md"
        source.write_text(
            "header\n| # | İddia |\n|---|---|\n| **1** | one |\n| **501** | two |\n",
            encoding="utf-8",
        )
        output = self.root / "generated"
        result = split_ledger(source, output)
        self.assertEqual(result["chunk1"], 1)
        self.assertEqual(result["chunk2"], 1)
        self.assertTrue((output / "iddia-defteri-index.md").is_file())
