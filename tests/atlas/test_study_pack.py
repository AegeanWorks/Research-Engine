"""Auto summaries + study pack (0.8.0 slice)."""
import json
import threading
import urllib.request
from http.server import HTTPServer

from domains.atlas import summaries as sm
from domains.atlas.schema import VisualAnalysis
from domains.atlas.demo.basal_ganglia_fixture import FIXTURE_ANALYSIS


def _analysis():
    return VisualAnalysis.from_dict(FIXTURE_ANALYSIS).to_dict()


def test_extractive_summary_covers_model():
    brief = sm.extractive_summary(_analysis())
    assert brief["stats"]["entities"] == 7
    assert brief["stats"]["located"] == 7
    assert any("striatum" in b.lower() for b in brief["entities"])
    assert any("evidence" in b.lower() or "fixture" in b.lower() for b in brief["entities"])
    # direct + indirect pathways surface as chains
    joined = " | ".join(brief["pathways"])
    assert "Striatum" in joined and "GPe" in joined


def test_pathway_chains_terminate_on_cycles():
    chains = sm.pathway_chains(_analysis())
    assert chains
    for chain in chains:
        assert len(chain) == len(set(chain))  # no revisits despite cortex cycle


def test_polish_summary_roundtrip():
    from domains.atlas.config import AtlasConfig
    from domains.atlas.muse_provider import MuseProvider

    def fake_transport(payload):
        assert "Rewrite the study brief" in payload["messages"][0]["content"]
        return {"choices": [{"message": {"content": "Polished prose."}}]}

    cfg = AtlasConfig(api_key="k", data_dir=".")
    assert MuseProvider(cfg, transport=fake_transport).polish_summary(
        {"overview": "o", "entities": ["e"], "pathways": []}) == "Polished prose."


def test_summary_arrow_format_and_hub_cap():
    from domains.atlas import summaries as sm
    ents = [{"id": f"e{i}", "name": f"N{i}", "category": "other",
             "description": "", "bbox": None, "source_evidence": "",
             "confidence": 1.0, "uncertainty": "", "mask_ref": "",
             "model_inferred": False} for i in range(8)]
    rels = [{"source_id": "e0", "target_id": f"e{i}", "rel_type": "activates",
             "explanation": "", "supporting_evidence": "", "confidence": 1.0,
             "provenance": "source", "model_inferred": False} for i in range(1, 8)]
    brief = sm.extractive_summary({"figure_id": "h", "entities": ents, "relationships": rels})
    hub = next(b for b in brief["entities"] if b.startswith("N0 "))
    assert "—activates→" in hub and "+2 more relations" in hub
    assert "receives receives-input-from" not in " ".join(brief["entities"])


def test_podcast_trims_big_models_with_note():
    from domains.atlas import materials as mat
    ents = [{"id": f"e{i}", "name": f"N{i}", "category": "other",
             "bbox": None, "confidence": 1.0} for i in range(40)]
    script = mat.podcast_script({"figure_id": "big", "entities": ents, "relationships": []})
    assert len(script["segments"]) <= 24 + 3
    assert "top of 40" in script["segments"][0]["text"]


def test_podcast_density_survives_many_explained_relations():
    from domains.atlas import materials as mat
    from domains.atlas import quality as qa
    ents = [{"id": "hub", "name": "Hub", "category": "other",
             "description": "Central structure.", "source_evidence": "panel one",
             "bbox": None, "confidence": 1.0}]
    ents += [{"id": f"t{i}", "name": f"Target{i}", "category": "other",
              "description": f"Target structure {i}.", "source_evidence": "panel two",
              "bbox": None, "confidence": 1.0} for i in range(6)]
    rels = [{"source_id": "hub", "target_id": f"t{i}", "rel_type": "activates",
             "explanation": "The hub sends a strong activating signal onward.",
             "supporting_evidence": "panel one", "confidence": 1.0,
             "provenance": "source", "model_inferred": False} for i in range(6)]
    analysis = {"figure_id": "dense", "entities": ents, "relationships": rels}
    report = qa.podcast_quality(mat.podcast_script(analysis), analysis)
    assert report["score"] == 100, report["issues"]


def test_question_bank_covers_isolated_undescribed_entities():
    from domains.atlas import materials as mat
    from domains.atlas import quality as qa
    analysis = {"figure_id": "iso", "entities": [
        {"id": "x", "name": "Xenon", "category": "other",
         "description": "", "source_evidence": "", "bbox": None, "confidence": 0.5},
        {"id": "y", "name": "Yara", "category": "person",
         "description": "", "source_evidence": "Sailed with the fleet.",
         "bbox": None, "confidence": 0.5}], "relationships": []}
    bank = mat.question_bank(analysis)
    report = qa.questions_quality(bank, analysis)
    assert report["score"] == 100, report["issues"]
    assert all(q["answer"] for q in bank["questions"])


def test_pathways_capped_with_total():
    from domains.atlas import summaries as sm
    ents = [{"id": "root", "name": "R", "category": "other",
             "bbox": None, "confidence": 1.0}]
    rels = [{"source_id": "root", "target_id": f"n{i}", "rel_type": "activates",
             "explanation": "", "supporting_evidence": "", "confidence": 1.0,
             "provenance": "source", "model_inferred": False} for i in range(30)]
    ents += [{"id": f"n{i}", "name": f"N{i}", "category": "other",
              "bbox": None, "confidence": 1.0} for i in range(30)]
    brief = sm.extractive_summary({"figure_id": "x", "entities": ents, "relationships": rels})
    assert len(brief["pathways"]) <= 12 and brief["pathways_total"] >= len(brief["pathways"])
    assert brief["pathways_truncated"] is True


def test_podcast_coverage_respects_trim_scope():
    from domains.atlas import materials as mat
    from domains.atlas import quality as qa
    ents = [{"id": f"e{i}", "name": f"Person{i}", "category": "person",
             "bbox": None, "confidence": 1.0} for i in range(40)]
    script = mat.podcast_script({"figure_id": "big", "entities": ents, "relationships": []})
    assert script["trimmed_from"] == 40 and len(script["covered_ids"]) == 24
    report = qa.podcast_quality(script, {"figure_id": "big", "entities": ents, "relationships": []})
    assert report["score"] == 100, report["issues"]


def test_selftest_passes_offline(tmp_path):
    from domains.atlas.selftest import run
    report = run(str(tmp_path / "selftest-data"))
    assert report["failed"] == 0, report
    assert report["passed"] >= 9


def test_state_and_text_digest(tmp_path):
    import urllib.request
    from http.server import HTTPServer
    from domains.atlas import app as atlas_app
    from domains.atlas.config import AtlasConfig
    from domains.atlas.store import AtlasStore

    AtlasStore(str(tmp_path)).save_analysis("st", {**_analysis(), "figure_id": "st"})
    atlas_app.Handler.store = None
    atlas_app.Handler.config = AtlasConfig.from_env(data_dir=str(tmp_path), api_key="")
    server = HTTPServer(("127.0.0.1", 0), atlas_app.Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with urllib.request.urlopen(  # noqa: S310
                f"http://127.0.0.1:{port}/api/state?figure_id=st", timeout=10) as r:
            state = json.load(r)
        assert state["deck_size"] > 7 and state["stats"]["entities"] == 7
        assert "Striatum" in state["text_digest"] and state["urls"]["obj"].endswith("format=obj")
        with urllib.request.urlopen(  # noqa: S310
                f"http://127.0.0.1:{port}/api/models?format=text", timeout=10) as r:
            digest = r.read().decode()
        assert "MODEL st" in digest and "PATHWAYS" in digest
    finally:
        server.shutdown()
        thread.join(timeout=5)
        atlas_app.Handler.store = None


def test_summary_endpoint_offline_and_keyless(tmp_path):
    from domains.atlas import app as atlas_app
    from domains.atlas.config import AtlasConfig
    from domains.atlas.store import AtlasStore

    AtlasStore(str(tmp_path)).save_analysis("s1", _analysis())
    atlas_app.Handler.store = None
    # Force keyless: the host env may carry MODEL_API_KEY, which would turn
    # /api/summary into a live Muse call with retries and exceed the test's
    # 10s client timeout. This test pins the offline/keyless path.
    atlas_app.Handler.config = AtlasConfig.from_env(data_dir=str(tmp_path), api_key="")
    server = HTTPServer(("127.0.0.1", 0), atlas_app.Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/summary",
            data=json.dumps({"figure_id": "s1"}).encode(),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as r:  # noqa: S310
            body = json.load(r)
        assert body["extractive"]["stats"]["entities"] == 7
        # no key in this environment: honest extractive-only flag
        assert body["polished"] is None or body["polished"].startswith("[polish unavailable")
        bad = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/summary",
            data=json.dumps({"figure_id": "missing"}).encode(),
            headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(bad, timeout=10):  # noqa: S310
                raise AssertionError("expected 400")
        except urllib.error.HTTPError as e:
            assert e.code == 400
    finally:
        server.shutdown()
        thread.join(timeout=5)
        atlas_app.Handler.store = None
