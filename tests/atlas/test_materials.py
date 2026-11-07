"""Materials: diagrams, 3D tours, podcast scripts, question banks (0.10.0)."""
import json
import threading
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from http.server import HTTPServer

from domains.atlas import materials as mat
from domains.atlas.schema import VisualAnalysis
from domains.atlas.demo.basal_ganglia_fixture import FIXTURE_ANALYSIS


def _analysis():
    return VisualAnalysis.from_dict(FIXTURE_ANALYSIS).to_dict()


def test_diagram_svg_valid_and_complete():
    svg = mat.diagram_svg(_analysis())
    root = ET.fromstring(svg)  # well-formed XML
    assert root.tag.endswith("svg")
    for name in ("Striatum", "GPe", "Thalamus", "inhibits"):
        assert name in svg


def test_declutter_spreads_overlaps_deterministically():
    from domains.atlas import materials as mat
    rects = {"a": (100.0, 100.0, 120.0, 60.0), "b": (150.0, 120.0, 120.0, 60.0),
             "c": (500.0, 400.0, 100.0, 50.0)}
    once = mat._declutter(rects)
    twice = mat._declutter(mat._declutter(rects))
    assert once == twice  # fixed point: deterministic and stable
    assert not mat._overlaps(once["a"], once["b"])
    for x, y, w, h in once.values():
        assert 0 <= x and 0 <= y and x + w <= mat.W and y + h <= mat.H
    # untouched when nothing overlaps
    solo = {"a": (100.0, 100.0, 50.0, 50.0)}
    assert mat._declutter(solo) == solo


def test_diagram_large_text_only_grid_has_no_overlaps():
    from domains.atlas import materials as mat
    from domains.atlas import quality as qa
    ents = [{"id": f"h{i}", "name": f"Topic {i}", "category": "other",
             "description": f"About topic {i}.", "source_evidence": f"page {i}",
             "bbox": None, "confidence": 0.9} for i in range(60)]
    analysis = {"figure_id": "big-text", "entities": ents, "relationships": []}
    report = qa.infographic_quality(mat.diagram_svg(analysis), analysis)
    assert report["score"] == 100, report["issues"]


def test_font_prefers_turkish_capable_truetype(tmp_path):
    from domains.atlas import materials as mat
    font, src = mat._font(20)
    assert hasattr(font, "getmask")
    if any(p for p in [r"C:\Windows\Fonts\arial.ttf",
                       "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                       "/usr/share/fonts/dejavu/DejaVuSans.ttf",
                       "/System/Library/Fonts/Supplemental/Arial.ttf"]
           if __import__("os").path.isfile(p)):
        assert src != "bundled-fallback", src
    # Turkish renders without raising anywhere text is drawn.
    img = mat.diagram_png({"figure_id": "Başarı ÇĞŞİÖÜ",
                           "entities": [{"id": "e", "name": "Başarı ÇĞŞ",
                                         "category": "other"}],
                           "relationships": []})
    assert img[:8] == b"\x89PNG\r\n\x1a\n"


def _two_layer_analysis():
    from domains.atlas.schema import VisualAnalysis
    return VisualAnalysis.from_dict({
        "figure_id": "layers", "entities": [
            {"id": "m", "name": "Molecule", "category": "molecule",
             "bbox": {"x_min": 0.05, "y_min": 0.05, "x_max": 0.4, "y_max": 0.3},
             "confidence": 0.9},
            {"id": "p", "name": "Pathway", "category": "pathway",
             "bbox": {"x_min": 0.55, "y_min": 0.55, "x_max": 0.95, "y_max": 0.9},
             "confidence": 0.9}],
        "relationships": []}).to_dict()


def test_diagram_poster_has_header_legend_footer():
    from domains.atlas import materials as mat
    from domains.atlas.schema import VisualAnalysis
    from domains.atlas.demo.basal_ganglia_fixture import FIXTURE_ANALYSIS
    a = VisualAnalysis.from_dict(FIXTURE_ANALYSIS).to_dict()
    svg = mat.diagram_svg(a)
    assert "Boxes mark figure locations" in svg
    assert "generated from the validated analysis" in svg
    assert 'id="dots"' in svg  # dotted backdrop, not flat void
    svg2 = mat.diagram_svg(_two_layer_analysis())
    strokes = {l.split('stroke="')[1].split('"')[0]
               for l in svg2.splitlines() if 'rx="10"' in l}
    assert len(strokes) == 2  # boxes shaded by knowledge layer


def test_brand_assets_name_the_right_project():
    import pathlib
    from PIL import Image
    assets = pathlib.Path(__file__).resolve().parents[2] / "domains" / "atlas" / "assets"
    social = (assets / "social-preview.svg").read_text(encoding="utf-8")
    assert "github.com/AegeanWorks/Atlas" in social
    assert ">aikit<" not in social  # template leftover, not this project
    assert "Atlas" in social
    png = assets / "social-preview.png"  # GitHub can't display SVG cards
    assert png.is_file()
    with Image.open(png) as im:  # hygiene: allow binary image open needs no text encoding
        assert im.size == (1280, 640)


def test_video_frames_carry_scene_counter_and_progress():
    import tempfile
    from PIL import Image
    from domains.atlas import materials as mat
    from domains.atlas.schema import VisualAnalysis
    from domains.atlas.demo.basal_ganglia_fixture import FIXTURE_ANALYSIS
    a = VisualAnalysis.from_dict(FIXTURE_ANALYSIS).to_dict()
    info = mat.video_slideshow(a, tempfile.mkdtemp(), fps=2, seconds_per_scene=0.5)
    assert info["scenes"] == len(a["entities"]) + 2
    last = sorted(__import__("glob").glob(info["mp4"].replace("study.mp4", "f_*.png")))[-1]
    with Image.open(last) as frame:  # hygiene: allow binary image open needs no text encoding
        strip = frame.convert("RGB").crop((70, mat.H - 26, mat.W - 70, mat.H - 20))
        teal = sum(1 for px in strip.getdata() if px[0] < 80 and px[1] > 150 and px[2] > 150)
        assert teal > strip.width * 0.5  # final scene: progress bar (nearly) full


def test_podcast_segments_carry_monotonic_timestamps():
    from domains.atlas import materials as mat
    from domains.atlas.schema import VisualAnalysis
    from domains.atlas.demo.basal_ganglia_fixture import FIXTURE_ANALYSIS
    script = mat.podcast_script(VisualAnalysis.from_dict(FIXTURE_ANALYSIS).to_dict())
    assert script["segments"][0]["starts_at"] == "00:00"
    times = [s["starts_at"] for s in script["segments"]]
    assert times == sorted(times) and len(set(times)) > 1
    md = mat.podcast_markdown(script)
    assert "[00:00]" in md


def test_diagram_png_opens():
    from PIL import Image
    import io
    with Image.open(io.BytesIO(mat.diagram_png(_analysis()))) as img:  # hygiene: allow binary image open needs no text encoding
        assert img.size == (960, 640) and img.mode == "RGB"


def test_tour_orders_layers():
    tour = mat.tour_3d(_analysis())
    layers = [s["layer"] for s in tour["stops"]]
    assert layers == sorted(layers) and len(tour["stops"]) == 7
    assert all(s["connections"] for s in tour["stops"] if s["entity_id"] != "snr")


def test_podcast_single_entity_has_no_dangling_walk():
    from domains.atlas import materials as mat
    script = mat.podcast_script({"figure_id": "solo", "entities": [
        {"id": "only", "name": "Only", "category": "other",
         "description": "The whole lesson.", "confidence": 0.9}],
        "relationships": []})
    walk = next(s for s in script["segments"] if s["cue"] == "pathway walk")
    assert "end to end: ." not in walk["text"]
    recap = next(s for s in script["segments"] if s["cue"] == "recap + quiz teasers")
    assert "Recap in one breath: ." not in recap["text"]


def test_podcast_covers_entities_and_times():
    script = mat.podcast_script(_analysis())
    text = " ".join(s["text"] for s in script["segments"])
    for name in ("Striatum", "GPe", "Thalamus", "STN"):
        assert name in text
    assert script["estimated_minutes"] > 0
    md = mat.podcast_markdown(script)
    assert md.startswith("#") and "HOST" in md


def test_question_bank_answers():
    bank = mat.question_bank(_analysis())
    kinds = {q["kind"] for q in bank["questions"]}
    assert {"identify-description", "spatial-recall", "relationship-recall"} <= kinds
    assert all(q["answer"] for q in bank["questions"])
    md = mat.questions_markdown(bank)
    assert "## Answers" in md and md.count("\n") > len(bank["questions"])


def test_material_endpoints_and_cli(tmp_path):
    from domains.atlas import app as atlas_app
    from domains.atlas.config import AtlasConfig
    from domains.atlas.store import AtlasStore

    AtlasStore(str(tmp_path)).save_analysis("m1", {**_analysis(), "figure_id": "m1"})
    atlas_app.Handler.store = None
    atlas_app.Handler.config = AtlasConfig.from_env(data_dir=str(tmp_path))
    server = HTTPServer(("127.0.0.1", 0), atlas_app.Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with urllib.request.urlopen(  # noqa: S310
                f"http://127.0.0.1:{port}/api/diagram?figure_id=m1&format=svg",
                timeout=10) as r:
            assert r.status == 200 and b"<svg" in r.read()
        with urllib.request.urlopen(  # noqa: S310
                f"http://127.0.0.1:{port}/api/diagram?figure_id=m1&format=png",
                timeout=10) as r:
            assert r.read()[:8] == b"\x89PNG\r\n\x1a\n"
        with urllib.request.urlopen(  # noqa: S310
                f"http://127.0.0.1:{port}/api/tour?figure_id=m1", timeout=10) as r:
            assert len(json.load(r)["stops"]) == 7
        with urllib.request.urlopen(  # noqa: S310
                f"http://127.0.0.1:{port}/api/podcast?figure_id=m1&format=json",
                timeout=10) as r:
            assert json.load(r)["segments"]
        with urllib.request.urlopen(  # noqa: S310
                f"http://127.0.0.1:{port}/api/questions?figure_id=m1&format=md",
                timeout=10) as r:
            assert b"## Answers" in r.read()
        try:
            with urllib.request.urlopen(  # noqa: S310
                    f"http://127.0.0.1:{port}/api/diagram?figure_id=nope",
                    timeout=10):
                raise AssertionError("expected 404")
        except urllib.error.HTTPError as e:
            assert e.code == 404
    finally:
        server.shutdown()
        thread.join(timeout=5)
        atlas_app.Handler.store = None


def test_cli_materials(tmp_path, capsys):
    from domains.atlas.cli import main
    from domains.atlas.store import AtlasStore
    AtlasStore(str(tmp_path)).save_analysis("m1", {**_analysis(), "figure_id": "m1"})
    assert main(["--data", str(tmp_path), "materials", "m1", "tour"]) == 0
    assert "stops" in capsys.readouterr().out
    out = str(tmp_path / "m1-questions.md")
    assert main(["--data", str(tmp_path), "materials", "m1", "questions"]) == 0
    assert main(["--data", str(tmp_path), "materials", "m1", "diagram-png",
                 "--out", str(tmp_path / "m.png")]) == 0
    assert (tmp_path / "m.png").is_file()
