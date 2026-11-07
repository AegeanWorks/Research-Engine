"""Yasui dynamical discriminator check (claim 52, ADR-044).

Zero free parameters, no full-field claims. The identical Verlet
machinery runs the Yasui trial (collapse expected) and the G-M twin
(period pi expected): shared integrator, opposite outcomes - the
controlled experiment. Floor-hit times are recorded (floors 0.05 and
0.02); the comparison uses the mild sigma = 0.5 crossing where both
methods are accurate. Spelling: Yasue is the literature name; spans
49-51 wrote "Yasui" for the same referent.
"""

from __future__ import annotations

import math

import numpy as np

from domains.fluid_universe.theory.yasue_dynamics import yasue_acceleration, yasue_scales

from .provenance import RESULTS_DIR, metadata, write_json, write_text_atomic

PERIOD_TOL = 1e-3
QUAD_RTOL = 1e-3
T_END = 2.0 * math.pi
GRID_S2 = tuple(float(v) for v in np.linspace(0.125, 2.0, 2001))


def run_yasue_dynamics_check(write: bool = True) -> dict:
    scales = yasue_scales()
    twin_kills = []
    for entry in scales["twins"]:
        period = entry["period"]
        twin_kills.append(
            (
                entry["factor"],
                not math.isfinite(period)
                or abs(period - math.pi) > PERIOD_TOL,
            )
        )
    twin_broken = any(k for _, k in twin_kills)
    collapse_kills = []
    for entry, quad in zip(scales["releases"], scales["mild_quadrature"]):
        monotone = entry["monotone"]
        hit = entry["floor_hit_time"]
        upward = entry["upward_crossings"]
        mild = entry["mild_crossing_time"]
        collapse_kills.append(
            (
                entry["factor"],
                (not monotone)
                or hit is None
                or hit >= math.pi
                or upward != 0
                or mild is None
                or (quad > 0.0 and abs(mild - quad) / quad > QUAD_RTOL),
            )
        )
    sign_grid = np.sqrt(np.array(GRID_S2))
    signs = [
        yasue_acceleration(float(s), 1.0, 1.0, 1.0) for s in sign_grid
    ]
    sign_kill = not all(v < 0.0 for v in signs)
    scaling = scales["scaling"]
    scale_kill = (
        scaling["release"]["floor_hit_time"] is None
        or scaling["release"]["floor_hit_time"] >= math.pi / 4.0
        or not math.isfinite(scaling["twin"]["period"])
        or abs(scaling["twin"]["period"] - math.pi / 2.0) > PERIOD_TOL
    )
    if twin_broken:
        status = "UNVERIFIED (twin control failed; apparatus suspect)"
    elif any(k for _, k in collapse_kills) or sign_kill or scale_kill:
        details = []
        if sign_kill:
            details.append("yasui accel non-negative somewhere")
        details += [f"collapse@{f}" for f, k in collapse_kills if k]
        if scale_kill:
            details.append("scaling")
        status = f"FALSIFIED (Yasui discriminator; {'; '.join(details)})"
    else:
        status = "NUMERIC (Yasui dynamical discriminator demonstrated)"
    result = {
        "scales": scales,
        "gates": {
            "period_tol": PERIOD_TOL,
            "quad_rtol": QUAD_RTOL,
            "twin_kills": [[f, bool(k)] for f, k in twin_kills],
            "collapse_kills": [[f, bool(k)] for f, k in collapse_kills],
            "sign_ok": bool(not sign_kill),
            "scale_kill": bool(scale_kill),
            "kills": (
                [["twin", bool(twin_broken)]]
                + [[f"collapse@{f}", bool(k)] for f, k in collapse_kills]
                + [["sign", bool(sign_kill)], ["scaling", bool(scale_kill)]]
            ),
        },
        "verdict": {
            "claim_52_status": status,
            "note": (
                "Yasui trial collapses monotonically to the floor with no "
                "return while the identical G-M machinery oscillates at pi: "
                "the action sign is dynamically discriminating within the "
                "trial class. No full-field claim is made."
            ),
        },
    }
    config = {
        "grids": {"s2": list(GRID_S2)},
        "base": scales["base"],
        "gates": {"period_tol": PERIOD_TOL, "quad_rtol": QUAD_RTOL},
        "scope": "trial-class discriminator, zero parameters, no full-field claim",
    }
    payload = {"meta": metadata(config), "result": result}
    if write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        write_json(RESULTS_DIR / "yasue_dynamics.json", payload)
        write_text_atomic(
            RESULTS_DIR / "yasue_dynamics.md", render_markdown(payload)
        )
    return payload


def render_markdown(payload: dict) -> str:
    result = payload["result"]
    scales = result["scales"]
    verdict = result["verdict"]
    lines = [
        "# Yasui dynamical discriminator (claim 52)",
        "",
        "Yasui runs away; G-M oscillates. Same integrator, opposite outcomes.",
        "",
        "| start | Yasui floor-hit | upward | mild (Verlet) | mild (quad) |",
        "|---|---|---|---|---|",
    ]
    for entry, quad in zip(scales["releases"], scales["mild_quadrature"]):
        lines.append(
            f"| {entry['factor']} | {entry['floor_hit_time']:.6f} | {entry['upward_crossings']} | "
            f"{entry['mild_crossing_time']:.6f} | {quad:.6f} |"
        )
    lines += [
        "",
        "| twin start | G-M period |",
        "|---|---|",
    ]
    for entry in scales["twins"]:
        lines.append(f"| {entry['factor']} | {entry['period']:.12f} |")
    lines += [
        f"| scaling omega=2 floor-hit | {scales['scaling']['release']['floor_hit_time']:.6f} |",
        f"| scaling G-M period | {scales['scaling']['twin']['period']:.12f} |",
        "",
        "## Verdict",
        "",
        f"- Claim 52: **{verdict['claim_52_status']}**.",
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
    payload = run_yasue_dynamics_check()
    print(payload["result"]["verdict"])
