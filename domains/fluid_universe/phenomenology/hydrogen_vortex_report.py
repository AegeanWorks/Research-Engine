"""Hydrogen 2p vortex identification report (claim 26, ADR-017)."""

from __future__ import annotations

import math

import numpy as np

from domains.fluid_universe.theory.hydrogen_vortex import (
    angular_momentum,
    azimuthal_velocity,
    circulation,
    loop_circulation,
    most_probable_radius,
    radial_probability,
)

from .provenance import RESULTS_DIR, metadata, write_json, write_text_atomic

RADIUS = 1.0
M = 1
LOOP_R = 2.0
LOOP_THETA = math.pi / 2.0


def run_hydrogen_vortex_check(write: bool = True) -> dict:
    r = np.linspace(0.0, 80.0, 160001)
    probability = radial_probability(r, RADIUS)
    normalization = float(np.trapezoid(probability, r))
    peak = float(r[np.argmax(probability)])

    expected_circulation = circulation(M)
    measured_circulation = loop_circulation(LOOP_R, LOOP_THETA, M)
    velocity = azimuthal_velocity(LOOP_R, LOOP_THETA, M)

    result = {
        "atomic_units": {
            "bohr_radius": RADIUS,
            "m": M,
            "radial_normalization": normalization,
            "most_probable_radius": peak,
            "expected_most_probable_radius": most_probable_radius(RADIUS),
            "circulation": expected_circulation,
            "loop_radius": LOOP_R,
            "loop_theta": LOOP_THETA,
            "measured_loop_circulation": measured_circulation,
            "azimuthal_velocity": velocity,
            "angular_momentum": angular_momentum(M),
        },
        "verdict": {
            "vortex_identified": bool(
                abs(normalization - 1.0) < 1e-6
                and abs(peak - 4.0) < 1e-3
                and abs(measured_circulation - 2.0 * math.pi) < 1e-10
                and abs(velocity - 0.5) < 1e-12
                and abs(angular_momentum(M) - 1.0) < 1e-12
            ),
            "claim_26_status": "NUMERIC (2p vortex identification)",
            "note": (
                "The 2p_(m=+-1) angular node is a quantized vortex with "
                "circulation 2 pi hbar m / m_e and angular momentum hbar m; "
                "the radial density is nodeless and peaks at 4 a0. The m=0 "
                "state has no vortex. This identifies the defect, not the 2p "
                "energy; radial nodes still require a separate model."
            ),
        },
    }
    config = {
        "radius": RADIUS,
        "m": M,
        "loop_r": LOOP_R,
        "loop_theta": LOOP_THETA,
        "scope": "hydrogen 2p vortex identification; circulation and angular momentum",
    }
    payload = {"meta": metadata(config), "result": result}
    if write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        write_json(RESULTS_DIR / "hydrogen_vortex.json", payload)
        write_text_atomic(
            RESULTS_DIR / "hydrogen_vortex.md", render_markdown(payload)
        )
    return payload


def render_markdown(payload: dict) -> str:
    result = payload["result"]
    atomic = result["atomic_units"]
    verdict = result["verdict"]
    lines = [
        "# Hydrogen 2p vortex identification (claim 26)",
        "",
        "The 2p_(m=+-1) angular node at the origin is a quantized vortex.",
        "",
        "## Atomic units",
        "",
        f"- Radial normalization: {atomic['radial_normalization']:.12f}.",
        f"- Most-probable radius: {atomic['most_probable_radius']:.9f} "
        f"(expected {atomic['expected_most_probable_radius']:.9f}).",
        f"- Circulation: {atomic['circulation']:.12f}.",
        f"- Loop circulation at r={atomic['loop_radius']:.3g}, "
        f"theta={atomic['loop_theta']:.6f}: "
        f"{atomic['measured_loop_circulation']:.12f}.",
        f"- Azimuthal velocity at the loop: {atomic['azimuthal_velocity']:.12f}.",
        f"- Angular momentum: {atomic['angular_momentum']:.12f}.",
        "",
        "## Verdict",
        "",
        f"- Vortex identified: **{verdict['vortex_identified']}**.",
        f"- Claim 26: **{verdict['claim_26_status']}**.",
        "",
        verdict["note"],
        "",
        f"- Config SHA-256: `{payload['meta']['config_sha256']}`",
        f"- Git: `{payload['meta']['git']['commit']}` "
        f"(dirty={payload['meta']['git']['dirty']})",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    payload = run_hydrogen_vortex_check()
    print(payload["result"]["verdict"])
