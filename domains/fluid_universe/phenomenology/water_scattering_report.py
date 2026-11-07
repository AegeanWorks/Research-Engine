"""1D water-wave scattering report (claim 31, ADR-022)."""

from __future__ import annotations

import math

from domains.fluid_universe.sims.water_scattering import horizon_flow, simulate, uniform_flow

from .provenance import RESULTS_DIR, metadata, write_json, write_text_atomic

DEPTH = 0.1
LENGTH = 20.0
N = 1200
T_MAX = 15.0
DT = 2e-4
CENTER = -3.0
WIDTH = 0.5


def run_water_scattering_check(write: bool = True) -> dict:
    c = math.sqrt(9.81 * DEPTH)
    horizon = simulate(
        lambda x: horizon_flow(x, c, LENGTH / 2.0),
        n=N,
        length=LENGTH,
        depth=DEPTH,
        center=CENTER,
        width=WIDTH,
        t_max=T_MAX,
        dt=DT,
    )
    uniform = simulate(
        lambda x: uniform_flow(x, c, 0.5),
        n=N,
        length=LENGTH,
        depth=DEPTH,
        center=CENTER,
        width=WIDTH,
        t_max=T_MAX,
        dt=DT,
    )
    result = {
        "sound_speed_m_s": c,
        "horizon": horizon,
        "uniform_control": uniform,
        "verdict": {
            "horizon_blocks": horizon["transmitted_fraction"] < 1e-3,
            "uniform_transmits": uniform["transmitted_fraction"] > 0.9,
            "claim_31_status": "NUMERIC (horizon blocking)",
            "note": (
                "A right-moving shallow-water packet leaves essentially no "
                "energy in the supersonic region at the horizon, while the "
                "uniform-flow control transmits. The 1D background flow is "
                "prescribed (kinematic analogue), not a consistent shallow-"
                "water equilibrium; a full radial simulation remains future "
                "work."
            ),
        },
    }
    config = {
        "n": N,
        "length_m": LENGTH,
        "depth_m": DEPTH,
        "center_m": CENTER,
        "width_m": WIDTH,
        "t_max_s": T_MAX,
        "dt_s": DT,
        "case": "1D linearized shallow water with prescribed flow",
    }
    payload = {"meta": metadata(config), "result": result}
    if write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        write_json(RESULTS_DIR / "water_scattering.json", payload)
        write_text_atomic(
            RESULTS_DIR / "water_scattering.md", render_markdown(payload)
        )
    return payload


def render_markdown(payload: dict) -> str:
    result = payload["result"]
    horizon = result["horizon"]
    uniform = result["uniform_control"]
    verdict = result["verdict"]
    lines = [
        "# 1D water-wave scattering at the horizon (claim 31)",
        "",
        f"Depth {DEPTH:.3g} m, length {LENGTH:.3g} m, N={N}, t_max={T_MAX:.3g} s, "
        f"dt={DT:.1e} s; c={result['sound_speed_m_s']:.9f} m/s.",
        "",
        "| case | transmitted fraction | final center (m) | total energy |",
        "|---|---:|---:|---:|",
        f"| horizon | {horizon['transmitted_fraction']:.3e} | "
        f"{horizon['final_center']:.6f} | {horizon['energy_total']:.6f} |",
        f"| uniform control | {uniform['transmitted_fraction']:.6f} | "
        f"{uniform['final_center']:.6f} | {uniform['energy_total']:.6f} |",
        "",
        "## Verdict",
        "",
        f"- Horizon blocks: **{verdict['horizon_blocks']}**.",
        f"- Uniform flow transmits: **{verdict['uniform_transmits']}**.",
        f"- Claim 31: **{verdict['claim_31_status']}**.",
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
    payload = run_water_scattering_check()
    print(payload["result"]["verdict"])
