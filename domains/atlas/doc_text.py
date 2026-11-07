"""Atlas document-text extraction — fully in-project, no external dependency.

These routines were originally adapted from NeuralDeck's ``document_processor.py``
(PDF/DOCX/PPTX/TXT/transcript dispatch) and are now Atlas-owned: install Atlas,
launch Atlas. Scope is deliberately narrow — plain-text extraction for figure
context and provenance. Audio files raise an informative error (supply a
transcript file instead).
"""
from __future__ import annotations

import io
import json
import os
import re

try:
    import pypdf
except ImportError:
    pypdf = None

try:
    import docx
except ImportError:
    docx = None

try:
    from pptx import Presentation
except ImportError:
    Presentation = None


AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".mp4",
                    ".mkv", ".webm", ".mov"}


def _extract_text_from_pdf_reader(reader, log_callback=None) -> str:
    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception:  # hygiene: allow empty-password probe may fail on real passwords
            pass
    if not reader.pages:
        raise Exception("PDF appears to be empty or corrupted (0 pages found).")
    text_parts: list[str] = []
    empty_pages: list[int] = []
    total_pages = len(reader.pages)
    for i, page in enumerate(reader.pages):
        try:
            extracted = page.extract_text()
            if extracted and extracted.strip():
                text_parts.append(extracted)
                text_parts.append("\n")
            else:
                empty_pages.append(i + 1)
                text_parts.append(f"\n[PAGE {i + 1}: NO TEXT DETECTED - SCANNED?]\n")
                msg = f"Warning: Page {i + 1} yielded no text (likely scanned or image)."
                if log_callback:
                    log_callback(msg)
        except Exception as page_error:
            empty_pages.append(i + 1)
            text_parts.append(f"\n[PAGE {i + 1}: EXTRACTION FAILED]\n")
            if log_callback:
                log_callback(f"Warning: Page {i + 1} failed: {page_error}")
    if len(empty_pages) == total_pages:
        raise Exception(
            f"No text on any of {total_pages} page(s): scanned images or encryption. "
            "Run an OCR tool first (e.g. ocrmypdf), then retry; "
            "figure overlays can still be made by rendering a page to PNG.")
    return "".join(text_parts)


def extract_text_from_pdf(file_path: str, log_callback=None) -> str:
    if pypdf is None:
        raise ImportError("pypdf is required (pip install -r requirements.txt)")
    try:
        with open(file_path, "rb") as fh:
            return _extract_text_from_pdf_reader(pypdf.PdfReader(fh), log_callback)
    except FileNotFoundError:
        raise FileNotFoundError(f"PDF file not found: {file_path}")
    except Exception as e:
        raise Exception(f"Failed to read PDF: {e}")


def extract_text_from_pdf_bytes(data: bytes, log_callback=None) -> str:
    if pypdf is None:
        raise ImportError("pypdf is required (pip install -r requirements.txt)")
    try:
        return _extract_text_from_pdf_reader(pypdf.PdfReader(io.BytesIO(data)), log_callback)
    except Exception as e:
        raise Exception(f"Failed to read PDF bytes: {e}")


def pdf_page_count(file_path: str) -> int:
    if pypdf is None:
        return -1
    try:
        with open(file_path, "rb") as fh:
            return len(pypdf.PdfReader(fh).pages)
    except Exception:
        return -1


def _extract_text_from_docx(file_path: str) -> str:
    if docx is None:
        raise ImportError("python-docx is not installed. Run 'pip install python-docx'.")
    document = docx.Document(file_path)
    return "\n".join(para.text for para in document.paragraphs)


def _extract_text_from_pptx(file_path: str) -> str:
    if Presentation is None:
        raise ImportError("python-pptx is not installed. Run 'pip install python-pptx'.")
    prs = Presentation(file_path)
    text_runs: list[str] = []
    for slide in prs.slides:
        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            for paragraph in shape.text_frame.paragraphs:
                for run in paragraph.runs:
                    text_runs.append(run.text)
    return "\n".join(text_runs)


def _extract_text_from_txt(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8", errors="ignore") as fh:
        return fh.read()


_VTT_TAG = re.compile(r"<[^>]+>")
_VTT_TS = re.compile(r"\d{2}:\d{2}:\d{2}[.,]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[.,]\d{3}.*")


def _extract_text_from_transcript(file_path: str) -> str:
    """Lean VTT/SRT/JSON transcript reader (caption context for figures)."""
    _, ext = os.path.splitext(file_path.lower())
    if ext == ".json":
        with open(file_path, encoding="utf-8", errors="replace") as fh:
            data = json.load(fh)
        return _transcript_json_to_text(data)
    with open(file_path, encoding="utf-8", errors="replace") as fh:
        raw = fh.read()
    lines: list[str] = []
    for line in raw.splitlines():
        s = line.strip()
        if not s or s.upper() == "WEBVTT" or s.isdigit() or _VTT_TS.match(s):
            continue
        lines.append(_VTT_TAG.sub("", s))
    # de-duplicate rolling-caption repeats while preserving order
    seen: set[str] = set()
    out: list[str] = []
    for line in lines:
        if line not in seen:
            seen.add(line)
            out.append(line)
    return "\n".join(out)


def _transcript_json_to_text(data) -> str:
    if isinstance(data, str):
        return data
    if isinstance(data, list):
        parts = []
        for item in data:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                for key in ("text", "caption", "content"):
                    if item.get(key):
                        parts.append(str(item[key]))
                        break
        return "\n".join(parts)
    if isinstance(data, dict):
        for key in ("transcript", "text", "captions"):
            if data.get(key):
                return _transcript_json_to_text(data[key])
    return ""


def extract_text_from_document(file_path: str, log_callback=None) -> str:
    """Dispatch over PDF/DOCX/PPTX/TXT/VTT/SRT/JSON."""
    _, extension = os.path.splitext(file_path.lower())
    if extension == ".pdf":
        return extract_text_from_pdf(file_path, log_callback)
    if extension == ".docx":
        if log_callback:
            log_callback("Extracting text from DOCX file...")
        return _extract_text_from_docx(file_path)
    if extension == ".pptx":
        if log_callback:
            log_callback("Extracting text from PPTX file...")
        return _extract_text_from_pptx(file_path)
    if extension == ".txt":
        if log_callback:
            log_callback("Extracting text from TXT file...")
        return _extract_text_from_txt(file_path)
    if extension in (".vtt", ".srt", ".json"):
        return _extract_text_from_transcript(file_path)
    if extension in AUDIO_EXTENSIONS:
        raise ValueError(
            "Audio/video transcription needs a speech-to-text engine and is not bundled "
            "with Atlas. Provide a VTT/SRT/JSON transcript file instead.")
    raise ValueError(
        f"Unsupported file type: {extension}. Use PDF, DOCX, PPTX, TXT, VTT, SRT or JSON.")
