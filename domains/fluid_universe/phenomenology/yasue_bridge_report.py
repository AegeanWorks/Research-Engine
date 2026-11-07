"""Pinned-endpoint Yasue bridge: the c<0 Pinney analytic family (claim 56, ADR-048).

Zero free parameters, no full-field claims. The Yasue width ODE with
c = -nu^2 admits the Pinney form with constraint A*C - B^2 = -nu^2;
endpoint pinning selects B_1 = 0.3660254038 (admissible: the recorded
claim-55 arc) and B_2 = -1.3660254038 (inadmissible: s^2 < 0
mid-interval, reported as the killed sibling). The omega = 2 scaling
preserves the structure; the nu -> 0 limit is the oscillator bridge
with peak 1.0823922003*a.

Kill logic: a nonzero ODE residual or a missed attribution FALSIFIES
the family; an admissible B_2 is a branch-count surprise (FALSIFIED,
re-scoped); a Jacobi zero caps the arc as saddle-like (FALSIFIED,
recorded not promoted). disc < 0 or non-attainment at a target point
is UNVERIFIED (bridge analysis needed), never a falsification.
"""

from __future__ import annotations

import json
import math

import numpy as np

from domains.fluid_universe.theory.yasue_bridge import (
    ATTRIB_TOL,
    FD_TOL,
    FIXED_A,
    GRID_N,
    NU_SERIES,
    RECORDED_S0_FACTOR,
    RESID_TOL,
    S1_HORIZON_FACTORS,
    S1_S0_FACTORS,
    attribution_diff,
    diffusivity,
    fd_ode_residual,
    horizon,
    jacobi_first_zero_yasue,
    newton_width,
    nu_limit_bridge,
    pinney_coeffs_yasue,
    pinney_path,
)
from domains.fluid_universe.theory.gaussian_fluid import quantum_width

from .provenance import RESULTS_DIR, metadata, write_json, write_text_atomic

NU0_PEAK = 1.0823922003
B1_REF = 0.3660254037844386
B2_REF = -1.3660254037844386


def _load_arc_profile() -> dict:
    payload = json.loads((RESULTS_DIR / "yasue_center.json").read_text())
    return payload["result"]["scales"]["arc_profile"]


def run_yasue_bridge_check(write: bool = True) -> dict:
    omega, hbar, mass = 1.0, 1.0, 1.0
    nu = diffusivity(hbar, mass)
    sq = quantum_width(omega, hbar, mass)
    T = horizon(omega)
    arc = _load_arc_profile()
    arc_interior = arc["sg"]

    branches, disc = pinney_coeffs_yasue(sq, sq, T, omega, hbar, mass)
    admissible = [b for b in branches if b["admissible"]]
    inadmissible = [b for b in branches if not b["admissible"]]
    b1 = admissible[0] if admissible else None
    grid = np.linspace(0.0, T, GRID_N)
    analytic_interior = (
        pinney_path(b1, grid, omega)[1:-1].tolist() if b1 else None
    )
    fd = fd_ode_residual(b1, omega, hbar, mass, T) if b1 else None
    constraint = (
        abs(b1["A"] * b1["C"] - b1["B"] * b1["B"] + nu * nu)
        if b1
        else None
    )
    attrib = (
        attribution_diff(analytic_interior, arc_interior)
        if analytic_interior
        else None
    )
    fine_t = np.linspace(0.0, T, 20001)
    fine_s = pinney_path(b1, fine_t, omega) if b1 else None
    jacobi_zero = (
        jacobi_first_zero_yasue(fine_t, fine_s, omega, nu)
        if b1 is not None
        else "skipped"
    )
    q_vals = (
        (-3.0 * nu * nu / np.maximum(fine_s, 1e-12) ** 4 + omega * omega)
        if b1 is not None
        else None
    )

    b2_min = inadmissible[0]["min_s2"] if inadmissible else None

    nu_limit = nu_limit_bridge()
    nu_series = []
    for nu_i in NU_SERIES:
        solves = newton_width(FIXED_A, FIXED_A, T, omega, hbar, mass, nu=nu_i)
        best = min(solves, key=lambda s: s["max_residual"])
        peak_ratio = best["max_sigma"] / FIXED_A if best["max_sigma"] else None
        nu_series.append(
            {
                "nu": nu_i,
                "attained": all(s["converged"] for s in solves),
                "best_residual": best["max_residual"],
                "peak_ratio": peak_ratio,
            }
        )

    om2, sq2, T2 = 2.0, quantum_width(2.0, hbar, mass), horizon(2.0)
    branches2, disc2 = pinney_coeffs_yasue(sq2, sq2, T2, om2, hbar, mass)
    adm2 = [b for b in branches2 if b["admissible"]]
    b1_2 = adm2[0] if adm2 else None
    solves2 = newton_width(sq2, sq2, T2, om2, hbar, mass)
    best2 = min(solves2, key=lambda s: s["max_residual"])
    grid2 = np.linspace(0.0, T2, GRID_N)
    analytic2 = pinney_path(b1_2, grid2, om2)[1:-1].tolist() if b1_2 else None
    attrib2 = attribution_diff(analytic2, best2["interior"]) if analytic2 else None
    fine_t2 = np.linspace(0.0, T2, 20001)
    fine_s2 = pinney_path(b1_2, fine_t2, om2) if b1_2 else None
    jacobi_zero2 = (
        jacobi_first_zero_yasue(fine_t2, fine_s2, om2, nu)
        if b1_2 is not None
        else "skipped"
    )

    s1_map = []
    for f in S1_S0_FACTORS:
        for hf in S1_HORIZON_FACTORS:
            T_i = hf * T
            s0_i = f * sq
            bi, di = pinney_coeffs_yasue(s0_i, sq, T_i, omega, hbar, mass)
            s1_map.append(
                {
                    "s0_factor": f,
                    "horizon_factor": hf,
                    "disc": di,
                    "n_branches": len(bi),
                    "n_admissible": sum(1 for b in bi if b["admissible"]),
                }
            )

    hard = [
        ("ode_identity", fd is None or fd["max_abs"] > FD_TOL),
        ("constraint", constraint is None or constraint > 1e-12),
        ("attribution", attrib is None or attrib > ATTRIB_TOL),
        ("b1_admissible", b1 is None or not b1["admissible"]),
        (
            "b2_inadmissible",
            b2_min is None or b2_min >= 0.0 or len(inadmissible) == 0,
        ),
        ("jacobi", False),
        (
            "nu_limit",
            abs(nu_series[-1]["peak_ratio"] - NU0_PEAK) > 1e-4
            if nu_series[-1]["peak_ratio"]
            else True,
        ),
        (
            "scaling_branches",
            b1_2 is None
            or abs(b1_2["B"] - B1_REF) > 1e-9
            or attrib2 is None
            or attrib2 > ATTRIB_TOL
            or (jacobi_zero2 is not None and jacobi_zero2 != "skipped"),
        ),
    ]
    # Jacobi zero is a real finding: normalize the check outcome first.
    jacobi_found = jacobi_zero is not None and jacobi_zero != "skipped"
    hard = [(n, k if n != "jacobi" else jacobi_found) for n, k in hard]
    soft = [
        ("disc_recorded", disc < 0.0),
        ("nu_attainment", any(not s["attained"] for s in nu_series)),
        ("scaling_attainment", not best2["converged"]),
    ]
    dead_hard = sorted(n for n, k in hard if k)
    dead_soft = sorted(n for n, k in soft if k)
    if dead_soft:
        status = f"UNVERIFIED ({'; '.join(dead_soft)})"
    elif dead_hard:
        if "jacobi" in dead_hard:
            status = f"FALSIFIED (saddle-like cap; {'; '.join(dead_hard)})"
        else:
            status = f"FALSIFIED ({'; '.join(dead_hard)})"
    else:
        status = "NUMERIC (Yasue-bridge analytic family demonstrated)"

    result = {
        "scales": {
            "base": {"omega": omega, "hbar": hbar, "mass": mass, "nu": nu},
            "recorded_point": {
                "s0": sq,
                "sT": sq,
                "T": T,
                "disc": disc,
                "branches": [
                    {
                        k: b[k]
                        for k in ("A", "B", "C", "min_s2", "admissible")
                    }
                    for b in branches
                ],
                "b1": {k: b1[k] for k in ("A", "B", "C")} if b1 else None,
                "b2_min_s2": b2_min,
                "fd_max_abs": fd["max_abs"] if fd else None,
                "fd_rms": fd["rms"] if fd else None,
                "constraint_dev": constraint,
                "attribution_max_abs": attrib,
                "analytic_interior": analytic_interior,
                "jacobi_first_zero": jacobi_zero,
                "q_min": float(np.min(q_vals)) if q_vals is not None else None,
                "q_max": float(np.max(q_vals)) if q_vals is not None else None,
            },
            "nu_limit": nu_limit,
            "nu_series": nu_series,
            "scaling": {
                "omega": om2,
                "disc": disc2,
                "b1": {k: b1_2[k] for k in ("A", "B", "C")} if b1_2 else None,
                "attribution_max_abs": attrib2,
                "jacobi_first_zero": jacobi_zero2,
                "attained": best2["converged"],
                "best_residual": best2["max_residual"],
            },
            "s1_map": s1_map,
        },
        "gates": {
            "resid_tol": RESID_TOL,
            "fd_tol": FD_TOL,
            "attrib_tol": ATTRIB_TOL,
            "kills_hard": [[n, bool(k)] for n, k in hard],
            "kills_soft": [[n, bool(k)] for n, k in soft],
        },
        "verdict": {
            "claim_56_status": status,
            "note": (
                "c<0 Pinney form satisfies the Yasue ODE; endpoint pinning "
                "gives B_1 admissible (recorded arc) and B_2 inadmissible; "
                "Jacobi zero-free; scaling preserves structure; nu->0 is "
                "the oscillator bridge."
                if status.startswith("NUMERIC")
                else status
            ),
        },
    }
    config = {
        "grids": {"n": GRID_N},
        "base": {"omega": omega, "hbar": hbar, "mass": mass},
        "recorded": {"s0_factor": RECORDED_S0_FACTOR, "T_fraction": 0.25},
        "nu_series": list(NU_SERIES),
        "gates": {
            "resid_tol": RESID_TOL,
            "fd_tol": FD_TOL,
            "attrib_tol": ATTRIB_TOL,
        },
        "scope": "Ritz trial BVP, zero parameters, no full-field claim",
    }
    payload = {"meta": metadata(config), "result": result}
    if write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        write_json(RESULTS_DIR / "yasue_bridge.json", payload)
        write_text_atomic(RESULTS_DIR / "yasue_bridge.md", render_markdown(payload))
    return payload


def render_markdown(payload: dict) -> str:
    result = payload["result"]
    scales = result["scales"]
    verdict = result["verdict"]
    rec = scales["recorded_point"]
    lines = [
        "# Yasue-bridge analytic family (claim 56)",
        "",
        "c<0 Pinney form with endpoint pinning: B_1 admissible (recorded arc), B_2 inadmissible.",
        "",
        "| check | value |",
        "|---|---|",
        f"| disc (recorded point) | {rec['disc']:.6f} |",
        f"| B_1 / B_2 | {rec['branches'][0]['B'] if rec['branches'] else None} / {rec['branches'][1]['B'] if len(rec['branches']) > 1 else None} |",
        f"| B_2 min s2 (must be < 0) | {rec['b2_min_s2']} |",
        f"| ODE FD max residual | {rec['fd_max_abs']:.3e} |",
        f"| constraint deviation | {rec['constraint_dev']:.3e} |",
        f"| attribution max-abs | {rec['attribution_max_abs']:.3e} |",
        f"| Jacobi first zero | {rec['jacobi_first_zero']} |",
        f"| Q range on arc | [{rec['q_min']:.3f}, {rec['q_max']:.3f}] |",
    ]
    for entry in scales["nu_series"]:
        lines.append(
            f"| nu={entry['nu']} | attained={entry['attained']}, "
            f"peak={entry['peak_ratio']}, res={entry['best_residual']:.3e} |"
        )
    lines.append(
        f"| scaling B_1 / attrib / jacobi "
        f"| {scales['scaling']['b1']['B'] if scales['scaling']['b1'] else None} / "
        f"{scales['scaling']['attribution_max_abs']} / "
        f"{scales['scaling']['jacobi_first_zero']} |"
    )
    lines += [
        "",
        "## Verdict",
        "",
        f"- Claim 56: **{verdict['claim_56_status']}**.",
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
    payload = run_yasue_bridge_check()
    print(payload["result"]["verdict"])
