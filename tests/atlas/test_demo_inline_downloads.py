"""Demo inline downloads: browser-only fixture must download without a model.

Stage-4 check showed every demo artifact link (`?figure_id=demo`) 404s because
the fixture lives in the browser only. The five download endpoints now accept
`POST {analysis, format?}` (tour/quality/summary parity); the toolbar tour fix
(ADR-011) already proved the pattern. This pins each inline route.
"""
import json
import threading
import urllib.request
import urllib.error
from http.server import HTTPServer

from domains.atlas import app as atlas_app
from domains.atlas.config import AtlasConfig
from domains.atlas.store import AtlasStore
from domains.atlas.demo.basal_ganglia_fixture import FIXTURE_ANALYSIS


def _post(port, path, obj):
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        data=json.dumps(obj).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:  # noqa: S310
        return r.status, r.headers.get("Content-Type", ""), r.read()


def test_inline_download_routes_serve_fixture(tmp_path):
    AtlasStore(str(tmp_path)).save_analysis("inline-fig", dict(FIXTURE_ANALYSIS))
    atlas_app.Handler.store = None
    atlas_app.Handler.config = AtlasConfig.from_env(data_dir=str(tmp_path))
    server = HTTPServer(("127.0.0.1", 0), atlas_app.Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        body = {"analysis": FIXTURE_ANALYSIS}
        status, ctype, blob = _post(port, "/api/diagram", {**body, "format": "svg"})
        assert status == 200 and "svg" in ctype and blob.lstrip().startswith(b"<svg")
        status, ctype, blob = _post(port, "/api/diagram", {**body, "format": "png"})
        assert status == 200 and ctype == "image/png"
        assert blob[:8] == b"\x89PNG\r\n\x1a\n"
        status, ctype, blob = _post(port, "/api/podcast", {**body, "format": "md"})
        assert status == 200 and blob.decode("utf-8").startswith("# ")
        status, _ctype, blob = _post(port, "/api/podcast", {**body, "format": "json"})
        assert json.loads(blob)["segments"]
        status, ctype, blob = _post(port, "/api/questions", {**body, "format": "md"})
        assert status == 200 and len(blob.decode("utf-8")) > 0
        status, _ctype, blob = _post(port, "/api/questions", {**body, "format": "json"})
        assert json.loads(blob)["questions"]
        status, ctype, blob = _post(port, "/api/model3d", {**body, "format": "obj"})
        assert status == 200 and b"\nv " in blob
        status, ctype, blob = _post(port, "/api/flashcards/export", body)
        assert status == 200 and b"\t" in blob
    finally:
        server.shutdown()
        thread.join(timeout=5)
        atlas_app.Handler.store = None


def test_demo_figure_id_still_404s_on_get(tmp_path):
    """Pins the browser-only contract: GET ?figure_id=demo is not a model."""
    atlas_app.Handler.store = None
    atlas_app.Handler.config = AtlasConfig.from_env(data_dir=str(tmp_path))
    server = HTTPServer(("127.0.0.1", 0), atlas_app.Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with urllib.request.urlopen(  # noqa: S310
                f"http://127.0.0.1:{port}/api/diagram?figure_id=demo&format=svg",
                timeout=30) as _r:
            raise AssertionError("demo GET should not resolve server-side")
    except urllib.error.HTTPError as e:
        assert e.code == 404
        assert "demo" in e.read().decode()
    finally:
        server.shutdown()
        thread.join(timeout=5)
        atlas_app.Handler.store = None
