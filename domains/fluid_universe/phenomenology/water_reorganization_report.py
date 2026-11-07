"""Water reorganization and the VDE-optical difference (claim 38, ADR-029)."""

from __future__ import annotations

from domains.fluid_universe.theory.water_reorganization import reorganization_scales

from .provenance import RESULTS_DIR, metadata, write_json, write_text_atomic

OBSERVED_OPTICAL_EV = 1.7


def run_water_reorganization_check(write: bool = True) -> dict:
    scales = reorganization_scales()
    capillary = scales["capillary"]
    required = scales["required"]
    pressure = scales["pressure"]
    result = {
        "scales": scales,
        "observed_optical_ev": OBSERVED_OPTICAL_EV,
        "verdict": {
            "lambda_within_15_percent": capillary["relative_residual"] < 0.15,
            "predicted_vde_within_2sigma": capillary["sigma"] < 2.0,
            "required_radius_within_15_percent": abs(
                1.0 - required["radius_ratio"]
            )
            < 0.15,
            "pressure_radius_inconsistent": pressure["lambda_ratio"] < 0.7,
            "claim_38_status": (
                "NUMERIC (reorganization relation; 11.9% residual, "
                "1.87 sigma)"
            ),
            "note": (
                "The VDE-optical difference 1.57 eV is close to water's "
                "dielectric reorganization energy at the capillary radius, "
                "lambda=1.383 eV (residual 0.187 eV, 11.9%, 1.87 sigma). The "
                "required radius is 2.518 Angstrom (0.881x capillary). The "
                "pressure-balanced radius 3.973 Angstrom gives only 0.995 eV "
                "(0.634x) and is inconsistent. The relation is approximate; "
                "a two-state Marcus model with the solvent coordinate is the "
                "next test."
            ),
        },
    }
    config = {
        "epsilon_s": scales["epsilon_s"],
        "epsilon_opt": scales["epsilon_opt"],
        "vde_ev": scales["vde_ev"],
        "optical_ev": OBSERVED_OPTICAL_EV,
        "scope": "water dielectric reorganization and the VDE-optical difference",
    }
    payload = {"meta": metadata(config), "result": result}
    if write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        write_json(RESULTS_DIR / "water_reorganization.json", payload)
        write_text_atomic(
            RESULTS_DIR / "water_reorganization.md", render_markdown(payload)
        )
    return payload


def render_markdown(payload: dict) -> str:
    result = payload["result"]
    scales = result["scales"]
    capillary = scales["capillary"]
    required = scales["required"]
    pressure = scales["pressure"]
    verdict = result["verdict"]
    lines = [
        "# Water reorganization and the VDE-optical difference (claim 38)",
        "",
        "Model: \\(\\lambda(R)=e^2(1/\\epsilon_\\infty-1/\\epsilon_s)/"
        "(8\\pi\\epsilon_0R)\\), with water's \\(\\epsilon_s=78.4\\) and "
        "\\(\\epsilon_\\infty=1.78\\). The measured VDE is "
        f"\\({scales['vde_ev']:.2f}\\pm{scales['vde_uncertainty_ev']:.2f}\\) "
        f"eV and the optical absorption is {OBSERVED_OPTICAL_EV:.2f} eV, so "
        f"the observed difference is {scales['observed_difference_ev']:.2f} eV.",
        "",
        "## Capillary radius",
        "",
        "| quantity | value |",
        "|---|---:|",
        f"| radius | {capillary['radius_m']:.9e} m "
        f"({capillary['radius_m'] / 1e-10:.6f} Angstrom) |",
        f"| reorganization energy | {capillary['lambda_ev']:.6f} eV |",
        f"| predicted VDE (optical + lambda) | "
        f"{capillary['predicted_vde_ev']:.6f} eV |",
        f"| residual (predicted - measured) | "
        f"{capillary['residual_ev']:.6f} eV |",
        f"| relative residual | {capillary['relative_residual']:.6f} |",
        f"| residual in VDE sigma | {capillary['sigma']:.6f} |",
        "",
        "## Required radius",
        "",
        "| quantity | value |",
        "|---|---:|",
        f"| radius for the 1.57 eV difference | "
        f"{required['radius_m']:.9e} m "
        f"({required['radius_m'] / 1e-10:.6f} Angstrom) |",
        f"| required / capillary | {required['radius_ratio']:.6f} |",
        "",
        "## Pressure-balanced radius",
        "",
        "| quantity | value |",
        "|---|---:|",
        f"| pressure-balanced radius | {pressure['radius_m']:.9e} m "
        f"({pressure['radius_m'] / 1e-10:.6f} Angstrom) |",
        f"| reorganization energy | {pressure['lambda_ev']:.6f} eV |",
        f"| lambda / observed difference | {pressure['lambda_ratio']:.6f} |",
        f"| residual | {pressure['residual_ev']:.6f} eV |",
        "",
        "The capillary radius is close to the radius required by the "
        "VDE-optical difference; the pressure-balanced radius is not. This "
        "favors the capillary-sized cavity for the optical reorganization, "
        "even though the pressure-balanced cavity is larger.",
        "",
        "## Verdict",
        "",
        f"- Lambda is within 15% of the observed difference: "
        f"**{verdict['lambda_within_15_percent']}**.",
        f"- Predicted VDE is within 2 sigma: "
        f"**{verdict['predicted_vde_within_2sigma']}**.",
        f"- Required radius is within 15% of the capillary radius: "
        f"**{verdict['required_radius_within_15_percent']}**.",
        f"- Pressure-balanced radius is inconsistent: "
        f"**{verdict['pressure_radius_inconsistent']}**.",
        f"- Claim 38: **{verdict['claim_38_status']}**.",
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
    payload = run_water_reorganization_check()
    print(payload["result"]["verdict"])
