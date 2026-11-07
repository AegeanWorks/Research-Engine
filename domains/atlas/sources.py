"""Universal source ingestion: link, YouTube, book (EPUB), video, and files.

Every source becomes the same thing: text for the text-knowledge path and/or
images for the visual path — both feeding one validated VisualAnalysis, which
drives canvas, graph, and learning. Stdlib only; no keys needed to ingest.

Honest limits (surfaced as errors, never silent):
- Video frames need a system `ffmpeg`; otherwise Atlas says so explicitly.
- YouTube needs public captions; age-gated/captionless videos refuse clearly.
- Web fetch caps size/time and only accepts textual content.
"""
from __future__ import annotations

import html as _html
import json as _json
import os
import re
import shutil
import subprocess
import urllib.parse
import urllib.request
import zipfile
from html.parser import HTMLParser

FETCH_TIMEOUT_S = 20
MAX_FETCH_BYTES = 3_000_000
MAX_TEXT_CHARS = 12_000


class _TextExtractor(HTMLParser):
    """Collect readable text; drop scripts, styles, nav boilerplate."""

    SKIP = {"script", "style", "noscript", "nav", "footer", "header", "aside"}

    def __init__(self) -> None:
        super().__init__()
        self._skip = 0
        self.chunks: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip += 1
        elif tag in ("p", "br", "h1", "h2", "h3", "h4", "h5", "h6", "li", "title"):
            self.chunks.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip:
            text = data.strip()
            if text:
                self.chunks.append(text + " ")

    def text(self) -> str:
        collapsed = re.sub(r"[ \t]+", " ", "".join(self.chunks))
        collapsed = re.sub(r"\n\s*\n+", "\n\n", collapsed)
        return _html.unescape(collapsed).strip()


def html_to_text(markup: str) -> str:
    parser = _TextExtractor()
    parser.feed(markup)
    return parser.text()


def fetch_url_text(url: str, timeout: int = FETCH_TIMEOUT_S) -> dict:
    """Fetch a web article into {title, text, url}. Textual content only."""
    scheme = urllib.parse.urlparse(url).scheme.lower()
    if scheme not in ("http", "https"):
        raise ValueError(f"only http(s) URLs can be fetched, got {url!r}")
    req = urllib.request.Request(url, headers={"User-Agent": "Atlas/1.0 (+learning)"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        ctype = resp.headers.get("Content-Type", "")
        raw = resp.read(MAX_FETCH_BYTES + 1)
    if len(raw) > MAX_FETCH_BYTES:
        raise ValueError("page exceeds the fetch size cap; narrow to the article URL")
    if "text/plain" in ctype:
        text = raw.decode("utf-8", "replace").strip()
        return {"title": url, "text": text, "url": url}
    if "html" not in ctype and "xml" not in ctype:
        raise ValueError(f"URL has non-textual content ({ctype or 'unknown'})")
    return {"title": url, "text": html_to_text(raw.decode("utf-8", "replace")), "url": url}


YOUTUBE_ID_PATTERNS = [
    r"[?&]v=([\w-]{6,})",
    r"youtu\.be/([\w-]{6,})",
    r"/shorts/([\w-]{6,})",
    r"/embed/([\w-]{6,})",
    r"/live/([\w-]{6,})",
]


def youtube_video_id(url: str) -> str | None:
    for pattern in YOUTUBE_ID_PATTERNS:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def is_youtube_url(url: str) -> bool:
    host = urllib.parse.urlparse(url).netloc.lower()
    return ("youtube.com" in host or "youtu.be" in host
            or "youtube-nocookie.com" in host)


def youtube_transcript(url: str, timeout: int = FETCH_TIMEOUT_S) -> dict:
    """Public captions of a YouTube video via its player response (no API key)."""
    video_id = youtube_video_id(url)
    if not video_id:
        raise ValueError(f"not a recognizable YouTube URL: {url!r}")
    watch = f"https://www.youtube.com/watch?v={video_id}"
    req = urllib.request.Request(watch, headers={"User-Agent": "Atlas/1.0 (+learning)",
                                                  "Accept-Language": "en"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        page = resp.read(MAX_FETCH_BYTES + 1).decode("utf-8", "replace")
    tracks = re.search(r'"captionTracks":\s*(\[.*?\])', page)
    if not tracks:
        raise ValueError("no public captions found (age-gated, captionless, or blocked)")
    try:
        items = _json.loads(tracks.group(1))
    except ValueError as exc:
        raise ValueError(f"could not read caption list: {exc}") from exc
    track = next((t for t in items if t.get("baseUrl") and "en" in str(t.get("languageCode", ""))),
                 next((t for t in items if t.get("baseUrl")), None))
    if track is None:
        raise ValueError("caption list has no downloadable track")
    with urllib.request.urlopen(track["baseUrl"], timeout=timeout) as resp:  # noqa: S310
        timed = resp.read(MAX_FETCH_BYTES + 1).decode("utf-8", "replace")
    texts = re.findall(r"<text[^>]*>(.*?)</text>", timed, re.S)
    if not texts:
        texts = [line for line in timed.splitlines() if line and not line.startswith(("WEBVTT", "NOTE"))]
    clean = _html.unescape(re.sub(r"<[^>]+>", "", "\n".join(texts))).strip()
    if not clean:
        raise ValueError("caption track downloaded but held no text")
    return {"title": f"YouTube {video_id}", "text": clean, "url": watch}


def epub_text(path: str) -> dict:
    """EPUB book → {title, text, chapters} in spine order (XHTML chapters)."""
    if not zipfile.is_zipfile(path):
        raise ValueError(f"not an EPUB file: {path!r}")
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        opf = next((n for n in names if n.endswith(".opf")), None)
        texts: list[str] = []
        title = os.path.basename(path)

        def _attrs(tag: str) -> dict:
            return dict(re.findall(r'''(\w+)\s*=\s*["']([^"']*)["']''', tag))

        if opf:
            root = os.path.dirname(opf)
            manifest = archive.read(opf).decode("utf-8", "replace")
            items = {}
            for tag in re.findall(r"<item\b[^>]*>", manifest):
                a = _attrs(tag)
                if a.get("id") and a.get("href"):
                    items[a["id"]] = a["href"]
            spine = [_attrs(t).get("idref", "") for t in re.findall(r"<itemref\b[^>]*>", manifest)]
            spine = [s for s in spine if s]
            if not spine:
                spine = list(items)
            title_match = re.search(r"<dc:title[^>]*>(.*?)</dc:title>", manifest, re.S)
            if title_match:
                title = _html.unescape(title_match.group(1)).strip()
            for ref in spine:
                href = items.get(ref, "")
                member = (root + "/" + href).lstrip("/") if root else href
                if member in names:
                    texts.append(html_to_text(
                        archive.read(member).decode("utf-8", "replace")))
        else:
            for member in sorted(names):
                if member.endswith((".xhtml", ".html", ".htm")):
                    texts.append(html_to_text(
                        archive.read(member).decode("utf-8", "replace")))
        body = "\n\n".join(t for t in texts if t).strip()
        if not body:
            raise ValueError("EPUB held no readable chapters (DRM or scans?)")
        return {"title": title, "text": body, "url": path, "chapters": len(texts)}


VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov", ".mkv", ".avi", ".m4v"}


def _ffmpeg_exe() -> str:
    """System ffmpeg, else the bundled imageio-ffmpeg binary (pip installable).

    Any broken state (missing provider, raising provider, moved/deleted
    binary) lands on the same designed refusal so callers can name the
    cause and fix instead of blaming the clip.
    """
    found = shutil.which("ffmpeg")
    if found and os.path.isfile(found):
        return found
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as exc:
        raise ValueError("video needs ffmpeg: install it system-wide or "
                         "pip install imageio-ffmpeg (Atlas bundles it as a dependency).") from exc
    if exe and os.path.isfile(exe):
        return exe
    raise ValueError("video needs ffmpeg: install it system-wide or "
                     "pip install imageio-ffmpeg (Atlas bundles it as a dependency).")


def render_pdf_page(path: str, page: int, outdir: str, dpi: int = 150) -> str:
    """PDF page → PNG still (needs optional PyMuPDF: pip install PyMuPDF).

    Medical PDFs are figure-heavy; this is the bridge from a text-only PDF to
    figure selection and visual analysis. Page numbers are 1-based for people.
    """
    try:
        import fitz  # type: ignore[import-not-found]  # optional: rasterizes without system tools
    except ImportError as exc:
        raise ImportError("PDF page rendering needs PyMuPDF (pip install PyMuPDF); "
                          "the PDF text path works without it.") from exc
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    os.makedirs(outdir, exist_ok=True)
    with fitz.open(path) as doc:  # hygiene: allow binary PDF open needs no text encoding
        if not 1 <= page <= doc.page_count:
            raise ValueError(f"page {page} out of range (1..{doc.page_count})")
        pix = doc[page - 1].get_pixmap(dpi=dpi)
        out = os.path.join(outdir, f"page_{page:03d}_{dpi}dpi.png")
        pix.save(out)
    return out


def video_frames(path: str, outdir: str, max_frames: int = 4) -> list[str]:
    """Video → up to max_frames stills (system or bundled imageio-ffmpeg)."""
    ffmpeg = _ffmpeg_exe()
    os.makedirs(outdir, exist_ok=True)
    pattern = os.path.join(outdir, "frame_%02d.png")
    cmd = [ffmpeg, "-y", "-v", "error", "-i", path, "-vf", "fps=1,scale=640:-1",
           "-frames:v", str(max_frames), pattern]
    try:
        subprocess.run(cmd, timeout=120, check=True,  # noqa: S603
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except (subprocess.SubprocessError, OSError) as exc:
        raise ValueError(f"ffmpeg could not read {path!r}: {exc}") from exc
    frames = sorted(f for f in os.listdir(outdir) if f.startswith("frame_") and f.endswith(".png"))
    if not frames:
        raise ValueError(f"ffmpeg extracted no frames from {path!r}")
    return [os.path.join(outdir, f) for f in frames]


def chunk_text(text: str, limit: int = MAX_TEXT_CHARS) -> list[str]:
    """Split long text into ≤limit chunks at paragraph boundaries (books)."""
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks, current = [], ""
    for para in paras:
        if len(current) + len(para) + 2 <= limit:
            current = (current + "\n\n" + para).strip()
        else:
            if current:
                chunks.append(current)
            while len(para) > limit:  # one giant paragraph: hard cut
                chunks.append(para[:limit])
                para = para[limit:]
            current = para
    if current:
        chunks.append(current)
    return chunks or [text[:limit]]


def trim_text(text: str, limit: int = MAX_TEXT_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n\n[truncated: first {limit} chars of the source]"


def ingest_any(source: str) -> dict:
    """Any supported source → normalized bundle with FULL text for the pipeline.

    Nothing is trimmed here: stats and provenance stay truthful. The Muse
    boundary (`analyze_text`) trims to its own window before transmitting.
    """
    if is_youtube_url(source):
        got = youtube_transcript(source)
        return {"kind": "text", "title": got["title"], "text": got["text"],
                "document_ref": got["url"]}
    if source.startswith(("http://", "https://")):
        got = fetch_url_text(source)
        return {"kind": "text", "title": got["title"], "text": got["text"],
                "document_ref": got["url"]}
    if not os.path.isfile(source):
        raise FileNotFoundError(source)
    ext = os.path.splitext(source)[1].lower()
    if ext in (".png", ".jpg", ".jpeg", ".jfif", ".gif", ".webp", ".bmp"):
        return {"kind": "image", "path": source, "document_ref": source}
    if ext == ".epub":
        got = epub_text(source)
        return {"kind": "text", "title": got["title"], "text": got["text"],
                "document_ref": source}
    if ext in VIDEO_EXTENSIONS:
        return {"kind": "video", "path": source, "document_ref": source}
    # pdf/txt/md/docx/pptx/vtt/srt/json fall through to the text backend
    from . import text_backend as _tb
    got = _tb.extract_text(source)
    return {"kind": "text", "title": os.path.basename(source),
            "text": got.text, "document_ref": source}
