"""Upload, auto-create, models index, contract, CLI (0.5.0 autonomy slice)."""
import io
import json
import os
import threading
import urllib.request
import urllib.error
from http.server import HTTPServer

from domains.atlas import app as atlas_app
from domains.atlas.config import AtlasConfig


def _serve(tmp_path):
    atlas_app.Handler.store = None
    atlas_app.Handler.config = AtlasConfig.from_env(data_dir=str(tmp_path))
    server = HTTPServer(("127.0.0.1", 0), atlas_app.Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def _post(port, path, obj):
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}",
                                 data=json.dumps(obj).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:  # noqa: S310
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, json.load(e)


def _multipart(field, filename, data, boundary="BOUNDARY"):
    head = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{field}\"; "
            f"filename=\"{filename}\"\r\nContent-Type: image/png\r\n\r\n").encode()
    return b"\r\n".join([head + data, f"--{boundary}--\r\n".encode()]), \
        f"multipart/form-data; boundary={boundary}"


FAKE_ANALYSIS = {
    "analysis_version": "domains.atlas.visual-knowledge/v1",
    "document_ref": "d", "source_page": 0, "figure_id": "auto1",
    "entities": [{"id": "striatum", "name": "Striatum", "category": "anatomical-structure",
                   "bbox": {"x_min": 0.1, "y_min": 0.1, "x_max": 0.9, "y_max": 0.9},
                   "confidence": 0.9}],
    "relationships": [],
}


class _FakeMuse:
    def analyze_figure(self, *a, **k):
        from domains.atlas.schema import VisualAnalysis
        return VisualAnalysis.from_dict(dict(FAKE_ANALYSIS))

    def analyze_text(self, text, note="", document_ref="", figure_id=""):
        from domains.atlas.schema import VisualAnalysis, VisualEntity
        return VisualAnalysis(document_ref=document_ref, figure_id=figure_id or "t",
                              entities=[VisualEntity(id="t1", name="Thing",
                                                     category="component",
                                                     source_evidence=text[:60])],
                              relationships=[])


def test_upload_then_auto_create_lists_model(tmp_path):
    from PIL import Image
    server, thread = _serve(tmp_path / "data")
    port = server.server_address[1]
    try:
        src = tmp_path / "drop.png"
        Image.new("RGB", (60, 40), (9, 9, 9)).save(src)
        body, ctype = _multipart("file", "drop.png", src.read_bytes())
        req = urllib.request.Request(f"http://127.0.0.1:{port}/api/upload", data=body,
                                     headers={"Content-Type": ctype})
        with urllib.request.urlopen(req, timeout=10) as r:  # noqa: S310
            up = json.load(r)
        assert up["staged_path"].endswith("drop.png")
        real = atlas_app.MuseProvider
        atlas_app.MuseProvider = lambda *a, **k: _FakeMuse()  # noqa: E731
        try:
            s, auto = _post(port, "/api/auto-create",
                            {"path": up["staged_path"], "figure_id": "auto1"})
        finally:
            atlas_app.MuseProvider = real
        assert s == 200 and auto["model_created"] is True
        assert auto["figure_url"].startswith("/figures/")
        with urllib.request.urlopen(  # noqa: S310
                f"http://127.0.0.1:{port}{auto['figure_url']}", timeout=10) as r:
            assert r.status == 200
        s, models = _post(port, "/nope", {})
        assert s == 404
        import urllib.request as u
        with u.urlopen(f"http://127.0.0.1:{port}/api/models", timeout=10) as r:  # noqa: S310
            listed = json.load(r)["models"]
        assert [m for m in listed if m["figure_id"] == "auto1"][0]["entities"] == 1
        with u.urlopen(f"http://127.0.0.1:{port}/api/contract", timeout=10) as r:  # noqa: S310
            contract = json.load(r)
        assert contract["contract_version"] == "domains.atlas.api/v1"
        assert "POST /api/upload (multipart file=)" in contract["endpoints"]
    finally:
        server.shutdown()
        thread.join(timeout=5)
        atlas_app.Handler.store = None


def test_auto_create_from_url_and_epub_upload(tmp_path, monkeypatch):
    import zipfile
    import domains.atlas.sources as sources

    server, thread = _serve(tmp_path / "data")
    port = server.server_address[1]
    try:
        monkeypatch.setattr(sources, "ingest_any", lambda s: {
            "kind": "text", "title": "Mock article", "text": "Cortex drives striatum. " * 50,
            "document_ref": s})
        real = atlas_app.MuseProvider
        atlas_app.MuseProvider = lambda *a, **k: _FakeMuse()
        try:
            s, auto = _post(port, "/api/auto-create",
                            {"path": "https://example.com/article", "figure_id": "url1"})
        finally:
            atlas_app.MuseProvider = real
        assert s == 200 and auto["model_created"] is True
        assert auto["source_kind"] == "text"

        epub = tmp_path / "book.epub"
        with zipfile.ZipFile(epub, "w") as z:
            z.writestr("mimetype", "application/epub+zip")
            z.writestr("META-INF/container.xml",
                       '<container><rootfiles><rootfile full-path="c.opf"/></rootfiles></container>')
            z.writestr("c.opf",
                       '<package><metadata><dc:title>EB</dc:title></metadata>'
                       '<manifest><item id="x" href="x.xhtml"/></manifest>'
                       '<spine><itemref idref="x"/></spine></package>')
            z.writestr("x.xhtml", "<html><body><p>EPUB words here.</p></body></html>")
        monkeypatch.undo()  # real ingestion for the EPUB file path
        body, ctype = _multipart("file", "book.epub", epub.read_bytes())
        req = urllib.request.Request(f"http://127.0.0.1:{port}/api/upload", data=body,
                                     headers={"Content-Type": ctype})
        with urllib.request.urlopen(req, timeout=10) as r:  # noqa: S310
            up = json.load(r)
        assert up["text_backend"] == "atlas" and up["text_chars"] > 0
        real = atlas_app.MuseProvider
        atlas_app.MuseProvider = lambda *a, **k: _FakeMuse()
        try:
            s, auto = _post(port, "/api/auto-create",
                            {"path": up["staged_path"], "figure_id": "epub1"})
        finally:
            atlas_app.MuseProvider = real
        assert s == 200 and auto["model_created"] is True
    finally:
        server.shutdown()
        thread.join(timeout=5)
        atlas_app.Handler.store = None


class _BoxlessMuse:
    def analyze_figure(self, *a, **k):
        from domains.atlas.schema import VisualAnalysis, VisualEntity
        return VisualAnalysis(document_ref=k.get("document_ref", ""),
                              figure_id=k.get("figure_id", "f"),
                              entities=[VisualEntity(id="t", name="Thing",
                                                     category="component")],
                              relationships=[])


def test_video_without_boxes_warns_text_only(tmp_path, monkeypatch):
    import domains.atlas.sources as sources
    from PIL import Image
    from domains.atlas.app import auto_create_model
    from domains.atlas.config import AtlasConfig
    from domains.atlas.store import AtlasStore

    real_frames = sources.video_frames
    monkeypatch.setattr(sources, "video_frames",
                        lambda path, outdir, max_frames=4: [str(tmp_path / "f.png")])
    import random
    from PIL import ImageDraw
    img = Image.new("RGB", (320, 240), (10, 20, 30))
    rnd, draw = random.Random(4), ImageDraw.Draw(img)
    for _ in range(600):
        draw.point((rnd.randrange(320), rnd.randrange(240)),
                   fill=(rnd.randrange(256), rnd.randrange(256), rnd.randrange(256)))
    img.save(tmp_path / "f.png")
    (tmp_path / "v.mp4").write_bytes(b"fake")
    import domains.atlas.ingestion as ing
    real_ingest = ing.import_document
    monkeypatch.setattr(ing, "import_document",
                        lambda p, d, page=0: {"document_ref": p, "sha256": "ab" * 32,
                                             "original_name": "v.mp4"})
    result = auto_create_model(AtlasStore(str(tmp_path / "d")),
                               AtlasConfig(api_key="", data_dir=str(tmp_path / "d")),
                               str(tmp_path / "v.mp4"), muse_provider=_BoxlessMuse())
    assert result["source_kind"] == "video"
    assert "text-only" in result["warning"]
    assert result["located_entities"] == 0


class _RetryMuse:
    """Boxless first pass, grounded retry — like a hesitant live model."""
    _live_transport = True

    def __init__(self):
        self.calls = 0

    def analyze_figure(self, image_path, note="", **k):
        from domains.atlas.schema import VisualAnalysis, VisualEntity, BoundingBox
        self.calls += 1
        if "normalized 0-1000 box" in note:
            return VisualAnalysis(document_ref=k.get("document_ref", ""),
                                  figure_id=k.get("figure_id", "f"),
                                  entities=[VisualEntity(
                                      id="e", name="Cell", category="cell-type",
                                      bbox=BoundingBox(0.1, 0.1, 0.5, 0.5))],
                                  relationships=[])
        return VisualAnalysis(document_ref=k.get("document_ref", ""),
                              figure_id=k.get("figure_id", "f"),
                              entities=[VisualEntity(id="e", name="Cell",
                                                     category="cell-type")],
                              relationships=[])


def test_video_retries_for_grounding(tmp_path, monkeypatch):
    import domains.atlas.ingestion as ing
    import domains.atlas.sources as src
    from domains.atlas.app import auto_create_model
    from domains.atlas.config import AtlasConfig
    from domains.atlas.store import AtlasStore
    from PIL import Image, ImageDraw
    import random

    monkeypatch.setattr(src, "video_frames", lambda *a, **k: [str(tmp_path / "f.png")])
    img = Image.new("RGB", (320, 240), (10, 20, 30))
    rnd, draw = random.Random(4), ImageDraw.Draw(img)
    for _ in range(600):
        draw.point((rnd.randrange(320), rnd.randrange(240)),
                   fill=(rnd.randrange(256), rnd.randrange(256), rnd.randrange(256)))
    img.save(tmp_path / "f.png")
    (tmp_path / "v.mp4").write_bytes(b"fake")
    monkeypatch.setattr(ing, "import_document",
                        lambda p, d, page=0: {"document_ref": p, "sha256": "ab" * 32,
                                             "original_name": "v.mp4"})
    fake = _RetryMuse()
    result = auto_create_model(AtlasStore(str(tmp_path / "d")),
                               AtlasConfig(api_key="", data_dir=str(tmp_path / "d")),
                               str(tmp_path / "v.mp4"), muse_provider=fake)
    assert result["located_entities"] == 1 and not result["warning"]
    assert fake.calls == 2


def test_upload_rejects_empty_and_missing_file(tmp_path):
    server, thread = _serve(tmp_path / "data")
    port = server.server_address[1]
    try:
        s, body = _post(port, "/api/upload", {})
        assert s == 400
        body2, ctype = _multipart("other", "x.bin", b"data")
        req = urllib.request.Request(f"http://127.0.0.1:{port}/api/upload", data=body2,
                                     headers={"Content-Type": ctype})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:  # noqa: S310
                raise AssertionError(r.status)
        except urllib.error.HTTPError as e:
            assert e.code == 400
    finally:
        server.shutdown()
        thread.join(timeout=5)
        atlas_app.Handler.store = None


def test_cli_models_and_learn_offline(tmp_path, capsys):
    from domains.atlas.cli import main
    from domains.atlas.store import AtlasStore
    AtlasStore(str(tmp_path)).save_analysis("auto1", dict(FAKE_ANALYSIS))
    assert main(["--data", str(tmp_path), "models"]) == 0
    assert "auto1" in capsys.readouterr().out
    assert main(["--data", str(tmp_path), "show", "auto1"]) == 0
    assert main(["--data", str(tmp_path), "learn", "auto1", "spatial-recall",
                 "--answer", "striatum"]) == 0
    out = capsys.readouterr().out
    assert '"correct": true' in out
    assert main(["--data", str(tmp_path), "contract"]) == 0
