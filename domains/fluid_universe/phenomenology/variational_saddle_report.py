"""2D Ritz saddle check (claim 50, ADR-042).

Zero free parameters, no dynamics beyond the stationary 2D Gaussian
trial class. Recomputes live from domains.fluid_universe.theory.variational_saddle:

- location: analytic (s*, c*) = (nu/omega, 0) == (0.5, 0) (gate 1e-9);
- conditional extremum: max over s at c = 0 AND min over c at the
  maximizing s agree within grid half-steps; 1D Newton polish each
  to 1e-9 (a joint box argmax is the WRONG gate for a saddle; the
  box max sits on the boundary above the saddle value — recorded,
  never gated);
- curvature: d2J/ds2 = -4.0 and d2J/dc2 = +1.0 at the extremum
  (gate 1e-9 each) with mixed sign (the saddle signature) and
  zero mixed partial;
- Yasui: derivative negative everywhere on the frozen grid
  (gate max < -1e-3) and J monotone; c selected at 0, no finite-s
  extremum;
- scaling: omega = 2 gives s* = 0.25 with curvatures (-32.0, +0.5).
"""

from __future__ import annotations

import math

from domains.fluid_universe.theory.variational_saddle import saddle_scales

from .provenance import RESULTS_DIR, metadata, write_json, write_text_atomic

LOC_TOL = 1e-9
CURV_TOL = 1e-9
YASUI_DERIV_MAX = -1e-3


def run_variational_saddle_check(write: bool = True) -> dict:
    scales = saddle_scales()
    analytic = scales["analytic"]
    grid = scales["grid"]
    yasui = scales["yasui"]
    loc_kill = abs(analytic["sigma_star_sq"] - 0.5) > LOC_TOL or abs(
        analytic["c_star"] - 0.0
    ) > LOC_TOL
    slice_kill = abs(grid["grid_s"] - 0.5) > grid["grid_step_s"] or abs(
        grid["grid_c"] - 0.0
    ) > grid["grid_step_c"]
    refine_kill = abs(grid["refined_s"] - 0.5) > LOC_TOL or abs(
        grid["refined_c"] - 0.0
    ) > LOC_TOL
    curv_kill = (
        abs(analytic["curvature_s"] - (-4.0)) > CURV_TOL
        or abs(analytic["curvature_c"] - 1.0) > CURV_TOL
    )
    sign_kill = not (
        analytic["curvature_s"] < 0.0
        and analytic["curvature_c"] > 0.0
        and analytic["mixed"] == 0.0
    )
    yasui_kill = not (
        yasui["all_negative"]
        and yasui["max_derivative"] < YASUI_DERIV_MAX
        and yasui["max_diff"] < 0.0
    )
    scal = scales["scalings"]
    scale_kill = abs(scal["refined_s"] - scal["predicted_s"]) > LOC_TOL or abs(
        scal["refined_c"] - 0.0
    ) > LOC_TOL
    scale_pred_kill = abs(scal["predicted_s"] - 0.25) > 1e-12
    scale_curv_kill = abs(scal["curvature_s"] - (-32.0)) > 1e-9 or abs(
        scal["curvature_c"] - 0.5
    ) > 1e-9
    killed = [
        ("gm_location", loc_kill),
        ("gm_slice_agree", slice_kill),
        ("gm_newton_refine", refine_kill),
        ("gm_curvature", curv_kill or sign_kill),
        ("yasui_no_zero", yasui_kill),
        ("scaling_point", scale_kill or scale_pred_kill or scale_curv_kill),
    ]
    dead = sorted(name for name, k in killed if k)
    if dead:
        status = f"FALSIFIED (Ritz saddle; {'; '.join(dead)})"
    else:
        status = "NUMERIC (Ritz saddle demonstrated)"
    result = {
        "scales": scales,
        "gates": {
            "loc_tol": LOC_TOL,
            "curv_tol": CURV_TOL,
            "yasui_deriv_max": YASUI_DERIV_MAX,
            "kills": [[n, bool(k)] for n, k in killed],
        },
        "verdict": {
            "claim_50_status": status,
            "note": (
                "G-M Ritz stationary point (0.5, 0) with mixed curvature "
                "(-4.0, +1.0): minimum in drift-rotation, maximum in "
                "width. Yasui selects c = 0 with no finite width."
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
        },
        "scope": "Ritz-restricted trial class, zero parameters, saddle signature only",
    }
    payload = {"meta": metadata(config), "result": result}
    if write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        write_json(RESULTS_DIR / "variational_saddle.json", payload)
        write_text_atomic(
            RESULTS_DIR / "variational_saddle.md", render_markdown(payload)
        )
    return payload


def render_markdown(payload: dict) -> str:
    result = payload["result"]
    scales = result["scales"]
    analytic = scales["analytic"]
    grid = scales["grid"]
    verdict = result["verdict"]
    lines = [
        "# 2D Ritz saddle (claim 50)",
        "",
        "G-M stationary point (0.5, 0) with mixed curvature (-4.0, +1.0).",
        "",
        "| quantity | value |",
        "|---|---:|",
        f"| analytic (s*, c*) | ({analytic['sigma_star_sq']:.12f}, {analytic['c_star']:.12f}) |",
        f"| conditional grid (s, c) | ({grid['grid_s']:.12f}, {grid['grid_c']:.12f}) |",
        f"| Newton refined (s, c) | ({grid['refined_s']:.12f}, {grid['refined_c']:.12f}) |",
        f"| curvature (s, c) | ({analytic['curvature_s']:.12f}, {analytic['curvature_c']:.12f}) |",
        f"| box argmax (s, c) [record] | ({grid['box_argmax_s']:.6f}, {grid['box_argmax_c']:.6f}) |",
        f"| box max vs saddle value [record] | {grid['box_max_value']:.6f} vs {grid['saddle_value']:.6f} |",
        f"| Yasui max derivative | {scales['yasui']['max_derivative']:.6f} |",
        "",
        "## Verdict",
        "",
        f"- Claim 50: **{verdict['claim_50_status']}**.",
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
    payload = run_variational_saddle_check()
    print(payload["result"]["verdict"])
