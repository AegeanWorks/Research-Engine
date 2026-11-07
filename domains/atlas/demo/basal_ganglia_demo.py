"""End-to-end P0 demo: import -> figure -> Muse -> SAM -> overlay -> recall.

Live model calls require MODEL_API_KEY/META_API_KEY. Without a key the script
runs in fixture mode and NEVER claims live results (honest labelling).

  python demo/basal_ganglia_demo.py --fixture-only
  python demo/basal_ganglia_demo.py --image path/to/figure.png --note "caption..."
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from domains.atlas.config import AtlasConfig
from domains.atlas.schema import VisualAnalysis
from domains.atlas.store import AtlasStore
from domains.atlas import ingestion as ing, learning as learn
from domains.atlas.demo.basal_ganglia_fixture import FIXTURE_ANALYSIS


def run_fixture(data_dir: str) -> dict:
    import copy
    store = AtlasStore(data_dir)
    analysis = VisualAnalysis.from_dict(FIXTURE_ANALYSIS)
    assert not analysis.validate(), analysis.validate()
    store.save_analysis("basal-ganglia-demo", analysis.to_dict())
    # Keep the workspace demo button in sync: refresh the static sample JSON
    # (fixture payload + display image) next to the bundled SVG schematic.
    try:
        static_json = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                   "static", "basal_ganglia_sample.json")
        if os.path.isdir(os.path.dirname(static_json)):
            payload = copy.deepcopy(analysis.to_dict())
            payload["_demo_image"] = "/static/basal_ganglia_demo.svg"
            with open(static_json, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2)
    except OSError:  # hygiene: allow demo refresh is best-effort when static dir is read-only
        pass
    challenge = learn.spatial_recall_challenge(analysis.to_dict(), seed=7)
    assert challenge["target_id"] in {e.id for e in analysis.entities}
    steps = [
        "1. import: fixture schematic (no PDF required in fixture mode)",
        "2. figure: manual crop coordinates preserved with provenance",
        "3. Muse: FIXTURE (set MODEL_API_KEY for a live call via /api/analyze)",
        "4. SAM: FIXTURE bbox-fallback (set MODEL_API_KEY for live sam-3.1 masks)",
        "5. overlay: entities render on the original figure; graph shares the same model",
        f"6. inspect: striatum relationships = "
        f"{[ (r.source_id, r.rel_type, r.target_id) for r in analysis.relationships if 'striatum' in (r.source_id, r.target_id) ]}",
        "7. pathways: direct (striatum->gpi) and indirect (striatum->gpe->stn->gpi) present",
        f"8. hide labels (spatial recall): '{challenge['prompt']}' target={challenge['target_id']}",
        "9. spatial recall graded against the same analysis model (no flashcard engine)",
        "10. evidence: per-entity source_evidence preserved; corrections stored separately",
    ]
    return {"mode": "fixture", "steps": steps, "analysis": analysis.to_dict()}


def run_live(image: str, note: str, data_dir: str, use_wonder: bool) -> dict:
    from domains.atlas.muse_provider import MuseProvider
    from domains.atlas.sam_provider import SamProvider

    config = AtlasConfig.from_env()
    if not config.has_api_key:
        raise SystemExit("MODEL_API_KEY/META_API_KEY is required for live mode.")
    store = AtlasStore(data_dir)
    doc = ing.import_document(image, data_dir)
    crop = ing.select_figure(image, (0.05, 0.05, 0.95, 0.95), data_dir,
                             document_ref=doc["document_ref"])
    analysis = MuseProvider(config, use_wonder=use_wonder).analyze_figure(
        crop.image_path, note, document_ref=doc["document_ref"],
        figure_id="basal-ganglia-live")
    store.save_analysis("basal-ganglia-live", analysis.to_dict())
    segmented = []
    for e in analysis.entities[:4]:
        seg = SamProvider(config).segment(
            crop.image_path, e.name, e.id, e.bbox)
        segmented.append({"entity": e.id, "kind": seg.kind})
    return {"mode": "live", "document": doc, "figure": crop.to_dict(),
            "analysis": analysis.to_dict(), "segmentation": segmented,
            "note": "live Meta Muse (+ SAM 3.1) results"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixture-only", action="store_true")
    ap.add_argument("--image", default="")
    ap.add_argument("--note", default="")
    ap.add_argument("--wonder", action="store_true")
    ap.add_argument("--data", default="data")
    args = ap.parse_args(argv)
    if args.fixture_only or not args.image:
        result = run_fixture(args.data)
    else:
        result = run_live(args.image, args.note, args.data, args.wonder)
    print(json.dumps({k: v for k, v in result.items() if k != "analysis"}, indent=2))
    print(f"entities={len(result['analysis']['entities'])} "
          f"relationships={len(result['analysis']['relationships'])} mode={result['mode']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
