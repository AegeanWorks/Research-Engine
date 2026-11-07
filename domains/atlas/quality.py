"""Automatic quality analysis for every generated artifact (0-100 each).

Every analyzer returns {"score", "checks": [{name, ok, detail}], "issues": []}.
Scores are heuristic but strict: missing coverage, broken references, empty
content, and invalid files all cost points openly. quality_report() rolls the
requested artifacts into one verdict so an AI (or person) can see at a glance
what is study-ready and what needs work.
"""
from __future__ import annotations

import os
import re

from PIL import Image, ImageFilter, ImageStat


def _result(score: int, checks: list, issues: list) -> dict:
    return {"score": max(0, min(100, score)), "checks": checks, "issues": issues}


def _check(name: str, ok: bool, detail: str = "") -> dict:
    return {"name": name, "ok": bool(ok), "detail": detail}


def flashcard_quality(deck: dict, analysis: dict) -> dict:
    """Coverage, clarity, grounding, and duplication of a flashcard deck."""
    cards = deck.get("cards", [])
    entities = list(analysis.get("entities", []))
    relationships = list(analysis.get("relationships", []))
    checks, issues = [], []
    covered = {c.get("entity_id") for c in cards}
    missing = [e["id"] for e in entities if e["id"] not in covered]
    checks.append(_check("entity-coverage", not missing,
                         f"{len(covered)}/{len(entities)} entities have cards"))
    if missing:
        issues.append(f"no cards for: {', '.join(missing[:5])}")
    rel_kinds = {c.get("kind") for c in cards}
    checks.append(_check("relation-cards", "relation" in rel_kinds or not relationships,
                         "relation recall present" if "relation" in rel_kinds else "no relationships to quiz"))
    long_fronts = [c["id"] for c in cards if len(c.get("front", {}).get("text", "")) > 280]
    checks.append(_check("front-clarity", not long_fronts,
                         "all fronts ≤280 chars" if not long_fronts else f"verbose: {long_fronts[:3]}"))
    if long_fronts:
        issues.append(f"{len(long_fronts)} fronts exceed 280 chars")
    no_back = [c["id"] for c in cards if not c.get("back", {}).get("text")]
    checks.append(_check("answers-present", not no_back,
                         "every card has an answer" if not no_back else f"missing: {no_back[:3]}"))
    if no_back:
        issues.append(f"{len(no_back)} cards lack answers")
    grounded = sum(1 for c in cards if c.get("back", {}).get("evidence"))
    checks.append(_check("evidence-grounding", grounded == len(cards) and cards != [],
                         f"{grounded}/{len(cards)} backs cite evidence"))
    if cards and grounded < len(cards):
        issues.append(f"{len(cards) - grounded} backs lack source evidence")
    seen, dupes = set(), 0
    for c in cards:
        key = (c.get("front", {}).get("text", ""), c.get("back", {}).get("text", ""))
        if key in seen:
            dupes += 1
        seen.add(key)
    checks.append(_check("no-duplicates", dupes == 0, "unique Q/A pairs" if not dupes else f"{dupes} duplicates"))
    if dupes:
        issues.append(f"{dupes} duplicate cards")
    # A mega-model deck (hundreds of cards) is complete but unreviewable in
    # one sitting — same flag-not-block philosophy as the tour duration cap.
    bounded = len(cards) <= 300
    checks.append(_check("deck-size-sane", bounded,
                         f"{len(cards)} cards" if bounded
                         else f"{len(cards)} cards exceed a single review session"))
    if not bounded:
        issues.append(f"deck too large to review at once: {len(cards)} cards")
    score = 100 - 25 * sum(1 for c in checks if not c["ok"])
    return _result(score, checks, issues)


def infographic_quality(svg: str, analysis: dict) -> dict:
    """The study diagram: labels, overlap, legibility, arrow validity."""
    import xml.etree.ElementTree as ET
    checks, issues = [], []
    try:
        root = ET.fromstring(svg)
        checks.append(_check("well-formed-svg", True, f"root {root.tag.split('}')[-1]}"))
    except ET.ParseError as exc:
        return _result(0, [_check("well-formed-svg", False, str(exc)[:100])],
                       [f"SVG does not parse: {exc}"])
    texts = [t.text or "" for t in root.iter() if t.tag.endswith("text")]
    names = [e.get("name", e["id"]) for e in analysis.get("entities", [])]
    unlabeled = [n for n in names if not any(n in t or (len(n) > 22 and n[:21] in t) for t in texts)]
    checks.append(_check("all-entities-labeled", not unlabeled,
                         "every entity on the poster" if not unlabeled else f"missing: {unlabeled[:3]}"))
    if unlabeled:
        issues.append(f"unlabeled: {', '.join(unlabeled[:5])}")
    def _fnum(value, default=None):
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    rects, skipped = [], 0
    for r in root.iter():
        if not r.tag.endswith("rect"):
            continue
        geom = [_fnum(r.get(k, 0)) for k in ("x", "y", "width", "height")]
        if any(v is None for v in geom):
            skipped += 1
            continue
        rects.append(tuple(geom))
    if skipped:
        issues.append(f"{skipped} boxes have non-numeric geometry and were skipped")
    # A full-canvas backdrop is decoration, not a colliding box.
    canvas = max([w * h for _, _, w, h in rects] or [1])
    rects = [r for r in rects if r[2] * r[3] < 0.9 * canvas]
    overlaps = 0
    for i, a in enumerate(rects):
        for b in rects[i + 1:]:
            if (a[0] < b[0] + b[2] and b[0] < a[0] + a[2]
                    and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]):
                overlaps += 1
    checks.append(_check("no-box-overlap", overlaps == 0,
                         "clean layout" if not overlaps else f"{overlaps} overlapping box pairs"))
    if overlaps:
        issues.append(f"{overlaps} overlapping boxes hurt readability")
    small = [t for t in root.iter() if t.tag.endswith("text")
             and (sz := _fnum(t.get("font-size", "99") or 99)) is not None
             and sz < 10]
    checks.append(_check("legible-type", not small,
                         "all type ≥10px" if not small else f"{len(small)} tiny labels"))
    if small:
        issues.append(f"{len(small)} labels under 10px")
    arrows = sum(1 for l in root.iter() if l.tag.endswith("line"))
    expected = len(analysis.get("relationships", []))
    checks.append(_check("arrows-match-relationships", arrows == expected,
                         f"{arrows}/{expected} relationships drawn"))
    if arrows != expected:
        issues.append(f"drawn {arrows} arrows for {expected} relationships")
    score = 100 - 25 * sum(1 for c in checks if not c["ok"])
    return _result(score, checks, issues)


def podcast_quality(script: dict, analysis: dict) -> dict:
    """Coverage, duration sanity, structure, and density of the audio script."""
    segments = script.get("segments", [])
    text = " ".join(s.get("text", "") for s in segments)
    checks, issues = [], []
    covered_ids = script.get("covered_ids")
    if covered_ids is not None:
        scope = [e for e in analysis.get("entities", []) if e["id"] in set(covered_ids)]
        scope_note = f" (trimmed episode: {len(scope)} of {len(analysis.get('entities', []))} covered)"
    else:
        scope = list(analysis.get("entities", []))
        scope_note = ""
    names = [e.get("name", e["id"]) for e in scope]
    missing = [n for n in names if n not in text]
    checks.append(_check("entity-coverage", not missing,
                         f"script walks all {len(names)} structures{scope_note}"
                         if not missing else f"unmentioned: {missing[:3]}"))
    if missing:
        issues.append(f"script skips: {', '.join(missing[:5])}")
    minutes = float(script.get("estimated_minutes", 0) or 0)
    checks.append(_check("duration-sane", 1 <= minutes <= 30,
                         f"~{minutes} min spoken"))
    if not 1 <= minutes <= 30:
        issues.append(f"duration {minutes} min outside the 1-30 min study window")
    cues = [s.get("cue", "") for s in segments]
    checks.append(_check("has-cold-open", any("cold open" in c for c in cues), "hooks the listener"))
    checks.append(_check("has-recap", any("recap" in c for c in cues), "closes the loop"))
    if not any("recap" in c for c in cues):
        issues.append("no recap segment")
    words = text.split()
    avg = len(words) / max(1, len([s for s in text.split(".") if s.strip()]))
    checks.append(_check("spoken-density", avg <= 25, f"~{avg:.0f} words/sentence"))
    if avg > 25:
        issues.append(f"sentences average {avg:.0f} words — dense for audio")
    score = 100 - 20 * sum(1 for c in checks if not c["ok"])
    return _result(score, checks, issues)


def model3d_quality(obj_text: str, analysis: dict) -> dict:
    """OBJ validity: groups, vertex/face math, bounds, naming, NaNs."""
    lines = obj_text.splitlines()
    checks, issues = [], []
    groups = [l[2:].strip() for l in lines if l.startswith("g ")]
    located = [e["id"] for e in analysis.get("entities", []) if e.get("bbox")]
    sanitized = {"".join(c if c.isalnum() or c in "-_" else "_" for c in str(i)): i
                 for i in located}
    missing = [sanitized[g] for g in sanitized if g not in groups]
    checks.append(_check("every-located-entity-meshed", not missing,
                         f"{len(groups)} groups" if not missing else f"missing: {missing[:3]}"))
    if missing:
        issues.append(f"unmeshed: {', '.join(missing[:5])}")
    verts = [l for l in lines if l.startswith("v ")]
    faces = [l for l in lines if l.startswith("f ")]
    checks.append(_check("cuboid-math", len(verts) == 8 * len(groups) and len(faces) == 6 * len(groups),
                         f"{len(verts)}v/{len(faces)}f for {len(groups)} cuboids"))
    if not (len(verts) == 8 * len(groups) and len(faces) == 6 * len(groups)):
        issues.append("vertex/face counts break the 8v/6f cuboid invariant")
    bad, coords = [], []
    for l in verts:
        try:
            vals = [float(x) for x in l.split()[1:4]]
        except ValueError:
            bad.append(l)
            continue
        if any(v != v or v in (float("inf"), float("-inf")) for v in vals):
            bad.append(l)
            continue
        coords.extend(vals)
    checks.append(_check("finite-geometry", not bad, "no NaN/Inf" if not bad else f"{len(bad)} bad lines"))
    if bad:
        issues.append(f"{len(bad)} non-finite geometry lines")
    out = [c for c in coords if abs(c) > 1.5]
    checks.append(_check("unit-bounds", not out, "model fits the unit frame" if not out else f"{len(out)} runaway coords"))
    if out:
        issues.append(f"{len(out)} coordinates outside the unit frame")
    score = 100 - 25 * sum(1 for c in checks if not c["ok"])
    return _result(score, checks, issues)


def video_quality_mp4(path: str) -> dict:
    """Technical quality of a rendered study MP4 (container, size, duration)."""
    checks, issues = [], []
    if not os.path.isfile(path):
        return _result(0, [_check("file-exists", False, path)], ["video file missing"])
    size = os.path.getsize(path)
    checks.append(_check("file-exists", True, f"{size // 1024} KB"))
    with open(path, "rb") as fh:
        head = fh.read(64)
    checks.append(_check("mp4-container", b"ftyp" in head, "ISO BMFF brand found"
                         if b"ftyp" in head else "no ftyp brand"))
    if b"ftyp" not in head:
        issues.append("not a recognizable MP4 container")
    checks.append(_check("nontrivial-size", size > 50_000, "real content, not a stub"
                         if size > 50_000 else f"only {size} bytes"))
    if size <= 50_000:
        issues.append("file suspiciously small for a study video")
    duration = _mp4_duration(path)
    if duration is None:
        checks.append(_check("duration-known", False, "could not probe duration"))
        issues.append("duration unknown — verify playback manually")
    else:
        ok = 5 <= duration <= 600
        checks.append(_check("duration-sane", ok, f"{duration:.0f}s"))
        if not ok:
            issues.append(f"{duration:.0f}s outside the 5s-10min study window")
    score = 100 - 25 * sum(1 for c in checks if not c["ok"])
    return _result(score, checks, issues)


def _luminance(path: str):
    with Image.open(path) as img:  # hygiene: allow binary image open needs no text encoding
        return img.convert("L").resize((64, 64))


def ahash(path: str) -> int:
    """Perceptual hash: identical/near-identical frames share a hash."""
    raw = bytes(_luminance(path).tobytes())
    mean = sum(raw) / max(1, len(raw))
    bits = 0
    for i, px in enumerate(raw):
        if px > mean:
            bits |= 1 << i
    return bits


def _hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def frame_sharpness(path: str) -> float:
    """Laplacian variance: motion blur and flat cards score near zero."""
    with Image.open(path) as img:  # hygiene: allow binary image open needs no text encoding
        gray = img.convert("L").resize((320, 320))
        edges = gray.filter(ImageFilter.Kernel(
            (3, 3), (-1, -1, -1, -1, 8, -1, -1, -1, -1), scale=1))
        # Pillow answers the 1px rim from padding, not content: ignore it.
        inner = edges.crop((1, 1, edges.width - 1, edges.height - 1))
        return ImageStat.Stat(inner).var[0]


def frames_quality(paths: list[str], blank_ceiling: float = 5.0,
                   low_detail_warn: float = 100.0, dup_bits: int = 6) -> dict:
    """Score extracted video frames; pick the ones worth analyzing.

    Drops true blanks and near-duplicates. Low-detail frames (paper texture,
    film grain, sparse marks: calibrated <100 on real footage) are KEPT but
    flagged — they may still be title cards worth a glance, just weak analysis
    targets. Returns per-frame verdicts + kept indices.
    """
    infos = []
    for path in paths:
        try:
            sharp = frame_sharpness(path)
            infos.append({"path": path, "sharpness": round(sharp, 1),
                          "hash": ahash(path)})
        except Exception as exc:
            infos.append({"path": path, "sharpness": 0.0, "hash": 0,
                          "error": f"{type(exc).__name__}"})
    kept, seen_hashes = [], []
    for i, info in enumerate(infos):
        if info.get("error"):
            info["verdict"] = "unreadable"
        elif info["sharpness"] < blank_ceiling:
            info["verdict"] = "blank-transition-card"
        elif any(_hamming(info["hash"], h) <= dup_bits for h in seen_hashes):
            info["verdict"] = "near-duplicate"
        elif info["sharpness"] < low_detail_warn:
            info["verdict"] = "low-detail"
            seen_hashes.append(info["hash"])
            kept.append(i)
        else:
            info["verdict"] = "keep"
            seen_hashes.append(info["hash"])
            kept.append(i)
    unique_ratio = len(kept) / max(1, len(infos))
    score = round(100 * unique_ratio)
    issues = []
    blanks = sum(1 for x in infos if x["verdict"] == "blank-transition-card")
    dupes = sum(1 for x in infos if x["verdict"] == "near-duplicate")
    thin = sum(1 for x in infos if x["verdict"] == "low-detail")
    if blanks:
        issues.append(f"{blanks} blank transition card(s) skipped")
    if dupes:
        issues.append(f"{dupes} near-duplicate frame(s) skipped")
    if thin:
        issues.append(f"{thin} low-detail frame(s) kept but weak analysis targets")
    if not kept:
        issues.append("no analyzable frames: all blank, duplicate, or unreadable")
        score = 0
    return {"score": score, "kept": kept, "frames": infos, "issues": issues,
            "checks": [
                _check("has-analyzable-frames", bool(kept), f"{len(kept)}/{len(infos)} kept"),
                _check("frame-diversity", unique_ratio >= 0.5,
                       f"{unique_ratio:.0%} unique"),
            ]}


def _mp4_duration(path: str) -> float | None:
    try:
        from domains.atlas.materials import _ffmpeg_exe
        exe = _ffmpeg_exe()
    except ImportError:
        return None
    import subprocess
    try:
        proc = subprocess.run([exe, "-i", path], capture_output=True,  # noqa: S603
                              text=True, timeout=60)
        match = re.search(r"Duration: (\d+):(\d+):([\d.]+)", proc.stderr)
        if not match:
            return None
        h, m, s = int(match.group(1)), int(match.group(2)), float(match.group(3))
        return h * 3600 + m * 60 + s
    except (subprocess.SubprocessError, OSError, ValueError):
        return None


def tour_quality(tour: dict, analysis: dict) -> dict:
    """Ordered 3D-layer walkthrough: every stop names a known entity."""
    checks, issues = [], []
    ids = {e["id"] for e in analysis.get("entities", [])}
    stops = tour.get("stops", [])
    located = [e["id"] for e in analysis.get("entities", []) if e.get("bbox")]
    if not analysis.get("entities"):
        return _result(0, [_check("has-stops", False, "model has no entities")],
                       ["nothing to tour"])
    if not stops and not located:
        return _result(100, [
            _check("tour-honest-empty", True, "text-only model: no 3D stops, expected"),
            _check("stops-reference-entities", True, "no stops to misreference"),
        ], [])
    bad = [s.get("entity_id", "?") for s in stops if s.get("entity_id") not in ids]
    checks.append(_check("stops-reference-entities", not bad,
                         f"{len(stops)} stops on known entities" if not bad else f"unknown: {bad[:3]}"))
    if bad:
        issues.append(f"tour references unknown entities: {bad[:3]}")
    thin = [s.get("entity_id", "?") for s in stops if not s.get("observe")]
    checks.append(_check("stops-have-guidance", not thin,
                         "every stop tells the learner what to observe" if not thin else f"empty: {thin[:3]}"))
    if thin:
        issues.append(f"{len(thin)} stops lack observation guidance")
    if located:
        covered = {s.get("entity_id") for s in stops}
        missing = [i for i in located if i not in covered]
        checks.append(_check("located-stops-covered", not missing,
                             f"{len(covered & set(located))}/{len(located)} located entities toured"
                             if not missing else f"untoured: {missing[:3]}"))
        if missing:
            issues.append(f"untoured located entities: {missing[:3]}")
    else:
        checks.append(_check("located-stops-covered", True, "text-only model: no located stops expected"))
    # Auto-play runs 3.2s per stop: a mega-model tour can outgrow the same
    # 30-minute study window the podcast honors. Flag, don't block.
    est_min = len(stops) * 3.2 / 60
    bounded = est_min <= 30
    checks.append(_check("tour-duration-sane", bounded,
                         f"~{est_min:.1f} min auto-play" if bounded
                         else f"~{est_min:.0f} min auto-play exceeds the 30 min study window"))
    if not bounded:
        issues.append(f"tour too long for one sitting: {len(stops)} stops (~{est_min:.0f} min)")
    score = 100 - 25 * sum(1 for c in checks if not c["ok"])
    return _result(score, checks, issues)


def questions_quality(bank: dict, analysis: dict) -> dict:
    """Question bank: every entity and relationship gets asked, with answers."""
    checks, issues = [], []
    questions = bank.get("questions", [])
    by_kind: dict[str, int] = {}
    for q in questions:
        by_kind[q.get("kind", "?")] = by_kind.get(q.get("kind", "?"), 0) + 1
    eids = [e["id"] for e in analysis.get("entities", [])]
    qtext = " ".join(q.get("question", "") for q in questions)
    missing_e = [e["id"] for e in analysis.get("entities", [])
                 if e.get("name", e["id"]) not in qtext and e["id"] not in qtext]
    checks.append(_check("entity-coverage", not missing_e,
                         f"{len(eids) - len(missing_e)}/{len(eids)} entities asked"
                         if eids else "no entities to ask"))
    if missing_e:
        issues.append(f"unasked entities: {missing_e[:3]}")
    rels = list(analysis.get("relationships", []))
    missing_r = [f"{r['source_id']}-{r['target_id']}" for r in rels
                 if not any(r["source_id"] in q.get("question", "") or
                            r["target_id"] in q.get("id", "") or
                            r["target_id"] in q.get("question", "") for q in questions)]
    checks.append(_check("relation-coverage", not missing_r or not rels,
                         f"{len(rels) - len(missing_r)}/{len(rels)} relationships asked"
                         if rels else "no relationships to ask"))
    if missing_r and rels:
        issues.append(f"unasked relationships: {missing_r[:3]}")
    no_answer = [q.get("id", "?") for q in questions if not q.get("answer")]
    checks.append(_check("answers-present", not no_answer,
                         "every question has an answer" if not no_answer else f"missing: {no_answer[:3]}"))
    if no_answer:
        issues.append(f"{len(no_answer)} questions lack answers")
    score = 100 - 25 * sum(1 for c in checks if not c["ok"])
    return _result(max(0, score), checks, issues)


def summary_quality(brief: dict, analysis: dict) -> dict:
    """Extractive study brief: counts match the model, pathways traced."""
    checks, issues = [], []
    stats = brief.get("stats", {})
    checks.append(_check("entity-count-matches",
                         stats.get("entities", -1) == len(analysis.get("entities", [])),
                         f"brief counts {stats.get('entities', '?')} entities"))
    if stats.get("entities", -1) != len(analysis.get("entities", [])):
        issues.append("brief entity count disagrees with the model")
    checks.append(_check("relation-count-matches",
                         stats.get("relationships", -1) == len(analysis.get("relationships", [])),
                         f"brief counts {stats.get('relationships', '?')} relationships"))
    if stats.get("relationships", -1) != len(analysis.get("relationships", [])):
        issues.append("brief relationship count disagrees with the model")
    rels = analysis.get("relationships", [])
    paths = brief.get("pathways", [])
    checks.append(_check("pathways-traced", bool(paths) or not rels,
                         f"{len(paths)} pathway(s)" if paths else "single-structure study"))
    if rels and not paths:
        issues.append("relationships exist but no pathway was traced")
    checks.append(_check("overview-present", bool(brief.get("overview")),
                         "overview sentence present" if brief.get("overview") else "overview missing"))
    if not brief.get("overview"):
        issues.append("brief has no overview")
    score = 100 - 25 * sum(1 for c in checks if not c["ok"])
    return _result(score, checks, issues)


def learn_quality(analysis: dict) -> dict:
    """All four learn modes build and grade correctly on this model."""
    from . import learning as learn
    checks, issues = [], []
    modes = ["spatial-recall", "pathway-tracing",
             "visual-identification", "relationship-recall"]
    builders = {"spatial-recall": learn.spatial_recall_challenge,
                "pathway-tracing": learn.pathway_tracing_challenge,
                "visual-identification": learn.visual_identification_challenge,
                "relationship-recall": learn.relationship_recall_challenge}
    for mode in modes:
        try:
            challenge = builders[mode](analysis, seed=0)
            key = {"spatial-recall": "answer_id",
                   "visual-identification": "answer_id",
                   "pathway-tracing": "answer",
                   "relationship-recall": "answer_rel_type"}[mode]
            graded = learn.grade(challenge, challenge.get(key))
            ok = bool(graded.get("correct"))
            checks.append(_check(f"learn-{mode}", ok,
                                 f"{mode} builds and grades" if ok else f"{mode} misgrades"))
            if not ok:
                issues.append(f"{mode} challenge does not grade its own answer")
        except Exception as exc:
            checks.append(_check(f"learn-{mode}", False, f"{type(exc).__name__}: {exc}"))
            issues.append(f"{mode} cannot build: {exc}")
    # Degeneracy guards: a self-grading tautology must still ask a real question.
    try:
        ents = list(analysis.get("entities", []))
        rels = list(analysis.get("relationships", []))
        spatial = builders["spatial-recall"](analysis, seed=0)
        opts = spatial.get("options", [])
        opt_ids = [o.get("id") for o in opts]
        diverse = len(opt_ids) == len(set(opt_ids)) and len(opt_ids) >= min(4, len(ents)) and len(opt_ids) > 1
        checks.append(_check("learn-spatial-options-diverse", diverse,
                             f"{len(opt_ids)} distinct options" if diverse else "spatial options degenerate"))
        if not diverse:
            issues.append("spatial-recall offers fewer than 2 distinct options")
        if len(rels) >= 2:
            chain = builders["pathway-tracing"](analysis, seed=0).get("chain", [])
            nontrivial = len(chain) >= 2
            checks.append(_check("learn-pathway-nontrivial", nontrivial,
                                 f"chain length {len(chain)}" if nontrivial else "pathway chain trivial"))
            if not nontrivial:
                issues.append("pathway-tracing chain trivial despite 2+ relationships")
        visual = builders["visual-identification"](analysis, seed=0)
        vopts = visual.get("options", [])
        vdiverse = len({o.get("id") for o in vopts}) > 1
        checks.append(_check("learn-visual-options-diverse", vdiverse,
                             "visual options distinct" if vdiverse else "visual options degenerate"))
        if not vdiverse:
            issues.append("visual-identification offers no distinct choice")
    except Exception as exc:
        checks.append(_check("learn-degeneracy-probe", False, f"{type(exc).__name__}: {exc}"))
        issues.append(f"degeneracy probe cannot build: {exc}")
    score = 100 - 25 * sum(1 for c in checks if not c["ok"])
    return _result(max(0, score), checks, issues)


def quality_report(analysis: dict, artifacts: dict) -> dict:
    """Score the requested artifacts; overall = mean of what was assessed.

    Also reports weakest (lowest-scoring artifact) and floor (False when any
    assessed artifact scores below 50). The pack still builds — the floor is
    a red badge, not a block — so headless flows never stall on a weak model.
    """
    from . import flashcards as fc
    from . import materials as mat
    report: dict[str, dict] = {}
    if "deck" in artifacts or "flashcards" in artifacts:
        deck = artifacts.get("deck") or artifacts.get("flashcards") or fc.build_deck(analysis)
        report["flashcards"] = flashcard_quality(deck, analysis)
    if "podcast" in artifacts:
        script = artifacts["podcast"]
        if isinstance(script, str):
            import json as _json
            try:
                script = _json.loads(script)
            except (ValueError, TypeError):
                script = None
            if not isinstance(script, dict):
                script = None
                report["podcast"] = _result(
                    0, [_check("podcast-parseable", False,
                               "podcast payload is not JSON")],
                    ["podcast payload is not JSON and cannot be scored"])
        if script is not None and not isinstance(script, dict):
            script = None
            report["podcast"] = _result(
                0, [_check("podcast-parseable", False,
                           "podcast payload is not JSON")],
                ["podcast payload is not JSON and cannot be scored"])
        if script is not None:
            report["podcast"] = podcast_quality(script, analysis)
    if "diagram_svg" in artifacts:
        report["infographic"] = infographic_quality(artifacts["diagram_svg"], analysis)
    if "obj" in artifacts:
        report["model3d"] = model3d_quality(artifacts["obj"], analysis)
    if "video_mp4" in artifacts:
        vrep = video_quality_mp4(artifacts["video_mp4"])
        if artifacts.get("video_frames"):
            try:
                frep = frames_quality(list(artifacts["video_frames"]))
                # Fold frame diversity into the video verdict: blank/duplicate
                # slideshows cannot score 100 on container math alone.
                vrep["checks"].append(_check(
                    "frames-analyzable", bool(frep.get("kept")),
                    f"{len(frep.get('kept', []))}/{len(frep.get('frames', []))} frames kept"))
                vrep["checks"].append(_check(
                    "frame-diversity", frep["score"] >= 50,
                    f"frames {frep['score']}/100"))
                for issue in frep.get("issues", []):
                    vrep["issues"].append(f"frames: {issue}")
                if frep["score"] < 50:
                    vrep["score"] = min(vrep["score"], 50)
                vrep["score"] = max(0, min(100, vrep["score"]))
            except Exception as exc:
                vrep["checks"].append(_check("frames-analyzable", False, f"{type(exc).__name__}"))
                vrep["issues"].append(f"frames probe failed: {exc}")
                vrep["score"] = min(vrep["score"], 75)
        report["video"] = vrep
    if "tour" in artifacts:
        report["tour"] = tour_quality(artifacts["tour"], analysis)
    if "questions" in artifacts:
        report["questions"] = questions_quality(artifacts["questions"], analysis)
    if "summary" in artifacts:
        report["summary"] = summary_quality(artifacts["summary"], analysis)
    if artifacts.get("include_learn"):
        report["learn"] = learn_quality(analysis)
    scored = {k: v for k, v in report.items() if isinstance(v, dict) and "score" in v}
    scores = [r["score"] for r in scored.values()]
    report["overall"] = round(sum(scores) / len(scores), 1) if scores else 0.0
    if scored:
        weakest = min(scored.items(), key=lambda kv: kv[1]["score"])
        report["weakest"] = weakest[0]
        report["floor"] = all(r["score"] >= 50 for r in scored.values())
    else:
        report["weakest"] = ""
        report["floor"] = True
    return report
