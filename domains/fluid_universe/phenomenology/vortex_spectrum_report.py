"""Vortex-knot mass spectrum report (claim 17, ADR-008).

The charged leptons are assigned to T(2,3), T(2,5), T(2,7) and their masses are
compared with the regularized thin-filament energies.  The test is parameter-
free once the knot family, geometry and core radius are fixed; a negative
falsifies this simplest vortex assignment, not the general fluid-vortex idea.
"""

from __future__ import annotations

import csv
from pathlib import Path

from domains.fluid_universe.theory.vortex_particles import mass_hypothesis

from .provenance import RESULTS_DIR, metadata, write_json, write_text_atomic

ROOT = Path(__file__).resolve().parents[1]
LEPTON_DATA = ROOT / "phenomenology" / "data" / "pdg2024_leptons.csv"


def load_lepton_masses() -> dict[str, float]:
    with LEPTON_DATA.open(encoding="utf-8", newline="") as handle:
        rows = {row["name"]: float(row["value_MeV"]) for row in csv.DictReader(handle)}
    return {name: rows[name] for name in ("m_e", "m_mu", "m_tau")}


def run_vortex_spectrum(write: bool = True) -> dict:
    masses = load_lepton_masses()
    observed = (masses["m_e"], masses["m_mu"], masses["m_tau"])
    result = mass_hypothesis(observed)
    config = {
        "knots": [3, 5, 7],
        "radius": 2.0,
        "tube": 1.0,
        "samples": 400,
        "core": 0.1,
        "data": "phenomenology/data/pdg2024_leptons.csv",
        "scope": "thin-filament vortex-knot mass hypothesis; scaling proxy",
    }
    payload = {
        "meta": metadata(config),
        "observed": masses,
        "result": result,
    }
    if write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        write_json(RESULTS_DIR / "vortex_knot_spectrum.json", payload)
        write_text_atomic(
            RESULTS_DIR / "vortex_knot_spectrum.md", render_markdown(payload)
        )
    return payload


def render_markdown(payload: dict) -> str:
    result = payload["result"]
    observed = payload["observed"]
    lines = [
        "# Vortex-knot mass spectrum (claim 17)",
        "",
        "The three charged leptons are assigned to the torus knots "
        "T(2,3), T(2,5), T(2,7); the mass is proportional to the regularized "
        "thin-filament Biot-Savart energy at core radius 0.1.",
        "",
        "## Observed pole masses (MeV)",
        "",
        f"m_e = {observed['m_e']:.9g}, m_mu = {observed['m_mu']:.9g}, "
        f"m_tau = {observed['m_tau']:.9g}.",
        "",
        "## Knot spectrum",
        "",
        "| knot | length | energy | energy ratio | observed ratio |",
        "|---:|---:|---:|---:|---:|",
    ]
    for knot, length, energy, ratio, obs in zip(
        result["knots"],
        result["lengths"],
        result["energies"],
        result["energy_ratios"],
        result["observed_ratios"],
    ):
        lines.append(
            f"| T(2,{knot}) | {length:.6f} | {energy:.6f} | {ratio:.6f} | "
            f"{obs:.6f} |"
        )
    lines += [
        "",
        "## Test",
        "",
        f"- Koide Q of the knot energies: {result['koide_q_energy']:.6f} "
        f"(target 2/3 = 0.666667).",
        f"- Koide Q of the knot lengths: {result['koide_q_length']:.6f}.",
        f"- Koide Q of the observed masses: {result['koide_q_observed']:.6f}.",
        f"- Maximum relative ratio error: {result['relative_error']:.3f}.",
        f"- Power p required by m ~ E^p: {result['required_power']:.3f}.",
        f"- **Status: {result['status']}.**",
        "",
        result["note"],
        "",
        f"- Config SHA-256: `{payload['meta']['config_sha256']}`",
        f"- Git: `{payload['meta']['git']['commit']}` "
        f"(dirty={payload['meta']['git']['dirty']})",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    result = run_vortex_spectrum()
    print(result["result"]["status"])
