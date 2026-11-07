"""Co-emergence of Newtonian center and Ermakov width (claim 53, ADR-045).

Zero free parameters, no full-field claims. For the time-dependent
2D-path Gaussian trial (center mu(t), width sigma(t)) the drift
v = mudot + (sigmadot/sigma)(x - mu) gives, with rho = N(mu, sigma^2):

    E[v^2] = mudot^2 + sigmadot^2     (cross term dies: E[x - mu] = 0)
    E[V]   = m*w^2*(sigma^2 + mu^2)/2

so the G-M action splits additively, J[mu,sigma] = J_mu[mu] + J_sg[sg],
with J_mu the classical HO action and J_sg the span-51 width action.
The stationary path is (0, sigma_q); small oscillations decouple:
mu at omega (period 2*pi) and sigma at 2*omega (period pi).

The frozen horizon T = pi/(4*omega) is governed by the tighter
(width) leg: first conjugate zero at pi/(2*omega) vs pi/omega for the
center. Weak-local-positivity only; no global claims. Yasui center
dynamics and the full control problem stay untested.
"""

from __future__ import annotations

import math

from domains.fluid_universe.theory.variational_center import dynamics_scales

from .provenance import RESULTS_DIR, metadata, write_json, write_text_atomic

LOC_TOL = 1e-9
RESID_TOL = 1e-12
PERIOD_TOL = 1e-3
TERM_RTOL = 1e-9
CONSISTENCY_TOL = 1e-6


def run_variational_center_check(write: bool = True) -> dict:
    scales = dynamics_scales()
    extrema = scales["extrema"]
    releases = scales["releases"]
    term = scales["term_match"]
    scaling = scales["scaling"]
    loc_kill = any(
        e["max_dev_mu"] > LOC_TOL or e["max_dev_sg"] > LOC_TOL or not e["converged"]
        for e in extrema
    )
    resid_kill = any(e["max_residual"] > RESID_TOL for e in extrema)
    mu_expected = [r for r in releases if r["mu0"] != 0.0]
    sg_expected = [r for r in releases if r["s0_factor"] != 1.0]
    mu_kill = any(not math.isfinite(r["mu_period"]) for r in mu_expected) or any(
        abs(r["mu_period"] - 2.0 * math.pi) > PERIOD_TOL for r in mu_expected
    )
    sg_kill = any(not math.isfinite(r["sg_period"]) for r in sg_expected) or any(
        abs(r["sg_period"] - math.pi) > PERIOD_TOL for r in sg_expected
    )
    term_kill = term["max_rel_error"] > TERM_RTOL
    span51_ref = 3.14159212985
    consist_kill = (
        abs([r for r in releases if r["s0_factor"] == 1.01][0]["sg_period"] - span51_ref)
        > CONSISTENCY_TOL
    )
    scale_kill = not (
        math.isfinite(scaling["mu_period"])
        and abs(scaling["mu_period"] - math.pi) <= PERIOD_TOL
        and math.isfinite(scaling["sg_period"])
        and abs(scaling["sg_period"] - math.pi / 2.0) <= PERIOD_TOL
    )
    killed = [
        ("extremum_location", loc_kill),
        ("extremum_residual", resid_kill),
        ("mu_period", mu_kill),
        ("sg_period", sg_kill),
        ("term_match", term_kill),
        ("span51_consistency", consist_kill),
        ("scaling", scale_kill),
    ]
    dead = sorted(name for name, k in killed if k)
    if dead:
        status = f"FALSIFIED (co-emergence; {'; '.join(dead)})"
    else:
        status = "NUMERIC (center-width co-emergence demonstrated)"
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
            "claim_53_status": status,
            "note": (
                "Time-dependent Gaussian Ritz: constant (0, sigma_q) "
                "extremum; Newtonian center (2pi) and Ermakov width (pi) "
                "co-emerge from one action; no cross-coupling."
            ),
        },
    }
    config = {
        "grids": scales["grids"],
        "base": scales["base"],
        "starts": scales["starts"],
        "gates": {
            "loc_tol": LOC_TOL,
            "resid_tol": RESID_TOL,
            "period_tol": PERIOD_TOL,
            "term_rtol": TERM_RTOL,
        },
        "scope": "Ritz trial pair, zero parameters, no full-field claim",
    }
    payload = {"meta": metadata(config), "result": result}
    if write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        write_json(RESULTS_DIR / "variational_center.json", payload)
        write_text_atomic(
            RESULTS_DIR / "variational_center.md", render_markdown(payload)
        )
    return payload


def render_markdown(payload: dict) -> str:
    result = payload["result"]
    scales = result["scales"]
    verdict = result["verdict"]
    lines = [
        "# Center-width co-emergence (claim 53)",
        "",
        "One G-M action gives Newtonian center (2pi) and Ermakov width (pi).",
        "",
        "| check | value |",
        "|---|---:|",
        f"| extremal max dev (mu, sg) | {max(e['max_dev_mu'] for e in scales['extrema']):.3e}, {max(e['max_dev_sg'] for e in scales['extrema']):.3e} |",
        f"| extremal max residual | {max(e['max_residual'] for e in scales['extrema']):.3e} |",
    ]
    for r in scales["releases"]:
        lines.append(
            f"| release mu0={r['mu0']}, s0={r['s0_factor']} | T_mu={r['mu_period']:.9f}, T_sg={r['sg_period']:.9f} |"
        )
    lines.append(f"| term match max rel err | {scales['term_match']['max_rel_error']:.3e} |")
    lines.append(
        f"| scaling mu / sg period | {scales['scaling']['mu_period']:.9f} / {scales['scaling']['sg_period']:.9f} |"
    )
    lines += [
        "",
        "## Verdict",
        "",
        f"- Claim 53: **{verdict['claim_53_status']}**.",
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
    payload = run_variational_center_check()
    print(payload["result"]["verdict"])
