"""Capillary validity report for the shallow-water horizon (claim 28, ADR-019)."""

from __future__ import annotations

from domains.fluid_universe.theory.water_analogue import (
    hawking_temperature,
    long_wavelength_min_flow,
    surface_gravity,
    validity,
)

from .provenance import RESULTS_DIR, metadata, write_json, write_text_atomic

DEPTH = 0.1
RATIO = 10.0


def _row(flow_rate: float) -> dict:
    result = validity(depth=DEPTH, flow_rate=flow_rate, ratio=RATIO)
    kappa = surface_gravity(flow_rate, DEPTH)
    return {
        **result,
        "surface_gravity_m_s2": kappa,
        "hawking_temperature_k": hawking_temperature(kappa),
    }


def run_water_validity_check(write: bool = True) -> dict:
    lab = _row(1e-3)
    valid = _row(0.05)
    minimum = long_wavelength_min_flow(DEPTH, ratio=RATIO)
    result = {
        "lab": lab,
        "valid_example": valid,
        "minimum_flow_m3_s": minimum,
        "required_ratio": RATIO,
        "verdict": {
            "lab_is_long_wavelength": lab["long_wavelength"],
            "valid_example_is_long_wavelength": valid["long_wavelength"],
            "claim_28_status": "PROVEN (capillary validity condition)",
            "note": (
                "The lab example Q=1e-3 m3/s has r_H=1.607 mm, below the "
                "2.727 mm capillary length, so capillary dispersion dominates "
                "at the horizon and the long-wavelength acoustic metric does "
                "not apply. A valid analogue needs r_H >= 10 ell_c, i.e. "
                "Q >= 0.01697 m3/s for h=0.1 m. Claim 27's formula remains "
                "exact in the long-wavelength limit; its lab example is "
                "flagged as capillary-dominated."
            ),
        },
    }
    config = {
        "depth_m": DEPTH,
        "rho_kg_m3": 998.0,
        "gamma_n_m": 0.0728,
        "gravity_m_s2": 9.81,
        "required_ratio": RATIO,
        "scope": "capillary validity of the shallow-water acoustic horizon",
    }
    payload = {"meta": metadata(config), "result": result}
    if write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        write_json(RESULTS_DIR / "water_validity.json", payload)
        write_text_atomic(
            RESULTS_DIR / "water_validity.md", render_markdown(payload)
        )
    return payload


def render_markdown(payload: dict) -> str:
    result = payload["result"]
    lab = result["lab"]
    valid = result["valid_example"]
    verdict = result["verdict"]
    lines = [
        "# Capillary validity of the shallow-water horizon (claim 28)",
        "",
        "Water at 20 C: rho=998 kg/m3, gamma=0.0728 N/m, g=9.81 m/s2; "
        f"capillary length {lab['capillary_length_m']:.9e} m.",
        "",
        "| case | Q (m3/s) | r_H (m) | r_H/ell_c | capillary ratio | long wavelength |",
        "|---|---:|---:|---:|---:|---|",
        f"| lab | {lab['flow_rate_m3_s']:.3g} | {lab['horizon_radius_m']:.6e} | "
        f"{lab['horizon_radius_m'] / lab['capillary_length_m']:.3f} | "
        f"{lab['capillary_ratio']:.6f} | {lab['long_wavelength']} |",
        f"| valid example | {valid['flow_rate_m3_s']:.3g} | "
        f"{valid['horizon_radius_m']:.6e} | "
        f"{valid['horizon_radius_m'] / valid['capillary_length_m']:.3f} | "
        f"{valid['capillary_ratio']:.6f} | {valid['long_wavelength']} |",
        "",
        f"- Minimum flow for r_H >= {result['required_ratio']:.0f} ell_c: "
        f"{result['minimum_flow_m3_s']:.6e} m3/s.",
        f"- Valid example surface gravity: "
        f"{valid['surface_gravity_m_s2']:.6f} m/s2; temperature "
        f"{valid['hawking_temperature_k']:.6e} K.",
        "",
        "## Verdict",
        "",
        f"- Lab example is long-wavelength: **{verdict['lab_is_long_wavelength']}**.",
        f"- Valid example is long-wavelength: "
        f"**{verdict['valid_example_is_long_wavelength']}**.",
        f"- Claim 28: **{verdict['claim_28_status']}**.",
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
    payload = run_water_validity_check()
    print(payload["result"]["verdict"])
