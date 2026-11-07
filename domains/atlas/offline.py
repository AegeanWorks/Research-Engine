"""Offline extractive fallback: real learning models with no API key.

When no MODEL_API_KEY/META_API_KEY is configured, ``auto_create_model`` uses
this builder instead of refusing. It is stdlib-only (frequency keyphrases +
co-occurrence relations) and every entity is labelled honestly: confidence
0.5, ``model_inferred=True``, uncertainty names the offline method, and
``source_evidence`` quotes the source sentence. Live Muse/SAM providers are
untouched and still refuse keyless calls directly.
"""
from __future__ import annotations

import os
import re

from .schema import VisualAnalysis, VisualEntity, VisualRelationship

STOPWORDS = frozenset("""
a an and are as at be but by for from has have he she it its in into is was
were will with that this these those they them their there here his her our
your you we of on or not no nor so such than then too very can could should
would may might must shall do does did done being been each other more most
other some any all only own same if when while where which who whom whose
what how why because until per via within without between through during
also just over under about out off up down again once et al fig figure
using used use study paper results based
along away across toward towards upon onto above below beneath near far
around among behind beyond against plus except whether either neither
left right top bottom center middle side sides forward backward upward
downward outward inward forth
""".split())

_TOKEN = re.compile(r"[A-Za-z][A-Za-z\-]{3,}")
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")


def _sentences(text: str) -> list[str]:
    parts = [s.strip() for s in _SENT_SPLIT.split(text or "") if s.strip()]
    return parts or []


def _slug(term: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", term.lower()).strip("-")
    return (slug or "entity")[:32]


def _filename_terms(path: str) -> str:
    base = os.path.splitext(os.path.basename(path or ""))[0]
    words = [w for w in re.split(r"[^A-Za-z0-9]+", base) if len(w) >= 3]
    return " ".join(words)


def build_offline_analysis(text: str, document_ref: str = "",
                           figure_id: str = "", source_kind: str = "text",
                           max_entities: int = 12) -> VisualAnalysis:
    """Keyphrase-frequency text → validated VisualAnalysis (no network, no key)."""
    sents = _sentences(text or "")
    freq: dict[str, int] = {}
    first_pos: dict[str, int] = {}
    for pos, sent in enumerate(sents):
        for tok in _TOKEN.findall(sent.lower()):
            if tok in STOPWORDS:
                continue
            freq[tok] = freq.get(tok, 0) + 1
            first_pos.setdefault(tok, pos)
    ranked = sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))
    if not ranked:
        ranked = [("figure", 1)]
        sents = [f"Figure file {os.path.basename(document_ref or '')} with no readable text. ".strip()]
    top = ranked[:max_entities]
    if len(sents) == 1 and len(top) > 4:
        top = top[:4]

    entities: list[VisualEntity] = []
    seen_ids: set[str] = set()
    for term, count in top:
        base_id = _slug(term)
        eid, n = base_id, 2
        while eid in seen_ids:
            eid = f"{base_id}-{n}"
            n += 1
        seen_ids.add(eid)
        ev = next((s for s in sents if term in s.lower()),
                  sents[0] if sents else term)
        ev = ev[:280]
        entities.append(VisualEntity(
            id=eid, name=term.title(), category="other",
            description=f"Mentioned {count} time(s) in this {source_kind} source. {ev[:220]}",
            bbox=None, source_evidence=ev + " (offline-extractive)",
            confidence=0.5,
            uncertainty=("offline-extractive keyword frequency, not Muse vision; "
                         "add MODEL_API_KEY for live analysis"),
            model_inferred=True))

    terms = [t for t, _ in top]
    id_of = {t: e.id for (t, _), e in zip(top, entities)}
    rels: list[VisualRelationship] = []
    seen: set[tuple] = set()
    for sent in sents:
        low = sent.lower()
        present = [t for t in terms if t in low]
        for i in range(len(present)):
            for j in range(i + 1, len(present)):
                key = (id_of[present[i]], id_of[present[j]])
                if key in seen or len(rels) >= 24:
                    continue
                seen.add(key)
                ev = sent[:280]
                rels.append(VisualRelationship(
                    source_id=key[0], target_id=key[1],
                    rel_type="participates-in",
                    explanation=f"Co-mentioned in source: {ev[:160]}",
                    supporting_evidence=ev, confidence=0.4,
                    provenance="offline-extractive", model_inferred=True))
        if len(rels) >= 24:
            break

    analysis = VisualAnalysis(document_ref=document_ref, figure_id=figure_id or "offline",
                              entities=entities, relationships=rels)
    errs = analysis.validate()
    if errs:  # pragma: no cover - defensive; builder guarantees validity
        raise ValueError("; ".join(errs))
    return analysis


def offline_text_for_source(bundle: dict, note: str = "") -> str:
    """Context text for image/video sources: note + filename terms."""
    if bundle.get("kind") == "text":
        return bundle.get("text", "")
    path = bundle.get("path", "") or bundle.get("document_ref", "")
    context = " ".join(p for p in [note.strip(), _filename_terms(path)] if p).strip()
    if not context:
        context = f"Figure {os.path.basename(path or 'image')} with no caption note. "
    return (context + " (offline-extractive image context: visual content not "
            "analyzed without MODEL_API_KEY.)")
