"""Soft-wall cavity and the hard VDE depth bound (claim 36, ADR-027)."""

from __future__ import annotations

from domains.fluid_universe.theory.water_softwall import softwall_scales

from .provenance import RESULTS_DIR, metadata, write_json, write_text_atomic

OBSERVED_EV = 1.7


def run_water_softwall_check(write: bool = True) -> dict:
    scales = softwall_scales()
    hard = scales["hard_bound"]
    closest = scales["closest"]
    capillary = scales["capillary"]
    stiff = next(
        row for row in scales["scans"] if row["diffuseness_angstrom"] == 1.0
    )
    soft = next(
        row for row in scales["scans"] if row["diffuseness_angstrom"] == 1.5
    )
    result = {
        "scales": scales,
        "verdict": {
            "born_depth_below_vde": hard["difference_ev"] > 0.0,
            "softness_trades_radius_for_depth": soft["radius_m"]
            < stiff["radius_m"]
            and soft["depth_ev"] > stiff["depth_ev"],
            "no_scan_point_at_capillary": all(
                row["depth_ev"] > hard["born_depth_ev"] + 1.0
                for row in scales["scans"]
            ),
            "claim_36_status": (
                "NUMERIC (hard depth bound 3.27 eV; Woods-Saxon scan)"
            ),
            "note": (
                "The VDE 3.27 eV is a hard lower bound on the well depth: a "
                "bound state cannot be deeper than its well. The Born depth "
                "2.486988 eV is 0.783012 eV too shallow, independent of the "
                "cavity shape. A Woods-Saxon scan trades radius for depth: "
                "at a=1.5 Angstrom the two-observable solution is R=3.078 "
                "Angstrom but V0=6.643 eV (2.67x the Born depth). Softness "
                "does not rescue the minimal cavity. Either the "
                "VDE-to-1s-binding identification, the cavity model, or the "
                "1.7 eV assignment must change."
            ),
        },
    }
    config = {
        "vde_ev": scales["vde_ev"],
        "vde_uncertainty_ev": scales["vde_uncertainty_ev"],
        "observed_absorption_ev": OBSERVED_EV,
        "scope": "Woods-Saxon cavity with the VDE and 1.7 eV absorption",
    }
    payload = {"meta": metadata(config), "result": result}
    if write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        write_json(RESULTS_DIR / "water_softwall.json", payload)
        write_text_atomic(
            RESULTS_DIR / "water_softwall.md", render_markdown(payload)
        )
    return payload


def render_markdown(payload: dict) -> str:
    result = payload["result"]
    scales = result["scales"]
    hard = scales["hard_bound"]
    closest = scales["closest"]
    capillary = scales["capillary"]
    verdict = result["verdict"]
    lines = [
        "# Soft-wall cavity and the hard VDE depth bound (claim 36)",
        "",
        "The VDE is identified with the 1s binding. A bound state cannot be "
        "deeper than its well, so \\(E_b\\le V_0\\). The Born depth is "
        f"{hard['born_depth_ev']:.6f} eV and the VDE is {hard['vde_ev']:.2f} "
        f"eV: the Born well is {hard['difference_ev']:.6f} eV too shallow "
        f"(ratio {hard['ratio']:.6f}) before any shape is chosen.",
        "",
        "## Woods-Saxon scan",
        "",
        "Model: \\(V(r)=-V_0(1+e^{-R/a})/(1+e^{(r-R)/a})\\), central depth "
        "\\(V_0\\), half-depth radius \\(R\\), diffuseness \\(a\\). At each "
        "\\(a\\), solve \\(V_0(R)\\) for \\(E_b=3.27\\) eV, then invert for "
        "the radius where the 1s->1p gap is 1.7 eV.",
        "",
        "| \\(a\\) (Angstrom) | \\(R\\) (Angstrom) | \\(V_0\\) (eV) | "
        "\\(E_{1s}\\) (eV) | \\(E_{1p}\\) (eV) | gap (eV) | "
        "Born at \\(R\\) (eV) | excess (eV) |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in scales["scans"]:
        lines.append(
            f"| {row['diffuseness_angstrom']:.3f} | "
            f"{row['radius_m'] / 1e-10:.6f} | {row['depth_ev']:.6f} | "
            f"{row['energy_1s_ev']:.6f} | {row['energy_1p_ev']:.6f} | "
            f"{row['gap_ev']:.6f} | {row['born_depth_ev']:.6f} | "
            f"{row['excess_ev']:.6f} |"
        )
    lines += [
        "",
        "The square limit \\(a=0.001\\) Angstrom gives "
        f"\\(R={scales['scans'][0]['radius_m'] / 1e-10:.6f}\\) Angstrom and "
        f"\\(V_0={scales['scans'][0]['depth_ev']:.6f}\\) eV, close to the "
        "claim-35 square-well solution. Between \\(a=1.0\\) and \\(1.5\\) "
        "Angstrom, the softer well has a smaller radius but a larger depth; "
        "the scan does not lower the required well depth.",
        "",
        "## Capillary comparison",
        "",
        "| quantity | value |",
        "|---|---:|",
        f"| capillary radius | {capillary['radius_m']:.9e} m "
        f"({capillary['radius_m'] / 1e-10:.6f} Angstrom) |",
        f"| Born depth | {capillary['born_depth_ev']:.6f} eV |",
        f"| maximum possible binding at Born depth | "
        f"{capillary['maximum_binding_ev']:.6f} eV |",
        f"| VDE | {hard['vde_ev']:.2f} eV |",
        f"| closest soft scan (a={closest['diffuseness_angstrom']:.1f} Angstrom) | "
        f"R={closest['radius_m'] / 1e-10:.6f} Angstrom, "
        f"V0={closest['depth_ev']:.6f} eV |",
        f"| closest radius / capillary | "
        f"{closest['radius_m'] / capillary['radius_m']:.6f} |",
        f"| closest depth / Born | "
        f"{closest['depth_ev'] / capillary['born_depth_ev']:.6f} |",
        "",
        "The closest soft scan still requires a depth 2.67x the Born depth. "
        "The hard bound alone rules out the capillary/Born cavity; the scan "
        "shows that a diffuse interface makes the depth problem worse.",
        "",
        "## Verdict",
        "",
        f"- Born depth is below the VDE: "
        f"**{verdict['born_depth_below_vde']}**.",
        f"- Softness trades radius for depth: "
        f"**{verdict['softness_trades_radius_for_depth']}**.",
        f"- No scan point is near the capillary depth: "
        f"**{verdict['no_scan_point_at_capillary']}**.",
        f"- Claim 36: **{verdict['claim_36_status']}**.",
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
    payload = run_water_softwall_check()
    print(payload["result"]["verdict"])
