"""Result payload for the 1D simulation baseline."""

from __future__ import annotations

import numpy as np

from domains.fluid_universe.sims.core import (
    analytic_kink,
    energy,
    gradient_error,
    gradient_flow,
    grid,
    hessian,
    kink_convergence,
    relax_kink,
    rotor_crosscheck,
)

from .provenance import RESULTS_DIR, metadata, write_json, write_text_atomic


def run_1d_baseline(write: bool = True) -> dict:
    mu = 1.0
    length = 30.0
    convergence = kink_convergence(mu=mu, length=length)
    x, dx = grid(length, 401)
    phi = analytic_kink(x, mu)
    perturbation = 0.05 * np.sin(2.0 * np.pi * (x + length / 2.0) / length)
    perturbed = phi + perturbation
    perturbed[0] = phi[0]
    perturbed[-1] = phi[-1]
    grad_error = gradient_error(perturbed, dx, mu)
    dt = 0.05 * dx**2
    flowed, energies = gradient_flow(perturbed, dx, mu, dt=dt, steps=200)
    monotone = bool(np.all(np.diff(energies) <= 1e-10))
    relaxed, relax_info = relax_kink(phi, dx, mu)
    kink_hessian = hessian(relaxed, dx, mu)
    vacuum = np.zeros_like(phi)
    vacuum_hessian = hessian(vacuum, dx, mu)
    kink_eigs = np.linalg.eigvalsh(kink_hessian)
    near_zero_count = int(np.sum(np.abs(kink_eigs) < 1e-4))
    vacuum_eigs = np.linalg.eigvalsh(vacuum_hessian)
    rotor = rotor_crosscheck()
    payload = {
        "meta": metadata(
            {
                "mu": mu,
                "length": length,
                "kink_sizes": [row["n"] for row in convergence["rows"]],
                "flow_n": 401,
                "flow_steps": 200,
                "flow_dt": dt,
                "seed": "none (fixed perturbation)",
            }
        ),
        "kink": convergence,
        "gradient": {
            "max_relative_error": grad_error,
            "tolerance": 1e-6,
            "passes": bool(grad_error < 1e-6),
        },
        "flow": {
            "energy_initial": float(energies[0]),
            "energy_final": float(energies[-1]),
            "monotone": monotone,
            "max_increase": float(np.max(np.diff(energies))),
        },
        "hessian": {
            "symmetric_kink": bool(np.allclose(kink_hessian, kink_hessian.T)),
            "relaxation": relax_info,
            "kink_min_eigenvalue": float(kink_eigs[0]),
            "kink_max_eigenvalue": float(kink_eigs[-1]),
            "vacuum_min_eigenvalue": float(vacuum_eigs[0]),
            "vacuum_max_eigenvalue": float(vacuum_eigs[-1]),
            "near_zero_count": near_zero_count,
            "zero_mode_counting": "one lifted translation mode counted as near-zero; no exact zero mode with Dirichlet boundaries",
        },
        "rotor": rotor,
        "verdict": {
            "baseline_1_kink": bool(abs(convergence["rows"][-1]["relative_error"]) < 1e-2),
            "baseline_2_gradient": bool(grad_error < 1e-6),
            "baseline_3_monotone": monotone,
            "baseline_6_rotor": bool(rotor["abs_delta_E0"] < 1e-3 and rotor["abs_delta_E1"] < 1e-3),
            "baseline_7_hessian_partial": bool(
                np.allclose(kink_hessian, kink_hessian.T)
                and kink_eigs[0] > -1e-4
                and vacuum_eigs[0] > 0.0
                and near_zero_count >= 1
            ),
            "production_ready": False,
            "claim_15_status": "UNVERIFIED / NOT ACHIEVED",
            "note": (
                "1D baselines only. No 3D lattice, no Hopf charge, no Z3 order parameter, "
                "and no production run. The earlier lost-run numbers are not used."
            ),
        },
    }
    if write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        write_json(RESULTS_DIR / "sim_core.json", payload)
        write_text_atomic(RESULTS_DIR / "sim_core.md", render_markdown(payload))
    return payload


def render_markdown(payload: dict) -> str:
    k = payload["kink"]
    v = payload["verdict"]
    lines = [
        "# 1D simulation baseline",
        "",
        "This is a validation baseline, not a 3D Hopfion result. "
        "Energy: E = int dx [1/2 (dphi/dx)^2 + mu(1-cos 3phi)], Dirichlet boundaries.",
        "",
        "## Kink convergence",
        "",
        "| N | dx | energy | energy - T | relative error |",
        "|---:|---:|---:|---:|---:|",
    ]
    for row in k["rows"]:
        lines.append(
            f"| {row['n']} | {row['dx']:.6f} | {row['energy']:.12f} | "
            f"{row['error_vs_tension']:+.6e} | {row['relative_error']:+.3e} |"
        )
    lines += [
        "",
        f"Analytic tension T = (8/3) sqrt(mu) = {k['tension']:.12f}. "
        f"Observed orders: {', '.join(f'{x:.2f}' for x in k['observed_orders'])}.",
        "",
        "## Baselines",
        "",
        f"- Gradient check: max relative error = {payload['gradient']['max_relative_error']:.3e} "
        f"(pass = {payload['gradient']['passes']}).",
        f"- Gradient flow: E {payload['flow']['energy_initial']:.12f} -> "
        f"{payload['flow']['energy_final']:.12f}; monotone = {payload['flow']['monotone']}.",
        f"- Hessian: symmetric = {payload['hessian']['symmetric_kink']}; "
        f"kink min eigenvalue = {payload['hessian']['kink_min_eigenvalue']:.3e}; "
        f"vacuum min eigenvalue = {payload['hessian']['vacuum_min_eigenvalue']:.6f}; "
        f"near-zero count = {payload['hessian']['near_zero_count']}.",
        f"- Rotor: |E0 Fourier - grid| = {payload['rotor']['abs_delta_E0']:.3e}; "
        f"|E1 Fourier - grid| = {payload['rotor']['abs_delta_E1']:.3e}.",
        "",
        "## Verdicts",
        "",
        f"- Baseline 1 (kink): {v['baseline_1_kink']}",
        f"- Baseline 2 (gradient): {v['baseline_2_gradient']}",
        f"- Baseline 3 (monotone flow): {v['baseline_3_monotone']}",
        f"- Baseline 6 (rotor): {v['baseline_6_rotor']}",
        f"- Baseline 7 (Hessian, partial): {v['baseline_7_hessian_partial']}",
        f"- Production ready: {v['production_ready']}",
        f"- Claim 15: {v['claim_15_status']}",
        "",
        v["note"],
        "",
        f"- Config SHA-256: `{payload['meta']['config_sha256']}`",
        f"- Git: `{payload['meta']['git']['commit']}` (dirty={payload['meta']['git']['dirty']})",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    print(run_1d_baseline()["verdict"])
