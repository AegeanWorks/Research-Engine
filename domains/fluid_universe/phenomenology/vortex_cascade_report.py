"""One-parameter vortex hierarchy report (claim 18, ADR-009)."""

from __future__ import annotations

import csv
from pathlib import Path

from domains.fluid_universe.theory.vortex_cascade import run_hypotheses

from .provenance import RESULTS_DIR, metadata, write_json, write_text_atomic

ROOT = Path(__file__).resolve().parents[1]
LEPTON_DATA = ROOT / "phenomenology" / "data" / "pdg2024_leptons.csv"


def load_lepton_masses() -> dict[str, float]:
    with LEPTON_DATA.open(encoding="utf-8", newline="") as handle:
        rows = {row["name"]: float(row["value_MeV"]) for row in csv.DictReader(handle)}
    return {name: rows[name] for name in ("m_e", "m_mu", "m_tau")}


def run_cascade_check(write: bool = True) -> dict:
    masses = load_lepton_masses()
    observed = (masses["m_e"], masses["m_mu"], masses["m_tau"])
    result = run_hypotheses(observed)
    config = {
        "models": ["geometric", "power_law_muon_fit", "power_law_koide_fit"],
        "data": "phenomenology/data/pdg2024_leptons.csv",
        "relative_tolerance": result["relative_tolerance"],
        "koide_tolerance": result["koide_tolerance"],
        "scope": "one-parameter vortex hierarchy test; no fit parameters added",
    }
    payload = {
        "meta": metadata(config),
        "observed": masses,
        "result": result,
    }
    if write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        write_json(RESULTS_DIR / "vortex_cascade.json", payload)
        write_text_atomic(
            RESULTS_DIR / "vortex_cascade.md", render_markdown(payload)
        )
    return payload


def render_markdown(payload: dict) -> str:
    result = payload["result"]
    observed = payload["observed"]
    lines = [
        "# One-parameter vortex hierarchy test (claim 18)",
        "",
        f"Observed pole masses: m_e={observed['m_e']:.9g}, "
        f"m_mu={observed['m_mu']:.9g}, m_tau={observed['m_tau']:.9g} MeV.",
        "",
        "| model | parameter | predicted tau ratio | observed | relative error | Q predicted | falsified |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for model in result["models"].values():
        lines.append(
            f"| {model['model']} | {model['parameter']:.6f} | "
            f"{model['predicted_tau_ratio']:.6f} | "
            f"{model['observed_tau_ratio']:.6f} | "
            f"{model['tau_relative_error']:+.6f} | "
            f"{model['koide_q_predicted']:.6f} | {model['falsified']} |"
        )
    lines += [
        "",
        f"**Status: {result['status']}.**",
        "",
        result["note"],
        "",
        f"- Observed Koide Q: "
        f"{next(iter(result['models'].values()))['koide_q_observed']:.6f} "
        f"(target {result['koide_target']:.6f}).",
        f"- Relative tolerance: {result['relative_tolerance']:.2f}; "
        f"Q tolerance: {result['koide_tolerance']:.2f}.",
        f"- Config SHA-256: `{payload['meta']['config_sha256']}`",
        f"- Git: `{payload['meta']['git']['commit']}` "
        f"(dirty={payload['meta']['git']['dirty']})",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    result = run_cascade_check()
    print(result["result"]["status"])
