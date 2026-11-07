"""Hydrated-electron cavity scale report (claim 32, ADR-023)."""

from __future__ import annotations

from domains.fluid_universe.theory.water_electron import hydrated_scales

from .provenance import RESULTS_DIR, metadata, write_json, write_text_atomic

OBSERVED_EV = 1.7


def run_water_electron_check(write: bool = True) -> dict:
    scales = hydrated_scales()
    ratio = scales["cavity_energy_ev"] / OBSERVED_EV
    result = {
        "scales": scales,
        "observed_absorption_ev": OBSERVED_EV,
        "cavity_to_observed_ratio": ratio,
        "verdict": {
            "screened_hydrogen_ruled_out": bool(
                scales["screened_bohr_radius_m"] > 1e-9
                and abs(scales["screened_energy_ev"]) < 0.01
            ),
            "cavity_scale_match": bool(
                2.0e-10 < scales["cavity_radius_m"] < 4.0e-10
                and 0.5 < scales["cavity_energy_ev"] < 2.0
            ),
            "claim_32_status": "NUMERIC (cavity scale match; factor 1.8 in energy)",
            "note": (
                "The screened hydrogen state is far too large and weakly "
                "bound. Balancing the electron quantum pressure against water "
                "surface tension gives a 2.858 Angstrom cavity and 0.933 eV, "
                "close to the hydrated-electron scale (absorption about "
                "1.7 eV). The energy is a factor 1.8 low; a finite-well or "
                "polaron model is needed for the exact value."
            ),
        },
    }
    config = {
        "epsilon_water": scales["epsilon_water"],
        "gamma_water_n_m": scales["gamma_water_n_m"],
        "observed_absorption_ev": OBSERVED_EV,
        "scope": "hydrated-electron cavity scale from water properties",
    }
    payload = {"meta": metadata(config), "result": result}
    if write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        write_json(RESULTS_DIR / "water_electron.json", payload)
        write_text_atomic(
            RESULTS_DIR / "water_electron.md", render_markdown(payload)
        )
    return payload


def render_markdown(payload: dict) -> str:
    result = payload["result"]
    scales = result["scales"]
    verdict = result["verdict"]
    lines = [
        "# Hydrated-electron cavity scale (claim 32)",
        "",
        f"Water at 20 C: epsilon_r={scales['epsilon_water']:.3g}, "
        f"gamma={scales['gamma_water_n_m']:.4g} N/m.",
        "",
        "## Scales",
        "",
        "| quantity | value |",
        "|---|---:|",
        f"| screened Bohr radius | {scales['screened_bohr_radius_m']:.6e} m |",
        f"| screened ground energy | {scales['screened_energy_ev']:.6e} eV |",
        f"| capillary cavity radius | {scales['cavity_radius_m']:.6e} m |",
        f"| capillary cavity energy | {scales['cavity_energy_ev']:.6f} eV |",
        f"| infinite-well ground-state energy at cavity radius | "
        f"{scales['well_gap_at_cavity_ev']:.6f} eV |",
        f"| infinite-well ground-state energy at 2.5 Angstrom | "
        f"{scales['well_gap_at_2p5_angstrom_ev']:.6f} eV |",
        f"| infinite-well ground-state radius for 1.7 eV | "
        f"{scales['well_radius_for_1p7_ev_m']:.6e} m |",
        "",
        f"- Observed hydrated-electron absorption: "
        f"{result['observed_absorption_ev']:.3g} eV.",
        f"- Cavity energy / observed: {result['cavity_to_observed_ratio']:.6f}.",
        "",
        "## Verdict",
        "",
        f"- Screened hydrogen ruled out: "
        f"**{verdict['screened_hydrogen_ruled_out']}**.",
        f"- Cavity scale match: **{verdict['cavity_scale_match']}**.",
        f"- Claim 32: **{verdict['claim_32_status']}**.",
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
    payload = run_water_electron_check()
    print(payload["result"]["verdict"])
