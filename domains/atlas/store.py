"""Atomic JSON persistence for Atlas-only data.

Layout under <data_dir>/:
  documents/  ingested originals (copies)
  figures/    figure crops
  analyses/   <figure_id>.analysis.json (model output, versioned)
  masks/      segmentation artifacts referenced by mask_ref
  corrections/corrections.json  user corrections, separate from model output
  cache/cache.json              content-hash keyed model/SAM results

Writes use temp + fsync + os.replace; user corrections never mutate analyses.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile


def _atomic_write_json(path: str, obj) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(os.path.abspath(path)),
                               prefix=".tmp_atlas_", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(obj, fh, indent=2, sort_keys=True)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:  # hygiene: allow best-effort temp cleanup after atomic replace
                pass


def _read_json(path: str, default, tolerant: bool = False):
    if not os.path.isfile(path):
        return default
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        # Tolerant reads are ONLY for recomputable state (cache): a torn
        # file degrades to a miss + recompute instead of 500ing the app.
        # Model truth (analyses) and user data (corrections) must fail
        # loudly rather than silently substitute — never pass tolerant=True.
        if tolerant:
            return default
        raise


class AtlasStore:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        for sub in ("documents", "figures", "analyses", "masks", "corrections", "cache"):
            os.makedirs(os.path.join(data_dir, sub), exist_ok=True)

    # -- analyses ---------------------------------------------------------
    def analysis_path(self, figure_id: str) -> str:
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in figure_id) or "figure"
        return os.path.join(self.data_dir, "analyses", f"{safe}.analysis.json")

    def save_analysis(self, figure_id: str, analysis: dict) -> str:
        path = self.analysis_path(figure_id)
        _atomic_write_json(path, analysis)
        return path

    def load_analysis(self, figure_id: str) -> dict | None:
        return _read_json(self.analysis_path(figure_id), None)

    # -- corrections (kept separate) --------------------------------------
    def corrections_path(self) -> str:
        return os.path.join(self.data_dir, "corrections", "corrections.json")

    def add_correction(self, entry: dict) -> list[dict]:
        path = self.corrections_path()
        items = _read_json(path, [])
        items.append(entry)
        _atomic_write_json(path, items)
        return items

    def load_corrections(self) -> list[dict]:
        return _read_json(self.corrections_path(), [])

    # -- cache -------------------------------------------------------------
    def cache_path(self) -> str:
        return os.path.join(self.data_dir, "cache", "cache.json")

    @staticmethod
    def cache_key(*parts: str) -> str:
        h = hashlib.sha256()
        for p in parts:
            b = str(p).encode()
            h.update(len(b).to_bytes(8, "big") + b"\0" + b)
        return h.hexdigest()[:32]

    def cache_get(self, key: str):
        return _read_json(self.cache_path(), {}, tolerant=True).get(key)

    def cache_put(self, key: str, value) -> None:
        path = self.cache_path()
        data = _read_json(path, {}, tolerant=True)
        data[key] = value
        _atomic_write_json(path, data)
