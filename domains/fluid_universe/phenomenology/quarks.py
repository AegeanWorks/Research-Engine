"""Quark Koide ratios from the full-SM MS-bar masses of Huang & Zhou (2021).

The direct quark extension is falsified: Q_up and Q_down stay far from 2/3 at
every tabulated scale.  The original numbers Q_up ~ 0.85 and Q_down ~ 0.73 are
scale-dependent; at M_Z the full-SM values are about 0.888 and 0.748.
"""

from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from pathlib import Path

from domains.fluid_universe.theory.circulant import q_masses

from .provenance import RESULTS_DIR, metadata, write_json, write_text_atomic

DATA_PATH = Path(__file__).resolve().parent / "data" / "quark_masses_hz2021.csv"
KOIDE = 2.0 / 3.0


@dataclass(frozen=True)
class QuarkRow:
    scale_label: str
    scale_GeV: float
    m_t_GeV: float
    m_b_GeV: float
    m_c_GeV: float
    m_s_GeV: float
    m_d_GeV: float
    m_u_GeV: float
    source: str


def load_rows(path: Path = DATA_PATH) -> list[QuarkRow]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return [
        QuarkRow(
            scale_label=row["scale_label"],
            scale_GeV=float(row["scale_GeV"]),
            m_t_GeV=float(row["m_t_GeV"]),
            m_b_GeV=float(row["m_b_GeV"]),
            m_c_GeV=float(row["m_c_GeV"]),
            m_s_GeV=float(row["m_s_GeV"]),
            m_d_GeV=float(row["m_d_GeV"]),
            m_u_GeV=float(row["m_u_GeV"]),
            source=row["source"],
        )
        for row in rows
    ]


def q_up(row: QuarkRow) -> float:
    return q_masses([row.m_u_GeV, row.m_c_GeV, row.m_t_GeV])


def q_down(row: QuarkRow) -> float:
    return q_masses([row.m_d_GeV, row.m_s_GeV, row.m_b_GeV])


def run_quark_check(write: bool = True) -> dict:
    rows = load_rows()
    points = []
    for row in rows:
        up = q_up(row)
        down = q_down(row)
        points.append(
            {
                "scale_label": row.scale_label,
                "scale_GeV": row.scale_GeV,
                "Q_up": up,
                "Q_down": down,
                "Q_up_minus_2_3": up - KOIDE,
                "Q_down_minus_2_3": down - KOIDE,
            }
        )
    up_values = [point["Q_up"] for point in points]
    down_values = [point["Q_down"] for point in points]
    closest = min(points, key=lambda point: min(abs(point["Q_up_minus_2_3"]), abs(point["Q_down_minus_2_3"])))
    min_distance = min(
        min(abs(point["Q_up_minus_2_3"]), abs(point["Q_down_minus_2_3"])) for point in points
    )
    payload = {
        "meta": metadata(
            {
                "data_sha256": hashlib.sha256(DATA_PATH.read_bytes()).hexdigest(),
                "mass_definition": "MS-bar, full SM, Huang & Zhou (2021) Table II",
                "koide_target": KOIDE,
            }
        ),
        "points": points,
        "ranges": {
            "Q_up_min": min(up_values),
            "Q_up_max": max(up_values),
            "Q_down_min": min(down_values),
            "Q_down_max": max(down_values),
        },
        "verdict": {
            "direct_extension_falsified": bool(min_distance > 0.05),
            "min_abs_Q_minus_2_3": float(min_distance),
            "closest_scale": closest["scale_label"],
            "closest_Q_up": closest["Q_up"],
            "closest_Q_down": closest["Q_down"],
            "note": (
                "Both quark ratios stay far from 2/3 at every tabulated scale. "
                "The original Q_up~0.85, Q_down~0.73 values are scale-dependent; "
                "at M_Z the full-SM values are about 0.888 and 0.748."
            ),
        },
    }
    if write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        write_json(RESULTS_DIR / "quarks.json", payload)
        write_text_atomic(RESULTS_DIR / "quarks.md", render_markdown(payload))
    return payload


def render_markdown(payload: dict) -> str:
    v = payload["verdict"]
    lines = [
        "# Quark Koide ratios",
        "",
        "Masses: MS-bar, full SM, Huang & Zhou (2021) Table II. "
        "The top, bottom, and charm masses are in GeV; the light quarks are converted from MeV.",
        "",
        "| scale | Q_up | Q_down | Q_up - 2/3 | Q_down - 2/3 |",
        "|---|---:|---:|---:|---:|",
    ]
    for point in payload["points"]:
        lines.append(
            f"| {point['scale_label']} | {point['Q_up']:.12f} | {point['Q_down']:.12f} | "
            f"{point['Q_up_minus_2_3']:+.6f} | {point['Q_down_minus_2_3']:+.6f} |"
        )
    lines += [
        "",
        f"Q_up range: [{payload['ranges']['Q_up_min']:.12f}, {payload['ranges']['Q_up_max']:.12f}]. "
        f"Q_down range: [{payload['ranges']['Q_down_min']:.12f}, {payload['ranges']['Q_down_max']:.12f}].",
        "",
        f"**Verdict:** direct quark extension falsified: **{v['direct_extension_falsified']}**. "
        f"Closest approach to 2/3 is {v['min_abs_Q_minus_2_3']:.6f} at {v['closest_scale']} "
        f"(Q_up={v['closest_Q_up']:.9f}, Q_down={v['closest_Q_down']:.9f}).",
        "",
        f"- Config SHA-256: `{payload['meta']['config_sha256']}`",
        f"- Git: `{payload['meta']['git']['commit']}` (dirty={payload['meta']['git']['dirty']})",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    result = run_quark_check()
    print(result["verdict"])
