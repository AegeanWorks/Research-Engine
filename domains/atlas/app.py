"""Atlas standalone application entry point.

  python -m atlas.app [--port 8765] [--data data]

Serves the visual workspace (static/) and a JSON API. Stdlib only.
Fully standalone; all document handling is in-project.
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

from . import __version__
from .config import AtlasConfig
from . import text_backend as nd
from . import ingestion as ing
from . import learning as learn
from .muse_provider import MuseProvider
from .sam_provider import SamProvider
from .schema import BoundingBox, VisualAnalysis
from .store import AtlasStore

ROOT = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(ROOT, "static")


def _json(handler: BaseHTTPRequestHandler, obj, status: int = 200) -> None:
    body = json.dumps(obj).encode()
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


MAX_UPLOAD_BYTES = 60_000_000


def honest_error(exc: Exception) -> dict:
    """Every failure is a message with the reason, never a silent nothing.

    Maps known error text to {error, cause, fix}; unknown errors pass through
    with empty cause/fix so the UI still shows the raw message.
    """
    msg = f"{type(exc).__name__}: {exc}"
    cause, fix = "", ""
    if "No text on any of" in msg and "page(s)" in msg:
        cause = "scanned-image PDF: the file has pages but no extractable text"
        fix = ("render the target page to PNG (Advanced: Render page → figure), "
               "or run OCR first (e.g. ocrmypdf) and retry")
    elif "no public captions" in msg:
        cause = "caption-less or age-gated YouTube video: no public captions found"
        fix = "paste the article URL instead, or upload a VTT/SRT transcript file"
    elif "video needs ffmpeg" in msg or "ffmpeg" in msg and "needs" in msg:
        cause = "video needs ffmpeg and none is installed"
        fix = "install system ffmpeg, or pip install imageio-ffmpeg, then retry"
    elif "not set; refusing live call" in msg:
        cause = "live AI call needs MODEL_API_KEY/META_API_KEY and none is set"
        fix = ("no key needed for the offline path: drop the file again for an "
               "offline-extractive model, or set MODEL_API_KEY for live Muse/SAM")
    elif "supply a transcript" in msg:
        cause = "audio/video transcription is not bundled with Atlas"
        fix = "upload a VTT/SRT/JSON transcript file instead"
    elif "non-textual content" in msg:
        cause = "the URL serves non-textual content (file download, app page)"
        fix = "paste the article URL, or download the file and drop it directly"
    elif "Unsupported file type" in msg:
        cause = "unsupported file type"
        fix = "use PDF, PNG, JPEG, EPUB, TXT, MD, DOCX, PPTX, MP4/WebM/MOV, or a VTT/SRT transcript"
    elif "blank transition cards or duplicates" in msg:
        cause = "narration-heavy video: stills carry little lesson content"
        fix = "supply a VTT/SRT transcript or PNG stills instead"
    elif "PyMuPDF" in msg:
        cause = "PDF page rendering needs the optional PyMuPDF package"
        fix = "pip install PyMuPDF, or auto-create a text model as-is"
    return {"error": msg, "cause": cause, "fix": fix}


def _parse_multipart(body: bytes, content_type: str) -> tuple[dict, dict]:
    """Minimal single-file multipart/form-data parser (stdlib only).

    Returns (fields, files) where files maps field name to
    {"filename": str, "content_type": str, "data": bytes}.
    """
    parts = content_type.split("boundary=")
    if len(parts) != 2 or not parts[1]:
        raise ValueError("multipart body needs a boundary")
    boundary = ("--" + parts[1].strip().strip('"')).encode()
    if len(body) > MAX_UPLOAD_BYTES:
        raise ValueError(f"upload exceeds {MAX_UPLOAD_BYTES} bytes")
    fields: dict = {}
    files: dict = {}
    for chunk in body.split(boundary):
        chunk = chunk.strip(b"\r\n")
        if not chunk or chunk == b"--":
            continue
        head, _, payload = chunk.partition(b"\r\n\r\n")
        if not payload:
            continue
        headers = head.decode("latin-1")
        name = ""
        filename = ""
        part_type = "application/octet-stream"
        for line in headers.split("\r\n"):
            low = line.lower()
            if low.startswith("content-disposition:"):
                for seg in line.split(";"):
                    seg = seg.strip()
                    if seg.startswith("name="):
                        name = seg[5:].strip('"')
                    elif seg.startswith("filename="):
                        filename = os.path.basename(seg[9:].strip('"'))
            elif low.startswith("content-type:"):
                part_type = line.split(":", 1)[1].strip()
        if not name:
            continue
        data = payload.rstrip(b"\r\n")
        if filename:
            files[name] = {"filename": filename, "content_type": part_type, "data": data}
        else:
            fields[name] = data.decode("utf-8", "replace")
    return fields, files


def _merge_frame_analyses(analyses: list, document_ref: str, figure_id: str):
    """Merge per-frame visual analyses, namespacing ids per frame (f0-, f1-...)."""
    from .schema import VisualAnalysis, VisualEntity, VisualRelationship
    entities, relationships = [], []
    for i, analysis in enumerate(analyses):
        prefix = f"f{i}-"
        for e in analysis.entities:
            d = e.to_dict()
            d["id"] = prefix + d["id"]
            entities.append(VisualEntity(**_entity_kwargs(d)))
        for r in analysis.relationships:
            d = r.to_dict()
            relationships.append(VisualRelationship(
                source_id=prefix + d["source_id"], target_id=prefix + d["target_id"],
                rel_type=d["rel_type"], explanation=d.get("explanation", ""),
                supporting_evidence=d.get("supporting_evidence", ""),
                confidence=d.get("confidence", 0.0),
                provenance=d.get("provenance", "model"),
                model_inferred=d.get("model_inferred", True)))
    return VisualAnalysis(document_ref=document_ref, figure_id=figure_id,
                          entities=entities, relationships=relationships)


def _entity_kwargs(d: dict) -> dict:
    from .schema import BoundingBox
    bbox = None
    if d.get("bbox"):
        b = d["bbox"]
        bbox = BoundingBox(x_min=b["x_min"], y_min=b["y_min"],
                           x_max=b["x_max"], y_max=b["y_max"])
    return {"id": d["id"], "name": d["name"], "category": d.get("category", "other"),
            "description": d.get("description", ""), "bbox": bbox,
            "source_evidence": d.get("source_evidence", ""),
            "confidence": d.get("confidence", 0.0),
            "uncertainty": d.get("uncertainty", ""),
            "mask_ref": d.get("mask_ref", ""),
            "model_inferred": d.get("model_inferred", False)}


def auto_create_model(store: AtlasStore, config: AtlasConfig, source: str,
                      note: str = "", figure_id: str = "", use_wonder: bool = False,
                      muse_provider=None, crop: tuple | None = None) -> dict:
    """One drop → one model, from anything: image, PDF, book, text, link,
    YouTube, or video. Images/frames take the visual path; everything textual
    takes the text path; both land in one validated model driving canvas,
    graph, and learning. `muse_provider` injectable for offline-safe use.
    """
    from . import sources as src
    from . import muse_provider as _mp
    # Tests (and power users) patch atlas.app.MuseProvider with a fake; honor
    # that ahead of the offline fallback so injected doubles keep working.
    _Provider = globals().get("MuseProvider", _mp.MuseProvider)
    _patched = _Provider is not _mp.MuseProvider
    is_url = source.startswith(("http://", "https://"))
    if is_url:
        bundle = src.ingest_any(source)
        doc = {"document_ref": bundle["document_ref"], "title": bundle.get("title", ""),
               "text_chars": len(bundle.get("text", ""))}
    else:
        doc = ing.import_document(source, store.data_dir)
        bundle = src.ingest_any(source)
    kind = bundle["kind"]
    if kind == "text":
        doc["title"] = bundle.get("title", doc.get("original_name", ""))
        doc["text_chars"] = len(bundle["text"])
        fid = figure_id or ("model-" + AtlasStore.cache_key(bundle["document_ref"])[:8])
        if muse_provider is not None:
            provider = muse_provider
            offline = False
        elif _patched or config.has_api_key:
            provider = _Provider(config, use_wonder=use_wonder)
            offline = False
        else:
            provider = None
            offline = True
        if not offline:
            analyze = getattr(provider, "analyze_long_text", None)
            if callable(analyze):
                analysis = analyze(bundle["text"], note,
                                   document_ref=bundle["document_ref"], figure_id=fid)
            else:  # injected test doubles without chunking: single pass
                analysis = provider.analyze_text(bundle["text"], note,
                                                 document_ref=bundle["document_ref"], figure_id=fid)
        else:
            from . import offline as _offline
            analysis = _offline.build_offline_analysis(
                bundle["text"], document_ref=bundle["document_ref"],
                figure_id=fid, source_kind="text")
        data = analysis.to_dict()
        store.save_analysis(fid, data)
        out = {"document": doc, "model_created": True, "figure_id": fid,
               "analysis": data, "source_kind": "text", "offline": offline}
        if offline:
            out["warning"] = ("offline-extractive model (no API key): keyword "
                              "frequency, not Muse vision. Add MODEL_API_KEY for live analysis.")
        return out
    if kind == "video":
        from . import quality as qa
        frames_dir = os.path.join(store.data_dir, "frames",
                                  AtlasStore.cache_key(bundle["path"])[:12])
        raw_frames = src.video_frames(bundle["path"], frames_dir)
        fq = qa.frames_quality(raw_frames)
        frames = [raw_frames[i] for i in fq["kept"]]
        if not frames:
            raise ValueError("video frames are all blank transition cards or duplicates "
                             "(motion-graphics/live-action need their transcript: "
                             "narration carries the lesson, stills carry little). "
                             "Supply a VTT/SRT transcript or PNG stills instead.")
        if muse_provider is None and not _patched and not config.has_api_key:
            from . import offline as _offline
            fid = figure_id or ("model-" + doc["sha256"][:8])
            context = _offline.offline_text_for_source(bundle, note)
            analysis = _offline.build_offline_analysis(
                context, document_ref=doc["document_ref"], figure_id=fid,
                source_kind="video")
            data = analysis.to_dict()
            store.save_analysis(fid, data)
            first = os.path.basename(frames[0])
            return {"document": doc, "model_created": True, "figure_id": fid,
                    "figure_url": "/frames/" + os.path.basename(frames_dir) + "/" + first,
                    "frames": len(frames), "frames_report": fq, "analysis": data,
                    "source_kind": "video", "offline": True, "located_entities": 0,
                    "warning": ("offline-extractive video model (no API key): frames kept "
                                f"{len(frames)}/{len(raw_frames)}, visual entities not detected. "
                                "Add MODEL_API_KEY for live frame analysis.")}
        provider = muse_provider if muse_provider is not None else _Provider(config, use_wonder=use_wonder)
        per_frame = []
        for i, frame in enumerate(frames):
            frame_note = ((note + " ") if note else "") + \
                f"[Video frame {i + 1} of {len(frames)} from {os.path.basename(bundle['path'])}.]"
            first = provider.analyze_figure(
                frame, frame_note, document_ref=doc["document_ref"], figure_id=f"frame-{i}")
            located = sum(1 for e in first.entities if e.bbox)
            if located == 0 and getattr(provider, "_live_transport", False):
                # One retry demanding grounding: stills carry boxes, so a
                # fully boxless frame pass is usually under-asking, not absence.
                retry = provider.analyze_figure(
                    frame, frame_note + " Return a normalized 0-1000 box for every visible entity.",
                    document_ref=doc["document_ref"], figure_id=f"frame-{i}")
                if any(e.bbox for e in retry.entities):
                    first = retry
            per_frame.append(first)
        fid = figure_id or ("model-" + doc["sha256"][:8])
        merged = _merge_frame_analyses(per_frame, doc["document_ref"], fid)
        data = merged.to_dict()
        store.save_analysis(fid, data)
        located = sum(1 for e in data["entities"] if e.get("bbox"))
        warning = ""
        if located == 0:
            warning = ("frames yielded no grounded boxes: this is a text-only model. "
                       "Learn via flashcards, summary, and podcast — not the canvas overlay.")
        elif located < len(data["entities"]) / 2:
            warning = (f"only {located}/{len(data['entities'])} entities grounded; "
                       "canvas overlay is partial, text paths are complete.")
        first = os.path.basename(frames[0])
        return {"document": doc, "model_created": True, "figure_id": fid,
                "figure_url": "/frames/" + os.path.basename(frames_dir) + "/" + first,
                "frames": len(frames), "frames_report": fq, "analysis": data,
                "source_kind": "video", "offline": False,
                "located_entities": located, "warning": warning}
    # image path: full-frame figure, visual analysis
    fid = figure_id or ("model-" + doc["sha256"][:8])
    figure = ing.select_figure(bundle["path"], crop or (0.0, 0.0, 1.0, 1.0),
                               store.data_dir, document_ref=doc["document_ref"])
    if muse_provider is not None:
        provider = muse_provider
        analysis = provider.analyze_figure(figure.image_path, note,
                                           document_ref=doc["document_ref"],
                                           figure_id=fid)
        offline = False
    elif _patched or config.has_api_key:
        analysis = _Provider(config, use_wonder=use_wonder).analyze_figure(
            figure.image_path, note, document_ref=doc["document_ref"], figure_id=fid)
        offline = False
    else:
        from . import offline as _offline
        context = _offline.offline_text_for_source(bundle, note)
        analysis = _offline.build_offline_analysis(
            context, document_ref=doc["document_ref"], figure_id=fid,
            source_kind="image")
        offline = True
    data = analysis.to_dict()
    store.save_analysis(fid, data)
    out = {"document": doc, "model_created": True, "figure_id": fid,
           "figure_url": "/figures/" + os.path.basename(figure.image_path),
           "analysis": data, "source_kind": "image", "offline": offline}
    if offline:
        out["warning"] = ("offline-extractive image model (no API key): figure shown, "
                          "visual entities not detected. Add MODEL_API_KEY for live vision.")
    return out


def list_models(store: AtlasStore) -> list[dict]:
    """Every model Atlas holds — the machine-visible model index."""
    out = []
    analyses = os.path.join(store.data_dir, "analyses")
    if not os.path.isdir(analyses):
        return out
    for name in sorted(os.listdir(analyses)):
        if not name.endswith(".analysis.json"):
            continue
        try:
            with open(os.path.join(analyses, name), encoding="utf-8") as fh:
                data = json.load(fh)
            out.append({"figure_id": data.get("figure_id", name[:-14]),
                        "entities": len(data.get("entities", [])),
                        "relationships": len(data.get("relationships", [])),
                        "document_ref": data.get("document_ref", "")})
        except (OSError, ValueError):
            continue
    return out


def describe_model(data: dict) -> str:
    """One model as plain text an AI (or person) can read in a glance."""
    from . import models3d as m3d
    from . import summaries as sm
    brief = sm.extractive_summary(data)
    view = m3d.iso_view(data)
    lines = [f"MODEL {data.get('figure_id', '?')}: {brief['overview']}",
             f"Source: {data.get('document_ref', '?')} (page {data.get('source_page', 0)})",
             "ENTITIES:"]
    for i, (e, b) in enumerate(zip(data.get("entities", []), brief["entities"])):
        box = e.get("bbox")
        loc = (f"at {box['x_min'] * 100:.0f},{box['y_min'] * 100:.0f}-"
               f"{box['x_max'] * 100:.0f},{box['y_max'] * 100:.0f}%" if box else "text-only")
        lines.append(f"  {i + 1}. {b} [{loc}]")
    lines.append("PATHWAYS:")
    lines.extend(f"  {i + 1}. {p}" for i, p in enumerate(brief["pathways"]))
    lines.append(f"3D layers present: {sorted({p['layer'] for p in view['polygons']}) or 'none'}; "
                 f"skipped (text-only): {', '.join(view['skipped']) or 'none'}")
    return "\n".join(lines)


def api_contract() -> dict:
    """Versioned machine contract so AI agents can drive Atlas autonomously."""
    return {
        "contract_version": "domains.atlas.api/v1",
        "atlas_version": __version__,
        "workflow": ["health", "upload|import", "auto-create", "models",
                      "analysis", "segment", "learn"],
        "endpoints": {
            "GET /api/health": "version, config (redacted), backend info",
            "GET /api/contract": "this contract",
            "GET /api/models": "list of created models (?format=text for a readable digest)",
            "GET /api/state?figure_id=": "one glance: digest, iso, deck size, stats, artifact URLs",
            "POST /api/upload (multipart file=)": "browser/AI file drop import",
            "POST /api/auto-create {path|document_ref, note?, figure_id?, crop?}":
                "one drop -> one model: image/PDF/EPUB/TXT/video/URL/YouTube",
            "sources": "pdf, epub, txt, md, docx, pptx, transcripts, images, "
                       "video (ffmpeg), article URLs, YouTube captions",
            "POST /api/segment {image_path, prompt, entity_id, bbox?}": "SAM 3.1 mask",
            "POST /api/analysis/attach-mask": "attach a mask to an entity",
            "GET /api/analysis?figure_id=": "read one model",
            "GET /api/model3d?figure_id=&format=json|obj": "isometric view or OBJ 3D export",
            "POST /api/model3d {figure_id|analysis, format?}": "isometric view or OBJ (inline analysis supported)",
            "POST /api/flashcards {analysis}": "flashcard deck",
            "GET /api/flashcards/export?figure_id=": "Anki TSV download",
            "POST /api/flashcards/export {figure_id|analysis}": "Anki TSV download (inline analysis supported)",
            "GET /api/diagram?figure_id=&format=svg|png": "printable study poster",
            "POST /api/diagram {figure_id|analysis, format?}": "printable study poster (inline analysis supported)",
            "GET /api/tour?figure_id=": "ordered 3D-layer walkthrough",
            "POST /api/tour {figure_id|analysis}": "ordered 3D-layer walkthrough (inline analysis supported)",
            "GET /api/podcast?figure_id=&format=md|json": "two-host audio script",
            "POST /api/podcast {figure_id|analysis, format?}": "two-host audio script (inline analysis supported)",
            "GET /api/questions?figure_id=&format=json|md": "question bank + worksheet",
            "POST /api/questions {figure_id|analysis, format?}": "question bank + worksheet (inline analysis supported)",
            "POST /api/video {figure_id|analysis}": "render the H.264 study MP4",
            "POST /api/quality {figure_id|analysis, include_video?}": "score every artifact 0-100",
            "POST /api/learn {analysis, mode, seed}": "challenge",
            "POST /api/learn/grade {challenge, answer}": "grade",
        },
        "notes": ("Only figure crops (+ optional note) leave the machine toward Meta; "
                  "keys via MODEL_API_KEY/META_API_KEY env; no key needed to read models."),
    }


class Handler(BaseHTTPRequestHandler):
    store: AtlasStore | None = None
    config: AtlasConfig = AtlasConfig.from_env()

    @classmethod
    def get_store(cls) -> AtlasStore:
        if cls.store is None:
            cls.store = AtlasStore(cls.config.data_dir)
        return cls.store

    def log_message(self, fmt, *args):  # quieter; no secrets ever logged
        _ = (fmt, args)
        return None

    # -- GET ------------------------------------------------------------
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path in ("/", "/index.html"):
            return self._serve_file(os.path.join(STATIC, "index.html"))
        if parsed.path.startswith("/static/"):
            name = os.path.basename(parsed.path)
            return self._serve_file(os.path.join(STATIC, name))
        if parsed.path.startswith("/figures/"):
            name = os.path.basename(parsed.path)
            return self._serve_file(os.path.join(self.get_store().data_dir, "figures", name))
        if parsed.path.startswith("/masks/"):
            name = os.path.basename(parsed.path)
            return self._serve_file(os.path.join(self.get_store().data_dir, "masks", name))
        if parsed.path.startswith("/frames/"):
            tail = parsed.path[len("/frames/"):]
            parts = [p for p in tail.split("/") if p not in ("", ".", "..")]
            if len(parts) != 2:
                return _json(self, {"error": "not found"}, 404)
            return self._serve_file(os.path.join(
                self.get_store().data_dir, "frames", parts[0], parts[1]))
        if parsed.path == "/api/health":
            return _json(self, {"ok": True, "version": __version__,
                                "config": self.config.redacted(),
                                "integration": nd.describe_integration()})
        if parsed.path == "/api/integration":
            return _json(self, nd.describe_integration())
        if parsed.path == "/api/analysis":
            q = urllib.parse.parse_qs(parsed.query)
            fid = (q.get("figure_id") or [""])[0]
            return _json(self, {"analysis": self.get_store().load_analysis(fid)})
        if parsed.path == "/api/corrections":
            return _json(self, {"corrections": self.get_store().load_corrections()})
        if parsed.path == "/api/models":
            q = urllib.parse.parse_qs(parsed.query)
            if (q.get("format") or ["json"])[0] == "text":
                parts = []
                for m in list_models(self.get_store()):
                    saved = self.get_store().load_analysis(m["figure_id"])
                    if saved is not None:
                        parts.append(describe_model(saved))
                body = "\n\n---\n\n".join(parts).encode() or b"(no models yet)"
                self.send_response(200)
                self.send_header("Content-Type", "text/plain")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            return _json(self, {"models": list_models(self.get_store())})
        if parsed.path == "/api/diagram":
            from . import materials as mat
            q = urllib.parse.parse_qs(parsed.query)
            fid = (q.get("figure_id") or [""])[0]
            saved = self.get_store().load_analysis(fid)
            if saved is None:
                return _json(self, {"error": f"unknown figure_id {fid!r}"}, 404)
            fmt = (q.get("format") or ["svg"])[0]
            try:
                if fmt == "png":
                    body = mat.diagram_png(saved)
                    ctype = "image/png"
                    fname = f"{fid}.png"
                else:
                    body = mat.diagram_svg(saved).encode()
                    ctype = "image/svg+xml"
                    fname = f"{fid}.svg"
            except ImportError as exc:
                return _json(self, {"error": str(exc)}, 400)
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Disposition", f'attachment; filename="{fname}"')
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path == "/api/tour":
            from . import materials as mat
            q = urllib.parse.parse_qs(parsed.query)
            fid = (q.get("figure_id") or [""])[0]
            saved = self.get_store().load_analysis(fid)
            if saved is None:
                return _json(self, {"error": f"unknown figure_id {fid!r}"}, 404)
            return _json(self, mat.tour_3d(saved))
        if parsed.path == "/api/podcast":
            from . import materials as mat
            q = urllib.parse.parse_qs(parsed.query)
            fid = (q.get("figure_id") or [""])[0]
            saved = self.get_store().load_analysis(fid)
            if saved is None:
                return _json(self, {"error": f"unknown figure_id {fid!r}"}, 404)
            script = mat.podcast_script(saved)
            if (q.get("format") or ["md"])[0] == "json":
                return _json(self, script)
            body = mat.podcast_markdown(script).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/markdown")
            self.send_header("Content-Disposition", f'attachment; filename="{fid}-podcast.md"')
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path == "/api/questions":
            from . import materials as mat
            q = urllib.parse.parse_qs(parsed.query)
            fid = (q.get("figure_id") or [""])[0]
            saved = self.get_store().load_analysis(fid)
            if saved is None:
                return _json(self, {"error": f"unknown figure_id {fid!r}"}, 404)
            bank = mat.question_bank(saved)
            if (q.get("format") or ["json"])[0] == "md":
                body = mat.questions_markdown(bank).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/markdown")
                self.send_header("Content-Disposition", f'attachment; filename="{fid}-questions.md"')
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            return _json(self, bank)
        if parsed.path.startswith("/videos/"):
            tail = parsed.path[len("/videos/"):]
            parts = [p for p in tail.split("/") if p not in ("", ".", "..")]
            if len(parts) != 2:
                return _json(self, {"error": "not found"}, 404)
            return self._serve_file(os.path.join(
                self.get_store().data_dir, "videos", parts[0], parts[1]))
        if parsed.path == "/api/state":
            q = urllib.parse.parse_qs(parsed.query)
            fid = (q.get("figure_id") or [""])[0]
            saved = self.get_store().load_analysis(fid)
            if saved is None:
                return _json(self, {"error": f"unknown figure_id {fid!r}"}, 404)
            from . import flashcards as fc
            from . import models3d as m3d
            from . import summaries as sm
            brief = sm.extractive_summary(saved)
            return _json(self, {
                "figure_id": fid,
                "text_digest": describe_model(saved),
                "iso": m3d.iso_view(saved),
                "deck_size": len(fc.build_deck(saved)["cards"]),
                "stats": brief["stats"],
                "urls": {
                    "obj": f"/api/model3d?figure_id={urllib.parse.quote(fid)}&format=obj",
                    "tsv": f"/api/flashcards/export?figure_id={urllib.parse.quote(fid)}",
                    "analysis": f"/api/analysis?figure_id={urllib.parse.quote(fid)}",
                },
            })
        if parsed.path == "/api/model3d":
            from . import models3d as m3d
            q = urllib.parse.parse_qs(parsed.query)
            fid = (q.get("figure_id") or [""])[0]
            saved = self.get_store().load_analysis(fid)
            if saved is None:
                return _json(self, {"error": f"unknown figure_id {fid!r}"}, 404)
            if (q.get("format") or ["json"])[0] == "obj":
                try:
                    body = m3d.export_obj(saved).encode()
                except ValueError as exc:
                    return _json(self, {"error": str(exc)}, 400)
                self.send_response(200)
                self.send_header("Content-Type", "text/plain")
                self.send_header("Content-Disposition",
                                 f'attachment; filename="{fid}.obj"')
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            return _json(self, m3d.iso_view(saved))
        if parsed.path == "/api/flashcards/export":
            from . import flashcards as fc
            q = urllib.parse.parse_qs(parsed.query)
            fid = (q.get("figure_id") or [""])[0]
            saved = self.get_store().load_analysis(fid)
            if saved is None:
                return _json(self, {"error": f"unknown figure_id {fid!r}"}, 404)
            try:
                body = fc.to_anki_tsv(fc.build_deck(saved)).encode("utf-8")
            except ValueError as exc:
                return _json(self, {"error": str(exc)}, 400)
            self.send_response(200)
            self.send_header("Content-Type", "text/tab-separated-values")
            self.send_header("Content-Disposition", f'attachment; filename="{fid}.tsv"')
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path == "/api/contract":
            return _json(self, api_contract())
        return _json(self, {"error": "not found"}, 404)

    def _serve_file(self, path: str):
        if not os.path.isfile(path):
            return _json(self, {"error": "not found"}, 404)
        mime, _ = mimetypes.guess_type(path)
        with open(path, "rb") as fh:
            body = fh.read()
        self.send_response(200)
        self.send_header("Content-Type", mime or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # -- POST -----------------------------------------------------------
    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0") or 0)
        raw = self.rfile.read(length) if length > 0 else b""
        try:
            body = json.loads(raw.decode("utf-8", "replace")) if raw else {}
        except json.JSONDecodeError as exc:
            ctype = self.headers.get("Content-Type", "")
            if "json" in ctype:
                return _json(self, {"error": f"ValueError: invalid JSON body: {exc}",
                                    "cause": "the request body is not valid JSON",
                                    "fix": "send a JSON object with Content-Type: application/json"}, 400)
            body = {}
        route = urllib.parse.urlparse(self.path).path
        store = self.get_store()

        def _resolve_inline(body, store):
            """figure_id or validated inline analysis (browser-only demo fixture)."""
            if body.get("analysis"):
                return VisualAnalysis.from_dict(body["analysis"]).to_dict()
            saved = store.load_analysis(body.get("figure_id", ""))
            if saved is None:
                raise ValueError(
                    f"unknown figure_id {body.get('figure_id')!r}: the demo fixture "
                    "lives in the browser only — drop the file to create a "
                    "server-side model, or send inline analysis")
            return saved

        def _send_blob(blob: bytes, ctype: str, fname: str):
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Disposition", f'attachment; filename="{fname}"')
            self.send_header("Content-Length", str(len(blob)))
            self.end_headers()
            self.wfile.write(blob)
        try:
            if route == "/api/import":
                if not body.get("path"):
                    raise ValueError("missing 'path': provide a server-local file path or URL")
                if body["path"].startswith(("http://", "https://")):
                    return _json(self, {"staged_path": body["path"],
                                        "hint": "URL: call /api/auto-create directly"})
                result = ing.import_document(body["path"], store.data_dir,
                                             int(body.get("page", 0)))
                if result.get("mime") == "application/pdf":
                    from . import doc_text as _dt
                    result["pages"] = _dt.pdf_page_count(body["path"])
                try:
                    from . import sources as _src
                    bundle = _src.ingest_any(body["path"])
                    if bundle["kind"] == "text":
                        result["text_chars"] = len(bundle["text"])
                        result["title"] = bundle.get("title", "")
                    else:
                        result["text_chars"] = 0
                        result["media"] = bundle["kind"]
                    result["text_backend"] = "atlas"
                except Exception as exc:
                    result["text_chars"] = 0
                    result["text_backend"] = f"unavailable: {type(exc).__name__}"
                if result["mime"] == "application/pdf":
                    result["figure_hint"] = ("PDF stored with text. Convert the target page to PNG/JPEG "
                                             "for figure overlays, or auto-create a text model as-is.")
                return _json(self, result)
            if route == "/api/pdf/render":
                from . import sources as _src
                doc_path = body.get("path") or body.get("document_ref", "")
                if not doc_path:
                    raise ValueError("pdf/render needs 'path'")
                page = int(body.get("page", 1))
                outdir = os.path.join(store.data_dir, "figures")
                try:
                    png = _src.render_pdf_page(doc_path, page, outdir)
                except ImportError as exc:
                    raise ValueError(str(exc)) from exc
                return _json(self, {"image_path": png,
                                    "figure_url": "/figures/" + os.path.basename(png),
                                    "page": page})
            if route == "/api/figure/select":
                crop = ing.select_figure(
                    body["image_path"], tuple(body["crop"]), store.data_dir,
                    body.get("document_ref", ""), int(body.get("page", 0)))
                payload = crop.to_dict()
                payload["figure_url"] = "/figures/" + os.path.basename(crop.image_path)
                return _json(self, payload)
            if route == "/api/analyze":
                key = AtlasStore.cache_key("muse", body.get("image_path", ""),
                                           body.get("note", ""), str(body.get("use_wonder", False)))
                cached = store.cache_get(key)
                if cached:
                    return _json(self, {"analysis": cached, "cached": True})
                provider = MuseProvider(self.config, use_wonder=bool(body.get("use_wonder", False)))
                analysis = provider.analyze_figure(
                    body["image_path"], body.get("note", ""),
                    body.get("document_ref", ""), int(body.get("page", 0)),
                    body.get("figure_id", "figure"))
                data = analysis.to_dict()
                store.save_analysis(body.get("figure_id", "figure"), data)
                store.cache_put(key, data)
                return _json(self, {"analysis": data, "cached": False})
            if route == "/api/segment":
                bbox = None
                if body.get("bbox"):
                    b = body["bbox"]
                    bbox = BoundingBox(x_min=b["x_min"], y_min=b["y_min"],
                                       x_max=b["x_max"], y_max=b["y_max"])
                provider = SamProvider(self.config)
                seg = provider.segment(body["image_path"], body.get("prompt", ""),
                                       body.get("entity_id", ""), bbox)
                key = AtlasStore.cache_key("sam", body.get("image_path", ""), body.get("prompt", ""))
                store.cache_put(key, {"kind": seg.kind, "mask_ref": seg.mask_ref})
                return _json(self, {"kind": seg.kind, "mask_ref": seg.mask_ref,
                                    "bbox": seg.bbox.to_dict() if seg.bbox else None,
                                    "note": seg.raw_note})
            if route == "/api/analysis/load":
                analysis = VisualAnalysis.from_dict(body["analysis"])
                store.save_analysis(body.get("figure_id", "figure"), analysis.to_dict())
                return _json(self, {"ok": True})
            if route == "/api/analysis/attach-mask":
                figure_id = body.get("figure_id", "")
                saved = store.load_analysis(figure_id)
                if saved is None:
                    raise ValueError(f"unknown figure_id {figure_id!r}")
                kind = body.get("kind", "")
                if kind not in ("mask", "bbox-fallback"):
                    raise ValueError(f"kind must be 'mask' or 'bbox-fallback', got {kind!r}")
                mask_ref = str(body.get("mask_ref", ""))
                entity_id = body.get("entity_id", "")
                entity = next((e for e in saved.get("entities", []) if e.get("id") == entity_id), None)
                if entity is None:
                    raise ValueError(f"unknown entity_id {entity_id!r}")
                entity["mask_ref"] = mask_ref
                if body.get("bbox"):
                    entity["bbox"] = body["bbox"]
                store.save_analysis(figure_id, saved)
                return _json(self, {"ok": True, "analysis": saved})
            if route == "/api/corrections":
                items = store.add_correction(body)
                return _json(self, {"corrections": items})
            if route == "/api/learn":
                mode = body.get("mode", "spatial-recall")
                analysis = VisualAnalysis.from_dict(body["analysis"]).to_dict()
                seed = int(body.get("seed", 0))
                modes = {"spatial-recall": learn.spatial_recall_challenge,
                         "pathway-tracing": learn.pathway_tracing_challenge,
                         "visual-identification": learn.visual_identification_challenge,
                         "relationship-recall": learn.relationship_recall_challenge}
                if mode not in modes:
                    raise ValueError(
                        f"unknown learn mode {mode!r}: use spatial-recall, "
                        "pathway-tracing, visual-identification, "
                        "relationship-recall")
                return _json(self, modes[mode](analysis, seed))
            if route == "/api/learn/grade":
                return _json(self, learn.grade(body["challenge"], body["answer"]))
            if route == "/api/flashcards":
                from . import flashcards as fc
                data = VisualAnalysis.from_dict(body["analysis"]).to_dict()
                return _json(self, fc.build_deck(data))
            if route == "/api/tour":
                from . import materials as _mat
                if body.get("analysis"):
                    data = VisualAnalysis.from_dict(body["analysis"]).to_dict()
                    return _json(self, _mat.tour_3d(data))
                saved = store.load_analysis(body.get("figure_id", ""))
                if saved is None:
                    raise ValueError(
                        f"unknown figure_id {body.get('figure_id')!r}: the demo fixture "
                        "lives in the browser only — drop the file to create a "
                        "server-side model, or send inline analysis")
                return _json(self, _mat.tour_3d(saved))
            if route == "/api/diagram":
                from . import materials as mat
                saved = _resolve_inline(body, store)
                fid = body.get("figure_id", "") or saved.get("figure_id", "model")
                if body.get("format", "svg") == "png":
                    _send_blob(mat.diagram_png(saved), "image/png", f"{fid}.png")
                else:
                    _send_blob(mat.diagram_svg(saved).encode(),
                               "image/svg+xml", f"{fid}.svg")
                return
            if route == "/api/podcast":
                from . import materials as mat
                saved = _resolve_inline(body, store)
                fid = body.get("figure_id", "") or saved.get("figure_id", "model")
                script = mat.podcast_script(saved)
                if body.get("format", "md") == "json":
                    return _json(self, script)
                _send_blob(mat.podcast_markdown(script).encode("utf-8"),
                           "text/markdown", f"{fid}-podcast.md")
                return
            if route == "/api/questions":
                from . import materials as mat
                saved = _resolve_inline(body, store)
                fid = body.get("figure_id", "") or saved.get("figure_id", "model")
                bank = mat.question_bank(saved)
                if body.get("format", "json") == "md":
                    _send_blob(mat.questions_markdown(bank).encode("utf-8"),
                               "text/markdown", f"{fid}-questions.md")
                    return
                return _json(self, bank)
            if route == "/api/model3d":
                from . import models3d as m3d
                saved = _resolve_inline(body, store)
                fid = body.get("figure_id", "") or saved.get("figure_id", "model")
                if body.get("format", "json") == "obj":
                    _send_blob(m3d.export_obj(saved).encode(),
                               "text/plain", f"{fid}.obj")
                    return
                return _json(self, m3d.iso_view(saved))
            if route == "/api/flashcards/export":
                from . import flashcards as fc
                saved = _resolve_inline(body, store)
                fid = body.get("figure_id", "") or saved.get("figure_id", "model")
                _send_blob(fc.to_anki_tsv(fc.build_deck(saved)).encode("utf-8"),
                           "text/tab-separated-values", f"{fid}.tsv")
                return
            if route == "/api/video":
                from . import materials as mat
                saved = None
                if body.get("analysis"):
                    saved = VisualAnalysis.from_dict(body["analysis"]).to_dict()
                elif body.get("figure_id"):
                    saved = store.load_analysis(body["figure_id"])
                if saved is None:
                    raise ValueError("video needs figure_id or inline analysis")
                fid = body.get("figure_id", "") or saved.get("figure_id", "film")
                vdir = os.path.join(store.data_dir, "videos", AtlasStore.cache_key(fid)[:12])
                fps = max(1, min(int(body.get("fps", 24)), 30))
                sps = max(0.5, min(float(body.get("seconds_per_scene", 1.5)), 4.0))
                try:
                    info = mat.video_slideshow(saved, vdir, fps=fps, seconds_per_scene=sps)
                except ImportError as exc:
                    raise ValueError(str(exc)) from exc
                return _json(self, {"mp4_url": "/videos/" + os.path.basename(vdir) + "/study.mp4",
                                    **info, "figure_id": saved.get("figure_id", "")})
            if route == "/api/quality":
                from . import flashcards as fc
                from . import materials as mat
                from . import models3d as m3d
                from . import quality as qa
                saved = None
                if body.get("analysis"):
                    saved = VisualAnalysis.from_dict(body["analysis"]).to_dict()
                elif body.get("figure_id"):
                    saved = store.load_analysis(body["figure_id"])
                if saved is None:
                    if body.get("figure_id"):
                        raise ValueError(
                            f"unknown figure_id {body.get('figure_id')!r}: the demo fixture "
                            "lives in the browser only — drop the file to create a "
                            "server-side model, or send inline analysis")
                    raise ValueError("quality needs figure_id or inline analysis")
                from . import summaries as sm
                artifacts = {"deck": fc.build_deck(saved),
                             "podcast": mat.podcast_script(saved),
                             "diagram_svg": mat.diagram_svg(saved),
                             "tour": mat.tour_3d(saved),
                             "questions": mat.question_bank(saved),
                             "summary": sm.extractive_summary(saved),
                             "include_learn": True}
                skipped = []
                try:
                    artifacts["obj"] = m3d.export_obj(saved)
                except ValueError as exc:
                    skipped.append(f"model3d: {exc}")
                if body.get("include_video"):
                    try:
                        vdir = os.path.join(store.data_dir, "videos",
                                            AtlasStore.cache_key(saved.get("figure_id", "q"))[:12])
                        artifacts["video_mp4"] = mat.video_slideshow(saved, vdir)["mp4"]
                    except (ValueError, ImportError) as exc:
                        skipped.append(f"video: {exc}")
                report = qa.quality_report(saved, artifacts)
                if skipped:
                    report["skipped"] = skipped
                return _json(self, report)
            if route == "/api/summary":
                from . import summaries as sm
                saved = store.load_analysis(body.get("figure_id", ""))
                if saved is None and not body.get("analysis"):
                    raise ValueError("summary needs figure_id or inline analysis")
                data = VisualAnalysis.from_dict(body["analysis"]).to_dict() if body.get("analysis") else saved
                brief = sm.extractive_summary(data)
                polished = None
                if self.config.has_api_key:
                    try:
                        polished = MuseProvider(self.config).polish_summary(brief)
                    except Exception as exc:
                        polished = f"[polish unavailable: {type(exc).__name__}: {exc}]"
                return _json(self, {"extractive": brief, "polished": polished,
                                    "polished_model": self.config.muse_model
                                    if polished and not polished.startswith("[") else ""})
            if route == "/api/upload":
                ctype = self.headers.get("Content-Type", "")
                if not raw or len(raw) > MAX_UPLOAD_BYTES:
                    raise ValueError("upload needs a non-empty body "
                                     f"(max {MAX_UPLOAD_BYTES} bytes)")
                _, files = _parse_multipart(raw, ctype)
                upload = files.get("file")
                if upload is None:
                    raise ValueError("multipart field 'file' is required")
                safe = "".join(c if c.isalnum() or c in "-_." else "_"
                               for c in upload["filename"]) or "upload.bin"
                incoming = os.path.join(store.data_dir, "documents",
                                        "incoming_" + safe)
                with open(incoming, "wb") as fh:
                    fh.write(upload["data"])
                result = ing.import_document(incoming, store.data_dir)
                try:
                    from . import sources as _src
                    bundle = _src.ingest_any(incoming)
                    if bundle["kind"] == "text":
                        result["text_chars"] = len(bundle["text"])
                        result["text_backend"] = "atlas"
                        result["title"] = bundle.get("title", "")
                    elif bundle["kind"] == "video":
                        result["text_chars"] = 0
                        result["text_backend"] = "atlas"
                        result["media"] = "video"
                    else:
                        result["text_chars"] = 0
                        result["text_backend"] = "atlas"
                        result["media"] = "image"
                except Exception as exc:
                    result["text_chars"] = 0
                    result["text_backend"] = f"unavailable: {type(exc).__name__}"
                result["staged_path"] = incoming
                return _json(self, result)
            if route == "/api/auto-create":
                path = body.get("path") or body.get("document_ref") or body.get("staged_path", "")
                if not path:
                    raise ValueError("auto-create needs 'path' (or staged_path/document_ref)")
                crop = tuple(body["crop"]) if body.get("crop") else None
                return _json(self, auto_create_model(
                    store, self.config, path, body.get("note", ""),
                    body.get("figure_id", ""), bool(body.get("use_wonder", False)),
                    crop=crop))
            return _json(self, {"error": "not found"}, 404)
        except Exception as exc:
            return _json(self, honest_error(exc), 400)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Atlas standalone app")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--data", default="data")
    args = ap.parse_args(argv)
    Handler.store = AtlasStore(args.data)
    Handler.config = AtlasConfig.from_env(data_dir=args.data)
    server = HTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Atlas on http://127.0.0.1:{args.port} (data={args.data})")
    print("Standalone visual knowledge app; visual AI: Meta Muse + SAM 3.1.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
