"""HO-1 finite-core node probe (claim 60, ADR-054).

Pre-registered eps0 = 0.1*a0 only; no eps scan. Grids N=256/512/1024/2048,
L=20. Gates frozen in ADR-054.
"""

from __future__ import annotations

import math

import numpy as np

from domains.fluid_universe.theory.excited_fluid import (
    excited_wavefunction,
    excited_quantum_pressure_regular,
    phase_gradient_max,
    phase_slip,
    scaling_slope,
)
from domains.fluid_universe.theory.vortex_core import (
    GRID_LENGTH,
    GRID_NS,
    core_phase,
    core_q_zero,
    core_radius,
    core_velocity,
    fd_q_zero,
    ho_sigma,
)

from .provenance import RESULTS_DIR, metadata, write_json, write_text_atomic

SLIP_TOL = 0.05
SLOPE_TOL = 0.01
QCONV_TOL = 0.05


def run_vortex_core_check(write: bool = True) -> dict:
    omega, hbar, mass = 1.0, 1.0, 1.0
    sigma = ho_sigma(omega, hbar, mass)
    eps0 = core_radius()
    # Singular control (apparatus must still kill): slope -1.
    dxs, gmax = [], []
    for n in GRID_NS:
        dx = GRID_LENGTH / n
        x = (np.arange(n) - n // 2) * dx
        psi = excited_wavefunction(x, omega, hbar, mass)
        dxs.append(dx)
        gmax.append(phase_gradient_max(psi, dx))
    slope = scaling_slope(np.array(dxs), np.array(gmax))
    singular_ok = abs(slope + 1.0) <= SLOPE_TOL
    # Core winding at eps0 (finest grid gates, coarser recorded).
    slips, mono = {}, {}
    for n in GRID_NS:
        dx = GRID_LENGTH / n
        x = (np.arange(n) - n // 2) * dx
        ph = core_phase(x, eps0)
        slips[n] = float(np.max(ph) - np.min(ph))
        d = np.diff(ph)
        mono[n] = bool(np.all(d <= 1e-12))
    slip_fine = slips[2048]
    winding_ok = abs(slip_fine - math.pi) <= SLIP_TOL and bool(mono[2048])
    # Core Q: analytic finite + FD N-convergence.
    q_analytic = core_q_zero(eps0, sigma, hbar, mass)
    fd = {n: fd_q_zero(eps0, n, GRID_LENGTH, sigma) for n in GRID_NS}
    q_finite = bool(math.isfinite(q_analytic) and all(math.isfinite(v) for v in fd.values()))
    conv_fine = abs(fd[2048] - q_analytic) / abs(q_analytic) <= QCONV_TOL
    conv_step = abs(fd[2048] - fd[1024]) / abs(fd[1024]) <= QCONV_TOL
    q_ok = q_finite and conv_fine and conv_step
    # Soft: far-field regular Q at x=0.996 (correspondence-only).
    q_far = float(excited_quantum_pressure_regular(np.array([0.996]), omega)[0])
    far_ok = abs(q_far - 1.003992) <= 1e-6
    hard = [
        ("singular_control_broken", not singular_ok),
        ("winding_below", (not winding_ok) and singular_ok),
        ("qcap_below", (not q_ok) and singular_ok),
    ]
    soft = [
        ("slope_attainment", not singular_ok),
        ("far_match", not far_ok),
    ]
    dead_hard = sorted(n for n, k in hard if k)
    dead_soft = sorted(n for n, k in soft if k)
    if "winding_below" in dead_hard or "qcap_below" in dead_hard:
        status = (
            "FALSIFIED (finite-core single-valued regular core insufficient: "
            "winding breaks or Q diverges at eps0)"
        )
    elif "singular_control_broken" in dead_hard:
        status = "UNVERIFIED (singular apparatus check failed; solver unreliable)"
    elif dead_soft:
        status = f"UNVERIFIED ({'; '.join(dead_soft)})"
    elif singular_ok and winding_ok and q_ok:
        status = (
            "NUMERIC (finite-core regularized defect demonstrated at eps0; "
            "winding preserved, Q finite and N-converged)"
        )
    else:
        status = "UNVERIFIED (no decision)"
    result = {
        "scales": {
            "base": {"omega": omega, "hbar": hbar, "mass": mass, "sigma": sigma},
            "eps0": eps0,
            "eps0_factor": 0.1,
            "grids": list(GRID_NS),
            "length": GRID_LENGTH,
            "singular": {"dx": dxs, "gmax": gmax, "slope": slope},
            "slips": slips,
            "monotone": mono,
            "q_analytic": q_analytic,
            "q_fd": fd,
            "q_far_0996": q_far,
        },
        "gates": {
            "slip_tol": SLIP_TOL,
            "slope_tol": SLOPE_TOL,
            "qconv_tol": QCONV_TOL,
            "kills_hard": [[n, bool(k)] for n, k in hard],
            "kills_soft": [[n, bool(k)] for n, k in soft],
        },
        "verdict": {"claim_60_status": status, "note": "HO-1 core probe only; 2p/2s queued."},
    }
    config = {
        "eps0_factor": 0.1,
        "eps0_from": "theory.hydrogen_fluid.bohr_radius",
        "grids": list(GRID_NS),
        "length": GRID_LENGTH,
        "gates": {"slip_tol": SLIP_TOL, "slope_tol": SLOPE_TOL, "qconv_tol": QCONV_TOL},
        "scope": "HO-1 finite-core node probe only; no 2p/2s claim",
    }
    payload = {"meta": metadata(config), "result": result}
    if write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        write_json(RESULTS_DIR / "vortex_core.json", payload)
        write_text_atomic(RESULTS_DIR / "vortex_core.md", render_markdown(payload))
    return payload


def render_markdown(payload: dict) -> str:
    r = payload["result"]
    s = r["scales"]
    v = r["verdict"]
    lines = [
        "# Finite-core node probe (claim 60)",
        "",
        "HO-1 complex-shift core at pre-registered eps0 = 0.1*a0.",
        "",
        "| check | value |",
        "|---|---|",
        f"| eps0 | {s['eps0']:.10f} |",
        f"| singular slope | {s['singular']['slope']:.6f} |",
        f"| slip N=2048 | {s['slips'][2048]:.8f} |",
        f"| Q analytic | {s['q_analytic']:.6f} |",
        f"| Q FD 1024/2048 | {s['q_fd'][1024]:.6f} / {s['q_fd'][2048]:.6f} |",
        f"| Q far 0.996 | {s['q_far_0996']:.6f} |",
        "",
        "## Verdict",
        "",
        f"- Claim 60: **{v['claim_60_status']}**.",
        "",
        v["note"],
        "",
        f"- Config SHA-256: `{payload['meta']['config_sha256']}`",
        f"- Git: `{payload['meta']['git']['commit']}` (dirty={payload['meta']['git']['dirty']})",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    payload = run_vortex_core_check()
    print(payload["result"]["verdict"])
