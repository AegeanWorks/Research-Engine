"""Small reproducibility helpers: git state, versions, config hashes."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = PROJECT_ROOT / "results"


def git_state() -> dict[str, Any]:
    def run(*args: str) -> str:
        try:
            return subprocess.check_output(
                ["git", *args],
                cwd=PROJECT_ROOT,
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=10,
            ).strip()
        except Exception:
            return ""

    commit = run("rev-parse", "HEAD") or "no-git"
    status = run("status", "--porcelain")
    return {"commit": commit, "dirty": bool(status)}


def package_versions() -> dict[str, str]:
    versions: dict[str, str] = {"python": sys.version.split()[0], "platform": platform.platform()}
    for name in ("numpy", "scipy", "sympy", "pytest", "hypothesis"):
        try:
            mod = __import__(name)
            versions[name] = getattr(mod, "__version__", "unknown")
        except Exception:
            versions[name] = "not installed"
    return versions


def config_hash(payload: dict[str, Any]) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def metadata(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "config": config,
        "config_sha256": config_hash(config),
        "git": git_state(),
        "packages": package_versions(),
    }


def write_text_atomic(path: Path, text: str) -> None:
    """Write a generated file atomically (temp file + fsync + replace)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    write_text_atomic(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")
