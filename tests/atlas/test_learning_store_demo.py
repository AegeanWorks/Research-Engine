import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from domains.atlas import learning as learn
from domains.atlas.store import AtlasStore
from domains.atlas.schema import VisualAnalysis
from domains.atlas.demo.basal_ganglia_fixture import FIXTURE_ANALYSIS


def test_learning_modes_deterministic():
    a = VisualAnalysis.from_dict(FIXTURE_ANALYSIS).to_dict()
    c1 = learn.spatial_recall_challenge(a, seed=7)
    c2 = learn.spatial_recall_challenge(a, seed=7)
    assert c1 == c2
    assert learn.grade(c1, c1["answer_id"])["correct"]
    assert not learn.grade(c1, "nope")["correct"]
    pt = learn.pathway_tracing_challenge(a, seed=1)
    assert pt["chain"][0] in {e["id"] for e in a["entities"]}
    assert learn.grade(pt, pt["chain"])["correct"]
    rr = learn.relationship_recall_challenge(a, seed=2)
    assert learn.grade(rr, rr["answer_rel_type"])["correct"]
    vi = learn.visual_identification_challenge(a, seed=3)
    assert learn.grade(vi, vi["answer_id"])["correct"]


def test_deck_dedupes_merged_frames():
    from domains.atlas import flashcards as fc
    from domains.atlas.app import _merge_frame_analyses
    base = VisualAnalysis.from_dict(FIXTURE_ANALYSIS)
    merged = _merge_frame_analyses([base, base], "d", "vid").to_dict()
    full = fc.build_deck(merged, dedupe=False)
    slim = fc.build_deck(merged)
    assert slim["deduped"] == len(full["cards"]) - len(slim["cards"]) > 0
    fronts = [(c["kind"], c["front"]["text"], c["back"]["text"]) for c in slim["cards"]]
    assert len(set(fronts)) == len(fronts)


def test_spatial_recall_prefers_located_entities():
    from domains.atlas import learning as learn
    analysis = {"entities": [
        {"id": "ghost", "name": "Ghost", "category": "other", "bbox": None},
        {"id": "seen", "name": "Seen", "category": "component",
         "bbox": {"x_min": 0.1, "y_min": 0.1, "x_max": 0.5, "y_max": 0.5}}],
        "relationships": []}
    for seed in range(10):
        c = learn.spatial_recall_challenge(analysis, seed=seed)
        assert c["target_id"] == "seen"
        assert c["highlight_bbox"] is not None


def test_store_keeps_corrections_separate(tmp_path):
    store = AtlasStore(str(tmp_path))
    store.save_analysis("fig", {"entities": []})
    assert store.load_analysis("fig") == {"entities": []}
    store.add_correction({"entity_id": "striatum", "field": "name", "value": "Striatum (D1/D2)"})
    assert store.load_corrections()[0]["entity_id"] == "striatum"
    assert store.load_analysis("fig") == {"entities": []}  # model output untouched


def test_end_to_end_demo_fixture(tmp_path):
    from domains.atlas.demo.basal_ganglia_demo import run_fixture
    result = run_fixture(str(tmp_path))
    assert result["mode"] == "fixture"
    assert len(result["analysis"]["entities"]) >= 7
    assert len(result["analysis"]["relationships"]) >= 6
    assert len(result["steps"]) == 10
