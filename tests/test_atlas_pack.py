"""Atlas pack contract for the host unittest gate."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from domains.atlas.demo.basal_ganglia_fixture import FIXTURE_ANALYSIS
from domains.atlas.flashcards import build_deck, to_anki_tsv
from domains.atlas.ingestion import import_document
from domains.atlas.offline import build_offline_analysis
from domains.atlas.schema import VisualAnalysis
from domains.atlas.store import AtlasStore


class AtlasPackTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = Path(tempfile.mkdtemp())
        self.addCleanup(
            lambda: __import__("shutil").rmtree(self.directory, ignore_errors=True)
        )

    def test_fixture_analysis_validates_and_builds_a_deck(self) -> None:
        analysis = VisualAnalysis.from_dict(FIXTURE_ANALYSIS)
        self.assertEqual(analysis.validate(), [])
        deck = build_deck(analysis.to_dict())
        self.assertTrue(deck["cards"])
        tsv = to_anki_tsv(deck)
        self.assertTrue(all(line.count("\t") == 1 for line in tsv.splitlines()))

    def test_offline_fallback_quotes_its_source(self) -> None:
        text = (
            "The striatum receives cortical input. The thalamus relays signals to cortex. "
            "The substantia nigra modulates the striatum."
        )
        analysis = build_offline_analysis(text, document_ref="lesson.txt").to_dict()
        self.assertTrue(analysis["entities"])
        self.assertTrue(all(entity["model_inferred"] for entity in analysis["entities"]))
        self.assertTrue(any(entity.get("source_evidence") for entity in analysis["entities"]))

    def test_store_keeps_model_output_and_corrections_separate(self) -> None:
        store = AtlasStore(str(self.directory))
        store.save_analysis("fig", {"entities": []})
        store.add_correction({"entity_id": "striatum", "field": "name", "value": "Striatum"})
        self.assertEqual(store.load_analysis("fig"), {"entities": []})
        self.assertEqual(store.load_corrections()[0]["entity_id"], "striatum")

    def test_text_ingestion_keeps_a_digest(self) -> None:
        source = self.directory / "lesson.txt"
        source.write_text("A short lesson about the basal ganglia.", encoding="utf-8")
        bundle = import_document(str(source), str(self.directory / "data"))
        self.assertEqual(bundle["mime"], "text/plain")
        self.assertEqual(len(bundle["sha256"]), 64)
        self.assertTrue(Path(bundle["document_ref"]).is_file())
