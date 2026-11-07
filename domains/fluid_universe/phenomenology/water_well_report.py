"""Finite spherical well for the hydrated electron (claim 33, ADR-024)."""

from __future__ import annotations

from domains.fluid_universe.theory.water_well import well_scales

from .provenance import RESULTS_DIR, metadata, write_json, write_text_atomic

OBSERVED_EV = 1.7


def run_water_well_check(write: bool = True) -> dict:
    scales = well_scales()
    capillary = scales["capillary"]
    threshold = scales["threshold"]
    inverse = scales["inverse"]
    minimum = inverse["minimum"]
    result = {
        "scales": scales,
        "observed_absorption_ev": OBSERVED_EV,
        "verdict": {
            "born_well_has_no_1p_at_capillary": capillary["u_1p"] is None,
            "born_well_never_reaches_1p7": threshold["max_born_gap_ev"]
            < OBSERVED_EV,
            "required_depth_above_born": minimum["excess_ev"] > 0.0,
            "claim_33_status": (
                "NUMERIC (negative: Born well cannot give 1.7 eV; "
                "required depth 3.715 eV)"
            ),
            "note": (
                "The minimal Born-depth finite well does not explain the "
                "1.7 eV hydrated-electron absorption: at the capillary radius "
                "it binds only 1s, and the maximum Born-depth s->p gap at any "
                "radius is 0.615 eV. A 1.7 eV gap requires at least 3.715 eV "
                "at R=3.181 Angstrom, 1.481 eV above Born. The missing depth "
                "is comparable to the optical-polarization reorganization "
                "energy (1.243 eV), so a polaron or band-offset correction is "
                "the next test, not a fitted parameter."
            ),
        },
    }
    config = {
        "epsilon_water": scales["model"]["epsilon_water"],
        "epsilon_optical": scales["model"]["epsilon_optical"],
        "observed_absorption_ev": OBSERVED_EV,
        "scope": "finite spherical well with the Born solvation depth",
    }
    payload = {"meta": metadata(config), "result": result}
    if write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        write_json(RESULTS_DIR / "water_well.json", payload)
        write_text_atomic(RESULTS_DIR / "water_well.md", render_markdown(payload))
    return payload


def render_markdown(payload: dict) -> str:
    result = payload["result"]
    scales = result["scales"]
    capillary = scales["capillary"]
    threshold = scales["threshold"]
    inverse = scales["inverse"]
    minimum = inverse["minimum"]
    infinite = scales["infinite_well"]
    verdict = result["verdict"]
    lines = [
        "# Finite spherical well for the hydrated electron (claim 33)",
        "",
        "Model: \\(V(r)=-V_0\\) for \\(r<R\\) and zero outside, with the "
        "Born depth \\(V_0(R)=e^2(1-1/\\epsilon_r)/(8\\pi\\epsilon_0R)\\). "
        "The l=0 and l=1 matching conditions give the 1s and 1p roots.",
        f"Observed hydrated-electron absorption: {OBSERVED_EV:.3g} eV.",
        "",
        "## Capillary cavity",
        "",
        "| quantity | value |",
        "|---|---:|",
        f"| radius | {capillary['radius_m']:.9e} m "
        f"({capillary['radius_m'] / 1e-10:.6f} Angstrom) |",
        f"| Born depth | {capillary['born_depth_ev']:.6f} eV |",
        f"| kappa | {capillary['kappa']:.6f} |",
        f"| 1s root | {capillary['u_1s']:.6f} |",
        f"| 1s energy | {capillary['energy_1s_ev']:.6f} eV |",
        f"| 1s binding | {capillary['binding_ev']:.6f} eV |",
        "| 1p root | none |",
        "| s->p gap | none |",
        "",
        "The 1s->continuum threshold is 0.528 eV; there is no bound-bound "
        "line in this well.",
        "",
        "## Depth scan at the capillary radius",
        "",
        "| \\(V_0\\) (eV) | \\(\\kappa\\) | \\(u_{1s}\\) | \\(u_{1p}\\) | gap (eV) |",
        "|---:|---:|---:|---:|---:|",
    ]
    for row in scales["depth_scan"]:
        u_1p = "none" if row["u_1p"] is None else f"{row['u_1p']:.6f}"
        transition = (
            "none"
            if row["transition_ev"] is None
            else f"{row['transition_ev']:.6f}"
        )
        lines.append(
            f"| {row['depth_ev']:.6f} | {row['kappa']:.6f} | "
            f"{row['u_1s']:.6f} | {u_1p} | {transition} |"
        )
    lines += [
        "",
        f"At the 1p threshold \\(V_0={threshold['depth_at_capillary_ev']:.6f}\\) eV, "
        f"the gap is {threshold['gap_at_capillary_ev']:.6f} eV. No depth gives "
        "1.7 eV at this radius.",
        "",
        "## Born-depth scan over radius",
        "",
        "| quantity | value |",
        "|---|---:|",
        f"| 1p threshold radius | {threshold['radius_m']:.9e} m "
        f"({threshold['radius_m'] / 1e-10:.6f} Angstrom) |",
        f"| maximum Born-depth s->p gap | {threshold['max_born_gap_ev']:.6f} eV |",
        f"| infinite-well s->p spacing at 4.703 Angstrom | "
        f"{infinite['transition_at_4p703_ev']:.6f} eV |",
        f"| infinite-well radius for 1.7 eV | "
        f"{infinite['radius_for_1p7_m']:.9e} m "
        f"({infinite['radius_for_1p7_m'] / 1e-10:.6f} Angstrom) |",
        "",
        "For \\(R<5.290\\) Angstrom the Born well has no 1p; for "
        "\\(R>5.290\\) Angstrom the Born-depth gap is below 0.615 eV. The "
        "earlier 4.703 Angstrom infinite-well estimate is the ground-state "
        "energy scale, not the s->p spacing.",
        "",
        "## Inverse: what a 1.7 eV gap would take",
        "",
        "| \\(R\\) (Angstrom) | Born (eV) | required (eV) | excess (eV) |",
        "|---:|---:|---:|---:|",
        f"| {minimum['radius_m'] / 1e-10:.6f} | {minimum['born_depth_ev']:.6f} | "
        f"{minimum['required_depth_ev']:.6f} | {minimum['excess_ev']:.6f} |",
        f"| {inverse['radius_3p2_m'] / 1e-10:.6f} | "
        f"{inverse['born_depth_3p2_ev']:.6f} | "
        f"{inverse['required_depth_3p2_ev']:.6f} | "
        f"{inverse['excess_3p2_ev']:.6f} |",
        "",
        f"Minimum required depth: {minimum['required_depth_ev']:.6f} eV at "
        f"\\(R={minimum['radius_m']:.9e}\\) m. The missing depth is "
        f"{minimum['excess_ev']:.6f} eV; the optical-polarization energy at "
        f"that radius is {inverse['optical_polarization_ev']:.6f} eV "
        f"(ratio {inverse['optical_polarization_ratio']:.6f}).",
        "",
        "## Verdict",
        "",
        f"- Born well has no 1p at the capillary radius: "
        f"**{verdict['born_well_has_no_1p_at_capillary']}**.",
        f"- The Born well never reaches 1.7 eV: "
        f"**{verdict['born_well_never_reaches_1p7']}**.",
        f"- The required depth is above Born: "
        f"**{verdict['required_depth_above_born']}**.",
        f"- Claim 33: **{verdict['claim_33_status']}**.",
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
    payload = run_water_well_check()
    print(payload["result"]["verdict"])
