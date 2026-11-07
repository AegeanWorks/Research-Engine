"""Self-consistent finite-well pressure balance (claim 37, ADR-028)."""

from __future__ import annotations

from domains.fluid_universe.theory.water_pressure import pressure_scales

from .provenance import RESULTS_DIR, metadata, write_json, write_text_atomic

OBSERVED_EV = 1.7


def run_water_pressure_check(write: bool = True) -> dict:
    scales = pressure_scales()
    vde = scales["vde_matched"]
    crude = scales["crude_capillary"]
    result = {
        "scales": scales,
        "verdict": {
            "pressure_radius_larger": scales["scans"][0]["radius_m"]
            > crude["radius_m"] * 1.2,
            "vde_matched": abs(vde["binding_ev"] - 3.27) < 0.01,
            "gap_below_observed": vde["gap_ev"] < OBSERVED_EV - 0.2,
            "crude_not_minimum": scales["scans"][0]["total_energy_ev"]
            < crude["total_energy_ev"],
            "claim_37_status": (
                "NUMERIC (pressure-balance radius 3.973 Angstrom; "
                "VDE-matched gap 1.344 eV)"
            ),
            "note": (
                "The fluid pressure balance makes the cavity larger and the "
                "1s->1p gap smaller. At the Born depth the minimum is "
                "R=3.973 Angstrom, binding 1.177 eV, gap 1.133 eV. At the "
                "VDE-matched depth V0=4.611 eV the minimum is R=4.336 "
                "Angstrom, binding 3.27 eV, gap 1.344 eV, not 1.7 eV. The "
                "crude fixed-radius cavity is not the pressure minimum. "
                "Adding the R-dependent Born energy separately double-counts "
                "the solvation and collapses the cavity; a self-consistent "
                "dielectric interface is the next test."
            ),
        },
    }
    config = {
        "gamma_water_n_m": scales["gamma_water_n_m"],
        "observed_absorption_ev": OBSERVED_EV,
        "scope": "finite-well pressure balance with surface tension",
    }
    payload = {"meta": metadata(config), "result": result}
    if write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        write_json(RESULTS_DIR / "water_pressure.json", payload)
        write_text_atomic(
            RESULTS_DIR / "water_pressure.md", render_markdown(payload)
        )
    return payload


def render_markdown(payload: dict) -> str:
    result = payload["result"]
    scales = result["scales"]
    vde = scales["vde_matched"]
    crude = scales["crude_capillary"]
    verdict = result["verdict"]
    lines = [
        "# Self-consistent finite-well pressure balance (claim 37)",
        "",
        "Model: at fixed well depth \\(V_0\\), minimize "
        "\\(E_{1s}(R,V_0)+4\\pi\\gamma R^2\\). This is the Laplace pressure "
        "balance between the electron pressure and surface tension, using "
        "the finite-well 1s eigenvalue rather than the crude "
        "\\(\\hbar^2/(2mR^2)\\).",
        "",
        "## Pressure-balanced scan",
        "",
        "| \\(V_0\\) (eV) | \\(R\\) (Angstrom) | binding (eV) | \\(E_{1p}\\) (eV) | gap (eV) | surface (eV) | total (eV) |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in scales["scans"]:
        lines.append(
            f"| {row['depth_ev']:.6f} | {row['radius_m'] / 1e-10:.6f} | "
            f"{row['binding_ev']:.6f} | {row['energy_1p_ev']:.6f} | "
            f"{row['gap_ev']:.6f} | {row['surface_energy_ev']:.6f} | "
            f"{row['total_energy_ev']:.6f} |"
        )
    lines += [
        "",
        "## VDE-matched point",
        "",
        "| quantity | value |",
        "|---|---:|",
        f"| depth | {vde['depth_ev']:.6f} eV |",
        f"| radius | {vde['radius_m']:.9e} m "
        f"({vde['radius_m'] / 1e-10:.6f} Angstrom) |",
        f"| binding | {vde['binding_ev']:.6f} eV |",
        f"| \\(E_{{1p}}\\) | {vde['energy_1p_ev']:.6f} eV |",
        f"| gap | {vde['gap_ev']:.6f} eV |",
        f"| surface energy | {vde['surface_energy_ev']:.6f} eV |",
        f"| total energy | {vde['total_energy_ev']:.6f} eV |",
        "",
        "## Crude fixed-radius comparison",
        "",
        "| quantity | value |",
        "|---|---:|",
        f"| crude capillary radius | {crude['radius_m']:.9e} m "
        f"({crude['radius_m'] / 1e-10:.6f} Angstrom) |",
        f"| crude total energy | {crude['total_energy_ev']:.6f} eV |",
        f"| pressure-balanced total at Born depth | "
        f"{scales['scans'][0]['total_energy_ev']:.6f} eV |",
        f"| pressure radius / crude radius | "
        f"{scales['scans'][0]['radius_m'] / crude['radius_m']:.6f} |",
        "",
        "The crude fixed-radius cavity is not the pressure minimum. The "
        "pressure balance moves the radius to 3.973 Angstrom at the Born "
        "depth and to 4.336 Angstrom at the VDE-matched depth. The gap at "
        "the VDE-matched point is 1.344 eV, not 1.7 eV.",
        "",
        "## Verdict",
        "",
        f"- Pressure radius is larger than the crude radius: "
        f"**{verdict['pressure_radius_larger']}**.",
        f"- The VDE-matched cavity is found: "
        f"**{verdict['vde_matched']}**.",
        f"- Its gap is below 1.7 eV: **{verdict['gap_below_observed']}**.",
        f"- The crude radius is not the pressure minimum: "
        f"**{verdict['crude_not_minimum']}**.",
        f"- Claim 37: **{verdict['claim_37_status']}**.",
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
    payload = run_water_pressure_check()
    print(payload["result"]["verdict"])
