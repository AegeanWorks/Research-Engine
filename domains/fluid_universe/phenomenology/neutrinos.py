"""Neutrino Koide ratio scan.

Inputs are the NuFit 5.2 (2022) oscillation parameters with SK-atm.  For each
mass ordering the lightest mass is scanned from 0 to 0.2 eV, and the 3-sigma
corners of the mass-squared splittings are checked separately.  The result is a
negative one: Q_nu never reaches 2/3.

The scan is a statement about the Koide ratio of the three active neutrino
masses.  It does not assume a circulant neutrino mass matrix.
"""

from __future__ import annotations

import csv
import hashlib
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from domains.fluid_universe.theory.circulant import q_masses

from .provenance import RESULTS_DIR, metadata, write_json, write_text_atomic

DATA_PATH = Path(__file__).resolve().parent / "data" / "nufit52_neutrinos.csv"
KOIDE = 2.0 / 3.0
M_LIGHT_MAX_EV = 0.2
SCAN_POINTS = 2001


@dataclass(frozen=True)
class NuFitParameters:
    dm21_sq: float
    dm31_sq_no: float
    dm31_sq_io: float
    dm21_low: float
    dm21_high: float
    dm31_no_low: float
    dm31_no_high: float
    dm31_io_low: float
    dm31_io_high: float
    theta12_deg: float
    theta13_deg: float
    theta23_deg: float


def load_parameters(path: Path = DATA_PATH) -> NuFitParameters:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    def value(name: str, ordering: str) -> float:
        for row in rows:
            if row["name"] == name and row["ordering"] in (ordering, "both"):
                return float(row["value"])
        raise KeyError(f"missing {name} for {ordering}")

    return NuFitParameters(
        dm21_sq=value("dm21_sq", "both"),
        dm31_sq_no=value("dm31_sq", "NO"),
        dm31_sq_io=value("dm31_sq", "IO"),
        dm21_low=value("dm21_sq_3sigma_low", "both"),
        dm21_high=value("dm21_sq_3sigma_high", "both"),
        dm31_no_low=value("dm31_sq_3sigma_low", "NO"),
        dm31_no_high=value("dm31_sq_3sigma_high", "NO"),
        dm31_io_low=value("dm31_sq_3sigma_low", "IO"),
        dm31_io_high=value("dm31_sq_3sigma_high", "IO"),
        theta12_deg=value("theta12_deg", "both"),
        theta13_deg=value("theta13_deg", "NO"),
        theta23_deg=value("theta23_deg", "NO"),
    )


def masses_normal(m_light: float, dm21_sq: float, dm31_sq_no: float) -> np.ndarray:
    """Return (m1, m2, m3) for normal ordering, m_light = m1."""
    return np.array(
        [
            m_light,
            math.sqrt(m_light**2 + dm21_sq),
            math.sqrt(m_light**2 + dm31_sq_no),
        ]
    )


def masses_inverted(m_light: float, dm21_sq: float, dm31_sq_io: float) -> np.ndarray:
    """Return (m1, m2, m3) for inverted ordering, m_light = m3."""
    dm31_abs = abs(dm31_sq_io)
    return np.array(
        [
            math.sqrt(m_light**2 + dm31_abs),
            math.sqrt(m_light**2 + dm31_abs + dm21_sq),
            m_light,
        ]
    )


def q_nu(masses: np.ndarray) -> float:
    return q_masses(masses)


def scan_ordering(
    ordering: str,
    params: NuFitParameters,
    m_light_max: float = M_LIGHT_MAX_EV,
    points: int = SCAN_POINTS,
) -> dict:
    m_light = np.linspace(0.0, m_light_max, points)
    if ordering == "NO":
        masses = [masses_normal(value, params.dm21_sq, params.dm31_sq_no) for value in m_light]
    elif ordering == "IO":
        masses = [masses_inverted(value, params.dm21_sq, params.dm31_sq_io) for value in m_light]
    else:
        raise ValueError("ordering must be NO or IO")
    q_values = np.array([q_nu(item) for item in masses])
    index = int(np.argmax(q_values))
    q_zero = q_nu(masses[0])
    samples = []
    for sample in (0.0, 0.001, 0.01, 0.03, 0.05, 0.1, 0.2):
        if sample > m_light_max:
            continue
        if ordering == "NO":
            m = masses_normal(sample, params.dm21_sq, params.dm31_sq_no)
        else:
            m = masses_inverted(sample, params.dm21_sq, params.dm31_sq_io)
        samples.append({"m_light_eV": sample, "masses_eV": [float(x) for x in m], "Q": q_nu(m)})
    return {
        "ordering": ordering,
        "m_light_max_eV": m_light_max,
        "scan_points": points,
        "Q_at_m_light_zero": float(q_zero),
        "Q_min": float(np.min(q_values)),
        "Q_max": float(np.max(q_values)),
        "m_light_at_Q_max_eV": float(m_light[index]),
        "monotonic_decreasing": bool(np.all(np.diff(q_values) <= 1e-15)),
        "samples": samples,
    }


def corner_max(ordering: str, params: NuFitParameters) -> dict:
    """Maximum Q at m_light = 0 over the 3-sigma corners of the splittings."""
    values = []
    for dm21 in (params.dm21_low, params.dm21_high):
        if ordering == "NO":
            for dm31 in (params.dm31_no_low, params.dm31_no_high):
                values.append((q_nu(masses_normal(0.0, dm21, dm31)), dm21, dm31))
        else:
            for dm31 in (params.dm31_io_low, params.dm31_io_high):
                values.append((q_nu(masses_inverted(0.0, dm21, dm31)), dm21, dm31))
    best = max(values, key=lambda item: item[0])
    return {
        "ordering": ordering,
        "Q_max_corner": float(best[0]),
        "dm21_sq_corner": float(best[1]),
        "dm31_sq_corner": float(best[2]),
        "corners": [
            {"Q": float(q), "dm21_sq": float(dm21), "dm31_sq": float(dm31)}
            for q, dm21, dm31 in values
        ],
    }


def run_neutrino_check(write: bool = True) -> dict:
    params = load_parameters()
    scans = [scan_ordering("NO", params), scan_ordering("IO", params)]
    corners = [corner_max("NO", params), corner_max("IO", params)]
    max_q = max(item["Q_max"] for item in scans)
    max_corner = max(item["Q_max_corner"] for item in corners)
    payload = {
        "meta": metadata(
            {
                "data_sha256": hashlib.sha256(DATA_PATH.read_bytes()).hexdigest(),
                "m_light_max_eV": M_LIGHT_MAX_EV,
                "scan_points": SCAN_POINTS,
                "koide_target": KOIDE,
                "source": "NuFit 5.2 (2022), with SK-atm",
            }
        ),
        "parameters": params.__dict__,
        "scans": scans,
        "corners": corners,
        "verdict": {
            "Q_nu_below_2_3_all_scanned": bool(max_q < KOIDE and max_corner < KOIDE),
            "Q_nu_max": float(max_q),
            "Q_nu_max_at_3sigma_corner": float(max_corner),
            "margin_to_2_3": float(KOIDE - max(max_q, max_corner)),
            "note": (
                "Negative result: no scanned neutrino mass ordering or lightest mass reaches "
                "Q=2/3. The maximum is at m_light=0 and decreases as the lightest mass grows."
            ),
        },
    }
    if write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        write_json(RESULTS_DIR / "neutrinos.json", payload)
        write_text_atomic(RESULTS_DIR / "neutrinos.md", render_markdown(payload))
    return payload


def render_markdown(payload: dict) -> str:
    v = payload["verdict"]
    lines = [
        "# Neutrino Koide scan",
        "",
        "Inputs: NuFit 5.2 (2022) with SK-atm. Scan: lightest mass 0 to "
        f"{payload['meta']['config']['m_light_max_eV']} eV, "
        f"{payload['meta']['config']['scan_points']} points per ordering.",
        "",
        "| ordering | Q at m_light=0 | Q min | Q max | m_light at Q max (eV) | monotonic decreasing |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for item in payload["scans"]:
        lines.append(
            f"| {item['ordering']} | {item['Q_at_m_light_zero']:.12f} | "
            f"{item['Q_min']:.12f} | {item['Q_max']:.12f} | "
            f"{item['m_light_at_Q_max_eV']:.6g} | {item['monotonic_decreasing']} |"
        )
    lines += [
        "",
        "| ordering | Q max at 3-sigma corner | dm21^2 corner | dm31^2 corner |",
        "|---|---:|---:|---:|",
    ]
    for item in payload["corners"]:
        lines.append(
            f"| {item['ordering']} | {item['Q_max_corner']:.12f} | "
            f"{item['dm21_sq_corner']:.6e} | {item['dm31_sq_corner']:.6e} |"
        )
    lines += [
        "",
        f"**Verdict:** Q_nu below 2/3 everywhere scanned: **{v['Q_nu_below_2_3_all_scanned']}**. "
        f"Maximum Q_nu = {v['Q_nu_max']:.12f}; 3-sigma corner maximum = "
        f"{v['Q_nu_max_at_3sigma_corner']:.12f}; margin to 2/3 = {v['margin_to_2_3']:.6f}.",
        "",
        f"- Config SHA-256: `{payload['meta']['config_sha256']}`",
        f"- Git: `{payload['meta']['git']['commit']}` (dirty={payload['meta']['git']['dirty']})",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    result = run_neutrino_check()
    print(result["verdict"])
