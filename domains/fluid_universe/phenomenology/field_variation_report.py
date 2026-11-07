"""Unstructured 1D fixed-endpoint-density G-M field variation (claim 58, ADR-050).

Zero free parameters, no full-field (>1D) claims. The discrete G-M
field action is minimized over unstructured interior densities (exact
1D flux elimination, slice-normalized mass, exp-parameterized
positivity) from adversarial starts at two tiers. The Gaussian bridge
was the predicted global minimizer; multi-start convergence was the
empirical check. The nu = 0 problem must reproduce -0.23852813742385703.

Outcome (FALSIFIED): the field does NOT re-select the Gaussian. Every
tier escapes far below the bank (coarse -3.26, fine -1.59 from the
bridge-warm start itself), still descending; the bridge Hessian has 51
negative directions on a tiny grid; the escape exploits near-vacuum
cells (min_rho ~1e-16, 31% high-frequency power). The nu = 0 control
approaches its bank (8.8e-5), validating code and banks; the failure
is specific to the nu = 0.5 landscape. Stationarity results of claims
51-57 stand untouched (a stationary principle needs no global minimum,
exactly as in Hamilton's principle); only the global-minimum reading
dies here.
"""

from __future__ import annotations

import math

import numpy as np

from domains.fluid_universe.theory.field_variation import (
    ACTION_TOL,
    ATTRIB_TOL,
    BASE,
    GRAD_TOL,
    GRID_COARSE,
    GRID_FINE,
    J_QUANTUM_BANK,
    STARTS,
    FieldProblem,
    bridge_widths,
    diffusivity,
    horizon,
)
from domains.fluid_universe.theory.gaussian_fluid import quantum_width

from .provenance import RESULTS_DIR, metadata, write_json, write_text_atomic

FINE_STARTS = ("bridge_warm", "wide")
NU0_STARTS = ("gauss_linear", "wide")
SCALING_STARTS = ("gauss_linear", "wide")


def _analytic_bridge_rho(problem: FieldProblem) -> np.ndarray:
    t = np.linspace(0.0, problem.T, problem.nt)
    s = bridge_widths(t, problem.s0, problem.omega)
    rho = np.empty((problem.nt, problem.nx))
    for k in range(problem.nt):
        rho[k] = np.exp(-problem.xc**2 / (2.0 * s[k] ** 2)) / math.sqrt(
            2.0 * math.pi * s[k] ** 2
        )
    return rho / (rho.sum(axis=1, keepdims=True) * problem.dx)


def _field_action_on_rho(problem: FieldProblem, rho: np.ndarray) -> float:
    # Exact inverse of unpack: pin the last component (subtract ITS value).
    # Max-subtraction here would corrupt the tail cell (weight 1 vs ~1e-11).
    phi = np.log(np.maximum(rho[1:-1] * problem.dx, 1e-300))
    phi = (phi - phi[:, -1:])[:, :-1]
    J, _ = problem.action_and_gradient(phi.ravel())
    return float(J)


def run_field_variation_check(write: bool = True) -> dict:
    omega, hbar, mass = BASE["omega"], BASE["hbar"], BASE["mass"]
    nu = diffusivity(hbar, mass)
    sq = quantum_width(omega, hbar, mass)
    T = horizon(omega)

    coarse = FieldProblem(GRID_COARSE[0], GRID_COARSE[1], nu, omega, mass)
    coarse_runs = [coarse.optimize(s) for s in STARTS]
    coarse_classical = FieldProblem(
        GRID_COARSE[0], GRID_COARSE[1], 0.0, omega, mass
    )
    coarse_nu0_runs = [coarse_classical.optimize(s) for s in NU0_STARTS]

    rho_bridge = _analytic_bridge_rho(coarse)
    j_bridge_field = _field_action_on_rho(coarse, rho_bridge)
    classical = _classical_transport_action(coarse.s0, coarse.sT, T, omega, mass)

    fine = FieldProblem(GRID_FINE[0], GRID_FINE[1], nu, omega, mass)
    rho_bridge_fine = _analytic_bridge_rho(fine)
    fine_runs = []
    for start in FINE_STARTS:
        if start == "bridge_warm":
            phi0 = np.log(np.maximum(rho_bridge_fine[1:-1] * fine.dx, 1e-300))
            phi0 = (phi0 - phi0[:, -1:])[:, :-1].ravel()
            from scipy.optimize import minimize

            res = minimize(
                lambda p: fine.action_and_gradient(p),
                phi0,
                jac=True,
                method="L-BFGS-B",
                options={
                    "maxiter": 2000,
                    "ftol": 1e-14,
                    "gtol": 1e-9,
                    "maxcor": 20,
                },
            )
            J, grad = fine.action_and_gradient(res.x)
            grad_inf = float(np.max(np.abs(grad)))
            rho = fine.unpack(res.x)
            fine_runs.append(
                {
                    "start": start,
                    "J_final": J,
                    "grad_inf": grad_inf,
                    "converged": bool(grad_inf <= GRAD_TOL),
                    "nit": int(res.nit),
                    "nfev": int(res.nfev),
                    "message": str(res.message),
                    "interior": rho[1:-1].tolist(),
                    "mass_err": float(
                        np.max(np.abs(rho.sum(axis=1) * fine.dx - 1.0))
                    ),
                    "min_rho": float(np.min(rho)),
                }
            )
        else:
            out = fine.optimize(start)
            fine_runs.append(out)
    best_fine = min(fine_runs, key=lambda r: r["J_final"])
    t_fine = np.linspace(0.0, T, GRID_FINE[1])
    s_bridge_fine = bridge_widths(t_fine, fine.s0, omega)
    rho_bf = np.empty((GRID_FINE[1], GRID_FINE[0]))
    for k in range(GRID_FINE[1]):
        s = s_bridge_fine[k]
        rho_bf[k] = np.exp(-fine.xc**2 / (2.0 * s * s)) / math.sqrt(
            2.0 * math.pi * s * s
        )
    rho_bf = rho_bf / (rho_bf.sum(axis=1, keepdims=True) * fine.dx)
    attrib = float(
        np.max(np.abs(np.array(best_fine["interior"]) - rho_bf[1:-1]))
    )

    om2 = 2.0
    scaling = FieldProblem(GRID_COARSE[0], GRID_COARSE[1], nu, om2, 1.0)
    scaling_runs = [scaling.optimize(s) for s in SCALING_STARTS]
    rho_sc_bridge = _analytic_bridge_rho(scaling)
    j_sc_bridge = _field_action_on_rho(scaling, rho_sc_bridge)

    lam_grid = [0.0, 0.25, 0.5, 0.75, 1.0]
    segments = {}
    for name in ("bimodal", "wide"):
        from domains.fluid_universe.theory.field_variation import start_fields

        target = start_fields(
            "bimodal" if name == "bimodal" else "wide",
            coarse.n_interior,
            coarse.xc,
            coarse.dx,
            coarse.rho0,
            coarse.rhoT,
            coarse.sq,
        )
        base = start_fields(
            "gauss_linear",
            coarse.n_interior,
            coarse.xc,
            coarse.dx,
            coarse.rho0,
            coarse.rhoT,
            coarse.sq,
        )
        full_base = np.concatenate([[coarse.rho0], base, [coarse.rhoT]])
        vals = []
        for lam in lam_grid:
            mix = (1.0 - lam) * full_base[1:-1] + lam * target
            mix = mix / (mix.sum(axis=1, keepdims=True) * coarse.dx)
            full = np.concatenate([[coarse.rho0], mix, [coarse.rhoT]])
            phi = np.log(np.maximum(full[1:-1] * coarse.dx, 1e-300))
            phi = (phi - phi[:, -1:])[:, :-1]
            vals.append(float(coarse.action_and_gradient(phi.ravel())[0]))
        segments[name] = vals

    bank = J_QUANTUM_BANK
    all_runs = coarse_runs + fine_runs
    below = [r for r in all_runs if r["J_final"] < bank - ACTION_TOL]
    fine_below = [r for r in fine_runs if r["J_final"] < bank - ACTION_TOL]
    hard = [
        ("escape_below", len(fine_below) > 0),
        ("path_match", attrib > ATTRIB_TOL),
        (
            "classical_match",
            any(
                r["converged"] and abs(r["J_final"] - classical["value"]) > ACTION_TOL
                for r in coarse_nu0_runs
            ),
        ),
        (
            "scaling_match",
            min(r["J_final"] for r in scaling_runs) > j_sc_bridge + ACTION_TOL
            or max(r["J_final"] for r in scaling_runs) < j_sc_bridge - ACTION_TOL,
        ),
    ]
    soft = [
        ("coarse_attainment", any(not r["converged"] for r in coarse_runs)),
        ("fine_attainment", any(not r["converged"] for r in fine_runs)),
        ("nu0_attainment", any(not r["converged"] for r in coarse_nu0_runs)),
        ("scaling_attainment", any(not r["converged"] for r in scaling_runs)),
        (
            "coarse_below_unconfirmed",
            len([r for r in coarse_runs if r["J_final"] < bank - ACTION_TOL]) > 0
            and len(fine_below) == 0,
        ),
        (
            "higher_non_gaussian",
            any(
                r["converged"] and r["J_final"] > bank + ACTION_TOL
                for r in all_runs
            ),
        ),
    ]
    dead_hard = sorted(n for n, k in hard if k)
    dead_soft = sorted(n for n, k in soft if k)
    if dead_hard:
        if "escape_below" in dead_hard:
            status = (
                "FALSIFIED (unstructured field escapes far below the bank; "
                "trial-class global minimality dead; "
                f"{'; '.join(dead_hard)})"
            )
        else:
            status = f"FALSIFIED ({'; '.join(dead_hard)})"
    elif dead_soft:
        status = f"UNVERIFIED ({'; '.join(dead_soft)})"
    else:
        status = "NUMERIC (unstructured field re-selects the Gaussian)"

    result = {
        "scales": {
            "base": {"omega": omega, "hbar": hbar, "mass": mass, "nu": nu},
            "grids": {"coarse": list(GRID_COARSE), "fine": list(GRID_FINE)},
            "bank": bank,
            "coarse_runs": [
                {k: r[k] for k in r if k != "interior"} for r in coarse_runs
            ],
            "coarse_nu0_runs": [
                {k: r[k] for k in r if k != "interior"}
                for r in coarse_nu0_runs
            ],
            "bridge_field_J": j_bridge_field,
            "classical": classical,
            "fine_runs": [
                {k: r[k] for k in r if k != "interior"} for r in fine_runs
            ],
            "attribution": attrib,
            "scaling": {
                "omega": om2,
                "runs": [
                    {k: r[k] for k in r if k != "interior"}
                    for r in scaling_runs
                ],
                "bridge_field_J": j_sc_bridge,
            },
            "segments": segments,
        },
        "gates": {
            "grad_tol": GRAD_TOL,
            "action_tol": ACTION_TOL,
            "attrib_tol": ATTRIB_TOL,
            "kills_hard": [[n, bool(k)] for n, k in hard],
            "kills_soft": [[n, bool(k)] for n, k in soft],
        },
        "verdict": {
            "claim_58_status": status,
            "note": _verdict_note(status),
        },
    }
    assert isinstance(result["verdict"]["note"], str)
    config = {
        "grids": {"coarse": list(GRID_COARSE), "fine": list(GRID_FINE)},
        "base": {"omega": omega, "hbar": hbar, "mass": mass},
        "starts": list(STARTS),
        "fine_starts": list(FINE_STARTS),
        "nu0_starts": list(NU0_STARTS),
        "gates": {
            "grad_tol": GRAD_TOL,
            "action_tol": ACTION_TOL,
            "attrib_tol": ATTRIB_TOL,
        },
        "scope": "1D field BVP, zero parameters, no full-field claim",
    }
    payload = {"meta": metadata(config), "result": result}
    if write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        write_json(RESULTS_DIR / "field_variation.json", payload)
        write_text_atomic(
            RESULTS_DIR / "field_variation.md", render_markdown(payload)
        )
    return payload


def _classical_transport_action(
    s0: float, sT: float, horizon_T: float, omega: float, mass: float
) -> dict:
    """Closed-form nu = 0 Gaussian transport action.

    s(t) = A*cos(wt) + B*sin(wt) pinned at the ends; the EL zeroes the
    bulk, leaving J = m*[s*sdot/2]_{0}^{T}. For equal ends this reduces
    to -m*w*a^2*alpha (alpha = sqrt(2)-1); for transport ends the A, B
    solve below are required (the equal-endpoint value is wrong here).
    """
    A = s0
    B = (sT - s0 * math.cos(omega * horizon_T)) / math.sin(omega * horizon_T)
    sdot0 = omega * B
    sdotT = omega * (-A * math.sin(omega * horizon_T) + B * math.cos(omega * horizon_T))
    return {
        "A": A,
        "B": B,
        "value": 0.5 * mass * (sT * sdotT - s0 * sdot0),
    }


def _verdict_note(status: str) -> str:
    if status.startswith("NUMERIC"):
        return (
            "Unstructured field variation from adversarial starts "
            "re-selects the Gaussian bridge value and path; nu = 0 "
            "reproduces the classical transport value."
        )
    if status.startswith("FALSIFIED"):
        return (
            "The fixed-endpoint G-M field does not re-select the "
            "Gaussian: every tier escapes far below the bank, still "
            "descending; the bridge Hessian has negative directions; "
            "the escape exploits near-vacuum cells. Stationarity "
            "results of claims 51-57 stand; only the global-minimum "
            "reading dies."
        )
    return status


def render_markdown(payload: dict) -> str:
    result = payload["result"]
    scales = result["scales"]
    verdict = result["verdict"]
    lines = [
        "# Unstructured field variation (claim 58)",
        "",
        "Adversarial-start field optimization against the Gaussian bridge bank.",
        "",
        "| check | value |",
        "|---|---|",
        f"| quantum bank | {scales['bank']:.10f} |",
    ]
    for r in scales["coarse_runs"]:
        lines.append(
            f"| coarse {r['start']} | J={r['J_final']:.10f}, "
            f"grad={r['grad_inf']:.3e}, conv={r['converged']} |"
        )
    for r in scales["fine_runs"]:
        lines.append(
            f"| fine {r['start']} | J={r['J_final']:.10f}, "
            f"grad={r['grad_inf']:.3e}, conv={r['converged']} |"
        )
    lines.append(f"| attribution | {scales['attribution']:.3e} |")
    lines.append(
        f"| classical bank / nu=0 best "
        f"| {scales['classical']['value']:.10f} / "
        f"{min(r['J_final'] for r in scales['coarse_nu0_runs']):.10f} |"
    )
    lines += [
        "",
        "## Verdict",
        "",
        f"- Claim 58: **{verdict['claim_58_status']}**.",
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
    payload = run_field_variation_check()
    print(payload["result"]["verdict"])
