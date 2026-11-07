"""SAM 3.1 segmentation integration.

Verified against https://dev.meta.ai/docs/media-segmentation + overview (2026-11-01):
- Model id: sam-3.1, via POST {base}/v1/responses (streamed) with
  input: [{type:message, role:user, content:[{type:input_text,text:<noun phrase>},
  {type:input_image, image_url:<url|data-url|file_id>}]}]
- Output: special-token text carrying one box + pixel mask per match; parse via
  client libraries (see docs/sam/reading-segmentation). This adapter parses the
  box portion when present and always records provenance + fallback state.

Contract:
- Muse identifies the entity -> this adapter sends the ORIGINAL crop + a short
  noun phrase -> SAM returns mask(s) -> Atlas overlays on the original image.
- Never confuse boxes with masks: results carry kind="mask" only when a mask
  payload decoded; otherwise kind="bbox-fallback" with the Muse box.
- Empirical (2026-11-01, live): sam-3.1 via POST /v1/responses returns status
  completed with EMPTY output_text for the documented noun-phrase shape, so
  live calls honestly land on bbox-fallback with a sized note; the adapter
  still scans raw output for localizable boxes/file ids first.
"""
from __future__ import annotations

import base64
import json
import time
import urllib.request
import urllib.error
from dataclasses import dataclass

from .config import AtlasConfig
from .schema import BoundingBox


@dataclass(frozen=True)
class Segmentation:
    entity_id: str
    kind: str  # "mask" | "bbox-fallback"
    bbox: BoundingBox | None
    mask_ref: str  # path or file_id when kind == "mask"
    raw_note: str = ""


class SamProvider:
    def __init__(self, config: AtlasConfig | None = None, transport=None):
        self.config = config or AtlasConfig.from_env()
        self._live_transport = transport is None
        self.transport = transport or self._http_post

    def _http_post(self, payload: dict) -> dict:
        body = json.dumps(payload).encode()
        last: Exception | None = None
        for attempt in range(max(1, self.config.max_retries)):
            req = urllib.request.Request(
                self.config.base_url.rstrip("/") + "/responses",
                data=body, headers={"Content-Type": "application/json"},
            )
            if self.config.api_key:
                req.add_header("Authorization", f"Bearer {self.config.api_key}")
            try:
                with urllib.request.urlopen(req, timeout=self.config.timeout_s) as resp:  # noqa: S310
                    text = resp.read().decode("utf-8", "replace")
                return {"raw": text}
            except urllib.error.HTTPError as exc:
                if 400 <= exc.code < 500:
                    raise RuntimeError(f"SAM request refused: HTTP {exc.code}: {exc.reason}") from exc
                last = exc
                time.sleep(min(2.0 ** attempt, 8.0))
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                last = exc
                time.sleep(min(2.0 ** attempt, 8.0))
        raise RuntimeError(f"SAM request failed after retries: {type(last).__name__}: {last}")

    def segment(self, image_path: str, prompt: str, entity_id: str,
                fallback_box: BoundingBox | None = None) -> Segmentation:
        """Segment one entity. Short noun phrase required (e.g. 'striatum')."""
        if not prompt or len(prompt.split()) > 8:
            raise ValueError("SAM prompt must be a short noun phrase naming one object")
        if not self.config.has_api_key and self._live_transport:
            raise RuntimeError("MODEL_API_KEY/META_API_KEY is not set; refusing live call")
        with open(image_path, "rb") as fh:
            raw = fh.read()
        if len(raw) > 45_000_000:
            raise ValueError("image exceeds the 50 MB inline limit; downscale first.")
        import os as _os
        _mime = {".png": "image/png", ".jpg": "image/jpeg",
                 ".jpeg": "image/jpeg", ".jfif": "image/jpeg",
                 ".gif": "image/gif", ".webp": "image/webp",
                 ".bmp": "image/bmp"}.get(_os.path.splitext(image_path)[1].lower(), "image/png")
        b64 = base64.b64encode(raw).decode()
        payload = {
            "model": self.config.sam_model,
            "input": [{"type": "message", "role": "user", "content": [
                {"type": "input_text", "text": prompt.strip()},
                {"type": "input_image", "image_url": f"data:{_mime};base64,{b64}"},
            ]}],
        }
        result = self.transport(payload)
        mask_ref = str(result.get("mask_ref", "") or result.get("file_id", ""))
        box = result.get("box")
        note = str(result.get("raw_note", ""))
        if box is None and not mask_ref:
            # Live sam-3.1 answers carry no mask_ref/box keys; scan the raw
            # payload for anything localizable before admitting fallback.
            raw = result.get("raw", "")
            box = _scan_box(raw)
            if not mask_ref:
                mask_ref = _scan_file_id(raw)
            if not note and raw:
                note = (f"sam-3.1 returned no localizable output "
                        f"({len(raw)} chars); bbox fallback")
        bbox = None
        if box:
            try:
                bbox = BoundingBox.from_grid1000([float(v) for v in box])
            except (ValueError, TypeError):
                bbox = fallback_box
        else:
            bbox = fallback_box
        if mask_ref:
            return Segmentation(entity_id, "mask", bbox, mask_ref, "sam-3.1 mask")
        return Segmentation(entity_id, "bbox-fallback", bbox, "", note or "bbox fallback; no mask decoded")

    def disclosure(self) -> str:
        return ("Transmits ONLY the selected figure crop + a short noun phrase to Meta "
                f"Model API SAM 3.1 ({self.config.base_url}/responses); never the full document.")


def _scan_box(raw: str) -> list | None:
    """Best-effort: first [x1,y1,x2,y2] int quad inside the 0..1000 grid."""
    import re
    if not isinstance(raw, str):
        return None
    for match in re.finditer(r"\[\s*(\d{1,4})\s*,\s*(\d{1,4})\s*,\s*(\d{1,4})\s*,\s*(\d{1,4})\s*\]", raw):
        vals = [float(g) for g in match.groups()]
        if all(0 <= v <= 1000 for v in vals) and vals[0] < vals[2] and vals[1] < vals[3]:
            return vals
    return None


def _scan_file_id(raw: str) -> str:
    import re
    if not isinstance(raw, str):
        return ""
    match = re.search(r"file[-_ ]?(?:id)?['\"]?\s*[:=]\s*['\"]?([A-Za-z0-9_-]{8,})", raw)
    return match.group(1) if match else ""
