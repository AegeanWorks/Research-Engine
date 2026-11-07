"""Artifact I/O: timestamps, output digests and atomic file replacement."""

from __future__ import annotations

import contextlib
import hashlib
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from engine.errors import EngineError


def utc_now() -> str:
    """Return a second-resolution UTC timestamp in ISO-8601 form."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def digest(kind: str, payload: str | bytes) -> str:
    """Domain-separated digest: the artifact kind is hashed before the payload.

    Two artifacts with identical bytes still get different digests when their kinds differ, so a
    report digest can never be mistaken for a graph digest.
    """
    data = payload.encode("utf-8") if isinstance(payload, str) else payload
    hasher = hashlib.sha256()
    hasher.update(kind.encode("utf-8"))
    hasher.update(b"\n")
    hasher.update(data)
    return hasher.hexdigest()


def sha256_text(value: str) -> str:
    """Hash extracted output so reproducibility is checked without storing it all."""
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()


def digest_tree(
    root: Path | str,
    suffixes: tuple = (),
    excluded_dirs: tuple = (".git", "__pycache__", ".pytest_cache", "node_modules"),
) -> dict:
    """Stream a directory into one path-and-content digest.

    The digest covers relative POSIX paths and file bytes in sorted order, so a renamed file
    changes it even when the bytes are identical. This is the reference form used for external
    data roots that must not be copied into the host.
    """
    base = Path(root)
    if not base.is_dir():
        raise EngineError(
            f"not a directory: {base}",
            "an external data root is a directory of files to fingerprint.",
            "pass an existing directory.",
        )
    digest = hashlib.sha256()
    files = 0
    total = 0
    allowed = tuple(suffix.lower() for suffix in suffixes)
    for path in sorted(base.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(base)
        if any(part in excluded_dirs for part in relative.parts):
            continue
        if allowed and path.suffix.lower() not in allowed:
            continue
        digest.update(relative.as_posix().encode("utf-8"))
        digest.update(b"\0")
        size = 0
        # hygiene: allow binary streaming read; text encoding does not apply
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
                size += len(chunk)
        digest.update(b"\0")
        files += 1
        total += size
    if files == 0:
        raise EngineError(
            f"no matching files under {base}",
            "an empty manifest would hide missing evidence.",
            "check the suffix filter and the data root.",
        )
    return {"sha256": digest.hexdigest(), "files": files, "bytes": total}


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
