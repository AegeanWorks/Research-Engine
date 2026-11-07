"""Contract coverage: every GET endpoint the machine contract promises exists.

POST creation paths are covered in their own suites (they need keys or
uploads); this test pins that no GET route in GET /api/contract rots.
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
from domains.atlas.schema import VisualAnalysis


def test_every_contracted_get_endpoint_responds(tmp_path):
    data = VisualAnalysis.from_dict(FIXTURE_ANALYSIS).to_dict()
    AtlasStore(str(tmp_path)).save_analysis("contract-fig", data)
    atlas_app.Handler.store = None
    atlas_app.Handler.config = AtlasConfig.from_env(data_dir=str(tmp_path))
    server = HTTPServer(("127.0.0.1", 0), atlas_app.Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        contract = atlas_app.api_contract()
        get_routes = [k for k in contract["endpoints"] if k.startswith("GET ")]
        assert len(get_routes) >= 10
        checked = 0
        import re
        for route in get_routes:
            template = route[4:].split(" ")[0]
            base, _, query = template.partition("?")
            query = query.replace("figure_id=", "figure_id=contract-fig")
            query = re.sub(r"format=([^&]*)", lambda m: "format=" + m.group(1).split("|")[0], query)
            path = base + ("?" + query if query else "")
            try:
                with urllib.request.urlopen(  # noqa: S310
                        f"http://127.0.0.1:{port}{path}", timeout=30) as r:
                    assert r.status == 200, (route, r.status)
                    checked += 1
            except urllib.error.HTTPError as e:
                raise AssertionError(f"{route} -> HTTP {e.code}")
        assert checked == len(get_routes)
        # and the text digest variant too
        with urllib.request.urlopen(  # noqa: S310
                f"http://127.0.0.1:{port}/api/models?format=text", timeout=30) as r:
            assert r.status == 200
    finally:
        server.shutdown()
        thread.join(timeout=5)
        atlas_app.Handler.store = None
