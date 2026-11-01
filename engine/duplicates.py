"""Duplicate-source detection by normalized DOI and title.

A split source is worse than a missing one: two records of the same paper double-count its
evidence and break the provenance trail. Detection is advisory; the engine never deletes or merges
a source on its own.
"""

from __future__ import annotations

import re
import sqlite3
import unicodedata
from typing import Dict, List, Sequence, Tuple

from engine.errors import EngineError
from engine.models import Source
from engine.researches import get_research
from engine.sources import list_sources

_DOI_PREFIXES = (
    "https://doi.org/",
    "http://doi.org/",
    "https://dx.doi.org/",
    "http://dx.doi.org/",
    "https://www.doi.org/",
    "http://www.doi.org/",
    "doi:",
)
_WORD = re.compile(r"[^\W_]+", re.UNICODE)


def normalize_doi(value: str) -> str:
    """Strip resolver prefixes and case-fold a DOI so two spellings compare equal."""
    text = str(value or "").strip()
    lowered = text.casefold()
    for prefix in _DOI_PREFIXES:
        if lowered.startswith(prefix):
            text = text[len(prefix):]
            break
    return text.strip().casefold()


def normalize_title(value: str) -> str:
    """Fold accents, case and punctuation while keeping letters from every script."""
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(character for character in text if not unicodedata.combining(character))
    return " ".join(_WORD.findall(text.casefold()))


def _group(items: Sequence[Source], reason: str, key: str) -> dict:
    ordered = sorted(items, key=lambda item: item.id)
    return {
        "research": ordered[0].research_id,
        "reason": reason,
        "key": key,
        "keep": ordered[0].id,
        "count": len(ordered),
        "sources": [
            {
                "id": item.id,
                "title": item.title,
                "year": item.year,
                "doi": item.doi,
                "url": item.url,
                "status": item.status,
            }
            for item in ordered
        ],
    }


def duplicate_sources(
    conn: sqlite3.Connection,
    research_ref: str | None = None,
    limit: int | None = 20,
) -> dict:
    """Return groups of sources that share a DOI, a normalized title/year, or a title variant."""
    if limit is not None and int(limit) < 1:
        raise EngineError(
            f"duplicate limit is {limit}",
            "a report needs at least one group.",
            "pass --limit 1 or more.",
        )
    research_id = get_research(conn, research_ref).id if research_ref else None
    sources = list_sources(conn, research_id)
    groups: List[dict] = []
    assigned = set()

    by_doi: Dict[Tuple[str, str], List[Source]] = {}
    for source in sources:
        doi = normalize_doi(source.doi)
        if doi:
            by_doi.setdefault((source.research_id, doi), []).append(source)
    for (_program, doi), items in sorted(by_doi.items()):
        if len(items) < 2:
            continue
        groups.append(_group(items, "doi", doi))
        assigned.update(item.id for item in items)

    by_title_year: Dict[Tuple[str, str, int | None], List[Source]] = {}
    for source in sources:
        title = normalize_title(source.title)
        if not title or source.id in assigned:
            continue
        by_title_year.setdefault((source.research_id, title, source.year), []).append(source)
    for (_program, title, year), items in sorted(
        by_title_year.items(), key=lambda item: (item[0][0], item[0][1], item[0][2] or 0)
    ):
        if len(items) < 2:
            continue
        groups.append(_group(items, "title_year", f"{title}|{year if year is not None else ''}"))
        assigned.update(item.id for item in items)

    by_title: Dict[Tuple[str, str], List[Source]] = {}
    for source in sources:
        title = normalize_title(source.title)
        if not title or source.id in assigned:
            continue
        by_title.setdefault((source.research_id, title), []).append(source)
    for (_program, title), items in sorted(by_title.items()):
        if len(items) < 2:
            continue
        groups.append(_group(items, "title_variant", title))

    groups.sort(key=lambda item: (-item["count"], item["keep"], item["reason"]))
    total = len(groups)
    if limit is not None:
        groups = groups[: int(limit)]
    return {
        "research": research_id or "all",
        "groups": groups,
        "total": total,
        "returned": len(groups),
    }
