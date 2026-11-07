"""Every directory under projects/ is named in the project scan."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECTS = ROOT.parent
SCAN = ROOT / "docs" / "merge" / "PROJECTS-SCAN.md"


class ProjectsScanCoverageTests(unittest.TestCase):
    def test_every_top_level_and_archived_project_is_listed(self) -> None:
        text = SCAN.read_text(encoding="utf-8")
        expected = {
            path.name
            for path in PROJECTS.iterdir()
            if path.is_dir()
            and not path.name.startswith(".")
            and "baseline" not in path.name.lower()
        }
        archived = {
            f"archive/{path.name}"
            for path in (PROJECTS / "archive").iterdir()
            if path.is_dir() and "baseline" not in path.name.lower()
        }
        missing = sorted(
            name for name in expected | archived
            if f"`{name}`" not in text
        )
        self.assertEqual(missing, [])
