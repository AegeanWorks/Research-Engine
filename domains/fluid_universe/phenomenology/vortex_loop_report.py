"""2p core-threading loop probe (claim 61, ADR-056).

Pre-registered delta0 = 0.1*a0 only; loops r = delta0/2delta0/2 at
theta=pi/2, m=1, samples=4000. Gates frozen in ADR-056.
"""

from __future__ import annotations

import math

from domains.fluid_universe.theory.hydrogen_vortex import azimuthal_velocity, loop_circulation
from domains.fluid_universe.theory.vortex_loop import (
    GRID_LENGTH,
    GRID_NS,
    LOOP_RADII,
    LOOP_THETA,
    SAMPLES,
    WINDING_M,
    blob_loop,
    blob_umax,
    core_scale,
    floor_vmax,
    numeric_blob_loop,
)

from .provenance import RESULTS_DIR, metadata, write_json, write_text_atomic

LOOP_TOL = 1e-6


def run_vortex_loop_check(write: bool = True) -> dict:
    delta0 = core_scale()
    gamma = 2.0 * math.pi
    # Singular control (apparatus must hold 2pi at r=2).
    sing = loop_circulation(2.0, LOOP_THETA, WINDING_M)
    sing_ok = abs(sing - gamma) / gamma <= LOOP_TOL
    # Blob: analytic fractions + one numeric confirmation each.
    blob = {}
    for r in LOOP_RADII:
        analytic = blob_loop(r, delta0, gamma)
        numeric = numeric_blob_loop(r, delta0, SAMPLES, gamma)
        blob[str(r)] = {"analytic": analytic, "numeric": numeric, "fraction": analytic / gamma}
    blob_below = any(abs(b["analytic"] - gamma) / gamma > LOOP_TOL for b in blob.values())
    # Floor: circulation exact (phase untouched), velocity diverges by rule.
    floor_loop = loop_circulation(2.0, LOOP_THETA, WINDING_M)
    floor_circ_ok = abs(floor_loop - gamma) / gamma <= LOOP_TOL
    vmax = {n: floor_vmax(n, GRID_LENGTH) for n in GRID_NS}
    floor_diverges = vmax[2048] > vmax[1024] > vmax[512] > vmax[256] and vmax[256] > 10.0
    # Caps: blob finite at 5.0; far-field 1/r law.
    umax = blob_umax(delta0, gamma)
    far = {r: azimuthal_velocity(r, LOOP_THETA, WINDING_M) for r in (1.0, 2.0, 4.0, 8.0)}
    far_ok = all(
        abs(far[r] - 1.0 / r) <= 1e-12 for r in far
    )
    hard = [
        ("singular_control_broken", not sing_ok),
        ("blob_below", bool(blob_below) and sing_ok),
        ("floorcap_below", bool(floor_diverges or not floor_circ_ok) and sing_ok),
    ]
    soft = [
        ("far_match", not far_ok),
        ("umax_finite", not (math.isfinite(umax) and abs(umax - 5.0) <= 1e-9)),
    ]
    dead_hard = sorted(n for n, k in hard if k)
    dead_soft = sorted(n for n, k in soft if k)
    if ("blob_below" in dead_hard or "floorcap_below" in dead_hard) and "singular_control_broken" not in dead_hard:
        status = (
            "FALSIFIED (single-valued regularized 2p vortex insufficient: "
            f"blob loops {[round(blob[k]['fraction'], 6) for k in sorted(blob)]} vs 1; "
            f"floor vmax {vmax[256]:.1f}->{vmax[2048]:.1f} diverges)"
        )
    elif "singular_control_broken" in dead_hard:
        status = "UNVERIFIED (singular apparatus check failed; solver unreliable)"
    elif dead_soft:
        status = f"UNVERIFIED ({'; '.join(dead_soft)})"
    elif sing_ok and not blob_below and not floor_diverges and floor_circ_ok:
        status = (
            "NUMERIC (regularized vortex holds 2pi on all core-threading loops "
            "with finite capped fields)"
        )
    else:
        status = "UNVERIFIED (no decision)"
    result = {
        "scales": {
            "delta0": delta0,
            "loops": LOOP_RADII,
            "theta": LOOP_THETA,
            "samples": SAMPLES,
            "singular_loop_r2": sing,
            "blob": blob,
            "floor_loop_r2": floor_loop,
            "floor_vmax": vmax,
            "blob_umax": umax,
            "far_field": far,
        },
        "gates": {
            "loop_tol": LOOP_TOL,
            "kills_hard": [[n, bool(k)] for n, k in hard],
            "kills_soft": [[n, bool(k)] for n, k in soft],
        },
        "verdict": {"claim_61_status": status, "note": "2p core-loop probe only; 2s shell queued."},
    }
    config = {
        "delta0_factor": 0.1,
        "delta0_from": "theory.hydrogen_fluid.bohr_radius (transferred claim-60, local-linearity)",
        "loops": list(LOOP_RADII),
        "samples": SAMPLES,
        "grids": list(GRID_NS),
        "gates": {"loop_tol": LOOP_TOL},
        "scope": "2p core-threading loop probe only; no 2s claim",
    }
    payload = {"meta": metadata(config), "result": result}
    if write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        write_json(RESULTS_DIR / "vortex_loop.json", payload)
        write_text_atomic(RESULTS_DIR / "vortex_loop.md", render_markdown(payload))
    return payload


def render_markdown(payload: dict) -> str:
    r = payload["result"]
    s = r["scales"]
    v = r["verdict"]
    lines = [
        "# 2p core-threading loop probe (claim 61)",
        "",
        "Single-valued regularized 2p vortex vs Wallstrom quantization inside the core.",
        "",
        "| loop r | blob fraction of 2pi |",
        "|---|---|",
    ]
    for k in sorted(s["blob"]):
        lines.append(f"| {k} | {s['blob'][k]['fraction']:.8f} |")
    lines += [
        "",
        f"- Singular loop r=2: {s['singular_loop_r2']:.12f}; floor loop r=2: {s['floor_loop_r2']:.12f}.",
        f"- Floor vmax: {s['floor_vmax'][256]:.1f} -> {s['floor_vmax'][2048]:.1f}; blob umax: {s['blob_umax']:.6f}.",
        "",
        "## Verdict",
        "",
        f"- Claim 61: **{v['claim_61_status']}**.",
        "",
        v["note"],
        "",
        f"- Config SHA-256: `{payload['meta']['config_sha256']}`",
        f"- Git: `{payload['meta']['git']['commit']}` (dirty={payload['meta']['git']['dirty']})",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    payload = run_vortex_loop_check()
    print(payload["result"]["verdict"])
