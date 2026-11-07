"""VDE and 1.7 eV absorption constrain the finite well (claim 35, ADR-026)."""

from __future__ import annotations

from domains.fluid_universe.theory.water_vde import vde_scales

from .provenance import RESULTS_DIR, metadata, write_json, write_text_atomic

OBSERVED_EV = 1.7


def run_water_vde_check(write: bool = True) -> dict:
    scales = vde_scales()
    central = scales["central"]
    lower = scales["lower"]
    upper = scales["upper"]
    capillary = scales["capillary"]
    result = {
        "scales": scales,
        "verdict": {
            "absorption_is_bound": scales["observed_absorption_ev"]
            < scales["vde_ev"] - scales["vde_uncertainty_ev"],
            "finite_well_satisfies_both": abs(central["gap_ev"] - OBSERVED_EV)
            < 0.01
            and abs(central["binding_ev"] - scales["vde_ev"]) < 0.01,
            "capillary_outside_vde_band": capillary["radius_m"]
            < lower["radius_m"]
            and capillary["born_depth_ev"] < lower["depth_ev"],
            "claim_35_status": (
                "NUMERIC (two-observable inversion; R=3.732 Angstrom, "
                "V0=4.998 eV)"
            ),
            "note": (
                "The measured VDE 3.27 +/- 0.10 eV and the 1.7 eV absorption "
                "force a bound-bound 1s->1p assignment. The finite well "
                "satisfies both only at R=3.732 Angstrom and V0=4.998 eV, "
                "where the 1p is bound by 1.57 eV. The capillary/Born cavity "
                "(R=2.858 Angstrom, V0=2.487 eV) is 30.6% smaller and 2.01x "
                "shallower, outside the VDE band. The required excess depth "
                "3.093 eV is 2.92x the optical reorganization energy at that "
                "radius, so a simple polaron correction is insufficient; a "
                "soft-wall or different potential is the next test."
            ),
        },
    }
    config = {
        "vde_ev": scales["vde_ev"],
        "vde_uncertainty_ev": scales["vde_uncertainty_ev"],
        "observed_absorption_ev": OBSERVED_EV,
        "scope": "VDE and 1.7 eV absorption in the finite spherical well",
    }
    payload = {"meta": metadata(config), "result": result}
    if write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        write_json(RESULTS_DIR / "water_vde.json", payload)
        write_text_atomic(RESULTS_DIR / "water_vde.md", render_markdown(payload))
    return payload


def render_markdown(payload: dict) -> str:
    result = payload["result"]
    scales = result["scales"]
    central = scales["central"]
    lower = scales["lower"]
    upper = scales["upper"]
    capillary = scales["capillary"]
    verdict = result["verdict"]
    lines = [
        "# VDE and 1.7 eV absorption constrain the finite well (claim 35)",
        "",
        "Measured vertical detachment energy: "
        f"\\({scales['vde_ev']:.2f}\\pm{scales['vde_uncertainty_ev']:.2f}\\) eV "
        "(Tang et al., PCCP 12, 3653, 2010). Observed absorption: "
        f"{OBSERVED_EV:.3g} eV. Because \\(1.7<3.27\\), the absorption is "
        "below the detachment threshold and must be bound-bound. The model "
        "identifies the VDE with the 1s binding \\(-E_{1s}\\) of the cavity.",
        "",
        "## Two-observable solution",
        "",
        "| quantity | value |",
        "|---|---:|",
        f"| radius | {central['radius_m']:.9e} m "
        f"({central['radius_m'] / 1e-10:.6f} Angstrom) |",
        f"| well depth | {central['depth_ev']:.6f} eV |",
        f"| \\(u_{{1s}}\\) | {central['u_1s']:.6f} |",
        f"| \\(u_{{1p}}\\) | {central['u_1p']:.6f} |",
        f"| \\(E_{{1s}}\\) | {central['energy_1s_ev']:.6f} eV |",
        f"| \\(E_{{1p}}\\) | {central['energy_1p_ev']:.6f} eV |",
        f"| 1s->1p gap | {central['gap_ev']:.6f} eV |",
        f"| Born depth at this radius | {central['born_depth_ev']:.6f} eV |",
        f"| excess depth | {central['excess_ev']:.6f} eV |",
        "",
        "## VDE uncertainty band",
        "",
        "| binding (eV) | radius (Angstrom) | depth (eV) | \\(E_{1p}\\) (eV) | gap (eV) |",
        "|---:|---:|---:|---:|---:|",
    ]
    for label, row in (("lower", lower), ("central", central), ("upper", upper)):
        lines.append(
            f"| {row['binding_ev']:.2f} | {row['radius_m'] / 1e-10:.6f} | "
            f"{row['depth_ev']:.6f} | {row['energy_1p_ev']:.6f} | "
            f"{row['gap_ev']:.6f} |"
        )
    lines += [
        "",
        "## Capillary/Born comparison",
        "",
        "| quantity | value |",
        "|---|---:|",
        f"| capillary radius | {capillary['radius_m']:.9e} m "
        f"({capillary['radius_m'] / 1e-10:.6f} Angstrom) |",
        f"| Born depth | {capillary['born_depth_ev']:.6f} eV |",
        f"| capillary 1s binding | {capillary['binding_ev']:.6f} eV |",
        "| capillary 1p | none |",
        f"| required/capillary radius | {capillary['radius_ratio']:.6f} |",
        f"| required/Born depth | {capillary['depth_ratio']:.6f} |",
        f"| required depth minus capillary Born | "
        f"{capillary['depth_excess_ev']:.6f} eV |",
        f"| optical reorganization at required radius | "
        f"{scales['reorganization_ev']:.6f} eV |",
        f"| excess/reorganization | {scales['excess_to_reorganization']:.6f} |",
        "",
        "The capillary/Born cavity is outside the VDE band: it is 30.6% "
        "smaller and 2.01x shallower than the two-observable solution. The "
        "required excess is 2.92x the optical reorganization energy, so the "
        "missing depth is not a simple polaron shift.",
        "",
        "## Verdict",
        "",
        f"- The 1.7 eV absorption is bound-bound: "
        f"**{verdict['absorption_is_bound']}**.",
        f"- The finite well satisfies both observables: "
        f"**{verdict['finite_well_satisfies_both']}**.",
        f"- The capillary cavity is outside the VDE band: "
        f"**{verdict['capillary_outside_vde_band']}**.",
        f"- Claim 35: **{verdict['claim_35_status']}**.",
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
    payload = run_water_vde_check()
    print(payload["result"]["verdict"])
