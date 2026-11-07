"""Yasue center-width discriminator (claim 55, ADR-047).

Zero free parameters, no full-field claims. The Yasue 2-path Gaussian
trial shares the classical center leg with G-M (mu at 2*pi) while the
width leg collapses (monotone to the floor, zero upward crossings,
floor-hit < pi). The identical G-M twin co-oscillates (2*pi and pi).

Kill logic: a Yasue width return (>= 1 upward crossing, or a width
oscillation at pi) FALSIFIES the discriminator. A missing Yasue center
oscillation breaks the split assumption (UNVERIFIED + theory revision,
not a win). A failing G-M twin is an apparatus failure (UNVERIFIED).
"""

from __future__ import annotations

import math

from domains.fluid_universe.theory.yasue_center import yasue_scales

from .provenance import RESULTS_DIR, metadata, write_json, write_text_atomic

LOC_TOL = 1e-9
RESID_TOL = 1e-12
PERIOD_TOL = 1e-3
TERM_RTOL = 1e-9
STATIC_RESID_MIN = 1e-3
QUAD_RTOL = 1e-3
TRACK_TOL = 1e-4
ARC_RESID_TOL = 1e-9


def run_yasue_center_check(write: bool = True) -> dict:
    scales = yasue_scales()
    statics = scales["statics"]
    attempts = scales["attempts"]
    releases = scales["releases"]
    twins = scales["twins"]
    term = scales["term_match"]
    scaling = scales["scaling"]
    probe02 = scales["floor_sensitivity"]

    static_kill = any(s["max_residual"] <= STATIC_RESID_MIN for s in statics)
    arc_kill = any(a["max_residual"] > ARC_RESID_TOL for a in attempts) or (
        max(a["min_sigma"] for a in attempts)
        - min(a["min_sigma"] for a in attempts)
        > 1e-9
    )
    center_kill = any(r["mu_track_max_dev"] > TRACK_TOL for r in releases)
    width_kill = any(not r["monotone"] for r in releases) or any(
        r["floor_hit_time"] is None or r["floor_hit_time"] >= math.pi
        for r in releases
    )
    width_return_kill = any(r["upward_crossings"] != 0 for r in releases)
    probe_kill = not (
        releases[2]["mu_track_max_dev"] <= TRACK_TOL
        and releases[2]["monotone"]
        and releases[2]["floor_hit_time"] is not None
        and releases[2]["floor_hit_time"] < math.pi
        and releases[2]["upward_crossings"] == 0
    )
    floor02_kill = not (
        probe02["monotone"]
        and probe02["floor_hit_time"] is not None
        and probe02["floor_hit_time"] < math.pi
        and probe02["upward_crossings"] == 0
    )
    quad_kill = any(
        q is None
        or m is None
        or abs(m - q) / max(abs(q), 1e-300) > QUAD_RTOL
        for q, m in zip(
            scales["mild_quadrature"],
            [r["mild_crossing_time"] for r in releases],
        )
        if not (q is None and m is None)
    )
    term_kill = term["max_rel_error"] > TERM_RTOL or term["max_accel"] >= 0.0
    twin_kill = any(
        not math.isfinite(t["mu_period"]) for t in twins if t["mu0"] != 0.0
    ) or any(
        abs(t["mu_period"] - 2.0 * math.pi) > PERIOD_TOL
        for t in twins
        if t["mu0"] != 0.0
    ) or any(
        abs(t["sg_period"] - math.pi) > PERIOD_TOL
        for t in twins
        if t["s0_factor"] != 1.0
    )
    scale_kill = not (
        scaling["yasue"]["mu_track_max_dev"] <= TRACK_TOL
        and scaling["yasue"]["monotone"]
        and scaling["yasue"]["floor_hit_time"] is not None
        and scaling["yasue"]["floor_hit_time"] < math.pi / 4.0
        and scaling["yasue"]["upward_crossings"] == 0
        and math.isfinite(scaling["twin_mu"]["mu_period"])
        and abs(scaling["twin_mu"]["mu_period"] - math.pi) <= PERIOD_TOL
        and math.isfinite(scaling["twin_sg"]["sg_period"])
        and abs(scaling["twin_sg"]["sg_period"] - math.pi / 2.0) <= PERIOD_TOL
    )
    killed = [
        ("static_residual", static_kill),
        ("arc_attainment", arc_kill),
        ("yasue_center_track", center_kill),
        ("yasue_width_collapse", width_kill),
        ("yasue_width_no_return", width_return_kill),
        ("joint_probe", probe_kill),
        ("floor_sensitivity", floor02_kill),
        ("quadrature_match", quad_kill),
        ("term_match", term_kill),
        ("gm_twin_control", twin_kill),
        ("scaling", scale_kill),
    ]
    dead = sorted(name for name, k in killed if k)
    if "gm_twin_control" in dead:
        status = "UNVERIFIED (apparatus failure; G-M twin did not reproduce claim 53)"
    elif "yasue_center_track" in dead:
        status = "UNVERIFIED (split assumption broken; Yasue center left the Newtonian track)"
    elif "arc_attainment" in dead:
        status = "UNVERIFIED (arc solve did not attain; bridge analysis needed)"
    elif dead:
        status = f"FALSIFIED (discriminator; {'; '.join(dead)})"
    else:
        status = "NUMERIC (Yasue center-width discriminator demonstrated)"
    result = {
        "scales": scales,
        "gates": {
            "loc_tol": LOC_TOL,
            "resid_tol": RESID_TOL,
            "period_tol": PERIOD_TOL,
            "term_rtol": TERM_RTOL,
            "static_resid_min": STATIC_RESID_MIN,
            "quad_rtol": QUAD_RTOL,
            "track_tol": TRACK_TOL,
            "arc_resid_tol": ARC_RESID_TOL,
            "kills": [[n, bool(k)] for n, k in killed],
        },
        "verdict": {
            "claim_55_status": status,
            "note": (
                "Yasue 2-path trial: center tracks Newton over the collapse "
                "window with collapsing width (floor-hit < pi, zero returns); "
                "G-M twin co-oscillates (2pi and pi); single BVP arc recorded; "
                "no fitted parameters."
            ),
        },
    }
    config = {
        "grids": scales["grids"],
        "base": scales["base"],
        "starts": scales["starts"],
        "releases": scales["releases_meta"],
        "floors": scales["floors"],
        "dt": scales["dt"],
        "gates": {
            "loc_tol": LOC_TOL,
            "resid_tol": RESID_TOL,
            "period_tol": PERIOD_TOL,
            "term_rtol": TERM_RTOL,
            "static_resid_min": STATIC_RESID_MIN,
            "quad_rtol": QUAD_RTOL,
            "track_tol": TRACK_TOL,
            "arc_resid_tol": ARC_RESID_TOL,
        },
        "scope": "Ritz trial pair, zero parameters, no full-field claim",
    }
    payload = {"meta": metadata(config), "result": result}
    if write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        write_json(RESULTS_DIR / "yasue_center.json", payload)
        write_text_atomic(
            RESULTS_DIR / "yasue_center.md", render_markdown(payload)
        )
    return payload


def render_markdown(payload: dict) -> str:
    result = payload["result"]
    scales = result["scales"]
    verdict = result["verdict"]
    lines = [
        "# Yasue center-width discriminator (claim 55)",
        "",
        "Yasue 2-path trial: classical center (2pi) with collapsing width;",
        "the G-M twin co-oscillates (2pi and pi).",
        "",
        "| check | value |",
        "|---|---:|",
        f"| static residual min | {min(s['max_residual'] for s in scales['statics']):.6f} |",
        f"| newton attempts converged | {sum(1 for a in scales['attempts'] if a['converged'])} |",
    ]
    for r in scales["releases"]:
        lines.append(
            f"| Yasue release mu0={r['mu0']}, s0={r['s0_factor']} "
            f"| track={r['mu_track_max_dev']:.3e}, hit={r['floor_hit_time']}, "
            f"mono={r['monotone']}, up={r['upward_crossings']} |"
        )
    lines.append(
        f"| arc min/max sigma | {scales['arc_min_sigma']:.12f} / "
        f"{scales['arc_max_sigma']:.12f} |"
    )
    for t in scales["twins"]:
        lines.append(
            f"| G-M twin mu0={t['mu0']}, s0={t['s0_factor']} "
            f"| T_mu={t['mu_period']:.9f}, T_sg={t['sg_period']:.9f} |"
        )
    lines.append(
        f"| term match max rel err | {scales['term_match']['max_rel_error']:.3e} |"
    )
    lines.append(
        f"| scaling yasue hit / twin mu / twin sg "
        f"| {scales['scaling']['yasue']['floor_hit_time']} / "
        f"{scales['scaling']['twin_mu']['mu_period']:.9f} / "
        f"{scales['scaling']['twin_sg']['sg_period']:.9f} |"
    )
    lines += [
        "",
        "## Verdict",
        "",
        f"- Claim 55: **{verdict['claim_55_status']}**.",
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
    payload = run_yasue_center_check()
    print(payload["result"]["verdict"])
