"""Atlas configuration. Environment-based, no credentials in code or logs.

Meta Model API (verified 2026-11-01 from https://dev.meta.ai/docs/overview):
  Base URL: https://api.meta.ai/v1
  Auth: Bearer $MODEL_API_KEY (also accepted as $META_API_KEY)
  Muse Spark models: muse-spark-1.3, muse-spark-1.2, muse-spark-1.1
    Contributor mode: muse-spark-1.3-contributor, muse-spark-1.2-contributor
  Muse Wonder (complex reasoning): muse-wonder-1.0
  SAM 3.1 (segmentation): sam-3.1 via POST /v1/responses (+ POST /v1/files)
  Context window (Spark/Wonder): 1,048,576 tokens.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field


META_BASE_URL = "https://api.meta.ai/v1"
DEFAULT_MUSE_MODEL = "muse-spark-1.3"
DEFAULT_WONDER_MODEL = "muse-wonder-1.0"
DEFAULT_SAM_MODEL = "sam-3.1"


def _env(*names: str, default: str = "") -> str:
    for n in names:
        v = os.environ.get(n, "")
        if v:
            return v
    return default


@dataclass(frozen=True)
class AtlasConfig:
    """Resolved entirely from environment + explicit overrides."""

    api_key: str = field(default="")
    base_url: str = field(default=META_BASE_URL)
    muse_model: str = field(default=DEFAULT_MUSE_MODEL)
    wonder_model: str = field(default=DEFAULT_WONDER_MODEL)
    sam_model: str = field(default=DEFAULT_SAM_MODEL)
    timeout_s: float = field(default=60.0)
    max_retries: int = field(default=3)
    data_dir: str = field(default="data")

    @classmethod
    def from_env(cls, **overrides) -> "AtlasConfig":
        raw_timeout = os.environ.get("ATLAS_TIMEOUT_S", "")
        try:
            timeout = float(raw_timeout) if raw_timeout else 60.0
        except ValueError:
            timeout = 60.0
        raw_retries = os.environ.get("ATLAS_MAX_RETRIES", "")
        try:
            retries = int(raw_retries) if raw_retries else 3
        except ValueError:
            retries = 3
        return cls(
            api_key=overrides.get("api_key", _env("MODEL_API_KEY", "META_API_KEY")),
            base_url=overrides.get("base_url", os.environ.get("ATLAS_BASE_URL", META_BASE_URL)),
            muse_model=overrides.get("muse_model", os.environ.get("ATLAS_MUSE_MODEL", DEFAULT_MUSE_MODEL)),
            wonder_model=overrides.get("wonder_model", os.environ.get("ATLAS_WONDER_MODEL", DEFAULT_WONDER_MODEL)),
            sam_model=overrides.get("sam_model", os.environ.get("ATLAS_SAM_MODEL", DEFAULT_SAM_MODEL)),
            timeout_s=overrides.get("timeout_s", timeout),
            max_retries=overrides.get("max_retries", retries),
            data_dir=overrides.get("data_dir", os.environ.get("ATLAS_DATA_DIR", "data")),
        )

    @property
    def has_api_key(self) -> bool:
        return bool(self.api_key)

    def redacted(self) -> dict:
        """Safe for logs: never includes the key."""
        return {
            "base_url": self.base_url,
            "muse_model": self.muse_model,
            "wonder_model": self.wonder_model,
            "sam_model": self.sam_model,
            "timeout_s": self.timeout_s,
            "max_retries": self.max_retries,
            "data_dir": self.data_dir,
            "has_api_key": self.has_api_key,
        }
