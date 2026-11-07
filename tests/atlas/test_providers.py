from domains.atlas.config import AtlasConfig
from domains.atlas.muse_provider import MuseProvider
from domains.atlas.sam_provider import SamProvider
from domains.atlas.schema import BoundingBox


def _muse_transport(payload):
    assert payload["model"].startswith("muse-spark")
    assert payload["response_format"]["type"] == "json_schema"
    content = [c for c in payload["messages"][1]["content"] if c["type"] == "image_url"]
    assert content and content[0]["image_url"]["url"].startswith("data:image/")
    return {"choices": [{"message": {"content":
        '{"entities": [{"id": "striatum", "name": "Striatum", '
        '"category": "anatomical-structure", "box": [10, 10, 50, 50], '
        '"confidence": 0.9}], "relationships": []}'}}]}


def _sam_transport(payload):
    assert payload["model"] == "sam-3.1"
    kinds = [c["type"] for c in payload["input"][0]["content"]]
    assert "input_text" in kinds and "input_image" in kinds
    return {"mask_ref": "", "box": [10, 10, 50, 50]}


def test_muse_provider_mock(tmp_path):
    img = tmp_path / "f.png"
    img.write_bytes(__import__("base64").b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="))
    cfg = AtlasConfig(api_key="test", data_dir=str(tmp_path))
    analysis = MuseProvider(cfg, transport=_muse_transport).analyze_figure(str(img))
    assert analysis.entities[0].id == "striatum"


def test_sam_scans_raw_before_fallback(tmp_path):
    from domains.atlas.sam_provider import _scan_box, _scan_file_id
    assert _scan_box('{"boxes": [[120, 200, 340, 400]]}') == [120.0, 200.0, 340.0, 400.0]
    assert _scan_box("no boxes here") is None
    assert _scan_box('{"a": [5, 5, 5, 5]}') is None  # degenerate, not a box
    assert _scan_file_id("mask file_id: abcDEF12-34") == "abcDEF12-34"
    assert _scan_file_id("nothing") == ""
    cfg = AtlasConfig(api_key="test", data_dir=str(tmp_path))
    img = tmp_path / "f.png"
    img.write_bytes(b"fakepng")

    def empty_live(payload):
        return {"raw": '{"status":"completed","output":[]}'}

    seg = SamProvider(cfg, transport=empty_live).segment(str(img), "cell", "c1")
    assert seg.kind == "bbox-fallback"
    assert "no localizable output" in seg.raw_note


def test_polish_summary_bans_machine_tokens(tmp_path):
    from domains.atlas.muse_provider import MuseProvider
    from domains.atlas.config import AtlasConfig

    seen = {}

    def fake_transport(payload):
        seen["system"] = payload["messages"][0]["content"]
        return {"choices": [{"message": {"content": "Polished."}}]}

    cfg = AtlasConfig(api_key="k", data_dir=str(tmp_path))
    assert MuseProvider(cfg, transport=fake_transport).polish_summary(
        {"overview": "o", "entities": [], "pathways": []}) == "Polished."
    assert "plain English" in seen["system"]
    assert "receives-input-from" in seen["system"]  # glossary translates it away


def test_sam_bbox_fallback(tmp_path):
    img = tmp_path / "f.png"
    img.write_bytes(b"fakepng")
    cfg = AtlasConfig(api_key="test", data_dir=str(tmp_path))
    seg = SamProvider(cfg, transport=_sam_transport).segment(
        str(img), "striatum", "striatum",
        BoundingBox(0, 0, 0.5, 0.5))
    assert seg.kind == "bbox-fallback"  # no mask decoded -> honest fallback, never fake mask
    assert seg.bbox is not None
