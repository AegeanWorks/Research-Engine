"""Meta Muse provider (Spark default, Wonder for complex reasoning).

Verified against https://dev.meta.ai/docs (2026-11-01):
- POST {base}/chat/completions with messages[].content:
  {"type":"text","text":...} + {"type":"image_url","image_url":{"url": data:...;base64,...}}
- Structured output: response_format {"type":"json_schema","json_schema":{...}}
- Perception grounding grid: normalized 0..1000, (0,0) top-left; clamp edge
  values (e.g. 1001) and convert with /1000 for storage, /10 for CSS %.
- Alternative: Responses API input_image blocks; this provider uses Chat
  Completions (OpenAI-compatible) so stdlib-only clients work.

No credentials in logs (see AtlasConfig.redacted()). Only the selected figure
crop — never the whole document — is transmitted. Mockable for offline tests.
"""
from __future__ import annotations

import base64
import json
import os
import time
import urllib.request
import urllib.error

from .config import AtlasConfig
from .schema import VisualAnalysis, coerce_muse_payload, merge_analyses, muse_json_schema


SYSTEM_PROMPT = (
    "You are a scientific figure interpreter. Identify visible structures only; "
    "never invent structures not present in the image. Return JSON matching the "
    "provided schema. Boxes use a normalized 0-1000 grid with (0,0) top-left. "
    "Mark anything not directly visible as model_inferred via low confidence "
    "and an uncertainty note. Ground every entity in source_evidence."
)


def build_request(image_b64: str, mime: str, note: str, model: str) -> dict:
    user_text = (
        "Analyze this scientific figure. Extract visible entities "
        "(anatomical structures, molecules, proteins, cell types, components, "
        "processes, functions, pathways) and directional relationships "
        "(activates, inhibits, projects-to, receives-input-from, produces, "
        "regulates, contains, participates-in). Use only supported relationship "
        "types. Context: " + (note or "no accompanying text provided.")
    )
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": [
                {"type": "text", "text": user_text},
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{image_b64}"}},
            ]},
        ],
        "response_format": {"type": "json_schema", "json_schema": muse_json_schema()},
        "temperature": 0.2,
    }


class MuseProvider:
    """Replaceable Meta API adapter with timeouts, retries, safe errors."""

    def __init__(self, config: AtlasConfig | None = None,
                 transport=None, use_wonder: bool = False):
        self.config = config or AtlasConfig.from_env()
        # NOTE: never detect "live" via `is` on bound methods — each attribute
        # access creates a new object, so that check is always False and would
        # silently bypass the no-key guard and hit the network.
        self._live_transport = transport is None
        self.transport = transport or self._http_post
        self.use_wonder = use_wonder

    @property
    def model(self) -> str:
        return self.config.wonder_model if self.use_wonder else self.config.muse_model

    def _http_post(self, payload: dict) -> dict:
        body = json.dumps(payload).encode()
        last: Exception | None = None
        for attempt in range(max(1, self.config.max_retries)):
            req = urllib.request.Request(
                self.config.base_url.rstrip("/") + "/chat/completions",
                data=body, headers={"Content-Type": "application/json"},
            )
            if self.config.api_key:
                req.add_header("Authorization", f"Bearer {self.config.api_key}")
            try:
                with urllib.request.urlopen(req, timeout=self.config.timeout_s) as resp:  # noqa: S310
                    return json.loads(resp.read().decode("utf-8", "replace"))
            except urllib.error.HTTPError as exc:
                if 400 <= exc.code < 500:
                    raise RuntimeError(f"Muse request refused: HTTP {exc.code}: {exc.reason}") from exc
                last = exc
                time.sleep(min(2.0 ** attempt, 8.0))
            except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
                last = exc
                time.sleep(min(2.0 ** attempt, 8.0))
        raise RuntimeError(f"Muse request failed after retries: {type(last).__name__}: {last}")

    def analyze_text(self, text: str, note: str = "",
                       document_ref: str = "", figure_id: str = "") -> VisualAnalysis:
        """Text source (book, article, transcript, PDF) → knowledge, no boxes.

        Entities carry source_evidence quotes instead of visual locations; the
        same validated schema drives graph + learning, minus the canvas overlay.
        """
        if not self.config.has_api_key and self._live_transport:
            raise RuntimeError("MODEL_API_KEY/META_API_KEY is not set; refusing live call")
        from .sources import trim_text
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": (
                    "Extract entities and directional relationships from this source "
                    "text. Omit 'box' (no visual location). Ground every entity in a "
                    "short 'source_evidence' quote from the text. Context: "
                    + (note or "no additional context.") + "\n\nSOURCE:\n"
                    + trim_text(text))},
            ],
            "response_format": {"type": "json_schema", "json_schema": muse_json_schema()},
            "temperature": 0.2,
        }
        response = self.transport(payload)
        content = self._extract_content(response)
        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Muse returned non-JSON content: {exc}") from exc
        return coerce_muse_payload(data, document_ref=document_ref, figure_id=figure_id)

    def analyze_long_text(self, text: str, note: str = "",
                          document_ref: str = "", figure_id: str = "") -> VisualAnalysis:
        """Whole books, not just the first 12k chars: chunk, analyze, merge.

        Entities merge on normalized names (descriptions keep the longest,
        evidence concatenates); relationships remap to canonical ids and
        dedupe exactly. Chunk indices ride in the note so cross-chunk
        references stay interpretable.
        """
        from .sources import chunk_text
        chunks = chunk_text(text)
        if len(chunks) == 1:
            return self.analyze_text(chunks[0], note, document_ref, figure_id)
        parts = [self.analyze_text(
            chunk, (note + " " if note else "") +
            f"[Part {i + 1}/{len(chunks)} of the same source; entities may repeat earlier parts.]",
            document_ref, f"{figure_id}-p{i + 1}" if figure_id else "")
            for i, chunk in enumerate(chunks)]
        analyses = [p if isinstance(p, VisualAnalysis) else coerce_muse_payload(
            p, document_ref=document_ref) for p in parts]
        return merge_analyses(analyses, document_ref=document_ref, figure_id=figure_id)

    # Machine relation names → plain English for student-facing prose.
    RELATION_VERBS = {
        "activates": "activates", "inhibits": "inhibits",
        "projects-to": "sends output to", "receives-input-from": "takes in",
        "produces": "produces", "regulates": "regulates",
        "contains": "contains", "participates-in": "takes part in",
    }

    def polish_summary(self, brief: dict) -> str:
        """Rewrite an extractive brief as flowing prose (needs key)."""
        if not self.config.has_api_key and self._live_transport:
            raise RuntimeError("MODEL_API_KEY/META_API_KEY is not set; refusing live call")
        glossary = "; ".join(f"{k} means '{v}'" for k, v in self.RELATION_VERBS.items())
        lines = [brief.get("overview", ""), *brief.get("entities", []),
                 *[f"Pathway: {p}" for p in brief.get("pathways", [])]]
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content":
                 "Rewrite the study brief below as a clear flowing summary for a student. "
                 "Keep every named structure and relationship; invent nothing. "
                 "Translate machine relation names to plain English "
                 f"({glossary}); never emit hyphenated tokens like "
                 "'receives-input-from' or 'participates-in'."},
                {"role": "user", "content": "\n".join(lines)},
            ],
            "temperature": 0.3,
        }
        response = self.transport(payload)
        return self._extract_content(response)

    @staticmethod
    def _extract_content(response: dict) -> str:
        try:
            return response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError(f"unexpected Muse response shape: {exc}") from exc

    def analyze_figure(self, image_path: str, note: str = "",
                       document_ref: str = "", source_page: int = 0,
                       figure_id: str = "") -> VisualAnalysis:
        if not self.config.has_api_key and self._live_transport:
            raise RuntimeError("MODEL_API_KEY/META_API_KEY is not set; refusing live call")
        with open(image_path, "rb") as fh:
            raw = fh.read()
        if len(raw) > 45_000_000:
            raise ValueError(
                f"image {len(raw)} bytes exceeds the 50 MB inline limit; "
                "downscale the figure crop before analysis (see docs).")
        ext = os.path.splitext(image_path)[1].lower()
        mime = {".png": "image/png", ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg", ".jfif": "image/jpeg",
                ".gif": "image/gif", ".webp": "image/webp",
                ".bmp": "image/bmp"}.get(ext, "image/png")
        payload = build_request(base64.b64encode(raw).decode(), mime, note, self.model)
        response = self.transport(payload)
        content = self._extract_content(response)
        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Muse returned non-JSON content: {exc}") from exc
        return coerce_muse_payload(data, document_ref=document_ref,
                                   source_page=source_page, figure_id=figure_id)

    def disclosure(self) -> str:
        return ("Transmits ONLY the selected figure crop (+ optional note) to Meta Model API "
                f"({self.config.base_url}) as a base64 image for visual understanding; "
                "never the full document. See docs/PRIVACY.md.")
