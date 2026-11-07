"""Pinned-endpoint Yasue-bridge action stationarity (claim 57, ADR-049).

Zero free parameters, no full-field claims. The discrete midpoint
Yasue action on the Newton B_1 arc agrees with the continuous-action
quadrature on the analytic B_1 path; the 2-shape variation probe is
flat to solver precision; the nu = 0 action equals the closed-form
oscillator-bridge value -m*w*a^2*alpha = -0.2071067812 at a^2 = 0.5
(the Stage-1 value -0.4142135624 was the a^2 = 1 value, caught by the
swarm and corrected here). The B_2 form admits no action (s^2 < 0).

Kill logic: discrete-vs-analytic mismatch > 1e-4 FALSIFIES the
stationarity (either the arc is not action-stationary or the
discretization is inconsistent); a classical mismatch > 1e-4 or a
probe slope > 1e-6 FALSIFIES the same way. Newton non-attainment at a
target is UNVERIFIED (bridge-analysis failure), never a falsification.
"""

from __future__ import annotations

import numpy as np

from domains.fluid_universe.theory.yasue_action import (
    ACTION_TOL,
    BASE,
    FIXED_A,
    GRID_N,
    GRID_STARTS,
    NU_SERIES,
    PROBE_BUMPS,
    PROBE_TOL,
    QUAD_N,
    RESID_TOL,
    S1_HORIZON_FACTORS,
    S1_S0_FACTORS,
    classical_bridge_action,
    probe_slope,
    variation_probe,
    yasue_analytic_action,
    yasue_discrete_action,
)
from domains.fluid_universe.theory.yasue_bridge import (
    diffusivity,
    horizon,
    newton_width,
    pinney_coeffs_yasue,
    pinney_path,
)
from domains.fluid_universe.theory.gaussian_fluid import quantum_width

from .provenance import RESULTS_DIR, metadata, write_json, write_text_atomic


def run_yasue_action_check(write: bool = True) -> dict:
    omega, hbar, mass = BASE["omega"], BASE["hbar"], BASE["mass"]
    nu = diffusivity(hbar, mass)
    sq = quantum_width(omega, hbar, mass)
    T = horizon(omega)
    grid = np.linspace(0.0, T, GRID_N)
    dt = T / (GRID_N - 1)

    branches, disc = pinney_coeffs_yasue(sq, sq, T, omega, hbar, mass)
    b1 = next(b for b in branches if b["admissible"])
    b2 = next(b for b in branches if not b["admissible"])
    analytic_path = pinney_path(b1, grid, omega)
    solves = newton_width(sq, sq, T, omega, hbar, mass)
    best = min(solves, key=lambda s: s["max_residual"])
    newton_full = np.concatenate([[sq], np.array(best["interior"]), [sq]])
    j_discrete_newton = yasue_discrete_action(
        newton_full, omega, hbar, mass, nu, dt
    )
    j_discrete_analytic = yasue_discrete_action(
        analytic_path, omega, hbar, mass, nu, dt
    )
    j_analytic = yasue_analytic_action(b1, omega, hbar, mass, nu, T)

    probes = []
    for kind in PROBE_BUMPS:
        fam = variation_probe(analytic_path, T, kind)
        for lam in (0.01, 0.02):
            row = probe_slope(
                analytic_path, fam["bump"], omega, hbar, mass, nu, dt,
                lam=lam,
            )
            probes.append(
                {"bump": kind, "lam": lam, "slope": row["slope"]}
            )

    nu_classical = classical_bridge_action(FIXED_A, omega, mass)
    nu_series = []
    for nu_i in NU_SERIES:
        rows = newton_width(FIXED_A, FIXED_A, T, omega, hbar, mass, nu=nu_i)
        top = min(rows, key=lambda s: s["max_residual"])
        full = np.concatenate([[FIXED_A], np.array(top["interior"]), [FIXED_A]])
        nu_series.append(
            {
                "nu": nu_i,
                "attained": all(s["converged"] for s in rows),
                "best_residual": top["max_residual"],
                "j_discrete": yasue_discrete_action(
                    full, omega, hbar, mass, nu_i, dt
                ),
            }
        )
    _tq = np.linspace(0.0, T, QUAD_N)
    _alpha = nu_classical["alpha"]
    _s0 = FIXED_A * (np.cos(omega * _tq) + _alpha * np.sin(omega * _tq))
    _v0 = np.gradient(_s0, _tq[1] - _tq[0])
    nu0_quad = float(
        np.trapezoid(0.5 * mass * _v0 * _v0 - 0.5 * mass * omega * omega * _s0 * _s0, _tq)
    )

    om2, sq2, T2 = 2.0, quantum_width(2.0, hbar, mass), horizon(2.0)
    branches2, disc2 = pinney_coeffs_yasue(sq2, sq2, T2, om2, hbar, mass)
    b1_2 = next(b for b in branches2 if b["admissible"])
    grid2 = np.linspace(0.0, T2, GRID_N)
    dt2 = T2 / (GRID_N - 1)
    solves2 = newton_width(sq2, sq2, T2, om2, hbar, mass)
    best2 = min(solves2, key=lambda s: s["max_residual"])
    newton_full2 = np.concatenate([[sq2], np.array(best2["interior"]), [sq2]])
    j_discrete_2 = yasue_discrete_action(
        newton_full2, om2, hbar, mass, nu, dt2
    )
    j_analytic_2 = yasue_analytic_action(b1_2, om2, hbar, mass, nu, T2)

    s1_map = []
    for f in S1_S0_FACTORS:
        for hf in S1_HORIZON_FACTORS:
            T_i, s0_i = hf * T, f * sq
            dt_i = T_i / (GRID_N - 1)
            rows = newton_width(
                s0_i, sq, T_i, omega, hbar, mass, nu=nu, starts=GRID_STARTS
            )
            top_i = min(rows, key=lambda s: s["max_residual"])
            full_i = np.concatenate([[s0_i], np.array(top_i["interior"]), [sq]])
            s1_map.append(
                {
                    "s0_factor": f,
                    "horizon_factor": hf,
                    "attained": all(s["converged"] for s in rows),
                    "best_residual": top_i["max_residual"],
                    "j_discrete": yasue_discrete_action(
                        full_i, omega, hbar, mass, nu, dt_i
                    ),
                }
            )

    hard = [
        ("action_match", abs(j_discrete_newton - j_analytic) > ACTION_TOL),
        (
            "classical_match",
            abs(nu_series[-1]["j_discrete"] - nu_classical["value"]) > ACTION_TOL,
        ),
        (
            "classical_quad",
            abs(nu0_quad - nu_classical["value"]) > 1e-6,
        ),
        ("probe", any(abs(p["slope"]) > PROBE_TOL for p in probes)),
        (
            "scaling_match",
            abs(j_discrete_2 - j_analytic_2) > ACTION_TOL,
        ),
    ]
    soft = [
        ("newton_attainment", not best["converged"]),
        ("nu_attainment", any(not s["attained"] for s in nu_series)),
        ("scaling_attainment", not best2["converged"]),
    ]
    dead_hard = sorted(n for n, k in hard if k)
    dead_soft = sorted(n for n, k in soft if k)
    if dead_soft:
        status = f"UNVERIFIED ({'; '.join(dead_soft)})"
    elif dead_hard:
        status = f"FALSIFIED ({'; '.join(dead_hard)})"
    else:
        status = "NUMERIC (Yasue-bridge action stationarity demonstrated)"

    result = {
        "scales": {
            "base": {"omega": omega, "hbar": hbar, "mass": mass, "nu": nu},
            "recorded_point": {
                "disc": disc,
                "b1": {k: b1[k] for k in ("A", "B", "C")},
                "b2": {k: b2[k] for k in ("A", "B", "C")},
                "b2_min_s2": b2["min_s2"],
                "j_discrete_newton": j_discrete_newton,
                "j_discrete_analytic_path": j_discrete_analytic,
                "j_analytic": j_analytic,
                "discrete_analytic_diff": abs(j_discrete_newton - j_analytic),
                "newton_residual": best["max_residual"],
            },
            "probes": probes,
            "classical": {
                "alpha": nu_classical["alpha"],
                "closed": nu_classical["value"],
                "quad_nu0": nu0_quad,
            },
            "nu_series": nu_series,
            "scaling": {
                "omega": om2,
                "disc": disc2,
                "b1": {k: b1_2[k] for k in ("A", "B", "C")},
                "j_discrete": j_discrete_2,
                "j_analytic": j_analytic_2,
                "diff": abs(j_discrete_2 - j_analytic_2),
                "attained": best2["converged"],
                "best_residual": best2["max_residual"],
            },
            "s1_map": s1_map,
        },
        "gates": {
            "resid_tol": RESID_TOL,
            "action_tol": ACTION_TOL,
            "probe_tol": PROBE_TOL,
            "kills_hard": [[n, bool(k)] for n, k in hard],
            "kills_soft": [[n, bool(k)] for n, k in soft],
        },
        "verdict": {
            "claim_57_status": status,
            "note": (
                "Discrete and continuous Yasue actions agree on the B_1 "
                "arc; the variation probe is flat; the nu = 0 action is "
                "the oscillator-bridge closed form; omega = 2 preserved."
                if status.startswith("NUMERIC")
                else status
            ),
        },
    }
    config = {
        "grids": {"n": GRID_N, "quad_n": QUAD_N},
        "base": {"omega": omega, "hbar": hbar, "mass": mass},
        "nu_series": list(NU_SERIES),
        "s1_grid": {
            "s0_factors": list(S1_S0_FACTORS),
            "horizon_factors": list(S1_HORIZON_FACTORS),
        },
        "gates": {
            "resid_tol": RESID_TOL,
            "action_tol": ACTION_TOL,
            "probe_tol": PROBE_TOL,
        },
        "scope": "Ritz trial BVP, zero parameters, no full-field claim",
    }
    payload = {"meta": metadata(config), "result": result}
    if write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        write_json(RESULTS_DIR / "yasue_action.json", payload)
        write_text_atomic(
            RESULTS_DIR / "yasue_action.md", render_markdown(payload)
        )
    return payload


def render_markdown(payload: dict) -> str:
    result = payload["result"]
    scales = result["scales"]
    verdict = result["verdict"]
    rec = scales["recorded_point"]
    lines = [
        "# Yasue-bridge action stationarity (claim 57)",
        "",
        "Discrete and continuous Yasue actions agree on the B_1 arc; the probe is flat; nu = 0 is the closed form.",
        "",
        "| check | value |",
        "|---|---|",
        f"| J discrete (Newton) | {rec['j_discrete_newton']:.10f} |",
        f"| J analytic (quadrature) | {rec['j_analytic']:.10f} |",
        f"| discrete-analytic diff | {rec['discrete_analytic_diff']:.3e} |",
        f"| B_2 min s2 (structural) | {rec['b2_min_s2']:.6f} |",
        f"| classical closed form | {scales['classical']['closed']:.10f} |",
        f"| nu=0 discrete / quad | {scales['nu_series'][-1]['j_discrete']:.10f} / {scales['classical']['quad_nu0']:.10f} |",
    ]
    for p in scales["probes"]:
        lines.append(
            f"| probe {p['bump']} lam={p['lam']} | slope={p['slope']:.3e} |"
        )
    lines.append(
        f"| scaling J discrete / analytic "
        f"| {scales['scaling']['j_discrete']:.10f} / {scales['scaling']['j_analytic']:.10f} |"
    )
    lines += [
        "",
        "## Verdict",
        "",
        f"- Claim 57: **{verdict['claim_57_status']}**.",
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
    payload = run_yasue_action_check()
    print(payload["result"]["verdict"])
