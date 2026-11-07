"""Offline no-key path: every drop becomes a real, honestly-labelled model."""
import json

import pytest

from domains.atlas import offline as off
from domains.atlas import sources as src
from domains.atlas.app import auto_create_model, honest_error
from domains.atlas.config import AtlasConfig
from domains.atlas.store import AtlasStore


TEXT = ("The striatum receives input from the cortex. The striatum inhibits "
        "the globus pallidus. The cortex activates the striatum. " * 4)


def test_offline_builder_validates():
    analysis = off.build_offline_analysis(TEXT, document_ref="d", figure_id="f")
    assert not analysis.validate()
    assert analysis.entities and analysis.relationships
    assert all(e.source_evidence and e.model_inferred for e in analysis.entities)
    assert all("offline-extractive" in e.uncertainty for e in analysis.entities)


def test_auto_create_text_without_key_uses_offline(tmp_path):
    src = tmp_path / "notes.txt"
    src.write_text(TEXT, encoding="utf-8")
    store = AtlasStore(str(tmp_path / "data"))
    config = AtlasConfig(api_key="", data_dir=str(tmp_path / "data"))
    result = auto_create_model(store, config, str(src))
    assert result["model_created"] is True and result["offline"] is True
    assert "offline-extractive" in result["warning"]


def test_auto_create_image_without_key_uses_offline(tmp_path):
    from PIL import Image
    src = tmp_path / "cortex.png"
    Image.new("RGB", (80, 60), (10, 20, 30)).save(src)
    store = AtlasStore(str(tmp_path / "data2"))
    config = AtlasConfig(api_key="", data_dir=str(tmp_path / "data2"))
    result = auto_create_model(store, config, str(src), note="cortex layers")
    assert result["model_created"] is True and result["offline"] is True
    assert result["figure_url"].startswith("/figures/")


def test_keyless_live_call_still_refuses():
    from domains.atlas.muse_provider import MuseProvider
    config = AtlasConfig(api_key="")
    try:
        MuseProvider(config).analyze_text(TEXT)
    except RuntimeError as exc:
        assert "refusing live call" in str(exc)
    else:
        raise AssertionError("keyless live call did not refuse")


def test_honest_error_names_cause_and_fix():
    body = honest_error(Exception(
        "No text on any of 3 page(s): scanned images or encryption."))
    assert "scanned-image PDF" in body["cause"] and "OCR" in body["fix"]
    keyless = honest_error(RuntimeError("MODEL_API_KEY/META_API_KEY is not set; refusing live call"))
    assert keyless["cause"] and keyless["fix"]


def test_extended_quality_covers_new_materials():
    from domains.atlas.demo.basal_ganglia_fixture import FIXTURE_ANALYSIS
    from domains.atlas import flashcards as fc
    from domains.atlas import materials as mat
    from domains.atlas import quality as qa
    from domains.atlas import summaries as sm
    data = json.loads(json.dumps(FIXTURE_ANALYSIS))
    report = qa.quality_report(data, {
        "deck": fc.build_deck(data), "podcast": mat.podcast_script(data),
        "diagram_svg": mat.diagram_svg(data), "tour": mat.tour_3d(data),
        "questions": mat.question_bank(data), "summary": sm.extractive_summary(data),
        "include_learn": True})
    for key in ("flashcards", "podcast", "infographic", "tour",
                "questions", "summary", "learn"):
        assert key in report, key
        assert 0 <= report[key]["score"] <= 100
    assert 0 <= report["overall"] <= 100


def _break_ffmpeg(monkeypatch, mode):
    """Simulate a machine whose ffmpeg is unusable, three ways."""
    import imageio_ffmpeg
    monkeypatch.setattr("shutil.which", lambda *a, **k: None)
    if mode == "raising-provider":
        def _boom():
            raise RuntimeError("bundle exploded")
        monkeypatch.setattr(imageio_ffmpeg, "get_ffmpeg_exe", _boom)
    elif mode == "missing-binary":
        monkeypatch.setattr(imageio_ffmpeg, "get_ffmpeg_exe",
                            lambda: r"C:\nonexistent-ffmpeg\ffmpeg.exe")
    elif mode == "no-provider-attr":
        monkeypatch.delattr(imageio_ffmpeg, "get_ffmpeg_exe")


@pytest.mark.parametrize("mode", ["raising-provider", "missing-binary",
                                  "no-provider-attr"])
def test_broken_ffmpeg_refuses_with_cause_and_fix(monkeypatch, mode,
                                                  tmp_path):
    _break_ffmpeg(monkeypatch, mode)
    with pytest.raises(ValueError, match="video needs ffmpeg"):
        src.video_frames(str(tmp_path / "clip.mp4"), str(tmp_path / "fr"))
    clip = tmp_path / "clip.mp4"
    clip.write_bytes(b"\x00\x00\x00\x18ftypmp42")
    store = AtlasStore(str(tmp_path / "data"))
    config = AtlasConfig(api_key="", data_dir=str(tmp_path / "data"))
    with pytest.raises(ValueError, match="video needs ffmpeg") as excinfo:
        auto_create_model(store, config, str(clip))
    body = honest_error(excinfo.value)
    assert "video needs ffmpeg" in body["cause"]
    assert "ffmpeg" in body["fix"]
