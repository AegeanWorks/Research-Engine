"""Atlas document-text backend — fully in-project, no external project needed.

Text extraction lives in :mod:`atlas.doc_text` (document routines originally
adapted from NeuralDeck's ``document_processor.py`` and since Atlas-owned).
This module is the single entry point the app uses.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from . import doc_text


@dataclass(frozen=True)
class DocumentText:
    source_path: str
    text: str
    pages: int
    backend: str  # always "atlas"


def extract_text(source_path: str, log_callback=None) -> DocumentText:
    """Extract text with the in-project backend."""
    ext = os.path.splitext(source_path)[1].lower()
    if ext == ".pdf":
        text = doc_text.extract_text_from_pdf(source_path, log_callback)
        return DocumentText(source_path, text, doc_text.pdf_page_count(source_path), "atlas")
    if ext in (".txt", ".md"):
        with open(source_path, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        return DocumentText(source_path, text, 1, "atlas")
    text = doc_text.extract_text_from_document(source_path, log_callback)
    return DocumentText(source_path, text, 1, "atlas")


def describe_integration() -> dict:
    return {
        "standalone": True,
        "backend": "atlas (in-project document text; no external project required)",
        "formats": ["pdf", "docx", "pptx", "txt", "vtt", "srt", "json"],
        "notes": ("Audio/video transcription is not bundled; supply a transcript "
                  "file instead."),
    }


def read_image_bytes(image_path: str) -> bytes:
    with open(image_path, "rb") as fh:
        return fh.read()
