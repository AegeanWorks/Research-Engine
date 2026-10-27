"""Artifact I/O: timestamps, output digests and atomic file replacement."""

from __future__ import annotations

import contextlib
import hashlib
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def utc_now() -> str:
    """Return a second-resolution UTC timestamp in ISO-8601 form."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_text(value: str) -> str:
    """Hash extracted output so reproducibility is checked without storing it all."""
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()


def atomic_write_text(path: Path, text: str) -> None:
    """Write UTF-8 text through a flushed temp file and an atomic replace."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.tmp_", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp_name)
        raise
