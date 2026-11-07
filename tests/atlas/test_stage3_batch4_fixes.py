"""Stage 3 batch 4 — failing-first guards for verified deferred findings.

B5 (HTML-escape mismatch) was reproduced as FALSE and is dropped, not fixed.
Run: python -m pytest tests/test_stage3_batch4_fixes.py -q -p no:cacheprovider
"""
import glob
import json
import os
import sys
import threading
import urllib.error
import urllib.request
from http.server import HTTPServer

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_weird_svg_scores_not_crashes():
    from domains.atlas import quality as q

    weird_font = ('<svg xmlns="http://www.w3.org/2000/svg">'
                  '<text font-size="medium">Cell</text></svg>')
    rep = q.infographic_quality(
        weird_font, {'entities': [{'id': 'c', 'name': 'Cell'}],
                     'relationships': []})
    assert isinstance(rep["score"], (int, float))

    pct_geom = ('<svg xmlns="http://www.w3.org/2000/svg">'
                '<rect x="0" y="0" width="100%" height="50"/>'
                '<text font-size="14">Cell</text></svg>')
    rep = q.infographic_quality(pct_geom, {'entities': [],
                                           'relationships': []})
    assert isinstance(rep["score"], (int, float))


def test_learn_bad_mode_400(tmp_path):
    from domains.atlas import app as atlas_app
    from domains.atlas.config import AtlasConfig

    atlas_app.Handler.store = None
    atlas_app.Handler.config = AtlasConfig.from_env(data_dir=str(tmp_path))
    server = HTTPServer(("127.0.0.1", 0), atlas_app.Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        from domains.atlas.demo.basal_ganglia_fixture import FIXTURE_ANALYSIS
        payload = json.dumps({"analysis": FIXTURE_ANALYSIS,
                              "mode": "bogus"}).encode()
        req = urllib.request.Request(  # noqa: S310
            f"http://127.0.0.1:{port}/api/learn", data=payload,
            method="POST", headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30):  # noqa: S310
                pytest.fail("expected HTTP 400 for bad learn mode")
        except urllib.error.HTTPError as e:
            assert e.code == 400, e.code
            body = json.loads(e.read().decode("utf-8"))
            assert "spatial-recall" in body["error"], body
            assert "KeyError" not in body["error"], body
    finally:
        server.shutdown()
        thread.join(timeout=5)
        atlas_app.Handler.store = None


def test_video_outdir_reuse_clean(tmp_path):
    pytest.importorskip("imageio_ffmpeg")
    from domains.atlas import materials as mat

    a = {"figure_id": "f",
         "entities": [{"id": str(i), "name": f"N{i}", "category": "other"}
                      for i in range(5)],
         "relationships": []}
    out = str(tmp_path / "frames")
    os.makedirs(out, exist_ok=True)
    mat.video_slideshow(a, out, fps=2, seconds_per_scene=0.5)
    n1 = len(glob.glob(os.path.join(out, "f_*.png")))
    small = {"figure_id": "f",
             "entities": [{"id": "0", "name": "N0", "category": "other"}],
             "relationships": []}
    mat.video_slideshow(small, out, fps=2, seconds_per_scene=0.5)
    n2 = len(glob.glob(os.path.join(out, "f_*.png")))
    assert n2 < n1, (n1, n2)


def test_parallel_rel_question_ids_unique():
    from domains.atlas import materials as mat

    a = {"figure_id": "f",
         "entities": [{"id": "A", "name": "A"}, {"id": "B", "name": "B"}],
         "relationships": [{"source_id": "A", "target_id": "B",
                            "rel_type": "activates"},
                           {"source_id": "A", "target_id": "B",
                            "rel_type": "inhibits"}]}
    bank = mat.question_bank(a)
    ids = [x["id"] for x in bank["questions"] if x["kind"] == "relationship-recall"]
    assert len(ids) == 2 and len(set(ids)) == 2, ids
