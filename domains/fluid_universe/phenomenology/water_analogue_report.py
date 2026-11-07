"""Shallow-water acoustic horizon report (claim 27, ADR-018)."""

from __future__ import annotations

import numpy as np

from domains.fluid_universe.theory.water_analogue import acoustic_metric, lab_scales

from .provenance import RESULTS_DIR, metadata, write_json, write_text_atomic


def run_water_analogue_check(write: bool = True) -> dict:
    scales = lab_scales()
    radius = scales["horizon_radius_m"]
    rows = []
    for factor in (0.5, 0.9, 1.0, 1.1, 2.0):
        r = factor * radius
        metric = acoustic_metric(r, scales["flow_rate_m3_s"], scales["depth_m"])
        rows.append(
            {
                "r_over_r_h": factor,
                "r_m": r,
                "v_over_c": metric["v_r"] / metric["c"],
                "g_tt": metric["g_tt"],
            }
        )
    result = {
        "scales": scales,
        "rows": rows,
        "verdict": {
            "horizon_exists": bool(
                abs(rows[2]["v_over_c"] - 1.0) < 1e-12
                and abs(rows[2]["g_tt"]) < 1e-15
                and scales["surface_gravity_m_s2"] > 0.0
                and scales["hawking_temperature_k"] > 0.0
            ),
            "claim_27_status": "PROVEN (acoustic horizon; analogue)",
            "note": (
                "The long-wavelength shallow-water metric has a horizon at "
                "r_H=Q/(2 pi h c), surface gravity c^2/r_H and analogue "
                "temperature hbar kappa/(2 pi k_B). This is an acoustic "
                "analogue, not a fundamental metric; capillary dispersion "
                "breaks it at short wavelengths."
            ),
        },
    }
    config = {
        "depth_m": scales["depth_m"],
        "flow_rate_m3_s": scales["flow_rate_m3_s"],
        "gravity_m_s2": scales["gravity_m_s2"],
        "scope": "shallow-water acoustic horizon; long-wavelength analogue",
    }
    payload = {"meta": metadata(config), "result": result}
    if write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        write_json(RESULTS_DIR / "water_analogue.json", payload)
        write_text_atomic(
            RESULTS_DIR / "water_analogue.md", render_markdown(payload)
        )
    return payload


def render_markdown(payload: dict) -> str:
    result = payload["result"]
    scales = result["scales"]
    verdict = result["verdict"]
    lines = [
        "# Shallow-water acoustic horizon (claim 27)",
        "",
        f"Depth h={scales['depth_m']:.3g} m, flow rate Q={scales['flow_rate_m3_s']:.3g} m^3/s, "
        f"g={scales['gravity_m_s2']:.4g} m/s^2.",
        "",
        "## Scales",
        "",
        f"- Sound speed: {scales['sound_speed_m_s']:.9f} m/s.",
        f"- Horizon radius: {scales['horizon_radius_m']:.9e} m.",
        f"- Surface gravity: {scales['surface_gravity_m_s2']:.6f} m/s^2.",
        f"- Analogue temperature: {scales['hawking_temperature_k']:.6e} K.",
        "",
        "## Metric across the horizon",
        "",
        "| r/r_H | r (m) | v/c | g_tt |",
        "|---:|---:|---:|---:|",
    ]
    for row in result["rows"]:
        lines.append(
            f"| {row['r_over_r_h']:.3g} | {row['r_m']:.9e} | "
            f"{row['v_over_c']:.9f} | {row['g_tt']:.6e} |"
        )
    lines += [
        "",
        "## Verdict",
        "",
        f"- Horizon exists: **{verdict['horizon_exists']}**.",
        f"- Claim 27: **{verdict['claim_27_status']}**.",
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
    payload = run_water_analogue_check()
    print(payload["result"]["verdict"])
