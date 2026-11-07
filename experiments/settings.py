"""Analysis settings for N1 experiments, mirroring the source SettingsManager."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Optional

DEFAULTS = {
    "min_baseline_days": 7,
    "min_intervention_days": 7,
    "min_data_points": 3,
    "max_safe_metrics": 3,
}


class SettingsManager:
    """Load, save and expose the four analysis thresholds."""

    def __init__(self, settings_file: Path | str | None = None) -> None:
        self.settings_file = Path(settings_file) if settings_file is not None else None
        self.defaults = dict(DEFAULTS)
        self.settings = self.load_settings()

    def load_settings(self) -> dict:
        self.settings = dict(self.defaults)
        if self.settings_file is None or not self.settings_file.is_file():
            return dict(self.settings)
        try:
            payload = json.loads(self.settings_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return dict(self.settings)
        if isinstance(payload, dict):
            for key in self.defaults:
                if key in payload:
                    self.settings[key] = payload[key]
        return dict(self.settings)

    def save_settings(self) -> bool:
        if self.settings_file is None:
            return False
        target = self.settings_file
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(
            dir=target.parent, prefix=f".{target.name}.", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
                json.dump(self.settings, handle, indent=4)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, target)
        except OSError:
            if os.path.exists(temporary):
                os.unlink(temporary)
            return False
        return True

    def get(self, key: str, default: Any = None) -> Any:
        return self.settings.get(key, default)

    def set(self, key: str, value: Any) -> None:
        if key in self.defaults:
            self.settings[key] = value
