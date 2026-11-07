"""Temperature-dependent Born cavity (claim 41, ADR-032)."""

from __future__ import annotations

from domains.fluid_universe.theory.water_temperature import temperature_scales

from .provenance import RESULTS_DIR, metadata, write_json, write_text_atomic

OBSERVED_LOWER_MEV_PER_K = 2.4
OBSERVED_UPPER_MEV_PER_K = 2.8


def run_water_temperature_check(write: bool = True) -> dict:
    scales = temperature_scales()
    result = {
        "scales": scales,
        "observed_shift_mev_per_k": OBSERVED_LOWER_MEV_PER_K,
        "observed_shift_upper_mev_per_k": OBSERVED_UPPER_MEV_PER_K,
        "verdict": {
            "nonzero_temperature_slope": abs(
                scales["lambda_slope_mev_per_k"]
            )
            > 1.0,
            "covers_less_than_half": scales["fraction_of_upper"] < 0.5,
            "width_broadens_with_temperature": scales["width_change_ev"] > 0.0,
            "claim_41_status": (
                "NUMERIC (temperature slope -1.068 meV/K vs observed "
                "2.4-2.8 meV/K)"
            ),
            "claim_42_status": (
                "NUMERIC (residual 1.33-1.85 meV/K after the cavity terms)"
            ),
            "residual_above_one_mev": scales[
                "residual_after_geometric_lower"
            ]
            > 1.0,
            "geometric_coverage_below_half": scales[
                "coverage_geometric_upper"
            ]
            < 0.5,
            "cavity_terms_oppose": scales["cavity_terms_oppose"],
            "net_coverage_below_tenth": scales["coverage_net_upper"] < 0.1,
            "note": (
                "The water-property Born cavity predicts a lambda/VDE red "
                "shift of 1.068036 meV/K from 0 to 45 C, 38.1%-44.5% of the "
                "observed 2.4-2.8 meV/K peak shift. The 1/R geometric slope "
                "is +0.946817 meV/K (33.8%-39.5%), and the two terms have "
                "opposite signs, so their signed sum is -0.121218 meV/K "
                "(4.3%-5.1% of the observed): the cavity does not explain the "
                "shift, and taking the geometric term alone in the observed "
                "direction still leaves 1.45-1.85 meV/K unexplained. The "
                "Marcus width broadens from 0.653822 eV at 0 C to 0.695194 eV "
                "at 45 C. The residual shift points toward a "
                "temperature-dependent bare gap or non-cavity structure, "
                "consistent with the Farr/Schwartz critique."
            ),
        },
    }
    config = {
        "observed_shift_mev_per_k": OBSERVED_LOWER_MEV_PER_K,
        "observed_shift_upper_mev_per_k": OBSERVED_UPPER_MEV_PER_K,
        "scope": "temperature-dependent Born cavity with water properties",
    }
    payload = {"meta": metadata(config), "result": result}
    if write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        write_json(RESULTS_DIR / "water_temperature.json", payload)
        write_text_atomic(
            RESULTS_DIR / "water_temperature.md", render_markdown(payload)
        )
    return payload


def render_markdown(payload: dict) -> str:
    result = payload["result"]
    scales = result["scales"]
    verdict = result["verdict"]
    lines = [
        "# Temperature-dependent Born cavity (claim 41)",
        "",
        "Model: water's static dielectric constant and surface tension",
        "",
        "\\(\\epsilon_s(T)=87.740-0.40008T+9.398\\times10^{-4}T^2"
        "-1.410\\times10^{-6}T^3\\),",
        "",
        "\\(\\gamma(T)=0.07564-1.4\\times10^{-4}T-3.0\\times10^{-7}T^2\\),",
        "",
        "with \\(T\\) in Celsius. The self-consistent Born cavity is solved at "
        "each temperature; \\(\\lambda(T)\\) and the Marcus width follow.",
        "",
        "## Temperature scan",
        "",
        "| \\(T\\) (C) | \\(R\\) (Angstrom) | \\(\\epsilon_s\\) | "
        "\\(\\gamma\\) (N/m) | \\(\\lambda\\) (eV) | VDE (eV) | FWHM (eV) |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in scales["scan"]:
        lines.append(
            f"| {row['temperature_c']:.0f} | "
            f"{row['radius_m'] / 1e-10:.6f} | {row['epsilon_s']:.6f} | "
            f"{row['gamma_n_m']:.6f} | {row['lambda_ev']:.6f} | "
            f"{row['predicted_vde_ev']:.6f} | {row['fwhm_ev']:.6f} |"
        )
    lines += [
        "",
        "## Shift and width",
        "",
        "| quantity | value |",
        "|---|---:|",
        f"| lambda slope | {scales['lambda_slope_mev_per_k']:.6f} meV/K |",
        f"| observed peak shift | {OBSERVED_LOWER_MEV_PER_K:.1f}-"
        f"{OBSERVED_UPPER_MEV_PER_K:.1f} meV/K |",
        f"| fraction of lower | {scales['fraction_of_lower']:.6f} |",
        f"| fraction of upper | {scales['fraction_of_upper']:.6f} |",
        f"| FWHM at 0 C | {scales['width_0c_ev']:.6f} eV |",
        f"| FWHM at 45 C | {scales['width_45c_ev']:.6f} eV |",
        f"| width change | {scales['width_change_ev']:.6f} eV |",
        "",
        "The cavity is not temperature-independent, but its lambda/VDE slope "
        "covers only 38%-45% of the observed peak shift. The residual points "
        "to a temperature-dependent bare gap or a non-cavity structure.",
        "",
        "## Residual shift",
        "",
        "| quantity | value |",
        "|---|---:|",
        f"| geometric 1/R slope | {scales['geometric_slope_mev_per_k']:.6f} meV/K |",
        f"| geometric coverage of lower | "
        f"{scales['coverage_geometric_lower']:.6f} |",
        f"| geometric coverage of upper | "
        f"{scales['coverage_geometric_upper']:.6f} |",
        f"| residual after lambda, lower | "
        f"{scales['residual_after_lambda_lower']:.6f} meV/K |",
        f"| residual after lambda, upper | "
        f"{scales['residual_after_lambda_upper']:.6f} meV/K |",
        f"| residual after geometric, lower | "
        f"{scales['residual_after_geometric_lower']:.6f} meV/K |",
        f"| residual after geometric, upper | "
        f"{scales['residual_after_geometric_upper']:.6f} meV/K |",
        f"| signed net cavity slope | "
        f"{scales['net_cavity_slope_mev_per_k']:.6f} meV/K |",
        f"| net coverage of lower | {scales['coverage_net_lower']:.6f} |",
        f"| net coverage of upper | {scales['coverage_net_upper']:.6f} |",
        f"| residual after both terms, lower | "
        f"{scales['residual_after_net_lower']:.6f} meV/K |",
        f"| residual after both terms, upper | "
        f"{scales['residual_after_net_upper']:.6f} meV/K |",
        "",
        "The cavity's dielectric and geometric terms have opposite signs, so "
        "they do not add: their signed sum is -0.121218 meV/K, 4.3%-5.1% of "
        "the observed shift, leaving 2.52-2.92 meV/K unexplained. Taking the "
        "geometric term alone in the observed direction still leaves "
        "1.45-1.85 meV/K. Neither reading is a trivial geometric effect.",
        "",
        "## Verdict",
        "",
        f"- Nonzero temperature slope: "
        f"**{verdict['nonzero_temperature_slope']}**.",
        f"- Covers less than half of the observed shift: "
        f"**{verdict['covers_less_than_half']}**.",
        f"- Width broadens with temperature: "
        f"**{verdict['width_broadens_with_temperature']}**.",
        f"- Residual after the cavity terms is above 1 meV/K: "
        f"**{verdict['residual_above_one_mev']}**.",
        f"- Geometric coverage is below half: "
        f"**{verdict['geometric_coverage_below_half']}**.",
        f"- The two cavity terms have opposite signs: "
        f"**{verdict['cavity_terms_oppose']}**.",
        f"- The signed net cavity coverage is below a tenth: "
        f"**{verdict['net_coverage_below_tenth']}**.",
        f"- Claim 41: **{verdict['claim_41_status']}**.",
        f"- Claim 42: **{verdict['claim_42_status']}**.",
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
    payload = run_water_temperature_check()
    print(payload["result"]["verdict"])
