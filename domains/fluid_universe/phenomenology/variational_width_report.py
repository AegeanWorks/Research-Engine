"""Gaussian Ritz width-selection check (claim 49, ADR-041).

Zero free parameters, no dynamics beyond the stationary Gaussian
trial class. Recomputes live from domains.fluid_universe.theory.variational_width:

- G-M: analytic extremum s2* = nu/omega == 0.5 (gate abs 1e-9),
  Newton-refined grid argmax agrees (gate 1e-9), curvature
  d2J/d(s2)^2 = -2.0 (gate abs 1e-9) and negative;
- Yasui: derivative negative everywhere on the frozen grid
  (gate max < -1e-3) and J monotone decreasing — no finite extremum;
- scaling: omega=2 and mass=2 both predict s2* = 0.25
  (Newton-refined gate 1e-9), curvatures -16.0/-8.0 analytic.
"""

from __future__ import annotations

import math

from domains.fluid_universe.theory.variational_width import selection_scales

from .provenance import RESULTS_DIR, metadata, write_json, write_text_atomic

LOC_TOL = 1e-9
CURV_TOL = 1e-9
YASUI_DERIV_MAX = -1e-3
SCALE_TOL = 1e-9


def run_variational_width_check(write: bool = True) -> dict:
    scales = selection_scales()
    analytic = scales["analytic"]
    grid = scales["grid"]
    yasui = scales["yasui"]
    loc_kill = abs(analytic["sigma_star_sq"] - 0.5) > LOC_TOL
    refine_kill = abs(grid["refined"] - 0.5) > LOC_TOL
    grid_kill = abs(grid["grid_argmax"] - 0.5) > grid["grid_step"]
    curv_kill = abs(analytic["curvature_s2"] - (-2.0)) > CURV_TOL
    curv_sign_kill = not analytic["curvature_s2"] < 0.0
    yasui_kill = not (
        yasui["all_negative"] and yasui["max_derivative"] < YASUI_DERIV_MAX
    ) or not (yasui["max_diff"] < 0.0)
    scale_kills = []
    for entry in scales["scalings"]:
        bad_refine = abs(entry["refined"] - entry["predicted"]) > SCALE_TOL
        bad_pred = abs(entry["predicted"] - 0.25) > SCALE_TOL
        scale_kills.append(((entry["omega"], entry["mass"]), bad_refine or bad_pred))
    killed = [
        ("gm_location", loc_kill),
        ("gm_grid_refine", refine_kill),
        ("gm_grid_agree", grid_kill),
        ("gm_curvature", curv_kill or curv_sign_kill),
        ("yasui_no_zero", yasui_kill),
    ] + [(f"scale_{o}_{m}", k) for (o, m), k in scale_kills]
    dead = sorted(name for name, k in killed if k)
    if dead:
        status = f"FALSIFIED (Ritz width-selection; {'; '.join(dead)})"
    else:
        status = "NUMERIC (Ritz width-selection demonstrated)"
    result = {
        "scales": scales,
        "gates": {
            "loc_tol": LOC_TOL,
            "curv_tol": CURV_TOL,
            "yasui_deriv_max": YASUI_DERIV_MAX,
            "scale_tol": SCALE_TOL,
            "kills": [[n, bool(k)] for n, k in killed],
        },
        "verdict": {
            "claim_49_status": status,
            "note": (
                "G-M Ritz extremum selects sigma^2 = nu/omega = 0.5 with "
                "maximum curvature; Yasui has no finite extremum. Location "
                "coincides with the Ermakov fixed point (claim 22) from an "
                "independent route."
            ),
        },
    }
    config = {
        "grids": scales["grids"],
        "base": scales["base"],
        "gates": {
            "loc_tol": LOC_TOL,
            "curv_tol": CURV_TOL,
            "yasui_deriv_max": YASUI_DERIV_MAX,
            "scale_tol": SCALE_TOL,
        },
        "scope": "Ritz-restricted trial class, zero parameters, no full variation",
    }
    payload = {"meta": metadata(config), "result": result}
    if write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        write_json(RESULTS_DIR / "variational_width.json", payload)
        write_text_atomic(
            RESULTS_DIR / "variational_width.md", render_markdown(payload)
        )
    return payload


def render_markdown(payload: dict) -> str:
    result = payload["result"]
    scales = result["scales"]
    analytic = scales["analytic"]
    grid = scales["grid"]
    verdict = result["verdict"]
    lines = [
        "# Gaussian Ritz width-selection (claim 49)",
        "",
        "G-M extremum selects sigma^2 = 0.5 (maximum); Yasui selects nothing.",
        "",
        "| quantity | value |",
        "|---|---:|",
        f"| analytic sigma*^2 | {analytic['sigma_star_sq']:.12f} |",
        f"| grid argmax | {grid['grid_argmax']:.12f} |",
        f"| Newton refined | {grid['refined']:.12f} |",
        f"| curvature d2J/d(s2)^2 | {analytic['curvature_s2']:.12f} |",
        f"| curvature d2J/d(sigma)^2 | {analytic['curvature_sigma']:.12f} |",
        f"| Yasui max derivative | {scales['yasui']['max_derivative']:.6f} |",
        "",
        "## Scalings (predicted s2* = nu/omega)",
        "",
        "| omega | mass | predicted | refined | curvature_s2 |",
        "|---|---|---|---|---:|",
    ]
    for entry in scales["scalings"]:
        lines.append(
            f"| {entry['omega']} | {entry['mass']} | {entry['predicted']:.12f} "
            f"| {entry['refined']:.12f} | {entry['curvature_s2']:.12f} |"
        )
    lines += [
        "",
        "## Verdict",
        "",
        f"- Claim 49: **{verdict['claim_49_status']}**.",
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
    payload = run_variational_width_check()
    print(payload["result"]["verdict"])
