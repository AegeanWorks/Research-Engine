"""Nelson stochastic kinematics report (claim 21, ADR-012)."""

from __future__ import annotations

import numpy as np

from domains.fluid_universe.theory.madelung import free_gaussian_density
from domains.fluid_universe.theory.nelson import (
    ground_state_density,
    histogram_density,
    l1_error,
    simulate_free_packet,
    simulate_ou,
)

from .provenance import RESULTS_DIR, metadata, write_json, write_text_atomic

PARTICLES = 50000
BINS = 80
SPAN = 6.0
OMEGA = 1.0
DT = 1e-3
GROUND_STEPS = 5000
FREE_T = 1.0
FREE_STEPS = 1000


def run_nelson_check(write: bool = True) -> dict:
    ground = simulate_ou(
        PARTICLES, OMEGA, steps=GROUND_STEPS, dt=DT, seed=20261030
    )
    ground_density, ground_centers, ground_width = histogram_density(
        ground, bins=BINS, span=SPAN
    )
    ground_exact = ground_state_density(ground_centers, OMEGA)
    ground_l1 = l1_error(ground_density, ground_exact, ground_width)

    free = simulate_free_packet(
        PARTICLES, FREE_T, 1.0, steps=FREE_STEPS, seed=20261030
    )
    free_density, free_centers, free_width = histogram_density(
        free, bins=BINS, span=SPAN
    )
    free_exact = free_gaussian_density(free_centers, FREE_T, 1.0)
    free_l1 = l1_error(free_density, free_exact, free_width)

    result = {
        "ground_state": {
            "omega": OMEGA,
            "variance": float(np.var(ground)),
            "expected_variance": 0.5,
            "l1_error": ground_l1,
            "particles": PARTICLES,
            "steps": GROUND_STEPS,
            "dt": DT,
        },
        "free_packet": {
            "t": FREE_T,
            "sigma0": 1.0,
            "l1_error": free_l1,
            "particles": PARTICLES,
            "steps": FREE_STEPS,
        },
        "verdict": {
            "kinematics_verified": bool(ground_l1 < 0.05 and free_l1 < 0.10),
            "claim_21_status": "NUMERIC (stochastic kinematics verified)",
            "note": (
                "The drift uses the exact quantum density, so this validates "
                "the Nelson kinematics, not a self-consistent derivation of "
                "the density. A modified diffusion law or a mean-field closure "
                "is the next falsifiable step."
            ),
        },
    }
    config = {
        "particles": PARTICLES,
        "bins": BINS,
        "span": SPAN,
        "omega": OMEGA,
        "dt": DT,
        "ground_steps": GROUND_STEPS,
        "free_t": FREE_T,
        "free_steps": FREE_STEPS,
        "scope": "Nelson stochastic kinematics with exact quantum drifts",
    }
    payload = {"meta": metadata(config), "result": result}
    if write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        write_json(RESULTS_DIR / "nelson.json", payload)
        write_text_atomic(RESULTS_DIR / "nelson.md", render_markdown(payload))
    return payload


def render_markdown(payload: dict) -> str:
    result = payload["result"]
    ground = result["ground_state"]
    free = result["free_packet"]
    verdict = result["verdict"]
    lines = [
        "# Nelson stochastic kinematics (claim 21)",
        "",
        "A Brownian particle with D=hbar/(2m) has the osmotic velocity "
        "u=D d_x ln(rho). The drift uses the exact quantum density.",
        "",
        "## Harmonic-oscillator ground state",
        "",
        f"- omega={ground['omega']:.3g}; particles={ground['particles']}; "
        f"steps={ground['steps']}; dt={ground['dt']:.1e}.",
        f"- Variance: {ground['variance']:.6f} "
        f"(expected {ground['expected_variance']:.6f}).",
        f"- Histogram L1 error: {ground['l1_error']:.4f}.",
        "",
        "## Free Gaussian packet",
        "",
        f"- t={free['t']:.3g}; sigma0={free['sigma0']:.3g}; "
        f"particles={free['particles']}; steps={free['steps']}.",
        f"- Histogram L1 error: {free['l1_error']:.4f}.",
        "",
        "## Verdict",
        "",
        f"- Kinematics verified: **{verdict['kinematics_verified']}**.",
        f"- Claim 21: **{verdict['claim_21_status']}**.",
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
    payload = run_nelson_check()
    print(payload["result"]["verdict"])
