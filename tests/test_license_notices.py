"""Ported packages keep their source notice, SHA and license text."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOTICES = {
    "adapters/lattice/NOTICE.md": "d3f0502b99983f1436fe9466f5553935ea7be868",
    "studio/NOTICE.md": "d3f0502b99983f1436fe9466f5553935ea7be868",
    "domains/pnn/NOTICE.md": "3b6e6c277552dcb2c3604483de1277307bc18c4d",
    "domains/fluid_universe/NOTICE.md": "7b4efe141dfbcc267b0efceb82247f5004186c06",
    "domains/obezite/NOTICE.md": "18b5d4d8e2196384f4e960f01b3031beb0a6315a",
    "domains/atlas/NOTICE.md": "f3cd7470e99683bc95b05f49e404bb00bffa2663",
}


class LicenseNoticeTests(unittest.TestCase):
    def test_every_ported_package_has_a_notice_with_its_pin(self) -> None:
        for relative, sha in NOTICES.items():
            path = ROOT / relative
            self.assertTrue(path.is_file(), relative)
            text = path.read_text(encoding="utf-8")
            self.assertIn(sha, text, relative)
            self.assertIn("License", text, relative)

    def test_al_and_asl_license_texts_are_present(self) -> None:
        self.assertTrue((ROOT / "LICENSES" / "LicenseRef-AL-1.1.txt").is_file())
        self.assertTrue((ROOT / "LICENSES" / "LicenseRef-ASL-1.1.txt").is_file())
        reuse = (ROOT / "REUSE.toml").read_text(encoding="utf-8")
        self.assertIn("LicenseRef-ASL-1.1", reuse)
