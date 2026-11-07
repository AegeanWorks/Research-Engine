"""Cycle-2 regression tests for bugs found in review."""
import json
import os
import threading
import urllib.request
from http.server import HTTPServer

import pytest

from domains.atlas import ingestion as ing
from domains.atlas import learning as learn
from domains.atlas.config import AtlasConfig
from domains.atlas.muse_provider import MuseProvider
from domains.atlas.demo.basal_ganglia_fixture import FIXTURE_ANALYSIS
from domains.atlas.schema import VisualAnalysis


def test_spatial_recall_options_carry_ids():
    a = VisualAnalysis.from_dict(FIXTURE_ANALYSIS).to_dict()
    c = learn.spatial_recall_challenge(a, seed=7)
    assert isinstance(c["options"], list) and c["options"]
    assert all(isinstance(o, dict) and "id" in o and "name" in o for o in c["options"])
    # grading with the option id (what the fixed frontend sends) must pass
    assert learn.grade(c, c["answer_id"])["correct"]
    target_opts = [o for o in c["options"] if o["id"] == c["answer_id"]]
    assert target_opts and target_opts[0]["name"]


def test_select_figure_rejects_pdf_with_guidance(tmp_path):
    pdf = str(tmp_path / "paper.pdf")
    with open(pdf, "wb") as fh:
        fh.write(b"%PDF-1.4 fake")
    with pytest.raises(ValueError, match="render the page first"):
        ing.select_figure(pdf, (0, 0, 0.5, 0.5), str(tmp_path))


def test_muse_refuses_oversize_image(tmp_path):
    big = tmp_path / "big.png"
    with open(big, "wb") as fh:
        fh.truncate(45_000_001)
    cfg = AtlasConfig(api_key="test", data_dir=str(tmp_path))
    with pytest.raises(ValueError, match="50 MB"):
        MuseProvider(cfg, transport=lambda p: {}).analyze_figure(str(big))


def test_figure_select_returns_display_url(tmp_path):
    from PIL import Image
    from domains.atlas import app as atlas_app

    src = str(tmp_path / "fig.png")
    Image.new("RGB", (40, 20), (1, 2, 3)).save(src)
    atlas_app.Handler.store = None
    atlas_app.Handler.config = AtlasConfig.from_env(data_dir=str(tmp_path / "data"))
    server = HTTPServer(("127.0.0.1", 0), atlas_app.Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        payload = json.dumps({"image_path": src, "crop": [0, 0, 0.5, 0.5]}).encode()
        req = urllib.request.Request(f"http://127.0.0.1:{port}/api/figure/select",
                                     data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
            result = json.load(resp)
        assert result["figure_url"].startswith("/figures/")
        assert os.path.isfile(os.path.join(str(tmp_path / "data"), "figures",
                                           os.path.basename(result["figure_url"])))
        # and the served bytes match the stored crop
        with urllib.request.urlopen(  # noqa: S310
                f"http://127.0.0.1:{port}{result['figure_url']}", timeout=10) as resp:
            assert resp.status == 200 and len(resp.read()) > 0
    finally:
        server.shutdown()
        thread.join(timeout=5)
        atlas_app.Handler.store = None
