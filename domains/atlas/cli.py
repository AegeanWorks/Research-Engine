"""Atlas headless CLI — AI agents and scripts drive Atlas without a browser.

  python -m atlas.cli create figure.png --note "caption..."   # one drop -> one model
  python -m atlas.cli models                                  # see every model
  python -m atlas.cli show <figure-id>                        # read one model
  python -m atlas.cli learn <figure-id> spatial-recall        # practice headlessly
  python -m atlas.cli contract                                # machine contract

Live creation needs MODEL_API_KEY/META_API_KEY; reading models never does.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from domains.atlas.app import api_contract, auto_create_model, list_models  # noqa: E402
from domains.atlas.config import AtlasConfig  # noqa: E402
from domains.atlas import learning as learn  # noqa: E402
from domains.atlas.store import AtlasStore  # noqa: E402


def cmd_create(args) -> int:
    store = AtlasStore(args.data)
    config = AtlasConfig.from_env(data_dir=args.data)
    try:
        result = auto_create_model(store, config, args.file, args.note,
                                   args.figure_id, args.wonder)
    except Exception as exc:
        from domains.atlas.app import honest_error
        print(json.dumps({"ok": False, **honest_error(exc)}))
        return 1
    if result.get("model_created"):
        a = result["analysis"]
        print(json.dumps({"ok": True, "figure_id": result["figure_id"],
                          "entities": len(a["entities"]),
                          "relationships": len(a["relationships"]),
                          "figure_url": result.get("figure_url", "")}))
    else:
        print(json.dumps({"ok": True, "model_created": False,
                          "document": result["document"]}))
    return 0


def cmd_models(args) -> int:
    print(json.dumps({"models": list_models(AtlasStore(args.data))}, indent=2))
    return 0


def cmd_show(args) -> int:
    data = AtlasStore(args.data).load_analysis(args.figure_id)
    if data is None:
        print(json.dumps({"ok": False, "error": f"unknown figure_id {args.figure_id!r}"}))
        return 1
    print(json.dumps(data, indent=2))
    return 0


def cmd_learn(args) -> int:
    data = AtlasStore(args.data).load_analysis(args.figure_id)
    if data is None:
        print(json.dumps({"ok": False, "error": f"unknown figure_id {args.figure_id!r}"}))
        return 1
    fn = {"spatial-recall": learn.spatial_recall_challenge,
          "pathway-tracing": learn.pathway_tracing_challenge,
          "visual-identification": learn.visual_identification_challenge,
          "relationship-recall": learn.relationship_recall_challenge}[args.mode]
    try:
        challenge = fn(data, args.seed)
    except ValueError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 1
    if args.answer is None:
        print(json.dumps(challenge, indent=2))
        return 0
    answer = args.answer
    if challenge.get("mode") == "pathway-tracing":
        answer = [a.strip() for a in answer.split(",")]
    print(json.dumps({"challenge": challenge.get("prompt"),
                      "grade": learn.grade(challenge, answer)}, indent=2))
    return 0


def cmd_deck(args) -> int:
    from domains.atlas import flashcards as fc
    data = AtlasStore(args.data).load_analysis(args.figure_id)
    if data is None:
        print(json.dumps({"ok": False, "error": f"unknown figure_id {args.figure_id!r}"}))
        return 1
    deck = fc.build_deck(data)
    if args.anki:
        with open(args.anki, "w", encoding="utf-8") as fh:
            fh.write(fc.to_anki_tsv(deck))
        print(json.dumps({"ok": True, "cards": len(deck["cards"]), "anki": args.anki}))
    else:
        print(json.dumps(deck, indent=2))
    return 0


def cmd_obj(args) -> int:
    from domains.atlas import models3d as m3d
    data = AtlasStore(args.data).load_analysis(args.figure_id)
    if data is None:
        print(json.dumps({"ok": False, "error": f"unknown figure_id {args.figure_id!r}"}))
        return 1
    try:
        text = m3d.export_obj(data)
    except ValueError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 1
    out = args.out or f"{args.figure_id}.obj"
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(text)
    print(json.dumps({"ok": True, "obj": out}))
    return 0


def cmd_summary(args) -> int:
    from . import summaries as sm
    data = AtlasStore(args.data).load_analysis(args.figure_id)
    if data is None:
        print(json.dumps({"ok": False, "error": f"unknown figure_id {args.figure_id!r}"}))
        return 1
    print(json.dumps(sm.extractive_summary(data), indent=2))
    return 0


def cmd_agent(args) -> int:
    """One command proving an AI can drive Atlas: fixture model, summary,
    deck, learn round, OBJ — all offline, all printed as JSON."""
    import tempfile
    from .selftest import run
    data_dir = args.data if args.data != "data" else tempfile.mkdtemp(prefix="atlas-agent-")
    report = run(data_dir)
    print(json.dumps(report, indent=2))
    return 0 if report["failed"] == 0 else 1


def cmd_materials(args) -> int:
    from . import materials as mat
    data = AtlasStore(args.data).load_analysis(args.figure_id)
    if data is None:
        print(json.dumps({"ok": False, "error": f"unknown figure_id {args.figure_id!r}"}))
        return 1
    kind = args.kind
    if kind == "tour":
        print(json.dumps(mat.tour_3d(data), indent=2))
    elif kind == "questions":
        print(json.dumps(mat.question_bank(data), indent=2))
    elif kind == "podcast-json":
        print(json.dumps(mat.podcast_script(data), indent=2))
    else:
        payload = {"diagram-svg": (mat.diagram_svg(data).encode(), ".svg"),
                   "diagram-png": (mat.diagram_png(data), ".png"),
                   "podcast-md": (mat.podcast_markdown(mat.podcast_script(data)).encode(), ".md"),
                   }[kind]
        out = args.out or f"{args.figure_id}-{kind}{payload[1]}"
        with open(out, "wb") as fh:
            fh.write(payload[0])
        print(json.dumps({"ok": True, "file": out}))
    return 0


def cmd_batch(args) -> int:
    from . import ingestion as ing
    from . import sources as src
    store = AtlasStore(args.data)
    rows = []
    try:
        names = sorted(os.listdir(args.folder))
    except OSError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 1
    import tempfile
    for name in names:
        path = os.path.join(args.folder, name)
        if not os.path.isfile(path):
            continue
        row = {"file": name}
        try:
            doc = ing.import_document(path, store.data_dir)
            row["document_ref"] = doc["document_ref"]
            bundle = src.ingest_any(path)
            row["kind"] = bundle["kind"]
            row["chars"] = len(bundle.get("text", ""))
            if bundle["kind"] == "video":
                try:
                    from . import quality as qa
                    frames = src.video_frames(
                        path, tempfile.mkdtemp(prefix="atlas-batch-"), max_frames=4)
                    fq = qa.frames_quality(frames)
                    row["frames"] = len(frames)
                    row["frames_kept"] = len(fq["kept"])
                    row["frames_issues"] = fq["issues"]
                except Exception as exc:
                    row["frames_error"] = f"{type(exc).__name__}: {exc}"
        except Exception as exc:
            row["error"] = f"{type(exc).__name__}: {exc}"
        rows.append(row)
    ok = sum(1 for r in rows if "error" not in r)
    print(json.dumps({"ok": True, "files": len(rows), "imported": ok, "rows": rows},
                     indent=2))
    return 0


def cmd_quality(args) -> int:
    import tempfile
    from . import flashcards as fc
    from . import materials as mat
    from . import models3d as m3d
    from . import quality as qa
    from . import summaries as sm
    data = AtlasStore(args.data).load_analysis(args.figure_id)
    if data is None:
        print(json.dumps({"ok": False, "error": f"unknown figure_id {args.figure_id!r}"}))
        return 1
    artifacts = {"deck": fc.build_deck(data), "podcast": mat.podcast_script(data),
                 "diagram_svg": mat.diagram_svg(data), "tour": mat.tour_3d(data),
                 "questions": mat.question_bank(data), "summary": sm.extractive_summary(data),
                 "include_learn": True}
    try:
        artifacts["obj"] = m3d.export_obj(data)
    except ValueError:
        artifacts.pop("obj", None)  # OBJ is optional: skip it when geometry is degenerate
    if args.video:
        vdir = tempfile.mkdtemp(prefix="atlas-vid-")
        artifacts["video_mp4"] = mat.video_slideshow(data, vdir)["mp4"]
    print(json.dumps(qa.quality_report(data, artifacts), indent=2))
    return 0


def cmd_video(args) -> int:
    import tempfile
    from . import materials as mat
    data = AtlasStore(args.data).load_analysis(args.figure_id)
    if data is None:
        print(json.dumps({"ok": False, "error": f"unknown figure_id {args.figure_id!r}"}))
        return 1
    info = mat.video_slideshow(data, args.out and os.path.dirname(os.path.abspath(args.out))
                               or tempfile.mkdtemp(prefix="atlas-vid-"))
    if args.out and info["mp4"] != args.out:
        import shutil
        shutil.copyfile(info["mp4"], args.out)
        info["mp4"] = args.out
    print(json.dumps({"ok": True, **info}))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Atlas headless CLI for AI agents")
    ap.add_argument("--data", default="data")
    sub = ap.add_subparsers(dest="command", required=True)
    c = sub.add_parser("create", help="one file -> one model")
    c.add_argument("file")
    c.add_argument("--note", default="")
    c.add_argument("--figure-id", default="")
    c.add_argument("--wonder", action="store_true")
    c.set_defaults(func=cmd_create)
    m = sub.add_parser("models", help="list every model")
    m.set_defaults(func=cmd_models)
    s = sub.add_parser("show", help="read one model")
    s.add_argument("figure_id")
    s.set_defaults(func=cmd_show)
    lrn = sub.add_parser("learn", help="challenge (and optionally grade)")
    lrn.add_argument("figure_id")
    lrn.add_argument("mode", choices=["spatial-recall", "pathway-tracing",
                                      "visual-identification", "relationship-recall"])
    lrn.add_argument("--seed", type=int, default=0)
    lrn.add_argument("--answer", default=None)
    lrn.set_defaults(func=cmd_learn)
    ct = sub.add_parser("contract", help="print the machine contract")
    ct.set_defaults(func=lambda a: (print(json.dumps(api_contract(), indent=2)), 0)[1])
    dk = sub.add_parser("deck", help="build flashcards (optionally export Anki TSV)")
    dk.add_argument("figure_id")
    dk.add_argument("--anki", default="")
    dk.set_defaults(func=cmd_deck)
    ob = sub.add_parser("obj", help="export the model as Wavefront OBJ 3D")
    ob.add_argument("figure_id")
    ob.add_argument("--out", default="")
    ob.set_defaults(func=cmd_obj)
    smry = sub.add_parser("summary", help="print the auto study brief")
    smry.add_argument("figure_id")
    smry.set_defaults(func=cmd_summary)
    ql = sub.add_parser("quality", help="score every generated artifact")
    ql.add_argument("figure_id")
    ql.add_argument("--video", action="store_true")
    ql.set_defaults(func=cmd_quality)
    vd = sub.add_parser("video", help="render the study MP4")
    vd.add_argument("figure_id")
    vd.add_argument("--out", default="")
    vd.set_defaults(func=cmd_video)
    mat = sub.add_parser("materials", help="study pack: diagram/tour/podcast/questions")
    mat.add_argument("figure_id")
    mat.add_argument("kind", choices=["diagram-svg", "diagram-png", "tour",
                                      "podcast-md", "podcast-json", "questions"])
    mat.add_argument("--out", default="")
    mat.set_defaults(func=cmd_materials)
    ag = sub.add_parser("agent", help="prove AI autonomy: fixture model end to end")
    ag.add_argument("--figure-id", default="agent-demo")
    ag.set_defaults(func=cmd_agent)
    bt = sub.add_parser("batch", help="import a folder of files, offline report")
    bt.add_argument("folder")
    bt.set_defaults(func=cmd_batch)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
