"""Two-component band-model comparison (claim 45, ADR-037)."""

from __future__ import annotations

from domains.fluid_universe.theory.water_twocomponent import (
    EMAX_EV,
    FWHM_CLASSICAL_TOL,
    FWHM_QUANTIZED_TOL,
    REFERENCE_CLASSICAL_EV,
    REFERENCE_QUANTIZED_EV,
    T_REF_K,
    WIDTH_RATIO_TOL,
    twocomponent_scales,
)

from .provenance import RESULTS_DIR, metadata, write_json, write_text_atomic


def run_water_twocomponent_check(write: bool = True) -> dict:
    scales = twocomponent_scales()
    ratio_kill = bool(scales["ratio_kill"])
    width_kill = bool(scales["width_kill"])
    if ratio_kill or width_kill:
        legs = []
        if ratio_kill:
            legs.append(
                f"ratio diff {scales['ratio_diff']:.4f} > {WIDTH_RATIO_TOL}"
            )
        if width_kill:
            legs.append(
                f"classical rel {scales['classical_rel_diff']:.4f} "
                f"(tol {FWHM_CLASSICAL_TOL})/quantized rel "
                f"{scales['quantized_rel_diff']:.4f} "
                f"(tol {FWHM_QUANTIZED_TOL})"
            )
        status = f"FALSIFIED (two-component join; {'; '.join(legs)})"
    else:
        status = "NUMERIC (two-component join survives one comparator)"
    result = {
        "scales": scales,
        "verdict": {
            "ratio_kill": bool(ratio_kill),
            "width_kill": bool(width_kill),
            "claim_45_status": status,
            "note": (
                "Zero-free-parameter join at Emax=1.72 eV: Gaussian red "
                "HWHM from the fixed Marcus scale plus n=4.4 power-law "
                "blue tail. Kill thresholds frozen from ADR-034. "
                "Observed side widths are the Jou-Freeman fits "
                "(G red, L blue) via the Coe review; Wb/Wr definitions "
                "per Bartels."
            ),
        },
    }
    config = {
        "temperature_k": T_REF_K,
        "emax_ev": EMAX_EV,
        "width_ratio_tol": WIDTH_RATIO_TOL,
        "fwhm_classical_tol": FWHM_CLASSICAL_TOL,
        "fwhm_quantized_tol": FWHM_QUANTIZED_TOL,
        "reference_classical_ev": REFERENCE_CLASSICAL_EV,
        "reference_quantized_ev": REFERENCE_QUANTIZED_EV,
        "scope": "two-component join vs observed side widths, no fit",
    }
    payload = {"meta": metadata(config), "result": result}
    if write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        write_json(RESULTS_DIR / "water_twocomponent.json", payload)
        write_text_atomic(
            RESULTS_DIR / "water_twocomponent.md", render_markdown(payload)
        )
    return payload


def render_markdown(payload: dict) -> str:
    result = payload["result"]
    scales = result["scales"]
    observed = scales["observed"]
    verdict = result["verdict"]
    lines = [
        "# Two-component band model vs observed side widths (claim 45)",
        "",
        "Join at Emax with zero free parameters; thresholds frozen.",
        "",
        "| quantity | value |",
        "|---|---:|",
        f"| T ref | {scales['temperature_k']:.2f} K |",
        f"| Marcus FWHM | {scales['marcus_fwhm_ev']:.6f} eV |",
        f"| red HWHM (pred) | {scales['red_hwhm_ev']:.6f} eV |",
        f"| blue HWHM (pred) | {scales['blue_hwhm_ev']:.6f} eV |",
        f"| R_pred | {scales['r_pred']:.6f} |",
        f"| R_obs (L/G) | {scales['r_obs']:.6f} |",
        f"| ratio diff | {scales['ratio_diff']:.6f} |",
        f"| FWHM model | {scales['fwhm_model_ev']:.6f} eV |",
        f"| FWHM obs (G+L) | {observed['fwhm_ev']:.6f} eV |",
        f"| Emax obs | {observed['emax_ev']:.6f} eV |",
        "",
        "## Verdict",
        "",
        f"- Ratio kill: **{verdict['ratio_kill']}**.",
        f"- Width kill: **{verdict['width_kill']}**.",
        f"- Claim 45: **{verdict['claim_45_status']}**.",
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
    payload = run_water_twocomponent_check()
    print(payload["result"]["verdict"])
