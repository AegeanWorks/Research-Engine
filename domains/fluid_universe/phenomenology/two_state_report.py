"""Shared-lambda two-state Marcus assignment (claim 44, ADR-036)."""

from __future__ import annotations

from domains.fluid_universe.theory.two_state_marcus import (
    LAMBDA_EV,
    ROOM_TEMPERATURE_K,
    SHAPE_RATIO_TOL,
    two_state_scales,
)

from .provenance import RESULTS_DIR, metadata, write_json, write_text_atomic


def run_two_state_comparison(
    temperature_k: float = ROOM_TEMPERATURE_K, write: bool = False
) -> dict:
    """Compare the shared-lambda equal-width prediction vs the observed ratio.

    Pure arithmetic on frozen inputs (no fit). The kill threshold is read
    from domains.fluid_universe.theory.two_state_marcus (frozen, inherited from ADR-034) and
    never tuned here. The temperature cancels in the ratio prediction;
    300 K matches the claim-40 reference.
    """
    scales = two_state_scales(temperature_k)
    prediction = scales["prediction"]
    observed = scales["observed"]
    pred_ratio = prediction["predicted_ratio"]
    obs_ratio = observed["observed_ratio"]
    ratio_diff = abs(obs_ratio - pred_ratio)
    worst_diff = abs(observed["worst_case_ratio"] - pred_ratio)
    shape_kill = ratio_diff > SHAPE_RATIO_TOL
    return {
        "temperature_k": temperature_k,
        "predicted_width_g1_ev": prediction["width_g1_ev"],
        "predicted_width_g2_ev": prediction["width_g2_ev"],
        "predicted_ratio": pred_ratio,
        "observed_g1_width_ev": observed["g1_width_ev"],
        "observed_g2_width_ev": observed["g2_width_ev"],
        "observed_ratio": obs_ratio,
        "observed_ratio_sigma": observed["observed_ratio_sigma"],
        "ratio_diff_vs_one": ratio_diff,
        "worst_case_diff_vs_one": worst_diff,
        "shape_kill_shared_lambda": bool(shape_kill),
        "shape_kill_threshold": SHAPE_RATIO_TOL,
    }


def run_two_state_check(write: bool = True) -> dict:
    scales = two_state_scales()
    comparison = run_two_state_comparison()
    shape_kill = comparison["shape_kill_shared_lambda"]
    if shape_kill:
        status = (
            "FALSIFIED (shared-lambda two-state Marcus assignment; "
            f"component ratio {comparison['observed_ratio']:.4f} vs 1, "
            f"diff {comparison['ratio_diff_vs_one']:.4f} > "
            f"{SHAPE_RATIO_TOL})"
        )
    else:
        status = (
            "UNVERIFIED (shared-lambda widths not killed by this "
            "comparator; not promoted)"
        )
    result = {
        "scales": scales,
        "comparison": comparison,
        "verdict": {
            "widths_identical": scales["prediction"]["width_g1_ev"]
            == scales["prediction"]["width_g2_ev"]
            and scales["prediction"]["predicted_ratio"] == 1.0,
            "ratio_kill": bool(shape_kill),
            "claim_44_status": status,
            "shape_kill_shared_lambda": bool(shape_kill),
            "note": (
                "IF the Jou-Freeman 0.71 vs 0.37 eV components were two "
                "classical Marcus states sharing the frozen Born-cavity "
                "lambda=1.617132544 eV at one temperature, both would have "
                f"FWHM {comparison['predicted_width_g1_ev']:.6f} eV "
                "(ratio exactly 1, T-independent). The observed ratio is "
                f"{comparison['observed_ratio']:.4f} "
                f"(+/- {comparison['observed_ratio_sigma']:.2f}), diff "
                f"{comparison['ratio_diff_vs_one']:.4f} > "
                f"{SHAPE_RATIO_TOL}, so the shared-lambda two-state "
                "assignment is falsified. This shares its shape fact with "
                "claim 43 and is not independent evidence. A "
                "state-dependent solvation (lambda1 != lambda2) would fit "
                "but predict nothing; a non-Marcus line shape is required."
            ),
        },
    }
    config = {
        "lambda_ev": LAMBDA_EV,
        "temperature_k": ROOM_TEMPERATURE_K,
        "shape_ratio_tol": SHAPE_RATIO_TOL,
        "scope": "shared-lambda two-state Marcus equal-width test, no fit",
        "observed": {
            "g1_width_ev": comparison["observed_g1_width_ev"],
            "g2_width_ev": comparison["observed_g2_width_ev"],
        },
    }
    payload = {"meta": metadata(config), "result": result}
    if write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        write_json(RESULTS_DIR / "two_state.json", payload)
        write_text_atomic(
            RESULTS_DIR / "two_state.md", render_markdown(payload)
        )
    return payload


def render_markdown(payload: dict) -> str:
    result = payload["result"]
    scales = result["scales"]
    prediction = scales["prediction"]
    observed = scales["observed"]
    comparison = result["comparison"]
    verdict = result["verdict"]
    lines = [
        "# Shared-lambda two-state Marcus assignment (claim 44)",
        "",
        "Conditional test: IF the observed components were two Marcus states",
        "sharing the frozen cavity lambda, their widths would be identical.",
        "",
        f"\\(\\lambda={scales['lambda_ev']:.9f}\\) eV; "
        f"\\(T={scales['prediction']['temperature_k']:.1f}\\) K.",
        "",
        "## Predicted widths (shared lambda)",
        "",
        "| quantity | value |",
        "|---|---:|",
        f"| G1 FWHM | {prediction['width_g1_ev']:.6f} eV |",
        f"| G2 FWHM | {prediction['width_g2_ev']:.6f} eV |",
        f"| predicted ratio | {prediction['predicted_ratio']:.6f} |",
        "",
        "## Observed comparator (Jou & Freeman 1979, no fit)",
        "",
        "| quantity | value |",
        "|---|---:|",
        f"| G1 width | {observed['g1_width_ev']} eV |",
        f"| G2 width | {observed['g2_width_ev']} eV |",
        f"| observed ratio | {comparison['observed_ratio']:.4f} +/- {comparison['observed_ratio_sigma']:.2f} |",
        f"| ratio diff vs 1 | {comparison['ratio_diff_vs_one']:.4f} |",
        f"| kill threshold | {comparison['shape_kill_threshold']:.2f} |",
        "",
        "## Verdict",
        "",
        f"- Widths identical: **{verdict['widths_identical']}**.",
        f"- Shape kill (shared lambda): **{verdict.get('shape_kill_shared_lambda')}**.",
        f"- Claim 44: **{verdict['claim_44_status']}**.",
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
    payload = run_two_state_check()
    print(payload["result"]["verdict"])
