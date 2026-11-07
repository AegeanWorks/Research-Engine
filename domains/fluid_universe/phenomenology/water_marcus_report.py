"""Marcus band width from the water reorganization energy (claim 40, ADR-031)."""

from __future__ import annotations

from domains.fluid_universe.theory.water_marcus import marcus_scales

from .provenance import RESULTS_DIR, metadata, write_json, write_text_atomic

OBSERVED_CENTER_EV = 1.7


def run_water_marcus_check(write: bool = True) -> dict:
    scales = marcus_scales()
    widths = scales["widths_ev"]
    result = {
        "scales": scales,
        "observed_center_ev": OBSERVED_CENTER_EV,
        "verdict": {
            "classical_width_within_5_percent": abs(
                1.0 - scales["ratio_classical"]
            )
            < 0.05,
            "quantized_width_within_15_percent": abs(
                1.0 - scales["ratio_quantized"]
            )
            < 0.15,
            "sqrt_temperature_scaling": abs(
                widths["350"] / widths["300"]
                - scales["sqrt_ratio_350_300"]
            )
            < 1.0e-6,
            "claim_40_status": (
                "NUMERIC (Marcus FWHM 0.681 eV; reference 0.706-0.773 eV)"
            ),
            "note": (
                "The same water reorganization energy that predicts the VDE "
                "also predicts the band width: FWHM=0.680915 eV at 300 K, "
                "3.6% below the classical reference 0.706 eV and 11.9% below "
                "the quantized 0.773 eV. The width scales as sqrt(T): "
                "0.555964 eV at 200 K and 0.735472 eV at 350 K. The classical "
                "Gaussian model is approximate; the experimental band is "
                "asymmetric with a blue tail. The next test is the asymmetric "
                "line shape and its temperature dependence."
            ),
        },
    }
    config = {
        "lambda_ev": scales["lambda_ev"],
        "center_ev": OBSERVED_CENTER_EV,
        "reference_classical_ev": scales["reference_classical_ev"],
        "reference_quantized_ev": scales["reference_quantized_ev"],
        "scope": "classical Marcus Gaussian width from water reorganization",
    }
    payload = {"meta": metadata(config), "result": result}
    if write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        write_json(RESULTS_DIR / "water_marcus.json", payload)
        write_text_atomic(RESULTS_DIR / "water_marcus.md", render_markdown(payload))
    return payload


def render_markdown(payload: dict) -> str:
    result = payload["result"]
    scales = result["scales"]
    widths = scales["widths_ev"]
    verdict = result["verdict"]
    lines = [
        "# Marcus band width from the water reorganization energy (claim 40)",
        "",
        "Model: the classical Marcus Gaussian width",
        "",
        "\\(\\text{FWHM}=2\\sqrt{2\\ln2}\\sqrt{2\\lambda k_BT}\\),",
        "",
        f"with the same \\(\\lambda={scales['lambda_ev']:.9f}\\) eV from claim 39.",
        "",
        "## Width versus temperature",
        "",
        "| temperature (K) | FWHM (eV) |",
        "|---:|---:|",
    ]
    for temperature in ("200", "250", "298", "300", "350"):
        lines.append(f"| {temperature} | {widths[temperature]:.6f} |")
    lines += [
        "",
        "## Reference comparison",
        "",
        "| quantity | value |",
        "|---|---:|",
        f"| Marcus FWHM at 300 K | {widths['300']:.6f} eV |",
        f"| classical reference | {scales['reference_classical_ev']:.3f} eV |",
        f"| quantized reference | {scales['reference_quantized_ev']:.3f} eV |",
        f"| Marcus / classical | {scales['ratio_classical']:.6f} |",
        f"| Marcus / quantized | {scales['ratio_quantized']:.6f} |",
        f"| sqrt(350/300) | {scales['sqrt_ratio_350_300']:.6f} |",
        "",
        "The reference widths are the classical (0.706 eV) and quantized "
        "(0.773 eV) bulk hydrated-electron values of Turi et al., JCTC 20, "
        "4265 (2024). The experimental band is broad and asymmetric, with a "
        "FWHM of order 0.7 eV.",
        "",
        "## Verdict",
        "",
        f"- Marcus width is within 5% of the classical reference: "
        f"**{verdict['classical_width_within_5_percent']}**.",
        f"- Marcus width is within 15% of the quantized reference: "
        f"**{verdict['quantized_width_within_15_percent']}**.",
        f"- The width follows sqrt(T): "
        f"**{verdict['sqrt_temperature_scaling']}**.",
        f"- Claim 40: **{verdict['claim_40_status']}**.",
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
    payload = run_water_marcus_check()
    print(payload["result"]["verdict"])
