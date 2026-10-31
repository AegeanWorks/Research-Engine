"""Markdown-safe rendering of untrusted text.

Claim text, quotes and locators are user input. Rendering them raw into a Markdown table breaks the
row, and rendering them raw into a heading lets the text inject structure. Every generated document
therefore passes user text through these helpers.
"""

from __future__ import annotations

import unicodedata

# Control, format, surrogate, private-use and line/paragraph separators have no place in a cell.
_BLOCKED = frozenset({"Cc", "Cf", "Cs", "Co", "Cn", "Zl", "Zp"})
DEFAULT_WIDTH = 160


def sanitize(text: object, width: int = DEFAULT_WIDTH) -> str:
    """Collapse to one safe line: no control characters, no newlines, capped width."""
    cleaned = []
    for character in str(text):
        if character in "\r\n\t":
            cleaned.append(" ")
            continue
        if unicodedata.category(character) in _BLOCKED:
            continue
        cleaned.append(character)
    flat = " ".join("".join(cleaned).split())
    if width > 0 and len(flat) > width:
        flat = flat[: max(width - 1, 0)].rstrip() + "\u2026"
    return flat


def cell(text: object, width: int = DEFAULT_WIDTH) -> str:
    """A Markdown table cell: sanitized, with pipe and backtick escaped."""
    value = sanitize(text, width)
    return value.replace("\\", "\\\\").replace("|", "\\|").replace("`", "\\`")


def bullet(text: object, width: int = DEFAULT_WIDTH) -> str:
    """One list or heading fragment: sanitized, with backticks escaped."""
    return sanitize(text, width).replace("`", "\\`")


def code(text: object, width: int = DEFAULT_WIDTH) -> str:
    """A fenced inline code fragment safe for a single-line context."""
    return sanitize(text, width).replace("`", "'")
