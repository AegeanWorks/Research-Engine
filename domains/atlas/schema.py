"""Versioned structured scientific visual-knowledge schema.

Coordinates are NORMALIZED 0..1 (storage) and converted to the Meta 0..1000
perception-grounding grid only at the provider boundary. See
https://dev.meta.ai/docs/image-understanding#perception-grounding
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any

SCHEMA_VERSION = "domains.atlas.visual-knowledge/v1"

ENTITY_CATEGORIES = {
    "anatomical-structure", "molecule", "protein", "cell-type",
    "component", "process", "function", "pathway",
    "person", "place", "other",
}

RELATIONSHIP_TYPES = {
    "activates", "inhibits", "projects-to", "receives-input-from",
    "produces", "regulates", "contains", "participates-in",
}


def _check_norm(value: float, name: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{name} must be a number in [0,1], got {value!r}")
    v = float(value)
    if not 0.0 <= v <= 1.0:
        raise ValueError(f"{name} must be in [0,1], got {v}")
    return v


@dataclass(frozen=True)
class BoundingBox:
    """Normalized box: (0,0) top-left, (1,1) bottom-right."""

    x_min: float
    y_min: float
    x_max: float
    y_max: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "x_min", _check_norm(self.x_min, "x_min"))
        object.__setattr__(self, "y_min", _check_norm(self.y_min, "y_min"))
        object.__setattr__(self, "x_max", _check_norm(self.x_max, "x_max"))
        object.__setattr__(self, "y_max", _check_norm(self.y_max, "y_max"))
        if not (self.x_min < self.x_max and self.y_min < self.y_max):
            raise ValueError(f"empty/inverted box {self}")

    def to_grid1000(self) -> list[int]:
        """Meta perception-grounding grid (0..1000). Docs: divide by 10 for CSS %."""
        return [round(self.x_min * 1000), round(self.y_min * 1000),
                round(self.x_max * 1000), round(self.y_max * 1000)]

    @classmethod
    def from_grid1000(cls, box: list[float]) -> "BoundingBox":
        if len(box) != 4:
            raise ValueError(f"box must have 4 entries, got {box!r}")
        lo = [min(max(float(v), 0.0), 1000.0) / 1000.0 for v in box]  # clamp edge 1001 etc.
        return cls(x_min=lo[0], y_min=lo[1], x_max=lo[2], y_max=lo[3])


@dataclass(frozen=True)
class VisualEntity:
    id: str
    name: str
    category: str
    description: str = ""
    bbox: BoundingBox | None = None
    source_evidence: str = ""
    confidence: float = 0.0
    uncertainty: str = ""
    mask_ref: str = ""  # segmentation reference, empty when bbox-only fallback
    model_inferred: bool = False

    def __post_init__(self) -> None:
        if not self.id or not self.name:
            raise ValueError("entity id and name are required")
        if self.category not in ENTITY_CATEGORIES:
            raise ValueError(f"unknown category {self.category!r}")
        c = _checked_confidence(self.confidence, f"entity {self.id!r}")
        object.__setattr__(self, "confidence", c)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["bbox"] = asdict(self.bbox) if self.bbox else None
        return d


@dataclass(frozen=True)
class VisualRelationship:
    source_id: str
    target_id: str
    rel_type: str
    explanation: str = ""
    supporting_evidence: str = ""
    confidence: float = 0.0
    provenance: str = "model"  # "model" | "source" | "user-correction"
    model_inferred: bool = True

    def __post_init__(self) -> None:
        if self.rel_type not in RELATIONSHIP_TYPES:
            raise ValueError(f"unknown relationship type {self.rel_type!r}")
        if not self.source_id or not self.target_id:
            raise ValueError("relationship endpoints are required")
        if self.source_id == self.target_id:
            raise ValueError("self-relationships are not allowed")
        c = _checked_confidence(self.confidence,
                                f"relationship {self.source_id!r}->{self.target_id!r}")
        object.__setattr__(self, "confidence", c)

    def to_dict(self) -> dict:
        return asdict(self)


def _req(mapping: dict, key: str, ctx: str):
    """Required key with context — malformed payloads raise ValueError, never KeyError."""
    try:
        return mapping[key]
    except (KeyError, TypeError):
        raise ValueError(f"{ctx}: missing required key {key!r}")


def _checked_confidence(value, ctx: str) -> float:
    """Confidence must be a real number in [0,1] — bool/str rejected like bad boxes."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{ctx}: confidence must be a number in [0,1], got {value!r}")
    c = float(value)
    if not 0.0 <= c <= 1.0:
        raise ValueError(f"{ctx}: confidence must be in [0,1], got {c}")
    return c


@dataclass
class VisualAnalysis:
    """One analyzed figure crop. Entities + relationships share IDs by construction."""

    analysis_version: str = SCHEMA_VERSION
    document_ref: str = ""
    source_page: int = 0
    figure_id: str = ""
    entities: list[VisualEntity] = field(default_factory=list)
    relationships: list[VisualRelationship] = field(default_factory=list)

    def validate(self) -> list[str]:
        errors: list[str] = []
        ids = {e.id for e in self.entities}
        if len(ids) != len(self.entities):
            errors.append("duplicate entity ids")
        for r in self.relationships:
            if r.source_id not in ids:
                errors.append(f"relationship from unknown entity {r.source_id}")
            if r.target_id not in ids:
                errors.append(f"relationship to unknown entity {r.target_id}")
        return errors

    def to_dict(self) -> dict:
        return {
            "analysis_version": self.analysis_version,
            "document_ref": self.document_ref,
            "source_page": self.source_page,
            "figure_id": self.figure_id,
            "entities": [e.to_dict() for e in self.entities],
            "relationships": [r.to_dict() for r in self.relationships],
        }

    @classmethod
    def from_dict(cls, raw: dict) -> "VisualAnalysis":
        entities = []
        for e in raw.get("entities", []):
            if not isinstance(e, dict):
                raise ValueError(f"entity: expected object, got {e!r}")
            ctx = f"entity {e.get('id', '?')}"
            bbox = None
            if e.get("bbox"):
                b = e["bbox"]
                bbox = BoundingBox(x_min=_req(b, "x_min", f"{ctx} bbox"),
                                    y_min=_req(b, "y_min", f"{ctx} bbox"),
                                    x_max=_req(b, "x_max", f"{ctx} bbox"),
                                    y_max=_req(b, "y_max", f"{ctx} bbox"))
            entities.append(VisualEntity(
                id=_req(e, "id", "entity"), name=_req(e, "name", ctx), category=e.get("category", "other"),
                description=e.get("description", ""), bbox=bbox,
                source_evidence=e.get("source_evidence", ""),
                confidence=_checked_confidence(e.get("confidence", 0.0), ctx),
                uncertainty=e.get("uncertainty", ""),
                mask_ref=e.get("mask_ref", ""),
                model_inferred=bool(e.get("model_inferred", False)),
            ))
        rels = [VisualRelationship(
            source_id=_req(r, "source_id", "relationship"),
            target_id=_req(r, "target_id", "relationship"),
            rel_type=_req(r, "rel_type", "relationship"), explanation=r.get("explanation", ""),
            supporting_evidence=r.get("supporting_evidence", ""),
            confidence=_checked_confidence(r.get("confidence", 0.0),
                                             "relationship"),
            provenance=r.get("provenance", "model"),
            model_inferred=bool(r.get("model_inferred", True)),
        ) for r in raw.get("relationships", [])]
        try:
            source_page = int(raw.get("source_page", 0))
        except (TypeError, ValueError):
            raise ValueError(
                f"analysis: invalid source_page {raw.get('source_page')!r}")
        obj = cls(
            analysis_version=raw.get("analysis_version", SCHEMA_VERSION),
            document_ref=raw.get("document_ref", ""),
            source_page=source_page,
            figure_id=raw.get("figure_id", ""),
            entities=entities, relationships=rels,
        )
        errs = obj.validate()
        if errs:
            raise ValueError("; ".join(errs))
        return obj


def _norm_name(name: str) -> str:
    return " ".join(str(name).lower().strip().split())


def merge_analyses(analyses: list, document_ref: str = "",
                   figure_id: str = "") -> "VisualAnalysis":
    """Merge chunk analyses: entities by normalized name, rels remapped + deduped."""
    by_name: dict[str, VisualEntity] = {}
    order: list[str] = []
    for a in analyses:
        for e in a.entities:
            key = _norm_name(e.name)
            if key in by_name:
                old = by_name[key]
                desc = e.description if len(e.description) > len(old.description) else old.description
                ev = old.source_evidence
                if e.source_evidence and e.source_evidence not in ev:
                    ev = (ev + " | " + e.source_evidence)[:2000] if ev else e.source_evidence
                bbox = old.bbox or e.bbox
                by_name[key] = VisualEntity(
                    id=old.id, name=old.name, category=old.category,
                    description=desc, bbox=bbox, source_evidence=ev,
                    confidence=max(old.confidence, e.confidence),
                    uncertainty="; ".join(filter(None, [old.uncertainty,
                                                         e.uncertainty]))[:500],
                    mask_ref=old.mask_ref or e.mask_ref,
                    model_inferred=old.model_inferred and e.model_inferred)
            else:
                by_name[key] = e
                order.append(key)
    id_map: dict[str, str] = {}
    for a in analyses:
        for e in a.entities:
            id_map[e.id] = by_name[_norm_name(e.name)].id
    seen, rels = set(), []
    for a in analyses:
        for r in a.relationships:
            s, t = id_map.get(r.source_id, r.source_id), id_map.get(r.target_id, r.target_id)
            if s == t:
                continue
            key = (s, t, r.rel_type)
            if key in seen:
                continue
            seen.add(key)
            rels.append(VisualRelationship(
                source_id=s, target_id=t, rel_type=r.rel_type,
                explanation=r.explanation, supporting_evidence=r.supporting_evidence,
                confidence=r.confidence, provenance=r.provenance,
                model_inferred=r.model_inferred))
    entities = [by_name[k] for k in order]
    # Chunks often reuse synthetic ids ("e1", "e2", ...): disambiguate so the
    # merged model never violates the unique-id invariant. Relationships built
    # above already point at merged entities; remap them to the final ids.
    final_id: dict[str, str] = {}
    used: set[str] = set()
    for e in entities:
        candidate, n = e.id, 2
        while candidate in used:
            candidate = f"{e.id}-c{n}"
            n += 1
        used.add(candidate)
        # First wins: relationships built above reference surviving ids, and
        # the original per-chunk reference is ambiguous by construction.
        final_id.setdefault(e.id, candidate)
        object.__setattr__(e, "id", candidate)
    for r in rels:
        object.__setattr__(r, "source_id", final_id.get(r.source_id, r.source_id))
        object.__setattr__(r, "target_id", final_id.get(r.target_id, r.target_id))
    return VisualAnalysis(document_ref=document_ref or (analyses[0].document_ref if analyses else ""),
                          figure_id=figure_id, entities=entities, relationships=rels)


def muse_json_schema() -> dict:
    """JSON Schema sent as response_format.json_schema so Muse output parses first try."""
    num = {"type": "number", "minimum": 0, "maximum": 1000}
    return {
        "name": "AtlasVisualKnowledge",
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "entities": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                        "category": {"type": "string", "enum": sorted(ENTITY_CATEGORIES)},
                        "description": {"type": "string"},
                        "box": {"type": "array", "items": num, "minItems": 4, "maxItems": 4},
                        "source_evidence": {"type": "string"},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                        "uncertainty": {"type": "string"},
                    },
                    # box optional: text-sourced entities have no visual location
                    "required": ["id", "name", "category", "confidence"],
                    },
                },
                "relationships": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "source_id": {"type": "string"},
                            "target_id": {"type": "string"},
                            "rel_type": {"type": "string", "enum": sorted(RELATIONSHIP_TYPES)},
                            "explanation": {"type": "string"},
                            "supporting_evidence": {"type": "string"},
                            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                        },
                        "required": ["source_id", "target_id", "rel_type", "confidence"],
                    },
                },
            },
            "required": ["entities", "relationships"],
        },
    }


def coerce_muse_payload(payload: dict[str, Any], document_ref: str = "",
                         source_page: int = 0, figure_id: str = "") -> VisualAnalysis:
    """Validate raw Muse JSON (0..1000 boxes) into a versioned VisualAnalysis."""
    entities: list[VisualEntity] = []
    for e in payload.get("entities", []):
        if not isinstance(e, dict):
            raise ValueError(f"muse entity: expected object, got {e!r}")
        bbox = None
        if e.get("box"):
            bbox = BoundingBox.from_grid1000([float(v) for v in e["box"]])
        ctx = f"muse entity {e.get('id', '?')}"
        entities.append(VisualEntity(
            id=str(_req(e, "id", "muse entity")),
            name=str(_req(e, "name", ctx)),
            category=str(e.get("category", "other")),
            description=str(e.get("description", "")),
            bbox=bbox, source_evidence=str(e.get("source_evidence", "")),
            confidence=_checked_confidence(e.get("confidence", 0.0), ctx),
            uncertainty=str(e.get("uncertainty", "")),
            model_inferred=True,
        ))
    rels = [VisualRelationship(
        source_id=str(_req(r, "source_id", "muse relationship")),
        target_id=str(_req(r, "target_id", "muse relationship")),
        rel_type=str(_req(r, "rel_type", "muse relationship")), explanation=str(r.get("explanation", "")),
        supporting_evidence=str(r.get("supporting_evidence", "")),
        confidence=_checked_confidence(r.get("confidence", 0.0),
                                       "muse relationship"),
    ) for r in payload.get("relationships", [])]
    analysis = VisualAnalysis(document_ref=document_ref, source_page=source_page,
                              figure_id=figure_id, entities=entities, relationships=rels)
    errs = analysis.validate()
    if errs:
        raise ValueError("; ".join(errs))
    return analysis
