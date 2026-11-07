"""Fixed-lambda cavity-Marcus line-shape prediction (claim 43, ADR-034)."""

from __future__ import annotations

import math

from domains.fluid_universe.theory.water_lineshape import (
    LAMBDA_EV,
    SHAPE_RATIO_TOL,
    SKEW_TOL,
    WIDTH_RATIO_TOL,
    lineshape_scales,
)
from domains.fluid_universe.theory.water_observed_shape import observed_scales

from .provenance import RESULTS_DIR, metadata, write_json, write_text_atomic


def run_water_lineshape_comparison(write: bool = False) -> dict:
    """Compare the fixed-lambda prediction against citable observed shape.

    Pure arithmetic on observed constants (no fit). Uses the Christensen &
    Sehested (1986) half-width slope and the Jou & Freeman (1979)
    two-Gaussian-plus-tail decomposition. Kill thresholds are read from
    theory.water_lineshape (frozen, ADR-034) and never tuned here.
    """
    scales = lineshape_scales()
    prediction = scales["prediction"]
    observed = observed_scales()
    width_obs = observed["width"]
    shape_obs = observed["shape"]

    # Width-ratio leg: observed change over 0-45 C from the Christensen
    # slope, ratio formed against the predicted 0 C width as the scale
    # (conservative: uses the model's own scale so no observed absolute
    # width is invented). Both readings of the ambiguous half-width
    # definition are carried.
    w0 = prediction["width_0c_ev"]
    span = width_obs["span_k"]
    obs_change = width_obs["change_as_stated_ev"]
    obs_change_hwhm = width_obs["change_if_hwhm_ev"]
    obs_ratio = (w0 + obs_change) / w0
    obs_ratio_hwhm = (w0 + obs_change_hwhm) / w0
    pred_ratio = prediction["width_ratio_45_over_0"]
    ratio_diff = abs(obs_ratio - pred_ratio)
    ratio_diff_hwhm = abs(obs_ratio_hwhm - pred_ratio)
    pred_change = prediction["width_change_ev"]
    pred_slope = pred_change / span
    obs_slope = width_obs["slope_ev_per_k"]

    # Shape leg: a single symmetric Gaussian has half-width ratio 1 and
    # skew 0. The observed band needs two Gaussians of different widths
    # (0.71 vs 0.37 eV, ratio 1.92) plus a power-law tail (n = 4.4),
    # and is described in every cited source as asymmetric
    # (Gaussian low-energy side, Lorentzian high-energy side).
    comp_ratio = shape_obs["component_width_ratio"]
    comp_diff = abs(comp_ratio - 1.0)
    shape_kill = comp_diff > SHAPE_RATIO_TOL and not shape_obs["tail_is_gaussian"]
    skew_kill = shape_obs["single_gaussian_compatible"] is False
    ratio_kill = ratio_diff > WIDTH_RATIO_TOL
    ratio_kill_hwhm = ratio_diff_hwhm > WIDTH_RATIO_TOL

    return {
        "observed": observed,
        "predicted_ratio": pred_ratio,
        "predicted_change_ev": pred_change,
        "predicted_slope_ev_per_k": pred_slope,
        "observed_change_ev": obs_change,
        "observed_change_if_hwhm_ev": obs_change_hwhm,
        "observed_ratio_on_predicted_scale": obs_ratio,
        "observed_ratio_if_hwhm": obs_ratio_hwhm,
        "ratio_diff": ratio_diff,
        "ratio_diff_if_hwhm": ratio_diff_hwhm,
        "ratio_kill": bool(ratio_kill),
        "ratio_kill_if_hwhm": bool(ratio_kill_hwhm),
        "component_width_ratio": comp_ratio,
        "component_width_diff_vs_one": comp_diff,
        "shape_kill_gaussian_only": bool(shape_kill),
        "skew_kill_gaussian_only": bool(skew_kill),
        "shape_kill_threshold": SHAPE_RATIO_TOL,
        "width_ratio_threshold": WIDTH_RATIO_TOL,
        "skew_threshold": SKEW_TOL,
    }


def run_water_lineshape_check(write: bool = True) -> dict:
    scales = lineshape_scales()
    moments = scales["moments"]
    prediction = scales["prediction"]
    comparison = run_water_lineshape_comparison()
    expected_ratio = math.sqrt(
        (prediction["lambda_45c_ev"] * 318.15)
        / (prediction["lambda_0c_ev"] * 273.15)
    )
    shape_kill = comparison["shape_kill_gaussian_only"]
    ratio_kill = comparison["ratio_kill"]
    if shape_kill:
        status = (
            "FALSIFIED (Gaussian-only shape; sqrt(lambda T) scaling "
            f"survives: ratio diff {comparison['ratio_diff']:.4f} "
            f"<= {WIDTH_RATIO_TOL})"
            if not ratio_kill
            else "FALSIFIED (Gaussian-only shape and width-ratio scaling)"
        )
    elif ratio_kill:
        status = "FALSIFIED (width-ratio scaling)"
    else:
        status = (
            "UNVERIFIED (prediction survives this comparator; "
            "shape not tested)"
        )
    result = {
        "scales": scales,
        "comparison": comparison,
        "verdict": {
            "symmetry_exact": moments["symmetric"] is True
            and moments["skewness"] == 0.0
            and moments["half_width_ratio"] == 1.0,
            "widths_match_temperature_scan": abs(
                prediction["width_0c_ev"] - 0.653821691
            )
            < 1.0e-6
            and abs(prediction["width_45c_ev"] - 0.695194215) < 1.0e-6,
            "ratio_matches_sqrt_lambda_t": abs(
                prediction["width_ratio_45_over_0"] - expected_ratio
            )
            < 1.0e-9,
            "claim_43_status": status,
            "shape_kill_gaussian_only": bool(shape_kill),
            "ratio_kill": bool(ratio_kill),
            "note": (
                "With lambda fixed at 1.617132544 eV from the Born cavity, "
                "the classical Marcus Gaussian predicts W(0 C)=0.653822 eV, "
                "W(45 C)=0.695194 eV, ratio 1.0633, with exact symmetry "
                "(skew 0, half-width ratio 1). Observed comparator: "
                "Christensen & Sehested 1986 width slope 2e-4 eV/K "
                f"(predicted slope {comparison['predicted_slope_ev_per_k']:.3e} "
                "eV/K) and Jou & Freeman 1979 two-Gaussian-plus-tail "
                "decomposition (0.71 vs 0.37 eV, tail n=4.4, asymmetric; "
                "Bartels et al. 2005 Gaussian/Lorentzian split). "
                f"Ratio diff {comparison['ratio_diff']:.4f} "
                f"(HWHM reading {comparison['ratio_diff_if_hwhm']:.4f}) "
                f"vs tolerance {WIDTH_RATIO_TOL}; component-width ratio "
                f"{comparison['component_width_ratio']:.4f} vs 1 "
                f"(diff {comparison['component_width_diff_vs_one']:.4f} "
                f"> {SHAPE_RATIO_TOL}). The single symmetric Gaussian is "
                "falsified on shape; the width-ratio scaling survives this "
                "comparator."
            ),
        },
    }
    config = {
        "lambda_ev": LAMBDA_EV,
        "width_ratio_tol": WIDTH_RATIO_TOL,
        "shape_ratio_tol": SHAPE_RATIO_TOL,
        "skew_tol": SKEW_TOL,
        "scope": "fixed-lambda Marcus line-shape vs observed comparator, no fit",
        "observed": {
            "width_slope_ev_per_k": comparison["observed"]["width"][
                "slope_ev_per_k"
            ],
            "g1_width_ev": comparison["observed"]["shape"]["g1_width_ev"],
            "g2_width_ev": comparison["observed"]["shape"]["g2_width_ev"],
            "tail_power_n_water": comparison["observed"]["shape"][
                "tail_power_n_water"
            ],
        },
    }
    payload = {"meta": metadata(config), "result": result}
    if write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        write_json(RESULTS_DIR / "water_lineshape.json", payload)
        write_text_atomic(
            RESULTS_DIR / "water_lineshape.md", render_markdown(payload)
        )
    return payload


def render_markdown(payload: dict) -> str:
    result = payload["result"]
    scales = result["scales"]
    prediction = scales["prediction"]
    moments = scales["moments"]
    thresholds = scales["thresholds"]
    verdict = result["verdict"]
    comparison = result.get("comparison", {})
    observed = comparison.get("observed", {})
    width_obs = observed.get("width", {})
    shape_obs = observed.get("shape", {})
    lines = [
        "# Fixed-lambda cavity-Marcus line-shape vs observed comparator (claim 43)",
        "",
        "Model: classical Marcus Gaussian with lambda fixed from claim 39.",
        "",
        f"\\(\\lambda={scales['lambda_ev']:.9f}\\) eV; "
        "\\(\\text{FWHM}=2\\sqrt{2\\ln2}\\sqrt{2\\lambda k_BT}\\).",
        "",
        "## Predicted widths",
        "",
        "| quantity | value |",
        "|---|---:|",
        f"| W(0 C) | {prediction['width_0c_ev']:.6f} eV |",
        f"| W(45 C) | {prediction['width_45c_ev']:.6f} eV |",
        f"| change | {prediction['width_change_ev']:.6f} eV |",
        f"| ratio W45/W0 | {prediction['width_ratio_45_over_0']:.6f} |",
        "",
        "## Symmetry (exact for a Gaussian)",
        "",
        "| quantity | value |",
        "|---|---:|",
        f"| skewness | {moments['skewness']:.6f} |",
        f"| half-width ratio | {moments['half_width_ratio']:.6f} |",
        f"| third central moment | {moments['third_central_moment']:.6f} |",
        "",
        "## Observed comparator (no fit)",
        "",
        "| quantity | value | source |",
        "|---|---|---|",
        f"| width slope | {width_obs.get('slope_ev_per_k', float('nan')):.1e} eV/K | Christensen & Sehested 1986 |",
        f"| observed change (45 K) | {comparison.get('observed_change_ev', float('nan')):.6f} eV | slope x span |",
        f"| predicted change | {comparison.get('predicted_change_ev', float('nan')):.6f} eV | fixed lambda |",
        f"| observed ratio on predicted scale | {comparison.get('observed_ratio_on_predicted_scale', float('nan')):.6f} | W0 predicted |",
        f"| ratio diff | {comparison.get('ratio_diff', float('nan')):.6f} | vs {comparison.get('width_ratio_threshold', 0.05)} |",
        f"| G1 width | {shape_obs.get('g1_width_ev', float('nan'))} eV | Jou & Freeman 1979 |",
        f"| G2 width | {shape_obs.get('g2_width_ev', float('nan'))} eV | Jou & Freeman 1979 |",
        f"| component ratio | {comparison.get('component_width_ratio', float('nan')):.4f} | 0.71/0.37 |",
        f"| tail power n | {shape_obs.get('tail_power_n_water', float('nan'))} | Jou & Freeman 1979 (water) |",
        "",
        "## Kill thresholds (frozen, ADR-034)",
        "",
        "| quantity | value |",
        "|---|---:|",
        f"| width ratio tolerance | {thresholds['width_ratio_tol']:.2f} |",
        f"| shape ratio tolerance | {thresholds['shape_ratio_tol']:.2f} |",
        f"| skew tolerance | {thresholds['skew_tol']:.2f} |",
        "",
        "## Verdict",
        "",
        f"- Symmetry exact: **{verdict['symmetry_exact']}**.",
        f"- Widths match the temperature scan: "
        f"**{verdict['widths_match_temperature_scan']}**.",
        f"- Ratio matches sqrt(lambda T): "
        f"**{verdict['ratio_matches_sqrt_lambda_t']}**.",
        f"- Shape kill (Gaussian-only): **{verdict.get('shape_kill_gaussian_only')}**.",
        f"- Ratio kill: **{verdict.get('ratio_kill')}**.",
        f"- Claim 43: **{verdict['claim_43_status']}**.",
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
    payload = run_water_lineshape_check()
    print(payload["result"]["verdict"])
