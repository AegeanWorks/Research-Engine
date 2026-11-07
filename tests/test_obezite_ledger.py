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
