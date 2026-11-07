"""Attach-mask endpoint + /masks/ serving tests (segmentation loop)."""
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


def _analysis():
    return {
        "analysis_version": "domains.atlas.visual-knowledge/v1",
        "document_ref": "d", "source_page": 0, "figure_id": "fig1",
        "entities": [
            {"id": "striatum", "name": "Striatum", "category": "anatomical-structure",
             "bbox": {"x_min": 0.1, "y_min": 0.1, "x_max": 0.5, "y_max": 0.5},
             "confidence": 0.9},
        ],
        "relationships": [],
    }


def test_attach_mask_flow_and_traversal_guard(tmp_path):
    server, thread = _serve(tmp_path / "data")
    port = server.server_address[1]
    try:
        s, _ = _post(port, "/api/analysis/load", {"figure_id": "fig1", "analysis": _analysis()})
        assert s == 200
        s, body = _post(port, "/api/analysis/attach-mask",
                        {"figure_id": "fig1", "entity_id": "striatum",
                         "kind": "bbox-fallback", "mask_ref": "",
                         "bbox": {"x_min": 0.1, "y_min": 0.1, "x_max": 0.5, "y_max": 0.5}})
        assert s == 200
        assert body["analysis"]["entities"][0]["mask_ref"] == ""
        s, _ = _post(port, "/api/analysis/attach-mask",
                     {"figure_id": "fig1", "entity_id": "ghost",
                      "kind": "bbox-fallback", "mask_ref": ""})
        assert s == 400
        s, _ = _post(port, "/api/analysis/attach-mask",
                     {"figure_id": "nope", "entity_id": "striatum",
                      "kind": "mask", "mask_ref": "x"})
        assert s == 400
        s, _ = _post(port, "/api/analysis/attach-mask",
                     {"figure_id": "fig1", "entity_id": "striatum",
                      "kind": "nonsense", "mask_ref": "x"})
        assert s == 400
        # /masks/ serves data-dir files only; traversal collapses to basename
        masks = os.path.join(str(tmp_path / "data"), "masks")
        os.makedirs(masks, exist_ok=True)
        with open(os.path.join(masks, "m1.bin"), "wb") as fh:
            fh.write(b"maskbytes")
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/masks/m1.bin",  # noqa: S310
                                    timeout=10) as r:
            assert r.status == 200 and r.read() == b"maskbytes"
        try:
            with urllib.request.urlopen(  # noqa: S310
                    f"http://127.0.0.1:{port}/masks/../analyses/fig1.analysis.json",
                    timeout=10) as r:
                raise AssertionError(f"traversal served: {r.status}")
        except urllib.error.HTTPError as e:
            assert e.code == 404
    finally:
        server.shutdown()
        thread.join(timeout=5)
        atlas_app.Handler.store = None
