"""Variational dynamics reproduces Ermakov (claim 51, ADR-043).

Zero free parameters, no full-field dynamics asserted. For the
time-dependent Gaussian trial (rho = N(0, sigma(t)^2),
v = (sigma_dot/sigma) x) with nu = hbar/(2*m), the path action

    J[sigma] = int_0^T [m*sdot^2/2 - m*nu^2/(2*s^2) - m*omega^2*s^2/2] dt

has Euler-Lagrange equation sddot = nu^2/s^3 - omega^2 s, exactly the
Ermakov equation (nu^2 = hbar^2/(4*m^2)). Linearized at s_q^2 = nu/omega
the Jacobi frequency is 2*omega (period pi/omega); the first conjugate
point is at pi/(2*omega), so the frozen horizon T = pi/4 carries no
conjugate ambiguity (Jacobi hypothesis satisfied; weak-local regime —
global uniqueness is probed empirically via four starts, never asserted).

Periods are measured as same-direction (full-period) zero-crossing
means (never doubled half-interval means, which are biased by
(A-B)/n for odd half-interval counts in the asymmetric potential).
Cross-checks compare matched omega only.
"""

from __future__ import annotations

import math

from domains.fluid_universe.theory.variational_dynamics import dynamics_scales

from .provenance import RESULTS_DIR, metadata, write_json, write_text_atomic

LOC_TOL = 1e-9
RESID_TOL = 1e-12
PERIOD_TOL = 1e-3
TERM_RTOL = 1e-9


def run_variational_dynamics_check(write: bool = True) -> dict:
    scales = dynamics_scales()
    extrema = scales["extrema"]
    releases = scales["releases"]
    scaling = scales["scaling"]
    loc_kill = any(e["max_deviation"] > LOC_TOL or not e["converged"] for e in extrema)
    resid_kill = any(e["max_residual"] > RESID_TOL for e in extrema)
    period_kills = []
    for r in releases:
        period = r["period"]
        period_kills.append(
            (r["factor"], not math.isfinite(period) or abs(period - math.pi) > PERIOD_TOL)
        )
    term = scales["term_match"]
    term_kill = term["max_rel_error"] > TERM_RTOL
    scale_period = scaling["release"]["period"]
    scale_kill = not math.isfinite(scale_period) or abs(
        scale_period - math.pi / 2.0
    ) > PERIOD_TOL
    killed = (
        [("extremum_location", loc_kill), ("el_residual", resid_kill)]
        + [(f"period_{f}", k) for f, k in period_kills]
        + [
            ("term_match", term_kill),
            ("scaling_period", scale_kill),
        ]
    )
    dead = sorted(name for name, k in killed if k)
    if dead:
        status = f"FALSIFIED (variational dynamics; {'; '.join(dead)})"
    else:
        status = "NUMERIC (variational dynamics reproduces Ermakov)"
    result = {
        "scales": scales,
        "gates": {
            "loc_tol": LOC_TOL,
            "resid_tol": RESID_TOL,
            "period_tol": PERIOD_TOL,
            "term_rtol": TERM_RTOL,
            "kills": [[n, bool(k)] for n, k in killed],
        },
        "verdict": {
            "claim_51_status": status,
            "note": (
                "Time-dependent Gaussian Ritz variation of the G-M action "
                "yields the Ermakov equation term-by-term; the discrete "
                "extremum is the constant path and small oscillations "
                "run at pi (pi/2 at omega=2)."
            ),
        },
    }
    config = {
        "grids": scales["grids"],
        "base": scales["base"],
        "starts": list(scales["starts"]),
        "gates": {
            "loc_tol": LOC_TOL,
            "resid_tol": RESID_TOL,
            "period_tol": PERIOD_TOL,
            "term_rtol": TERM_RTOL,
        },
        "scope": "time-dependent Gaussian Ritz, zero parameters, no full-field claim",
    }
    payload = {"meta": metadata(config), "result": result}
    if write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        write_json(RESULTS_DIR / "variational_dynamics.json", payload)
        write_text_atomic(
            RESULTS_DIR / "variational_dynamics.md", render_markdown(payload)
        )
    return payload


def render_markdown(payload: dict) -> str:
    result = payload["result"]
    scales = result["scales"]
    verdict = result["verdict"]
    lines = [
        "# Variational dynamics reproduces Ermakov (claim 51)",
        "",
        "G-M action over sigma(t) gives the Ermakov equation; period pi (pi/2 at omega=2).",
        "",
        "| check | value |",
        "|---|---:|",
        f"| extremal max deviation | {max(e['max_deviation'] for e in scales['extrema']):.3e} |",
        f"| extremal max residual | {max(e['max_residual'] for e in scales['extrema']):.3e} |",
    ]
    for r in scales["releases"]:
        lines.append(f"| release f={r['factor']} period | {r['period']:.12f} |")
    lines += [
        f"| term-match max rel err | {scales['term_match']['max_rel_error']:.3e} |",
        f"| scaling omega=2 period | {scales['scaling']['release']['period']:.12f} |",
        "",
        "## Verdict",
        "",
        f"- Claim 51: **{verdict['claim_51_status']}**.",
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
    payload = run_variational_dynamics_check()
    print(payload["result"]["verdict"])
