"""Documentation and project memory stay discoverable and within budget."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class DocsTests(unittest.TestCase):
    def test_readme_has_the_cold_start_contract(self) -> None:
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertLess(len(text), 22_500)
        for heading in (
            "30-Second Cold-Start Quick Reference",
            "Runtime Prerequisites",
            "Canonical Regression Shield Gate",
            "AIKit Commands",
            "Data Model",
            "Non-Negotiables",
            "License",
        ):
            self.assertIn(heading, text)

    def test_architecture_and_mechanics_documents_exist(self) -> None:
        architecture = (ROOT / "docs" / "ARCHITECTURE.md").read_text(encoding="utf-8")
        mechanics = (ROOT / "docs" / "MECHANICS.md").read_text(encoding="utf-8")
        self.assertIn("Invariants", architecture)
        self.assertIn("Reproducibility", architecture)
        for name in ("lattice", "fluid-universe", "obezite-mekanizma-projesi", "PNN"):
            self.assertIn(name, mechanics)

    def test_project_memory_declares_the_test_command(self) -> None:
        payload = json.loads((ROOT / ".aikit" / "project.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["test_command"], "python -m unittest discover -s tests -t .")
        self.assertIn("aikit", payload["topics"])

    def test_readme_tree_names_real_modules(self) -> None:
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        for module in (
            "database.py",
            "claims.py",
            "killtests.py",
            "cascade.py",
            "integrity.py",
            "manifest.py",
            "provenance.py",
            "events.py",
            "maintenance.py",
            "markdown.py",
            "screening.py",
            "observations.py",
            "stats.py",
        ):
            self.assertIn(module, text)
            self.assertTrue((ROOT / "engine" / module).exists())

    def test_readme_documents_the_current_schema_and_gates(self) -> None:
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("schema version 10", text)
        for code in ("EVID-005", "EVID-006", "EVID-008", "EVID-009", "PROV-003", "SCREEN-001",
                     "TEST-001", "OBS-001"):
            self.assertIn(code, text)
        self.assertIn("--group", text)
        self.assertIn("--strict", text)
        self.assertIn("--control", text)
        self.assertIn("source screen", text)
        self.assertIn("db backup", text)
        self.assertIn("events", text)
        self.assertIn("observation add", text)
        self.assertIn("analysis stats", text)
        self.assertIn("analysis trend", text)

    def test_architecture_documents_binding_and_digests(self) -> None:
        text = (ROOT / "docs" / "ARCHITECTURE.md").read_text(encoding="utf-8")
        for heading in ("Evidence Binding", "Schema Versions", "Generated Reports", "Promotion"):
            self.assertIn(heading, text)
        self.assertIn("content_sha256", text)
        self.assertIn("graph_sha256", text)


if __name__ == "__main__":
    unittest.main()
