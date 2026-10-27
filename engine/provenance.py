"""Workspace provenance: the code and input identity a test run or report is bound to."""

from __future__ import annotations

import glob
import hashlib
import platform
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

from engine import __version__
from engine.errors import EngineError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENGINE_DIR = PROJECT_ROOT / "engine"
GIT_TIMEOUT = 5
KIND_FILE = b"file"
KIND_MISSING = b"missing"


@dataclass(frozen=True)
class Fingerprint:
    """Identity of the engine code and the declared inputs."""

    code_sha256: str
    inputs_sha256: str
    code_files: int
    input_files: int

    def to_dict(self) -> dict:
        return {
            "code_sha256": self.code_sha256,
            "inputs_sha256": self.inputs_sha256,
            "code_files": self.code_files,
            "input_files": self.input_files,
        }


def _digest(entries: Iterable[Tuple[str, bytes, bytes]]) -> str:
    """Hash `(name, kind, content)` triples with length prefixes.

    Length prefixes make the encoding injective: a file whose content happens to be the word
    `missing` cannot collide with an absent file, because the kind tag and the lengths are
    hashed as separate fields.
    """
    hasher = hashlib.sha256()
    for name, kind, content in entries:
        encoded = name.encode("utf-8")
        hasher.update(len(encoded).to_bytes(8, "big"))
        hasher.update(encoded)
        hasher.update(len(kind).to_bytes(1, "big"))
        hasher.update(kind)
        hasher.update(len(content).to_bytes(8, "big"))
        hasher.update(content)
    return hasher.hexdigest()


def code_sha256() -> Tuple[str, int]:
    """Hash the engine package; the test harness and prose are deliberately excluded."""
    files = sorted(ENGINE_DIR.rglob("*.py"))
    digest = _digest(
        (path.relative_to(PROJECT_ROOT).as_posix(), KIND_FILE, path.read_bytes())
        for path in files
    )
    return digest, len(files)


def _inside(path: Path) -> bool:
    try:
        path.resolve().relative_to(PROJECT_ROOT)
        return True
    except ValueError:
        return False


def _name_for(path: Path, raw: str) -> str:
    """A stable name: project-relative when possible, otherwise the raw declaration."""
    return path.relative_to(PROJECT_ROOT).as_posix() if _inside(path) else raw


def _expand(raw: str) -> List[str]:
    """Expand one declaration into canonical names, deterministically.

    A declaration that matches nothing stays as written, so creating the file later changes the
    digest instead of being invisible. A directory is refused: hashing a directory would record
    an empty content and silently ignore everything inside it.
    """
    text = str(raw).strip()
    if not text:
        return []
    path = Path(text)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    matches = sorted(glob.glob(str(path), recursive=True))
    if not matches:
        return [text]
    names = []
    for match in matches:
        candidate = Path(match)
        if candidate.is_dir():
            raise EngineError(
                f"declared input is a directory: {match}",
                "a directory has no stable content, so binding it would hash nothing and hide"
                " every file inside it.",
                "declare the files with a glob such as `--input data/*.csv`, or declare each file.",
            )
        names.append(_name_for(candidate, match))
    return names


def resolve_inputs(paths: Sequence[str]) -> Tuple[str, ...]:
    """Canonical, sorted, de-duplicated input names for a declaration list."""
    names = {name for raw in paths for name in _expand(raw)}
    return tuple(sorted(names))


def inputs_sha256(paths: Sequence[str]) -> Tuple[str, int]:
    """Hash declared inputs; an absent declaration hashes as a distinct typed marker."""
    entries = []
    for name in resolve_inputs(paths):
        path = Path(name)
        if not path.is_absolute():
            path = PROJECT_ROOT / name
        if path.is_dir():
            raise EngineError(
                f"declared input is a directory: {name}",
                "a directory has no stable content to bind.",
                "declare files or a glob pattern instead.",
            )
        if path.is_file():
            entries.append((name, KIND_FILE, path.read_bytes()))
        else:
            entries.append((name, KIND_MISSING, b""))
    return _digest(entries), len(entries)


def fingerprint(inputs: Sequence[str] = ()) -> Fingerprint:
    """Compute the current code and input fingerprint."""
    code, code_files = code_sha256()
    declared, input_files = inputs_sha256(inputs)
    return Fingerprint(code, declared, code_files, input_files)


def git_state() -> Tuple[str, bool]:
    """Return `(commit, dirty)`; a missing repository reports `no-git` and dirty."""
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=str(PROJECT_ROOT),
            text=True,
            timeout=GIT_TIMEOUT,
            stderr=subprocess.DEVNULL,
        ).strip()
        status = subprocess.check_output(
            ["git", "status", "--porcelain"],
            cwd=str(PROJECT_ROOT),
            text=True,
            timeout=GIT_TIMEOUT,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.SubprocessError):
        return "no-git", True
    return commit or "no-git", bool(status)


def environment() -> dict:
    """Runtime identity recorded for diagnosis, not used for binding."""
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "engine": __version__,
    }


def provenance(inputs: Sequence[str] = ()) -> dict:
    """One block combining binding data with diagnostic metadata."""
    current = fingerprint(inputs)
    commit, dirty = git_state()
    return {
        **current.to_dict(),
        "git_commit": commit,
        "git_dirty": dirty,
        **environment(),
    }
