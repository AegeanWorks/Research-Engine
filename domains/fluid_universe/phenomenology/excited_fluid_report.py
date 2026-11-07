"""First-excited-state node report (claim 24, ADR-015)."""

from __future__ import annotations

import math

import numpy as np

from domains.fluid_universe.theory.excited_fluid import (
    excited_density,
    excited_quantum_pressure_regular,
    excited_wavefunction,
    phase_gradient_max,
    phase_slip,
    scaling_slope,
)
from domains.fluid_universe.theory.madelung import fluid_fields

from .provenance import RESULTS_DIR, metadata, write_json, write_text_atomic

LENGTH = 20.0
GRIDS = (256, 512, 1024, 2048)
COMPARISON_N = 1024
COMPARISON_X = 1.0


def run_excited_fluid_check(write: bool = True) -> dict:
    dx_values = []
    gradients = []
    for n in GRIDS:
        dx = LENGTH / n
        x = (np.arange(n) - n // 2) * dx
        psi = excited_wavefunction(x, 1.0)
        dx_values.append(dx)
        gradients.append(phase_gradient_max(psi, dx))
    slope = scaling_slope(np.array(dx_values), np.array(gradients))

    dx = LENGTH / COMPARISON_N
    x = (np.arange(COMPARISON_N) - COMPARISON_N // 2) * dx
    psi = excited_wavefunction(x, 1.0)
    density = excited_density(x, 1.0)
    _rho, _velocity, quantum = fluid_fields(psi, dx)
    index = int(np.argmin(np.abs(x - COMPARISON_X)))
    numerical_q = float(quantum[index])
    analytic_q = float(
        excited_quantum_pressure_regular(np.array([x[index]]), 1.0)[0]
    )
    relative_q_error = abs(numerical_q - analytic_q) / abs(analytic_q)

    node_density = float(
        excited_density(np.array([0.0]), 1.0)[0]
    )
    slip = phase_slip(psi)

    result = {
        "grids": list(GRIDS),
        "dx_values": dx_values,
        "phase_gradient_max": gradients,
        "gradient_scaling_slope": slope,
        "phase_slip": slip,
        "node_density": node_density,
        "regular_quantum_pressure": {
            "x": float(x[index]),
            "numerical": numerical_q,
            "analytic": analytic_q,
            "relative_error": float(relative_q_error),
        },
        "verdict": {
            "regular_representation": False,
            "claim_24_status": "FALSIFIED (node phase slip)",
            "note": (
                "The density vanishes at x=0, the phase jumps by pi, and the "
                "discrete phase gradient diverges as 1/dx. The regular quantum "
                "pressure matches away from the node, but the node is a phase "
                "slip, not a regular single-valued fluid point. A two-component "
                "or defect model is required."
            ),
        },
    }
    config = {
        "length": LENGTH,
        "grids": list(GRIDS),
        "comparison_n": COMPARISON_N,
        "comparison_x": COMPARISON_X,
        "scope": "first-excited-state node singularity; regular pressure away from node",
    }
    payload = {"meta": metadata(config), "result": result}
    if write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        write_json(RESULTS_DIR / "excited_fluid.json", payload)
        write_text_atomic(
            RESULTS_DIR / "excited_fluid.md", render_markdown(payload)
        )
    return payload


def render_markdown(payload: dict) -> str:
    result = payload["result"]
    regular = result["regular_quantum_pressure"]
    verdict = result["verdict"]
    lines = [
        "# First excited state and the node singularity (claim 24)",
        "",
        "psi_1 has a node at x=0; the density vanishes and the phase jumps by pi.",
        "",
        "## Phase slip",
        "",
        f"- Phase slip: {result['phase_slip']:.9f} (pi = {math.pi:.9f}).",
        f"- Node density: {result['node_density']:.3e}.",
        "",
        "| N | dx | max |phase gradient| |",
        "|---:|---:|---:|",
    ]
    for n, dx, gradient in zip(
        result["grids"], result["dx_values"], result["phase_gradient_max"]
    ):
        lines.append(f"| {n} | {dx:.9f} | {gradient:.9f} |")
    lines += [
        "",
        f"- Scaling slope: {result['gradient_scaling_slope']:.9f} "
        "(expected -1).",
        "",
        "## Regular quantum pressure away from the node",
        "",
        f"- x={regular['x']:.9f}: numerical {regular['numerical']:.12f}, "
        f"analytic {regular['analytic']:.12f}, "
        f"relative error {regular['relative_error']:.3e}.",
        "",
        "## Verdict",
        "",
        f"- Regular representation: **{verdict['regular_representation']}**.",
        f"- Claim 24: **{verdict['claim_24_status']}**.",
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
    payload = run_excited_fluid_check()
    print(payload["result"]["verdict"])
