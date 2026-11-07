"""3D from 2D knowledge: isometric view + printable OBJ export (stdlib only).

A figure analysis is flat (normalized 0..1 boxes). This module gives it depth:
- Isometric projection for an offline 2.5D canvas view (stacked by category,
  so pathways read as layers); pure math, no dependency.
- OBJ export: one cuboid per located entity, grouped and named, with a minimal
  .MTL — opens in Blender/MeshLab/Windows 3D Viewer and 3D-prints as a tactile
  study model. Text-only entities are listed in the OBJ comment, never faked
  into geometry.
"""
from __future__ import annotations

import math

# Stable layer order: input structures at the bottom, outputs on top.
CATEGORY_LAYERS = {
    "cell-type": 0, "molecule": 1, "protein": 2, "component": 3,
    "anatomical-structure": 4, "person": 4, "place": 4,
    "process": 5, "function": 6, "pathway": 7, "other": 8,
}

ISO_ANGLE = math.radians(30)
COS_A, SIN_A = math.cos(ISO_ANGLE), math.sin(ISO_ANGLE)


def iso_project(x: float, y: float, z: float) -> tuple[float, float]:
    """Isometric 2D projection of a 3D point (all inputs in model units)."""
    return (x - y) * COS_A, (x + y) * SIN_A - z


def layer_of(category: str) -> int:
    return CATEGORY_LAYERS.get(category, CATEGORY_LAYERS["other"])


def iso_view(analysis: dict, depth: float = 0.12) -> dict:
    """Entities with boxes → isometric polygons for the 2.5D canvas view.

    Returns {"polygons": [{id, name, points: [[x, y]...], layer}], "skipped": [ids]}
    in a 0..1-centred frame; the frontend scales to pixels.
    """
    polygons, skipped = [], []
    for e in analysis.get("entities", []):
        bbox = e.get("bbox")
        if not bbox:
            skipped.append(e.get("id", "?"))
            continue
        z = layer_of(e.get("category", "other")) * depth
        corners = [(bbox["x_min"], bbox["y_min"]), (bbox["x_max"], bbox["y_min"]),
                   (bbox["x_max"], bbox["y_max"]), (bbox["x_min"], bbox["y_max"])]
        base = [iso_project(x, y, z) for x, y in corners]
        top = [iso_project(x, y, z + depth) for x, y in corners]
        polygons.append({"id": e["id"], "name": e.get("name", e["id"]),
                         "category": e.get("category", "other"),
                         "layer": layer_of(e.get("category", "other")),
                         "top": [[round(px, 4), round(py, 4)] for px, py in top],
                         "base": [[round(px, 4), round(py, 4)] for px, py in base]})
    polygons.sort(key=lambda p: layer_of(p["category"]))
    return {"polygons": polygons, "skipped": skipped}


def _cuboid(center: tuple[float, float, float],
            size: tuple[float, float, float]) -> tuple[list, list]:
    cx, cy, cz = center
    sx, sy, sz = size[0] / 2, size[1] / 2, size[2] / 2
    verts = [(cx - sx, cy - sy, cz - sz), (cx + sx, cy - sy, cz - sz),
             (cx + sx, cy + sy, cz - sz), (cx - sx, cy + sy, cz - sz),
             (cx - sx, cy - sy, cz + sz), (cx + sx, cy - sy, cz + sz),
             (cx + sx, cy + sy, cz + sz), (cx - sx, cy + sy, cz + sz)]
    faces = [(1, 2, 3, 4), (5, 8, 7, 6), (1, 5, 6, 2),
             (2, 6, 7, 3), (3, 7, 8, 4), (4, 8, 5, 1)]
    return verts, faces


def export_obj(analysis: dict, depth: float = 0.15) -> str:
    """Validated analysis → Wavefront OBJ text (cuboid per located entity)."""
    lines = [f"# Atlas 3D model: {analysis.get('figure_id', 'model')}",
             "# units: figure width=1, height=1, depth=layer*0.15; +z up"]
    skipped: list[str] = []
    offset = 1
    groups = 0
    for e in analysis.get("entities", []):
        bbox = e.get("bbox")
        if not bbox:
            skipped.append(str(e.get("id", "?")))
            continue
        cx = (bbox["x_min"] + bbox["x_max"]) / 2 - 0.5
        cy = 0.5 - (bbox["y_min"] + bbox["y_max"]) / 2  # y-up for 3D tools
        cz = layer_of(e.get("category", "other")) * depth
        size = (max(bbox["x_max"] - bbox["x_min"], 0.01),
                max(bbox["y_max"] - bbox["y_min"], 0.01), depth)
        verts, faces = _cuboid((cx, cy, cz), size)
        name = "".join(c if c.isalnum() or c in "-_" else "_" for c in str(e.get("id", "e")))
        lines.append(f"g {name}")
        for v in verts:
            lines.append(f"v {v[0]:.4f} {v[1]:.4f} {v[2]:.4f}")
        for f in faces:
            lines.append("f " + " ".join(str(i + offset) for i in f))
        offset += len(verts)
        groups += 1
    if skipped:
        lines.append(f"# text-only entities without geometry: {', '.join(skipped)}")
    if groups == 0:
        raise ValueError("no located entities: nothing to export to 3D")
    return "\n".join(lines) + "\n"
