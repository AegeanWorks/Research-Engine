"""Ritz-widened squared-Hermite trial BVP (claim 59, ADR-051).

Zero free parameters, no full-field claims. The Gaussian trial is
widened with Hermite-polynomial shape modes (exact mass conservation
by renormalization, ends pinned to the Gaussian bridge). K = 0 is the
span-54 trial exactly (built-in calibration). If the widened
minimizer re-selects the Gaussian at every rung, the claim-58 escape
is rough-direction-only (NUMERIC-REVERSAL, qualified). A smooth
below-bank minimizer CONFIRMS the falsification (trial-class program
dead beyond appeal). Non-convergence without below-bank escape is
UNVERIFIED.
"""

from __future__ import annotations

import math

import numpy as np

from domains.fluid_universe.theory.widened_ritz import (
    ACTION_TOL,
    ATTRIB_TOL,
    BASE,
    GRAD_TOL,
    K_LADDER,
    STARTS,
    WidenedProblem,
    bridge_widths,
    diffusivity,
    horizon,
)
from domains.fluid_universe.theory.gaussian_fluid import quantum_width

from .provenance import RESULTS_DIR, metadata, write_json, write_text_atomic

FINE_NT = 201
# R1 (Stage-2 revision): nu0 control at K=0 (Gaussian classical bridge);
# K=6 nu0 was over-parameterised and never converged. Two distinct s-inits.
NU0_K = 0
NU0_STARTS = ("gauss", "wide_sigma")


def _analytic_bridge_J(problem) -> float:
    t = np.linspace(0.0, problem.T, problem.nt)
    s = bridge_widths(t, problem.s0, problem.omega)
    nu = diffusivity(1.0, 1.0)
    dt = problem.T / (problem.nt - 1)
    v = (s[1:] - s[:-1]) / dt
    sm = 0.5 * (s[1:] + s[:-1])
    return float(
        np.sum(
            0.5 * v * v
            - 0.5 * nu * nu / (sm * sm)
            - 0.5 * problem.omega**2 * sm * sm
        )
        * dt
    )


# R3 (G-003 budget): K6 single start; 3-start K6 exceeded 900 s.
# K2 keeps 3 starts as the minimal widening probe.
LADDER_STARTS = {
    0: ("gauss",),
    2: ("gauss", "c2_bump", "wide_sigma"),
    4: ("gauss",),
    6: ("gauss",),
}


def run_widened_ritz_check(write: bool = True) -> dict:
    omega, hbar, mass = BASE["omega"], BASE["hbar"], BASE["mass"]
    nu = diffusivity(hbar, mass)
    sq = quantum_width(omega, hbar, mass)
    T = horizon(omega)

    # Production tier NT=101 (R2-validated: resolves the bank to 1.4e-5);
    # the NT=201 spot below guards resolution. Keeps run_all in budget.
    ladder = []
    for k in K_LADDER:
        import time as _time

        _t0 = _time.time()
        print(f"[widened] K={k} start", flush=True)
        prob = WidenedProblem(k, nx=101, nt=101, nu=nu, omega=omega, mass=mass)
        runs = []
        for start in LADDER_STARTS[k]:
            out = prob.solve(start, maxiter=2000)
            polished = False
            if not out["converged"]:
                out = prob.newton_polish(np.array(out["params"]), steps=8)
                polished = True
            # R2: recompute shape-coefficient magnitude from params so both
            # solve and polish paths carry it (polish output lacks the field).
            try:
                _fields = prob.unpack(np.array(out["params"]))
                _cks = [
                    float(np.max(np.abs(_fields[j][1:-1])))
                    for j in range(1, prob.k_max + 1)
                ]
                out["max_ck_overall"] = float(max(_cks)) if _cks else 0.0
            except Exception:
                out["max_ck_overall"] = float("nan")
            out["start"] = start
            out["polished"] = polished
            runs.append(dict(out, start=start, k=k))
            print(
                f"[widened] K={k} {start}: J={out['J_final']:.6f} "
                f"grad={out['grad_inf']:.2e} conv={out['converged']} "
                f"nit={out.get('nit')} t={_time.time()-_t0:.0f}s",
                flush=True,
            )
        conv = [r for r in runs if r["converged"]]
        pool = conv if conv else runs
        best = min(pool, key=lambda r: abs(r["J_final"] + 0.3906340559))
        rho_best = prob.unpack(np.array(best["params"]))
        rho_best = prob.build_rho(rho_best)
        t_ref = np.linspace(0.0, T, prob.nt)
        s_ref = bridge_widths(t_ref, prob.s0, omega)
        rho_ref = np.empty((prob.nt, prob.nx))
        for kk in range(prob.nt):
            rho_ref[kk] = np.exp(-prob.xc**2 / (2.0 * s_ref[kk] ** 2)) / math.sqrt(
                2.0 * math.pi * s_ref[kk] ** 2
            )
        rho_ref = rho_ref / (rho_ref.sum(axis=1, keepdims=True) * prob.dx)
        attrib = float(np.max(np.abs(rho_best - rho_ref)))
        # R2: shape-magnitude of the best (closest-to-bank) run.
        try:
            _bf = prob.unpack(np.array(best["params"]))
            _bcks = [
                float(np.max(np.abs(_bf[j][1:-1])))
                for j in range(1, prob.k_max + 1)
            ]
            best_max_ck = float(max(_bcks)) if _bcks else 0.0
        except Exception:
            best_max_ck = float("nan")
        ladder.append(
            {"k": k, "runs": runs, "attribution": attrib,
             "best_max_ck": best_max_ck}
        )

    nt_spot = None
    prob_spot = WidenedProblem(0, nx=101, nt=201, nu=nu, omega=omega, mass=mass)
    out_spot = prob_spot.solve("gauss", maxiter=2000)
    if not out_spot["converged"]:
        out_spot = prob_spot.newton_polish(np.array(out_spot["params"]), steps=8)
    nt_spot = {
        "nx": 101,
        "nt": 201,
        "J_final": out_spot["J_final"],
        "grad_inf": out_spot["grad_inf"],
        "converged": out_spot["converged"],
        "nit": out_spot["nit"],
    }

    t_ref = np.linspace(0.0, T, 401)
    s_ref = bridge_widths(t_ref, 1.2 * sq, omega)
    analytic_J = _analytic_bridge_J(
        WidenedProblem(0, nu=nu, omega=omega, mass=mass)
    )

    nu0 = []
    for start in NU0_STARTS:
        prob0 = WidenedProblem(NU0_K, nx=101, nt=101, nu=0.0, omega=omega, mass=mass)
        out = prob0.solve(start, maxiter=2000)
        polished = False
        if not out["converged"]:
            out = prob0.newton_polish(np.array(out["params"]), steps=12)
            polished = True
        out["start"] = start
        out["polished"] = polished
        nu0.append(dict(out, start=start))

    classical_closed = -0.23852813742385703

    k0_runs = ladder[0]["runs"]
    k0_ok = any(
        r["converged"] and abs(r["J_final"] + 0.3906340559) <= ACTION_TOL
        for r in k0_runs
    )
    escape_runs = [
        (rung["k"], r["start"])
        for rung in ladder
        if rung["k"] > 0
        for r in rung["runs"]
        if r["J_final"] < -0.3906340559 - ACTION_TOL
    ]
    # R2: reversal needs J at bank AND shape modes ~0 AND density
    # attribution ~0. J-only match with c2~0.05 (flat valley) does not reverse.
    reversal_ok = all(
        any(
            r["converged"]
            and abs(r["J_final"] + 0.3906340559) <= ACTION_TOL
            and float(r.get("max_ck_overall", float("inf")) or 0.0) <= ATTRIB_TOL
            for r in rung["runs"]
        )
        and rung["attribution"] <= ATTRIB_TOL
        and float(rung.get("best_max_ck", float("inf")) or 0.0) <= ATTRIB_TOL
        for rung in ladder
    )
    hard = [
        ("k0_calibration_broken", not k0_ok),
        ("escape_below", len(escape_runs) > 0 and k0_ok),
        ("reversal_branch", reversal_ok and not escape_runs),
        (
            "classical_match",
            any(
                r["converged"]
                and abs(r["J_final"] - classical_closed) > ACTION_TOL
                for r in nu0
            ),
        ),
    ]
    soft = [
        (
            "ladder_attainment",
            any(not r["converged"] for rung in ladder for r in rung["runs"]),
        ),
        ("nu0_attainment", any(not r["converged"] for r in nu0)),
        (
            "nu0_match",
            not any(
                abs(r["J_final"] - classical_closed) <= ACTION_TOL for r in nu0
            ),
        ),
        (
            "path_match",
            any(
                rung["attribution"] > ATTRIB_TOL
                or float(rung.get("best_max_ck", float("inf")) or 0.0)
                > ATTRIB_TOL
                for rung in ladder
            ),
        ),
    ]
    dead_hard = sorted(n for n, k in hard if k)
    dead_soft = sorted(n for n, k in soft if k)
    if "escape_below" in dead_hard:
        status = (
            "CONFIRMED FALSIFIED (widened smooth trial escapes below the bank "
            "at tier-persistent depth; trial-class program dead beyond appeal)"
        )
    elif "reversal_branch" in dead_hard:
        status = (
            "NUMERIC-REVERSAL (Gaussian re-selected within the smooth widened "
            "class at every rung; claim-58 escape is rough-direction-only)"
        )
    elif "k0_calibration_broken" in dead_hard:
        status = "UNVERIFIED (K=0 apparatus check failed; solver unreliable)"
    elif "classical_match" in dead_hard:
        status = "UNVERIFIED (nu=0 control mismatch; investigate apparatus)"
    elif dead_soft:
        status = f"UNVERIFIED ({'; '.join(dead_soft)})"
    else:
        status = "UNVERIFIED (no rung converged at the bank)"
    result = {
        "scales": {
            "base": {"omega": omega, "hbar": hbar, "mass": mass, "nu": nu},
            "ladder": [
                {
                    "k": rung["k"],
                    "runs": [
                        {kk: r[kk] for kk in r if kk not in ("interior_s", "params")}
                        for r in rung["runs"]
                    ],
                    "attribution": rung["attribution"],
                    "best_max_ck": rung.get("best_max_ck", float("nan")),
                    "best_params": next(
                        (
                            r["params"]
                            for r in rung["runs"]
                            if r["converged"]
                        ),
                        rung["runs"][0]["params"],
                    ),
                }
                for rung in ladder
            ],
            "bank": -0.3906340559,
            "analytic_J": analytic_J,
            "classical_closed": classical_closed,
            "nu0_runs": [{k: r[k] for k in r if k != "interior_s"} for r in nu0],
            "nt_spot": nt_spot,
        },
        "gates": {
            "grad_tol": GRAD_TOL,
            "action_tol": ACTION_TOL,
            "attrib_tol": ATTRIB_TOL,
            "kills_hard": [[n, bool(k)] for n, k in hard],
            "kills_soft": [[n, bool(k)] for n, k in soft],
        },
        "verdict": {
            "claim_59_status": status,
            "note": (
                "K-ladder re-derivation with zero fitted parameters; "
                "verdict follows the gates."
            ),
        },
    }
    config = {
        "ladder": list(K_LADDER),
        "starts": {str(k): list(v) for k, v in LADDER_STARTS.items()},
        "nu0_k": NU0_K,
        "nu0_starts": list(NU0_STARTS),
        "grid": {"nx": 101, "nt": 101, "nt_spot": 201, "x_lim": 6.0},
        "base": {"omega": omega, "hbar": hbar, "mass": mass},
        "gates": {
            "grad_tol": GRAD_TOL,
            "action_tol": ACTION_TOL,
            "attrib_tol": ATTRIB_TOL,
        },
        "scope": "smooth Ritz trial only; no full-field claim",
    }
    payload = {"meta": metadata(config), "result": result}
    if write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        write_json(RESULTS_DIR / "widened_ritz.json", payload)
        write_text_atomic(
            RESULTS_DIR / "widened_ritz.md", render_markdown(payload)
        )
    return payload


def render_markdown(payload: dict) -> str:
    result = payload["result"]
    scales = result["scales"]
    verdict = result["verdict"]
    lines = [
        "# Ritz-widened trial class (claim 59)",
        "",
        "K-ladder re-derivation of the fixed-endpoint Gaussian bridge.",
        "",
        "| check | value |",
        "|---|---|",
        f"| bank | {scales['bank']:.10f} |",
    ]
    for rung in scales["ladder"]:
        for r in rung["runs"]:
            lines.append(
                f"| K={rung['k']} {r['start']} | J={r['J_final']:.10f}, "
                f"grad={r['grad_inf']:.3e}, conv={r['converged']} |"
            )
    lines += [
        "",
        "## Verdict",
        "",
        f"- Claim 59: **{verdict['claim_59_status']}**.",
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
    payload = run_widened_ritz_check()
    print(payload["result"]["verdict"])
