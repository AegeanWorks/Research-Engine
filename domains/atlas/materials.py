"""Study-material generators: every format from the same validated model.

- Study diagram (SVG + PNG): clean labeled schematic redrawn from entity
  boxes and relationship arrows — a printable poster of the knowledge.
- 3D tour: ordered layer-by-layer stops guiding the isometric/OBJ view.
- Podcast script: two-host conversational walkthrough with evidence, pathway
  segment, recap, and quiz teasers — TTS-ready markdown + structured JSON.
- Question bank: every generated question with answers + evidence, as JSON or
  a markdown worksheet.

All extractive and offline (Pillow only for PNG). Nothing invented: every
line traces to an entity, a relationship, or stated evidence.
"""
from __future__ import annotations

import html as _html
import io
import math
import os

from .models3d import iso_view, layer_of

W, H = 960, 640
MARGIN = 70


def _names(analysis: dict) -> dict:
    return {e["id"]: e.get("name", e["id"]) for e in analysis.get("entities", [])}


def _font(size: int):
    """Turkish-capable truetype font: Pillow's bundled fonts miss Latin
    Extended (ğşçıİ renders as tofu boxes, caught by eye on real output).
    Prefers system Arial/DejaVu, falls back to bundled with a clear note."""
    from PIL import ImageFont
    candidates = [
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ]
    for path in candidates:
        if os.path.isfile(path):
            try:
                return ImageFont.truetype(path, size), path
            except OSError:
                continue
    return ImageFont.load_default(size=size), "bundled-fallback"


def _wrap(draw, text: str, font, max_width: float) -> list[str]:
    """Greedy word-wrap to a pixel width (Pillow has no textbox).

    Long descriptions used to run past the frame edge (hard-truncated at
    100 chars); wrapping keeps every word inside the storyboard. Returns
    at least one line so callers never index an empty list.
    """
    words = str(text).split()
    if not words:
        return [""]
    # A single token wider than the frame (hashes, long ids) can never wrap
    # on spaces: hard-split it first so nothing paints past the edge.
    toks: list[str] = []
    for w in words:
        while draw.textlength(w, font=font) > max_width and len(w) > 1:
            lo, hi = 1, len(w)
            while lo < hi:
                mid = (lo + hi) // 2
                if draw.textlength(w[:mid], font=font) <= max_width:
                    lo = mid + 1
                else:
                    hi = mid
            cut = max(1, lo - 1)
            toks.append(w[:cut])
            w = w[cut:]
        toks.append(w)
    lines, cur = [], ""
    for w in toks:
        trial = f"{cur} {w}".strip()
        if draw.textlength(trial, font=font) <= max_width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [""]


def _layout(analysis: dict) -> dict:
    """Entity id → canvas rect (uses the figure box, else a grid fallback)."""
    entities = list(analysis.get("entities", []))
    rects = {}
    homeless = [e for e in entities if not e.get("bbox")]
    if homeless:
        # Text-only models have no figure positions: lay their boxes out as
        # an index grid that always fits the frame. Small models get roomy
        # 180x80 boxes; huge ones (a 245-entity book) get compact boxes so
        # every label still has its own non-overlapping slot.
        n = len(homeless)
        usable_w = W - 2 * MARGIN
        avail_h = (H - 24) - _POSTER_TOP
        cols = max(1, min(n, math.ceil((n * usable_w / max(avail_h, 1)) ** 0.5)))
        rows = math.ceil(n / cols)
        box_w = max(36.0, min(180.0, usable_w / cols - 6))
        box_h = max(24.0, min(80.0, avail_h / rows - 6))
        for i, e in enumerate(homeless):
            c, r = i % cols, i // cols
            x = MARGIN if cols == 1 else MARGIN + c * (usable_w - box_w) / (cols - 1)
            y = _POSTER_TOP if rows == 1 else _POSTER_TOP + r * (avail_h - box_h) / (rows - 1)
            rects[e["id"]] = (x, y, box_w, box_h)
    # Dense cap keys on grounded boxes, not total entities: a text-heavy model
    # with 30 entities but 5 boxes still gets roomy boxes; a merged
    # multi-frame model with 25 grounded boxes gets compact caps so labels fit.
    n_grounded = sum(1 for e in entities if e.get("bbox"))
    dense = n_grounded > 20
    for e in entities:
        bbox = e.get("bbox")
        if not bbox:
            continue
        x = MARGIN + bbox["x_min"] * (W - 2 * MARGIN)
        y = MARGIN + bbox["y_min"] * (H - 2 * MARGIN - 60)
        # Poster boxes are approximate (footer says so): floor tiny slivers
        # so labels have a box to sit in, cap giants so one frame-filling
        # entity cannot swallow the poster on merged multi-frame models.
        w = min(max((bbox["x_max"] - bbox["x_min"]) * (W - 2 * MARGIN), 90), 180 if dense else 240)
        h = min(max((bbox["y_max"] - bbox["y_min"]) * (H - 2 * MARGIN - 60), 44), 100 if dense else 130)
        rects[e["id"]] = (x, y, w, h)
    placed = _declutter(rects)
    return _fit_frame(placed)


def _fit_frame(rects: dict) -> dict:
    """Vertically center poster content in the usable frame.

    Figure boxes map from figure space, so top-heavy models leave the
    poster's bottom half empty. This translates (never reorders/resizes)
    so content sits centered between the header rule and the footer line.
    No-op on empty input; clamped so nothing leaves the frame.
    """
    if not rects:
        return rects
    top, bottom = float(_POSTER_TOP), float(H - 34)
    min_y = min(r[1] for r in rects.values())
    max_y = max(r[1] + r[3] for r in rects.values())
    shift = round((top + bottom - (min_y + max_y)) / 2)
    if not shift:
        return rects
    out = {}
    for k, (x, y, w, h) in rects.items():
        ny = min(max(y + shift, top), bottom - h)
        out[k] = (x, ny, w, h)
    return out


def _overlaps(a: tuple, b: tuple) -> bool:
    return (a[0] < b[0] + b[2] and b[0] < a[0] + a[2]
            and a[1] < b[1] + b[3] and b[1] < a[1] + a[3])


# Poster furniture: title bar (64) + rule (3) + padding. The quality scorer
# counts every SVG rect, header included, so boxes must start below it.
_POSTER_TOP = 72
_POSTER_PAD = 4
_GAP = 2


def _clamp_box(x: float, y: float, w: float, h: float) -> tuple:
    return (min(max(x, _POSTER_PAD), W - w - _POSTER_PAD),
            min(max(y, _POSTER_TOP), H - h - _POSTER_PAD), w, h)


def _declutter(rects: dict, max_passes: int = 200) -> dict:
    """Spread overlapping poster boxes apart (the poster is a derivation;
    evidence boxes on the canvas are untouched). Deterministic: sorted ids,
    each box keeps its figure position when free, else the nearest free
    spot on a spiral, else the first free slot of a coarse top-down grid.
    Fixed point when clean. (max_passes is kept for caller compatibility.)"""
    ids = sorted(rects)
    placed: dict[str, tuple] = {}
    order: list[str] = []
    for i in ids:
        box = _clamp_box(*rects[i])
        if not any(_overlaps(box, placed[j]) for j in order):
            placed[i] = box
            order.append(i)
            continue
        found = None
        radius = 4
        while radius <= 260 and found is None:
            for k in range(8):
                ang = k * math.pi / 4
                cand = _clamp_box(box[0] + radius * math.cos(ang),
                                  box[1] + radius * math.sin(ang) * 0.75,
                                  box[2], box[3])
                if not any(_overlaps(cand, placed[j]) for j in order):
                    found = cand
                    break
            radius += 4
        if found is None:
            # Dense poster: scan a coarse grid top-down for any free slot.
            # Deterministic; if none exists the box keeps its (honest,
            # scorer-flagged) figure position.
            w, h = box[2], box[3]
            gy = _POSTER_TOP
            while gy <= H - h - _POSTER_PAD and found is None:
                gx = float(_POSTER_PAD)
                while gx <= W - w - _POSTER_PAD and found is None:
                    if not any(_overlaps((gx, gy, w, h), placed[j]) for j in order):
                        found = (gx, gy, w, h)
                    gx += 8
                gy += 8
        if found is None:
            found = box
        placed[i] = found
        order.append(i)
    return placed


def diagram_svg(analysis: dict) -> str:
    """Study diagram as SVG: labeled boxes + directional arrows."""
    names = _names(analysis)
    rects = _layout(analysis)
    layers = [layer_of(e.get("category", "other")) for e in analysis.get("entities", [])]
    top_layer = max(layers) if layers else 0

    def layer_stroke(layer: int) -> str:
        t = (layer / top_layer) if top_layer else 0.0
        r = round(0x22 + (0x8B - 0x22) * t)
        g = round(0xD3 + (0x5C - 0xD3) * t)
        b = round(0xEE + (0xF6 - 0xEE) * t)
        return f"#{r:02x}{g:02x}{b:02x}"

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img">',
        f'<rect width="{W}" height="{H}" fill="#0b1530"/>',
        '<defs><pattern id="dots" width="26" height="26" patternUnits="userSpaceOnUse">'
        '<circle cx="2" cy="2" r="1.2" fill="#1b2b52"/></pattern>'
        '<marker id="arr" markerWidth="9" markerHeight="9" refX="7" refY="4.5" '
        'orient="auto"><path d="M0,0 L8,4.5 L0,9" fill="none" stroke="#22d3ee" stroke-width="1.6"/></marker></defs>',
        f'<rect width="{W}" height="{H}" fill="url(#dots)" opacity="0.55"/>',
        f'<rect x="0" y="0" width="{W}" height="64" fill="#0e1830"/>',
        f'<rect x="0" y="64" width="{W}" height="3" fill="#22d3ee" opacity="0.8"/>',
        f'<text x="{MARGIN}" y="28" fill="#dbe7ff" font-size="22" font-weight="bold" '
        f'font-family="sans-serif">{_html.escape(str(analysis.get("figure_id", "Atlas study diagram")))}</text>',
        f'<text x="{MARGIN}" y="50" fill="#8fa3c8" font-size="12" '
        f'font-family="sans-serif">Boxes mark figure locations · arrows carry the relationship type</text>',
    ]
    for r in analysis.get("relationships", []):
        a, b = rects.get(r["source_id"]), rects.get(r["target_id"])
        if not a or not b:
            continue
        x1, y1 = a[0] + a[2] / 2, a[1] + a[3] / 2
        x2, y2 = b[0] + b[2] / 2, b[1] + b[3] / 2
        parts.append(
            f'<line x1="{x1:.0f}" y1="{y1:.0f}" x2="{x2:.0f}" y2="{y2:.0f}" '
            f'stroke="#22d3ee" stroke-width="1.6" marker-end="url(#arr)" opacity="0.85"/>')
        parts.append(
            f'<text x="{(x1 + x2) / 2:.0f}" y="{(y1 + y2) / 2 - 6:.0f}" text-anchor="middle" '
            f'fill="#7dd3fc" font-size="11" font-family="sans-serif" '
            f'stroke="#0b1530" stroke-width="3" paint-order="stroke">'
            f'{_html.escape(str(r.get("rel_type", "")))}</text>')
    for e in analysis.get("entities", []):
        r = rects.get(e["id"])
        if not r:
            continue
        x, y, w, h = r
        label = names[e["id"]]
        short = label if len(label) <= 22 else label[:21] + "…"
        stroke = layer_stroke(layer_of(e.get("category", "other")))
        parts.append(
            f'<rect x="{x:.0f}" y="{y:.0f}" width="{w:.0f}" height="{h:.0f}" rx="10" '
            f'fill="#1b2b52" stroke="{stroke}" stroke-width="2"/>')
        parts.append(
            f'<text x="{x + w / 2:.0f}" y="{y + h / 2 + 5:.0f}" text-anchor="middle" '
            f'fill="#dbe7ff" font-size="14" font-family="sans-serif">{_html.escape(short)}</text>')
    parts.append(
        f'<text x="{MARGIN}" y="{H - 14}" fill="#5b6b8c" font-size="11" font-family="sans-serif">'
        f'Atlas study diagram · generated from the validated analysis · positions approximate · {_html.escape(str(analysis.get("document_ref", "")))}</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def diagram_png(analysis: dict) -> bytes:
    """Same schematic rasterized with Pillow (text may wrap, never invented)."""
    from PIL import Image, ImageDraw
    names = _names(analysis)
    rects = _layout(analysis)
    title_font, _ = _font(22)
    label_font, _ = _font(14)
    rel_font, _ = _font(11)
    img = Image.new("RGB", (W, H), (11, 21, 48))
    draw = ImageDraw.Draw(img)
    title = str(analysis.get("figure_id", "Atlas"))[:40]
    draw.text(((W - draw.textlength(title, font=title_font)) / 2, 12), title,
              font=title_font, fill=(219, 231, 255))
    for r in analysis.get("relationships", []):
        a, b = rects.get(r["source_id"]), rects.get(r["target_id"])
        if not a or not b:
            continue
        draw.line([a[0] + a[2] / 2, a[1] + a[3] / 2, b[0] + b[2] / 2, b[1] + b[3] / 2],
                  fill=(34, 211, 238), width=2)
        # Same midpoint label the SVG carries: dark pill behind cyan text
        # so it reads over lines and box edges alike.
        tag = str(r.get("rel_type", ""))
        if tag:
            mx, my = (a[0] + a[2] / 2 + b[0] + b[2] / 2) / 2, (a[1] + a[3] / 2 + b[1] + b[3] / 2) / 2 - 8
            bb = draw.textbbox((mx, my), tag, font=rel_font, anchor="mm")
            draw.rectangle([bb[0] - 3, bb[1] - 2, bb[2] + 3, bb[3] + 2], fill=(11, 21, 48))
            draw.text((mx, my), tag, font=rel_font, fill=(125, 211, 252), anchor="mm")
    for e in analysis.get("entities", []):
        r = rects.get(e["id"])
        if not r:
            continue
        x, y, w, h = r
        draw.rectangle([x, y, x + w, y + h], outline=(139, 92, 246), width=2)
        draw.text((x + 8, y + h / 2 - 7), names[e["id"]][:24],
                  font=label_font, fill=(219, 231, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def tour_3d(analysis: dict) -> dict:
    """Ordered stops through the 3D stack, bottom layer first."""
    view = iso_view(analysis)
    by_id = {e["id"]: e for e in analysis.get("entities", [])}
    names = _names(analysis)
    rels: dict[str, list] = {}
    for r in analysis.get("relationships", []):
        rels.setdefault(r["source_id"], []).append(r)
        rels.setdefault(r["target_id"], []).append(r)
    stops = []
    for i, p in enumerate(sorted(view["polygons"], key=lambda q: q["layer"])):
        e = by_id.get(p["id"], {})
        links = [f"{names.get(r['source_id'], '?')} {r['rel_type']} {names.get(r['target_id'], '?')}"
                 for r in rels.get(p["id"], [])]
        stops.append({
            "stop": i + 1, "entity_id": p["id"], "name": p["name"],
            "layer": p["layer"], "category": p["category"],
            "observe": (e.get("description", "") or f"Locate {p['name']} in the stack."),
            "connections": links,
            "camera": f"isolate layer {p['layer']} (slider ≤ {p['layer']}), then reveal upward",
        })
    return {"figure_id": analysis.get("figure_id", ""), "stops": stops}


def _spoken_relation(r: dict, names: dict) -> str:
    """Audible relationship: type + target + the model's own explanation.

    The explanation is already-grounded study content (it ships in the
    validated model) that the old script left unsaid; speaking it is what
    lifts thin episodes without filler. Single sentence per relation so
    spoken-density stays flat.
    """
    base = (f"{names.get(r['source_id'], '?')} {r.get('rel_type', '?')} "
            f"{names.get(r['target_id'], '?')}")
    expl = (r.get("explanation") or "").strip().rstrip(".")
    if expl and expl.lower() not in (base.lower(), r.get("rel_type", "").lower()):
        return f"{base} — {expl}"
    return base


def _spoken_out(r: dict, names: dict) -> str:
    """Entity-segment form: relation + target + explanation (no repeated source)."""
    base = f"{r.get('rel_type', '?')} {names.get(r['target_id'], '?')}"
    expl = (r.get("explanation") or "").strip().rstrip(".")
    if expl and expl.lower() not in (base.lower(), r.get("rel_type", "").lower()):
        return f"{base} — {expl}"
    return base


def _spoken_in(r: dict, names: dict) -> str:
    """Incoming-relation form: rel_type + this entity + explanation."""
    base = f"{r.get('rel_type', '?')} {names.get(r['target_id'], '?')}"
    expl = (r.get("explanation") or "").strip().rstrip(".")
    if expl and expl.lower() not in (base.lower(), r.get("rel_type", "").lower()):
        return f"{base} — {expl}"
    return base


def podcast_script(analysis: dict, max_segments: int = 24) -> dict:
    """Two-host conversational walkthrough, TTS-ready segments + duration.

    Big models are trimmed to the highest-degree entities so the episode stays
    inside the 30-minute study window; the script says how many were covered.
    """
    names = _names(analysis)
    degree: dict[str, int] = {}
    for r in analysis.get("relationships", []):
        degree[r["source_id"]] = degree.get(r["source_id"], 0) + 1
        degree[r["target_id"]] = degree.get(r["target_id"], 0) + 1
    entities = sorted(list(analysis.get("entities", [])),
                      key=lambda e: (-degree.get(e["id"], 0), e.get("name", "")))
    trimmed = max(0, len(entities) - max_segments)
    entities = entities[:max_segments]
    segments = [{
        "speaker": "HOST", "cue": "cold open",
        "text": (f"Welcome to Atlas TAC. Start with {len(entities)} key structures"
                 + (f" (top of {len(analysis.get('entities', []))} in the model)"
                    if trimmed else "")
                 + f", {len(analysis.get('relationships', []))} connections, one figure. "
                   "Let's walk it together."),
    }]
    for e in entities:
        outs = [r for r in analysis.get("relationships", []) if r["source_id"] == e["id"]]
        ins = [r for r in analysis.get("relationships", []) if r["target_id"] == e["id"]]
        line = f"{e.get('name', e['id'])}. {e.get('description', 'A key structure in this figure.')}"
        if outs:
            line += " " + ". ".join(
                f"It {_spoken_out(r, names)}" for r in outs) + "."
        if ins:
            line += " " + ". ".join(
                f"{names.get(r['source_id'], '?')} {_spoken_in(r, names)}" for r in ins) + "."
        if e.get("source_evidence"):
            line += f" On the figure: {e['source_evidence']}."
        segments.append({"speaker": "GUIDE", "cue": f"segment: {e.get('name', e['id'])}",
                         "text": line})
    chains = []
    seen: set[str] = set()
    for r in analysis.get("relationships", []):
        key = f"{r['source_id']} {r['rel_type']} {r['target_id']}"
        if key not in seen:
            seen.add(key)
            chains.append(_spoken_relation(r, names))
    walk = ("Now trace it end to end. " + ". ".join(chains[:8]) + "." if chains
            else "A single-structure study: hold its definition and evidence in mind.")
    segments.append({"speaker": "HOST", "cue": "pathway walk", "text": walk})
    teasers = [f"What does {e.get('name', e['id'])} connect to?" for e in entities[:3]]
    recap = ("Recap in one breath. " + ". ".join(chains[:5]) + ". " if chains
             else "Recap in one breath: " + (entities[0].get("description", "") if entities else "review the card above") + ". ")
    segments.append({"speaker": "GUIDE", "cue": "recap + quiz teasers",
                     "text": recap + "Test yourself: " + " ".join(teasers)})
    # Chapter timestamps: cumulative spoken time so TTS pipelines and show
    # notes can jump straight to a segment.
    elapsed = 0.0
    for s in segments:
        s["starts_at"] = _mmss(elapsed)
        elapsed += len(s["text"].split()) / 150 * 60
    words = sum(len(s["text"].split()) for s in segments)
    return {"title": f"Atlas audio walkthrough: {analysis.get('figure_id', 'model')}",
            "segments": segments,
            "estimated_minutes": round(words / 150, 1),
            "covered_ids": [e["id"] for e in entities],
            "trimmed_from": len(analysis.get("entities", []))}


def _mmss(total_seconds: float) -> str:
    total_seconds = max(0, int(round(total_seconds)))
    return f"{total_seconds // 60:02d}:{total_seconds % 60:02d}"


def podcast_markdown(script: dict) -> str:
    lines = [f"# {script['title']}", "",
             f"*~{script['estimated_minutes']} min spoken · generated from the validated model*",
             ""]
    for s in script["segments"]:
        stamp = f" [{s['starts_at']}]" if s.get("starts_at") else ""
        lines += [f"## {s['speaker']} — {s['cue']}{stamp}", "", s["text"], ""]
    return "\n".join(lines)


def _ffmpeg_exe() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError as exc:
        raise ImportError("Video rendering needs imageio-ffmpeg (pip install -r requirements.txt).") from exc


def video_slideshow(analysis: dict, outdir: str, fps: int = 30,
                    seconds_per_scene: float = 2.0) -> dict:
    """Model → narrated-caption MP4 study video (title, entity spotlights, outro).

    Frames are Pillow storyboards; the bundled imageio-ffmpeg binary encodes
    real H.264 — no system ffmpeg, no key, fully offline after pip install.
    """
    import subprocess
    from PIL import Image, ImageDraw, ImageFont
    names = _names(analysis)
    entities = list(analysis.get("entities", []))[:8]  # keep study videos tight
    if not entities:
        raise ValueError("no entities: nothing to film")
    os.makedirs(outdir, exist_ok=True)
    import glob as _glob
    for old in _glob.glob(os.path.join(outdir, "f_*.png")):
        try:
            os.remove(old)
        except OSError:  # hygiene: allow best-effort removal of stale frames
            pass
    title_font, _ = _font(30)
    body_font, _ = _font(16)

    def card(title: str, lines: list[str], highlight: str | None = None,
             scene: tuple[int, int] | None = None) -> "Image.Image":
        img = Image.new("RGB", (W, H), (11, 21, 48))
        draw = ImageDraw.Draw(img)
        shown = _wrap(draw, title[:80], title_font, W - 2 * MARGIN)[:2]
        draw.text((MARGIN, 40), shown[0], font=title_font, fill=(125, 211, 252))
        if len(shown) > 1:
            draw.text((MARGIN, 72), shown[1], font=title_font, fill=(125, 211, 252))
        y = 128
        shown_lines: list[str] = []
        for line in lines:
            shown_lines.extend(_wrap(draw, line, body_font, W - 2 * MARGIN) or [""])
        for line in shown_lines[:9]:
            draw.text((MARGIN, y), line, font=body_font, fill=(219, 231, 255))
            y += 30
        if highlight:
            # Underline the title itself, not the whole frame width.
            bar_w = max(60, min(draw.textlength(shown[0], font=title_font) + 16, W - 2 * MARGIN))
        if highlight:
            # Underline the title itself, not the whole frame width.
            bar_w = max(60, min(draw.textlength(shown[0], font=title_font) + 16, W - 2 * MARGIN))
            draw.rectangle([MARGIN - 8, 108, MARGIN - 8 + bar_w, 108 + 8], fill=(34, 211, 238))
        if scene is not None:
            i, n = scene
            tag = f"{i} / {n}"
            tw = draw.textlength(tag, font=body_font)
            draw.text((W - MARGIN - tw, 44), tag, font=body_font, fill=(125, 211, 252))
            draw.rectangle([MARGIN, H - 26, W - MARGIN, H - 20], outline=(34, 53, 99))
            draw.rectangle([MARGIN, H - 26, MARGIN + (W - 2 * MARGIN) * i / max(1, n), H - 20],
                           fill=(34, 211, 238))
        return img

    total_scenes = len(entities) + 2
    lineup = [names.get(e["id"], e["id"]) for e in entities[:3]]
    scenes: list[tuple["Image.Image", str]] = [
        (card(str(analysis.get("figure_id", "Atlas study film")),
              [f"{len(entities)} structures", f"{len(analysis.get('relationships', []))} connections"]
              + (["Featuring: " + ", ".join(lineup)] if lineup else []),
              scene=(1, total_scenes)),
         "title")]
    for k, e in enumerate(entities, start=2):
        eid = e["id"]
        links = [r for r in analysis.get("relationships", [])
                 if r["source_id"] == eid or r["target_id"] == eid][:4]
        lines = ([e.get("description", "")] +
                 [f"{names.get(r['source_id'], '?')} {r['rel_type']} "
                  f"{names.get(r['target_id'], '?')}" for r in links])
        scenes.append((card(names.get(eid, eid), [l for l in lines if l], highlight=eid,
                            scene=(k, total_scenes)), eid))
    scenes.append((card("Recap", [f"{names.get(e['id'], e['id'])}" for e in entities],
                          scene=(total_scenes, total_scenes)), "recap"))

    per_scene = max(1, int(fps * seconds_per_scene))
    frame = 0
    for img, _tag in scenes:
        for _ in range(per_scene):
            img.save(os.path.join(outdir, f"f_{frame:04d}.png"))
            frame += 1
    mp4 = os.path.join(outdir, "study.mp4")
    cmd = [_ffmpeg_exe(), "-y", "-v", "error", "-framerate", str(fps),
           "-i", os.path.join(outdir, "f_%04d.png"),
           "-c:v", "libx264", "-pix_fmt", "yuv420p", mp4]
    try:
        subprocess.run(cmd, timeout=300, check=True,  # noqa: S603
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except (subprocess.SubprocessError, OSError) as exc:
        raise ValueError(f"ffmpeg could not encode the study video: {exc}") from exc
    duration = len(scenes) * seconds_per_scene
    return {"mp4": mp4, "duration_s": round(duration, 1),
            "scenes": len(scenes), "fps": fps}


def question_bank(analysis: dict) -> dict:
    """Every generatable question with its answer + evidence (worksheet source)."""
    names = _names(analysis)
    questions = []
    for e in analysis.get("entities", []):
        if e.get("description"):
            questions.append({
                "id": f"q-desc-{e['id']}", "kind": "identify-description",
                "question": f"Which structure is this? {e['description']}",
                "answer": names[e["id"]], "evidence": e.get("source_evidence", "")})
        if e.get("bbox"):
            questions.append({
                "id": f"q-spot-{e['id']}", "kind": "spatial-recall",
                "question": f"Point to {names[e['id']]} on the figure.",
                "answer": names[e["id"]], "evidence": e.get("source_evidence", "")})
    for r in analysis.get("relationships", []):
        questions.append({
            "id": f"q-rel-{r['source_id']}-{r.get('rel_type', '?')}-{r['target_id']}", "kind": "relationship-recall",
            "question": (f"How are {names.get(r['source_id'], '?')} and "
                         f"{names.get(r['target_id'], '?')} connected?"),
            "answer": r["rel_type"], "evidence": r.get("supporting_evidence", "")})
    # Every entity must be askable by name: description questions withhold
    # the name on purpose (it is the answer) and boxless, isolated entities
    # otherwise never appear in the bank. Fall back to what the model does
    # assert — the recorded category (names the entity without giving
    # anything away), plus a grounded evidence question where evidence
    # exists (names nothing, recalls the entity from its source).
    texts = [q["question"] for q in questions]
    for e in analysis.get("entities", []):
        if any(e.get("name", e["id"]) in t or e["id"] in t for t in texts):
            continue
        questions.append({
            "id": f"q-kind-{e['id']}", "kind": "identify-category",
            "question": f"What kind of structure is {names[e['id']]}?",
            "answer": e.get("category", "other"), "evidence": ""})
        texts.append(questions[-1]["question"])
        if e.get("source_evidence"):
            questions.append({
                "id": f"q-evidence-{e['id']}", "kind": "identify-description",
                "question": (f"Which structure is described by this evidence? "
                             f"{e['source_evidence']}"),
                "answer": names[e["id"]], "evidence": e.get("source_evidence", "")})
            texts.append(questions[-1]["question"])
    return {"figure_id": analysis.get("figure_id", ""), "questions": questions}


def questions_markdown(bank: dict) -> str:
    order = ["identify-description", "spatial-recall", "relationship-recall",
             "identify-category"]
    groups: dict[str, list] = {}
    for q in bank["questions"]:
        groups.setdefault(q["kind"], []).append(q)
    kinds = [k for k in order if k in groups] + [k for k in groups if k not in order]
    titles = {"identify-description": "Name it from the description",
              "spatial-recall": "Point to it on the figure",
              "relationship-recall": "How are they connected",
              "identify-category": "What kind of structure"}
    lines = [f"# Question bank: {bank.get('figure_id', 'model')}",
             f"*{len(bank['questions'])} questions, answers at the end*", ""]
    numbered = []
    for kind in kinds:
        lines += [f"## {titles.get(kind, kind)}", ""]
        for q in groups[kind]:
            numbered.append(q)
            lines.append(f"{len(numbered)}. [{q['kind']}] {q['question']}")
        lines.append("")
    lines += ["## Answers", ""]
    for i, q in enumerate(numbered, 1):
        ev = f" _(evidence: {q['evidence']})_" if q.get("evidence") else ""
        lines.append(f"{i}. {q['answer']}{ev}")
    return "\n".join(lines) + "\n"
