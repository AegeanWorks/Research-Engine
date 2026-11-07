"""Universal ingestion: every source becomes learning material."""
import io
import json
import zipfile

import pytest

from domains.atlas import sources as src
from domains.atlas.schema import coerce_muse_payload


class _FakeResp:
    def __init__(self, data: bytes, ctype: str = "text/html"):
        self._data = data
        self.headers = {"Content-Type": ctype}

    def read(self, n: int = -1):
        return self._data if n is None or n < 0 else self._data[:n]

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_html_to_text_drops_boilerplate():
    html = ("<html><head><title>T</title></head><body><nav>menu</nav>"
            "<script>evil()</script><h1>Head</h1><p>Body text.</p></body></html>")
    text = src.html_to_text(html)
    assert "Head" in text and "Body text." in text
    assert "menu" not in text and "evil" not in text


def test_fetch_url_text_and_plain(monkeypatch):
    calls = []

    def fake_open(req, timeout=None):
        calls.append(req.full_url)
        if req.full_url.endswith(".txt"):
            return _FakeResp(b"plain words", "text/plain")
        return _FakeResp(b"<html><body><p>Article body here.</p></body></html>")
    monkeypatch.setattr(src.urllib.request, "urlopen", fake_open)
    got = src.fetch_url_text("https://example.com/a")
    assert "Article body here." in got["text"]
    assert src.fetch_url_text("https://example.com/f.txt")["text"] == "plain words"
    with pytest.raises(ValueError, match="http"):
        src.fetch_url_text("ftp://example.com/x")


def test_youtube_transcript_parses_captions(monkeypatch):
    watch = ('<html><body>{"captionTracks":[{"baseUrl":"https://t.example/cap",'
             '"languageCode":"en"}]}</body></html>')
    caps = '<transcript><text start="0">hello world</text><text start="1">second line</text></transcript>'

    def fake_open(url, timeout=None):
        target = url.full_url if hasattr(url, "full_url") else url
        return _FakeResp(caps.encode() if "t.example" in target else watch.encode())
    monkeypatch.setattr(src.urllib.request, "urlopen", fake_open)
    got = src.youtube_transcript("https://www.youtube.com/watch?v=abc123XYZ-_")
    assert "hello world" in got["text"] and "second line" in got["text"]
    with pytest.raises(ValueError, match="recognizable"):
        src.youtube_transcript("https://example.com/notube")
    assert src.youtube_video_id("https://youtu.be/abc123XYZ-_") == "abc123XYZ-_"


def _write_epub(path):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("mimetype", "application/epub+zip")
        z.writestr("META-INF/container.xml",
                   '<container><rootfiles><rootfile full-path="OEBPS/content.opf"/>'
                   "</rootfiles></container>")
        z.writestr("OEBPS/content.opf",
                   '<package><metadata><dc:title>Test Book</dc:title></metadata>'
                   '<manifest><item id="c1" href="ch1.xhtml"/><item id="c2" href="ch2.xhtml"/>'
                   "</manifest><spine><itemref idref=\"c1\"/><itemref idref=\"c2\"/></spine></package>")
        z.writestr("OEBPS/ch1.xhtml", "<html><body><p>Chapter one words.</p></body></html>")
        z.writestr("OEBPS/ch2.xhtml", "<html><body><p>Chapter two words.</p></body></html>")


def test_epub_text_in_spine_order(tmp_path):
    path = str(tmp_path / "book.epub")
    _write_epub(path)
    got = src.epub_text(path)
    assert got["title"] == "Test Book" and got["chapters"] == 2
    assert got["text"].index("Chapter one") < got["text"].index("Chapter two")


def test_video_without_any_ffmpeg_is_honest(tmp_path, monkeypatch):
    import sys
    monkeypatch.setattr(src.shutil, "which", lambda *a, **k: None)
    monkeypatch.setitem(sys.modules, "imageio_ffmpeg", None)
    with pytest.raises(ValueError, match="ffmpeg"):
        src.video_frames(str(tmp_path / "clip.mp4"), str(tmp_path))


def test_video_frames_roundtrip_with_bundled_ffmpeg(tmp_path):
    pytest.importorskip("imageio_ffmpeg")
    import subprocess
    from PIL import Image
    from domains.atlas.sources import _ffmpeg_exe
    clip = str(tmp_path / "clip.mp4")
    subprocess.run([_ffmpeg_exe(), "-y", "-v", "error", "-f", "lavfi",
                    "-i", "testsrc=duration=3:size=128x96:rate=5",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", clip],
                   check=True, timeout=120)  # noqa: S603
    frames = src.video_frames(clip, str(tmp_path / "frames"), max_frames=3)
    assert len(frames) == 3  # fps=1 filter yields t=0,1,2 from a 3s clip
    for f in frames:
        with Image.open(f) as im:  # hygiene: allow binary image open needs no text encoding
            assert im.size == (640, 480)  # normalized width


def test_trim_text_marks_truncation():
    assert src.trim_text("a" * 12001).endswith("[truncated: first 12000 chars of the source]")
    assert src.trim_text("short") == "short"


def test_coerce_allows_boxless_text_entities():
    a = coerce_muse_payload(
        {"entities": [{"id": "e1", "name": "N1", "category": "process",
                       "confidence": 0.8, "source_evidence": "quote"}],
         "relationships": []})
    assert a.entities[0].bbox is None


def test_analyze_text_roundtrip():
    from domains.atlas.config import AtlasConfig
    from domains.atlas.muse_provider import MuseProvider

    def fake_transport(payload):
        user = payload["messages"][1]["content"]
        assert "SOURCE:" in user and "some text" in user
        assert payload["response_format"]["type"] == "json_schema"
        return {"choices": [{"message": {"content":
            '{"entities": [{"id": "x", "name": "X", "category": "process", '
            '"confidence": 0.7, "source_evidence": "q"}], "relationships": []}'}}]}
    cfg = AtlasConfig(api_key="k", data_dir=".")
    analysis = MuseProvider(cfg, transport=fake_transport).analyze_text("some text")
    assert analysis.entities[0].bbox is None
    assert analysis.entities[0].source_evidence == "q"


class _FakeMuseBoth:
    def analyze_text(self, text, note="", document_ref="", figure_id=""):
        from domains.atlas.schema import VisualAnalysis, VisualEntity
        return VisualAnalysis(document_ref=document_ref, figure_id=figure_id,
                              entities=[VisualEntity(id="t1", name="Thing",
                                                     category="component",
                                                     source_evidence=text[:20])],
                              relationships=[])

    def analyze_figure(self, *a, **k):
        from domains.atlas.schema import VisualAnalysis, VisualEntity
        return VisualAnalysis(document_ref=k.get("document_ref", ""),
                              figure_id=k.get("figure_id", "f"),
                              entities=[VisualEntity(id="v1", name="Region",
                                                     category="component")],
                              relationships=[])


def test_auto_create_from_text_and_image(tmp_path):
    from domains.atlas.app import auto_create_model, list_models
    from domains.atlas.config import AtlasConfig
    from domains.atlas.store import AtlasStore
    store = AtlasStore(str(tmp_path))
    cfg = AtlasConfig(api_key="", data_dir=str(tmp_path))
    txt = tmp_path / "n.txt"
    txt.write_text("Cortex drives striatum.", encoding="utf-8")
    r = auto_create_model(store, cfg, str(txt), muse_provider=_FakeMuseBoth())
    assert r["model_created"] and r["source_kind"] == "text"
    from PIL import Image
    img = tmp_path / "f.png"
    Image.new("RGB", (40, 30), (1, 2, 3)).save(img)
    r2 = auto_create_model(store, cfg, str(img), muse_provider=_FakeMuseBoth())
    assert r2["source_kind"] == "image" and r2["figure_url"].startswith("/figures/")
    ids = {m["figure_id"] for m in list_models(store)}
    assert {r["figure_id"], r2["figure_id"]} <= ids


def test_scanned_pdf_error_names_pages(tmp_path):
    pytest.importorskip("pypdf")
    from pypdf import PdfWriter
    p = str(tmp_path / "scan.pdf")
    w = PdfWriter()
    for _ in range(3):
        w.add_blank_page(200, 200)
    with open(p, "wb") as fh:
        w.write(fh)
    with pytest.raises(Exception, match="3 page"):
        src.ingest_any(p)


def test_pdf_render_needs_fitz_or_renders(tmp_path, monkeypatch):
    import sys
    import types
    from PIL import Image
    if "fitz" in sys.modules:
        monkeypatch.delitem(sys.modules, "fitz")
    with pytest.raises(ImportError, match="PyMuPDF"):
        src.render_pdf_page(str(tmp_path / "x.pdf"), 1, str(tmp_path))

    class FakePix:
        def save(self, out):
            Image.new("RGB", (60, 80), (1, 2, 3)).save(out)

    class FakePage:
        def get_pixmap(self, dpi=None):
            return FakePix()

    class FakeDoc:
        page_count = 5
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
        def __getitem__(self, i):
            assert i == 1
            return FakePage()

    stub = types.ModuleType("fitz")
    stub.open = lambda path: FakeDoc()
    monkeypatch.setitem(sys.modules, "fitz", stub)
    pdf = tmp_path / "real.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    out = src.render_pdf_page(str(pdf), 2, str(tmp_path / "figs"))
    assert out.endswith("page_002_150dpi.png")
    with Image.open(out) as rendered:  # hygiene: allow binary image open needs no text encoding
        assert rendered.size == (60, 80)
    with pytest.raises(ValueError, match="out of range"):
        src.render_pdf_page(str(pdf), 9, str(tmp_path / "figs"))


def test_cli_batch_reports_mixed_folder(tmp_path, capsys):
    from domains.atlas.cli import main
    (tmp_path / "a.txt").write_text("hello world", encoding="utf-8")
    (tmp_path / "b.xyz").write_text("junk", encoding="utf-8")
    assert main(["--data", str(tmp_path / "data"), "batch", str(tmp_path)]) == 0
    import json
    report = json.loads(capsys.readouterr().out)
    assert report["files"] >= 2 and report["imported"] >= 1
    assert any("error" in r for r in report["rows"])


def test_import_reports_pdf_pages(tmp_path):
    import json
    import threading
    import urllib.request
    from http.server import HTTPServer
    from domains.atlas import app as atlas_app
    from domains.atlas.config import AtlasConfig

    pytest.importorskip("pypdf")
    from pypdf import PdfWriter
    pdf = str(tmp_path / "p.pdf")
    w = PdfWriter()
    w.add_blank_page(72, 72)
    with open(pdf, "wb") as fh:
        w.write(fh)
    atlas_app.Handler.store = None
    atlas_app.Handler.config = AtlasConfig.from_env(data_dir=str(tmp_path / "data"))
    server = HTTPServer(("127.0.0.1", 0), atlas_app.Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/import",
            data=json.dumps({"path": pdf}).encode(),
            headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:  # noqa: S310
                body = json.load(r)
        except urllib.error.HTTPError as e:
            body = json.load(e)
        assert body.get("pages") == 1 or "text_backend" in body
    finally:
        server.shutdown()
        thread.join(timeout=5)
        atlas_app.Handler.store = None


def test_chunk_text_respects_paragraphs():
    from domains.atlas.sources import chunk_text
    paras = ["para one words " * 200, "para two words " * 200, "short three"]
    chunks = chunk_text("\n\n".join(paras), limit=3000)
    assert len(chunks) >= 2
    assert all(len(c) <= 3000 for c in chunks)
    assert chunk_text("tiny")[0] == "tiny"


def test_merge_analyses_dedupes_and_remaps():
    from domains.atlas.schema import VisualAnalysis, VisualEntity, VisualRelationship, merge_analyses
    a = VisualAnalysis(
        entities=[VisualEntity(id="a1", name="Striatum", category="anatomical-structure"),
                  VisualEntity(id="b1", name="GPe", category="anatomical-structure")],
        relationships=[VisualRelationship(source_id="a1", target_id="b1",
                                          rel_type="inhibits")])
    b = VisualAnalysis(
        entities=[VisualEntity(id="a2", name="striatum ", category="anatomical-structure",
                               description="longer description here",
                               source_evidence="q2"),
                  VisualEntity(id="c2", name="STN", category="anatomical-structure")],
        relationships=[VisualRelationship(source_id="a2", target_id="c2",
                                          rel_type="inhibits")])
    merged = merge_analyses([a, b], document_ref="d", figure_id="m")
    names = sorted(e.name for e in merged.entities)
    assert names == ["GPe", "STN", "Striatum"]
    striatum = next(e for e in merged.entities if e.name == "Striatum")
    assert striatum.description == "longer description here"
    assert striatum.source_evidence == "q2"
    pairs = {(r.source_id, r.target_id, r.rel_type) for r in merged.relationships}
    assert ("a1", "b1", "inhibits") in pairs and ("a1", "c2", "inhibits") in pairs


def test_analyze_long_text_chunks_and_merges():
    from domains.atlas.config import AtlasConfig
    from domains.atlas.muse_provider import MuseProvider

    calls = []

    def fake_transport(payload):
        user = payload["messages"][1]["content"]
        assert "SOURCE:" in user
        calls.append(user)
        return {"choices": [{"message": {"content":
            '{"entities": [{"id": "e", "name": "Thing", "category": "component", '
            '"confidence": 0.8}], "relationships": []}'}}]}

    cfg = AtlasConfig(api_key="k", data_dir=".")
    provider = MuseProvider(cfg, transport=fake_transport)
    short = provider.analyze_long_text("small text")
    assert len(calls) == 1 and short.entities[0].name == "Thing"
    big = provider.analyze_long_text("para. " * 5000)
    assert len(calls) > 2  # chunked into several Muse calls
    assert big.entities[0].name == "Thing"


def test_merge_disambiguates_reused_chunk_ids():
    from domains.atlas.schema import VisualAnalysis, VisualEntity, VisualRelationship, merge_analyses
    mk = lambda i, n: VisualEntity(id=i, name=n, category="component")
    a = VisualAnalysis(entities=[mk("e1", "Alpha")], relationships=[])
    b = VisualAnalysis(entities=[mk("e1", "Beta"), mk("e9", "Other")],
                       relationships=[VisualRelationship(source_id="e1", target_id="e9",
                                                         rel_type="activates")])
    merged = merge_analyses([a, b], document_ref="d", figure_id="m")
    ids = sorted(e.id for e in merged.entities)
    assert ids == ["e1", "e1-c2", "e9"]
    assert merged.validate() == []
    assert all({r.source_id, r.target_id} <= set(ids) for r in merged.relationships)


def test_merge_frames_namespaces_ids():
    from domains.atlas.app import _merge_frame_analyses
    from domains.atlas.schema import VisualAnalysis, VisualEntity, VisualRelationship
    mk = lambda p, s, t: VisualAnalysis(
        entities=[VisualEntity(id="a", name="A", category="component"),
                  VisualEntity(id="b", name="B", category="component")],
        relationships=[VisualRelationship(source_id="a", target_id="b",
                                          rel_type="activates")])
    merged = _merge_frame_analyses([mk(0, 0, 0), mk(1, 1, 1)], "d", "vid")
    ids = {e.id for e in merged.entities}
    assert ids == {"f0-a", "f0-b", "f1-a", "f1-b"}
    assert {(r.source_id, r.target_id) for r in merged.relationships} == \
        {("f0-a", "f0-b"), ("f1-a", "f1-b")}
