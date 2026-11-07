"""Domain packs stay isolated: no pack imports another pack or a studio surface."""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKS = ("pnn", "fluid_universe", "obezite", "atlas")
FORBIDDEN = ("studio", "adapters", "experiments")


def _imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.append(node.module)
    return names


class DomainIsolationTests(unittest.TestCase):
    def test_no_pack_imports_another_pack(self) -> None:
        violations = []
        for pack in PACKS:
            base = ROOT / "domains" / pack
            for path in base.rglob("*.py"):
                for module in _imports(path):
                    if module.startswith("domains."):
                        owner = module.split(".")[1]
                        if owner != pack:
                            violations.append(f"{path.relative_to(ROOT)} -> {module}")
        self.assertEqual(violations, [])

    def test_no_pack_imports_a_surface_or_adapter(self) -> None:
        violations = []
        for pack in PACKS:
            base = ROOT / "domains" / pack
            for path in base.rglob("*.py"):
                for module in _imports(path):
                    if module.split(".")[0] in FORBIDDEN:
                        violations.append(f"{path.relative_to(ROOT)} -> {module}")
        self.assertEqual(violations, [])

    def test_engine_does_not_import_a_pack_or_surface(self) -> None:
        violations = []
        for path in (ROOT / "engine").rglob("*.py"):
            for module in _imports(path):
                if module.split(".")[0] in ("domains", "studio", "adapters"):
                    violations.append(f"{path.relative_to(ROOT)} -> {module}")
        self.assertEqual(violations, [])
