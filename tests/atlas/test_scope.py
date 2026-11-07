"""Scope guard: Atlas is learning material, easy drag-and-drop (not figures-only).

Correction atlas_scope: everything provided is learning material.
The hero/tagline must say learning material; figures are one format among many.
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_readme_hero_is_learning_material():
    readme = _read("domains/atlas/README.md")
    assert "learning material" in readme.lower()
    # Hero tagline itself must not be figures-only.
    hero = [ln for ln in readme.splitlines() if "interactive visual knowledge platform" in ln]
    assert hero, "hero tagline missing"
    assert "learning material" in hero[0].lower()
    assert "scientific figures." not in hero[0]


def test_readme_documents_drag_and_drop():
    readme = _read("domains/atlas/README.md")
    assert "drop zone" in readme.lower()
    assert "drop anything" in readme.lower()


def test_package_docstring_is_learning_material():
    init = _read("domains/atlas/__init__.py")
    assert "learning material" in init.lower()
    assert "scientific figures" not in init


def test_workspace_sub_is_learning_material():
    index = _read("domains/atlas/static/index.html")
    assert "learning material" in index.lower()
