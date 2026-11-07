"""Automatic video + quality analysis (goal slice)."""
import json
import threading
import urllib.request
import urllib.error
from http.server import HTTPServer

import pytest

from domains.atlas import quality as qa
from domains.atlas.schema import VisualAnalysis
from domains.atlas.demo.basal_ganglia_fixture import FIXTURE_ANALYSIS


def _analysis():
    return VisualAnalysis.from_dict(FIXTURE_ANALYSIS).to_dict()


def _tiny():
    a = _analysis()
    a["entities"] = a["entities"][:2]
    a["relationships"] = [r for r in a["relationships"]
                          if r["source_id"] in ("cortex", "striatum")
                          and r["target_id"] in ("cortex", "striatum")]
    a["figure_id"] = "tiny"
    return a


def _deck():
    from domains.atlas import flashcards as fc
    return fc.build_deck(_analysis())


def test_flashcard_quality_perfect_and_broken():
    good = qa.flashcard_quality(_deck(), _analysis())
    assert good["score"] == 100 and not good["issues"]
    bad = qa.flashcard_quality({"figure_id": "x", "cards": [
        {"id": "d1", "entity_id": "striatum", "kind": "identify-description",
         "front": {"text": "x" * 300}, "back": {"text": ""}}]}, _analysis())
    assert bad["score"] < 100
    assert any("280" in i for i in bad["issues"]) and any("answers" in i for i in bad["issues"])


def test_infographic_quality_spots_problems():
    from domains.atlas import materials as mat
    good = qa.infographic_quality(mat.diagram_svg(_analysis()), _analysis())
    assert good["score"] == 100, good["issues"]
    broken = mat.diagram_svg(_analysis()).replace("Striatum", "XXXX")
    bad = qa.infographic_quality(broken, _analysis())
    assert bad["score"] < 100 and any("unlabeled" in i for i in bad["issues"])
    assert qa.infographic_quality("not xml", _analysis())["score"] == 0


def test_podcast_and_model3d_quality():
    from domains.atlas import materials as mat
    from domains.atlas import models3d as m3d
    script = mat.podcast_script(_analysis())
    assert qa.podcast_quality(script, _analysis())["score"] == 100
    thin = dict(script, segments=[{"speaker": "HOST", "cue": "cold open", "text": "hi"}],
                estimated_minutes=0.1)
    assert qa.podcast_quality(thin, _analysis())["score"] < 100
    obj = m3d.export_obj(_analysis())
    assert qa.model3d_quality(obj, _analysis())["score"] == 100
    assert qa.model3d_quality(obj.replace("v 0", "v nan", 1), _analysis())["score"] < 100


def test_video_render_and_quality(tmp_path):
    from domains.atlas import materials as mat
    pytest.importorskip("imageio_ffmpeg")
    info = mat.video_slideshow(_tiny(), str(tmp_path / "vid"), fps=5, seconds_per_scene=0.4)
    assert info["scenes"] == 4 and info["mp4"].endswith(".mp4")
    tiny = qa.video_quality_mp4(info["mp4"])
    assert tiny["score"] < 75 and tiny["issues"]  # honest: a 2s stub is a poor study video
    a = _analysis()
    a["entities"] = a["entities"][:4]
    a["relationships"] = [r for r in a["relationships"]
                          if r["source_id"] in {e["id"] for e in a["entities"]}
                          and r["target_id"] in {e["id"] for e in a["entities"]}]
    full = mat.video_slideshow(a, str(tmp_path / "vid2"), fps=10, seconds_per_scene=1.0)
    report = qa.video_quality_mp4(full["mp4"])
    assert report["score"] >= 75, report
    missing = qa.video_quality_mp4(str(tmp_path / "nope.mp4"))
    assert missing["score"] == 0


def test_quality_and_video_endpoints_and_cli(tmp_path):
    from domains.atlas import app as atlas_app
    from domains.atlas.config import AtlasConfig
    from domains.atlas.store import AtlasStore

    from domains.atlas.schema import VisualAnalysis
    saved = {"figure_id": "qv", **{k: v for k, v in _tiny().items() if k != "figure_id"}}
    VisualAnalysis.from_dict(saved)  # validate fixture shape once
    AtlasStore(str(tmp_path)).save_analysis("qv", saved)
    atlas_app.Handler.store = None
    atlas_app.Handler.config = AtlasConfig.from_env(data_dir=str(tmp_path))
    server = HTTPServer(("127.0.0.1", 0), atlas_app.Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        # Regression: every route must work in one server lifetime — an inline
        # import inside one branch once poisoned the whole handler (UnboundLocalError).
        load = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/analysis/load",
            data=json.dumps({"figure_id": "qv2", "analysis": saved}).encode(),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(load, timeout=10) as r:  # noqa: S310
            assert json.load(r)["ok"] is True
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/quality",
            data=json.dumps({"figure_id": "qv"}).encode(),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as r:  # noqa: S310
            report = json.load(r)
        assert report["overall"] > 80, report
        assert set(report) >= {"flashcards", "podcast", "infographic", "model3d", "overall"}
        from domains.atlas.cli import main
        assert main(["--data", str(tmp_path), "quality", "qv"]) == 0
    finally:
        server.shutdown()
        thread.join(timeout=5)
        atlas_app.Handler.store = None
