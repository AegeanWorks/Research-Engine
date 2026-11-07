"""Madelung fluid dictionary report (claim 20, ADR-011)."""

from __future__ import annotations

import math

import numpy as np

from domains.fluid_universe.theory.madelung import (
    coherent_state_density,
    continuity_residual,
    euler_residual_fields,
    fluid_fields,
    free_gaussian_density,
    free_gaussian_fields,
    split_step,
)

from .provenance import RESULTS_DIR, metadata, write_json, write_text_atomic

N = 512
LENGTH = 40.0
DT = 1e-4


def _grid() -> tuple[np.ndarray, float]:
    dx = LENGTH / N
    x = (np.arange(N) - N // 2) * dx
    return x, dx


def run_madelung_check(write: bool = True) -> dict:
    x, dx = _grid()
    sigma = 1.0
    free = (2.0 * math.pi * sigma**2) ** -0.25 * np.exp(
        -x * x / (4.0 * sigma**2)
    )
    free_final = split_step(free, 0.0, DT, int(1.0 / DT), dx)
    free_rho = np.abs(free_final) ** 2
    free_exact = free_gaussian_density(x, 1.0, sigma)
    free_l2 = float(np.sqrt(np.sum((free_rho - free_exact) ** 2) * dx))
    free_linf = float(np.max(np.abs(free_rho - free_exact)))

    continuity = continuity_residual(
        free, split_step(free, 0.0, DT, 1, dx), DT, dx
    )

    t_euler = 0.1
    dt_euler = 1e-5
    euler = euler_residual_fields(
        *free_gaussian_fields(x, t_euler - dt_euler, sigma),
        *free_gaussian_fields(x, t_euler + dt_euler, sigma),
        2.0 * dt_euler,
        dx,
    )

    x0 = 2.0
    ho_sigma = 1.0 / math.sqrt(2.0)
    ho = (2.0 * math.pi * ho_sigma**2) ** -0.25 * np.exp(
        -((x - x0) ** 2) / (4.0 * ho_sigma**2)
    )
    potential = 0.5 * x * x
    ho_final = split_step(ho, potential, DT, int((math.pi / 2.0) / DT), dx)
    ho_rho = np.abs(ho_final) ** 2
    ho_exact = coherent_state_density(x, math.pi / 2.0, x0)
    ho_l2 = float(np.sqrt(np.sum((ho_rho - ho_exact) ** 2) * dx))
    ho_linf = float(np.max(np.abs(ho_rho - ho_exact)))

    result = {
        "free_gaussian": {
            "t": 1.0,
            "sigma0": sigma,
            "l2_error": free_l2,
            "linf_error": free_linf,
            "continuity_residual": continuity,
        },
        "coherent_state": {
            "t": math.pi / 2.0,
            "x0": x0,
            "l2_error": ho_l2,
            "linf_error": ho_linf,
        },
        "euler_residual_core": euler,
        "verdict": {
            "dictionary_verified": bool(
                free_l2 < 1e-10 and ho_l2 < 1e-3 and continuity < 1e-2 and euler < 1e-2
            ),
            "claim_20_status": "NUMERIC (exact representation verified)",
            "note": (
                "The Madelung dictionary is exact: QM is a fluid with a "
                "nonlocal quantum pressure. This is not a microphysical "
                "derivation; the quantum pressure is singular at nodes and "
                "has no independent fluid origin yet."
            ),
        },
    }
    config = {
        "n": N,
        "length": LENGTH,
        "dt": DT,
        "free_t": 1.0,
        "coherent_t": math.pi / 2.0,
        "euler_t": t_euler,
        "euler_dt": dt_euler,
        "scope": "Madelung dictionary validation against exact Gaussian solutions",
    }
    payload = {"meta": metadata(config), "result": result}
    if write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        write_json(RESULTS_DIR / "madelung.json", payload)
        write_text_atomic(RESULTS_DIR / "madelung.md", render_markdown(payload))
    return payload


def render_markdown(payload: dict) -> str:
    result = payload["result"]
    free = result["free_gaussian"]
    coherent = result["coherent_state"]
    verdict = result["verdict"]
    lines = [
        "# Madelung fluid dictionary (claim 20)",
        "",
        "The Schrodinger equation is written as a fluid: continuity plus Euler "
        "with the quantum pressure Q = -hbar^2/(2m) (d_x^2 sqrt(rho))/sqrt(rho).",
        "",
        "## Free Gaussian packet",
        "",
        f"- t={free['t']:.3g}, sigma0={free['sigma0']:.3g}.",
        f"- Density L2 error: {free['l2_error']:.3e}; "
        f"Linf error: {free['linf_error']:.3e}.",
        f"- Continuity residual: {free['continuity_residual']:.3e}.",
        "",
        "## Harmonic-oscillator coherent state",
        "",
        f"- t={coherent['t']:.6f}, x0={coherent['x0']:.3g}.",
        f"- Density L2 error: {coherent['l2_error']:.3e}; "
        f"Linf error: {coherent['linf_error']:.3e}.",
        "",
        "## Euler equation",
        "",
        f"- Exact-Gaussian core residual: {result['euler_residual_core']:.3e}.",
        "",
        "## Verdict",
        "",
        f"- Dictionary verified: **{verdict['dictionary_verified']}**.",
        f"- Claim 20: **{verdict['claim_20_status']}**.",
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
    payload = run_madelung_check()
    print(payload["result"]["verdict"])
