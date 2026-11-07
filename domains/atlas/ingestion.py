"""Atlas document + figure ingestion.

Supports PDF / PNG / JPEG. Manual figure selection (crop box) is the guaranteed
MVP path; automatic figure detection is a stubbed P1 hook. Every artifact keeps
document provenance: source path, page, crop box, image size, analysis version.
"""
from __future__ import annotations

import hashlib
import mimetypes
import os
import shutil
from dataclasses import dataclass, asdict

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None


SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".jfif", ".gif",
                            ".webp", ".bmp",
                            ".epub", ".txt", ".md",
                            ".docx", ".pptx", ".vtt", ".srt", ".json",
                            ".mp4", ".webm", ".mov", ".mkv", ".avi", ".m4v"}


@dataclass(frozen=True)
class FigureCrop:
    document_ref: str
    source_page: int
    crop_rel: tuple[float, float, float, float]  # normalized x_min,y_min,x_max,y_max
    image_path: str
    image_width: int
    image_height: int
    sha256: str

    def to_dict(self) -> dict:
        d = asdict(self)
        d["crop_rel"] = list(self.crop_rel)
        return d


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _check_ext(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"unsupported file type {ext!r}; use PDF, PNG, JPEG, EPUB, TXT, MD, "
            "DOCX, PPTX, MP4/WebM/MOV, or a VTT/SRT transcript")
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    return ext


def import_document(source_path: str, data_dir: str, source_page: int = 0) -> dict:
    """Copy the original into Atlas storage and record provenance (never mutates source)."""
    _check_ext(source_path)
    os.makedirs(os.path.join(data_dir, "documents"), exist_ok=True)
    digest = _sha256_file(source_path)[:16]
    dest = os.path.join(data_dir, "documents", f"{digest}_{os.path.basename(source_path)}")
    if not os.path.isfile(dest):
        shutil.copyfile(source_path, dest)
    mime, _ = mimetypes.guess_type(source_path)
    return {
        "document_ref": dest,
        "original_name": os.path.basename(source_path),
        "sha256": _sha256_file(source_path),
        "mime": mime or "application/octet-stream",
        "source_page": source_page,
    }


def _validate_crop(crop: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    x0, y0, x1, y1 = (float(v) for v in crop)
    for v in (x0, y0, x1, y1):
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"crop coordinates must be normalized 0..1, got {crop!r}")
    if not (x0 < x1 and y0 < y1):
        raise ValueError(f"empty/inverted crop {crop!r}")
    return (x0, y0, x1, y1)


def select_figure(image_path: str, crop_rel: tuple[float, float, float, float],
                  data_dir: str, document_ref: str = "",
                  source_page: int = 0) -> FigureCrop:
    """Manual figure selection: crop an image region, preserve original + coordinates."""
    if Image is None:
        raise ImportError("Pillow is required (pip install -r requirements.txt)")
    if not os.path.isfile(image_path):
        raise FileNotFoundError(image_path)
    if os.path.splitext(image_path)[1].lower() not in (
            ".png", ".jpg", ".jpeg", ".jfif", ".gif", ".webp", ".bmp"):
        raise ValueError(
            f"figure selection needs a rendered image, got {image_path!r}. "
            "For PDFs: render the page first (POST /api/pdf/render), then select.")
    crop = _validate_crop(crop_rel)
    with Image.open(image_path) as im:  # hygiene: allow binary image open needs no text encoding
        im = im.convert("RGB")
        w, h = im.size
        px = (int(crop[0] * w), int(crop[1] * h), int(crop[2] * w), int(crop[3] * h))
        region = im.crop(px)
        os.makedirs(os.path.join(data_dir, "figures"), exist_ok=True)
        digest = hashlib.sha256(f"{image_path}{crop}{w}x{h}".encode()).hexdigest()[:16]
        out = os.path.join(data_dir, "figures", f"fig_{digest}.png")
        region.save(out, format="PNG")
        rw, rh = region.size
    return FigureCrop(document_ref=document_ref or image_path, source_page=source_page,
                      crop_rel=crop, image_path=out, image_width=rw,
                      image_height=rh, sha256=_sha256_file(out))


def detect_figures(_image_path: str) -> list[dict]:
    """P1 hook: automatic figure detection. MVP raises explicitly instead of guessing."""
    _ = _image_path  # explicitly unused: manual select_figure() is the MVP path
    raise NotImplementedError("automatic figure detection is P1; use select_figure()")
