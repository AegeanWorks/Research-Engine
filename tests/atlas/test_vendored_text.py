"""Vendored text extraction + standalone adapter tests (no sibling needed)."""
import json
import os

import pytest

from domains.atlas import doc_text
from domains.atlas import text_backend as nd


def test_txt_and_markdown_dispatch(tmp_path):
    p = tmp_path / "note.txt"
    p.write_text("cortex projects to striatum", encoding="utf-8")
    assert "striatum" in doc_text.extract_text_from_document(str(p))


def test_srt_transcript_cleaned(tmp_path):
    p = tmp_path / "cap.srt"
    p.write_text("1\n00:00:00,000 --> 00:00:01,000\n<b>striatum</b> fires\n\n"
                 "2\n00:00:01,000 --> 00:00:02,000\nstriatum fires\n",
                 encoding="utf-8")
    text = doc_text.extract_text_from_document(str(p))
    assert "striatum fires" in text and "<b>" not in text
    assert text.count("striatum fires") == 1  # repeats de-duplicated


def test_json_transcript_segments(tmp_path):
    p = tmp_path / "cap.json"
    p.write_text(json.dumps([{"text": "GPe inhibits STN"}, {"text": "STN excites GPi"}]),
                 encoding="utf-8")
    text = doc_text.extract_text_from_document(str(p))
    assert "GPe inhibits STN" in text and "STN excites GPi" in text


def test_unsupported_and_audio_errors(tmp_path):
    p = tmp_path / "x.xyz"
    p.write_text("hi", encoding="utf-8")
    with pytest.raises(ValueError, match="Unsupported file type"):
        doc_text.extract_text_from_document(str(p))
    a = tmp_path / "ep.mp3"
    a.write_bytes(b"fake")
    with pytest.raises(ValueError, match="transcript file instead"):
        doc_text.extract_text_from_document(str(a))


def test_pdf_empty_raises_honestly(tmp_path):
    pytest.importorskip("pypdf")
    from pypdf import PdfWriter
    p = str(tmp_path / "blank.pdf")
    w = PdfWriter()
    w.add_blank_page(200, 200)
    with open(p, "wb") as fh:
        w.write(fh)
    assert doc_text.pdf_page_count(p) == 1
    with pytest.raises(Exception, match="No text on any of 1 page"):
        doc_text.extract_text_from_pdf(p)


def test_adapter_standalone(tmp_path):
    p = tmp_path / "n.txt"
    p.write_text("thalamus relays to cortex", encoding="utf-8")
    got = nd.extract_text(str(p))
    assert got.backend == "atlas"
    assert "cortex" in got.text
    info = nd.describe_integration()
    assert info["standalone"] is True


def test_external_project_env_is_ignored(tmp_path, monkeypatch):
    monkeypatch.setenv("NEURALDECK_PATH", r"C:\definitely\not\here")
    p = tmp_path / "n.txt"
    p.write_text("striatum inhibits GPe", encoding="utf-8")
    assert nd.extract_text(str(p)).backend == "atlas"


def test_providers_refuse_without_key_and_never_touch_network(tmp_path):
    from domains.atlas.config import AtlasConfig
    from domains.atlas.muse_provider import MuseProvider
    from domains.atlas.sam_provider import SamProvider

    img = tmp_path / "f.png"
    img.write_bytes(b"fakepng")
    cfg = AtlasConfig(api_key="", data_dir=str(tmp_path))
    # Default (live) transport + no key: refuse BEFORE any network I/O.
    with pytest.raises(RuntimeError, match="MODEL_API_KEY"):
        MuseProvider(cfg).analyze_figure(str(img))
    with pytest.raises(RuntimeError, match="MODEL_API_KEY"):
        SamProvider(cfg).segment(str(img), "striatum", "striatum")
    # live transports are detected even though they are bound methods
    # (the old `transport is self._http_post` check was always False)
    assert MuseProvider(cfg)._live_transport is True
    assert SamProvider(cfg)._live_transport is True
    assert MuseProvider(cfg, transport=lambda p: {})._live_transport is False
