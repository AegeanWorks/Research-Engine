"""Atlas offline self-test: one command proves the app works, no key, no browser.

  python -m atlas.selftest [--data DIR]

Prints a JSON report {"checks": [{name, ok, detail}], "passed", "failed"} and
exits 0 when everything passes. AI agents and CI run this first: if it passes,
the app is usable; if not, the failing check names the broken layer.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class _FakeMuse:
    def analyze_figure(self, image_path, note="", document_ref="", source_page=0, figure_id="f"):
        from domains.atlas.schema import BoundingBox, VisualAnalysis, VisualEntity, VisualRelationship
        mk = lambda i, n: VisualEntity(
            id=i, name=n, category="component", source_evidence="selftest",
            bbox=BoundingBox(0.05, 0.05, 0.45, 0.45) if i == "a"
            else BoundingBox(0.55, 0.55, 0.95, 0.95))
        return VisualAnalysis(
            document_ref=document_ref, source_page=source_page, figure_id=figure_id,
            entities=[mk("a", "Alpha"), mk("b", "Beta")],
            relationships=[VisualRelationship(source_id="a", target_id="b",
                                              rel_type="activates")])

    def analyze_text(self, text, note="", document_ref="", figure_id=""):
        return self.analyze_figure("x", note, document_ref, 0, figure_id or "t")


def run(data_dir: str) -> dict:
    from domains.atlas import flashcards as fc
    from domains.atlas import learning as learn
    from domains.atlas import models3d as m3d
    from domains.atlas import sources as src
    from domains.atlas import summaries as sm
    from domains.atlas.app import api_contract, auto_create_model, list_models
    from domains.atlas.config import AtlasConfig
    from domains.atlas.schema import VisualAnalysis
    from domains.atlas.store import AtlasStore

    checks: list[dict] = []

    def check(name, fn):
        try:
            detail = fn() or "ok"
            checks.append({"name": name, "ok": True, "detail": str(detail)})
        except Exception as exc:
            checks.append({"name": name, "ok": False,
                           "detail": f"{type(exc).__name__}: {exc}"})

    store = AtlasStore(data_dir)
    config = AtlasConfig(api_key="", data_dir=data_dir)
    state: dict = {}

    def t_text_backend():
        probe = os.path.join(data_dir, "probe.txt")
        with open(probe, "w", encoding="utf-8") as fh:
            fh.write("Thalamus relays processed signals back to the cortex. " * 10)
        got = src.ingest_any(probe)
        assert got["kind"] == "text" and len(got["text"]) > 100
        return f"{len(got['text'])} chars via text backend"

    def t_ingest_and_crop():
        from PIL import Image
        img = os.path.join(data_dir, "selftest.png")
        Image.new("RGB", (80, 60), (1, 2, 3)).save(img)
        from domains.atlas import ingestion as ing
        doc = ing.import_document(img, data_dir)
        crop = ing.select_figure(img, (0, 0, 0.5, 0.5), data_dir,
                                 document_ref=doc["document_ref"])
        state["image"] = crop.image_path
        assert crop.image_width == 40 and crop.image_height == 30
        return "crop 40x30"

    def t_auto_create_image():
        result = auto_create_model(store, config, state["image"],
                                   figure_id="selftest-fig",
                                   muse_provider=_FakeMuse())
        assert result["model_created"] is True
        state["fid"] = result["figure_id"]
        return f"figure_id={state['fid']}"

    def t_models_visible():
        models = list_models(store)
        assert any(m["figure_id"] == state["fid"] for m in models)
        return f"{len(models)} model(s) listed"

    def t_learn_and_grade():
        data = store.load_analysis(state["fid"])
        challenge = learn.spatial_recall_challenge(data, seed=1)
        assert learn.grade(challenge, challenge["answer_id"])["correct"]
        assert not learn.grade(challenge, "wrong")["correct"]
        return "spatial-recall grades correctly"

    def t_flashcards_and_summary():
        data = store.load_analysis(state["fid"])
        deck = fc.build_deck(data)
        assert deck["cards"] and fc.to_anki_tsv(deck).count("\n") == len(deck["cards"])
        brief = sm.extractive_summary(data)
        assert brief["stats"]["entities"] == 2 and brief["pathways"]
        return f"{len(deck['cards'])} cards, {len(brief['pathways'])} pathway(s)"

    def t_3d_export():
        data = store.load_analysis(state["fid"])
        view = m3d.iso_view(data)
        obj = m3d.export_obj({**data, "figure_id": state["fid"]})
        assert view["polygons"] and obj.count("\ng ") == 2
        return "iso + OBJ ok"

    def t_contract():
        contract = api_contract()
        assert contract["contract_version"].startswith("domains.atlas.api/")
        assert "POST /api/auto-create" in str(contract["endpoints"])
        return contract["contract_version"]

    def t_schema_rejects_bad():
        try:
            VisualAnalysis.from_dict({"entities": [{"id": "x"}],
                                      "relationships": [{"source_id": "x", "target_id": "ghost",
                                                         "rel_type": "activates", "confidence": 1}]})
        except (ValueError, KeyError):
            return "dangling refs rejected"
        raise AssertionError("invalid analysis accepted")

    for name, fn in [("text-backend", t_text_backend),
                     ("ingest-and-crop", t_ingest_and_crop),
                     ("auto-create", t_auto_create_image),
                     ("models-visible", t_models_visible),
                     ("learn-and-grade", t_learn_and_grade),
                     ("flashcards-and-summary", t_flashcards_and_summary),
                     ("3d-export", t_3d_export),
                     ("contract", t_contract),
                     ("schema-guards", t_schema_rejects_bad)]:
        check(name, fn)
    passed = sum(1 for c in checks if c["ok"])
    return {"checks": checks, "passed": passed, "failed": len(checks) - passed}


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Atlas offline self-test")
    ap.add_argument("--data", default="")
    args = ap.parse_args(argv)
    data_dir = args.data or tempfile.mkdtemp(prefix="atlas-selftest-")
    report = run(data_dir)
    print(json.dumps(report, indent=2))
    return 0 if report["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
