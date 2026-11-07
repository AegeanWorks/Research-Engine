"""Two-branch defect representation check (claim 46, ADR-038).

Representation-only, zero free parameters. Recomputes the frozen
correspondence numbers live from domains.fluid_universe.theory.node_defect (which itself
reuses theory.excited_fluid and theory.hydrogen_vortex without
duplicating their constants):

- branch identities: psi == s*|psi| residual 0, node density 0,
  phase slip pi;
- node scaling: gradient maxima pi/(2dx) at N=256/512/1024/2048,
  log-log slope -1 (kill gate abs 0.01);
- vortex gate: circulation 2pi, loop integral equal, velocity 0.5,
  momentum 1.0, most-probable radius 4.0, radial norm 1.0
  (kill gate rel 1e-6 on circulation);
- control: regular-Q branch form shared away from the node.

The Q-match at x=0.996 (4.8e-13 record) is correspondence-only;
it is reported, never gated (S6: 2nd-order central gives ~6e-06,
8th-order ~8.6e-13 — method-specific, not pinned here).
"""

from __future__ import annotations

import math

from domains.fluid_universe.theory.node_defect import representation_scales

from .provenance import RESULTS_DIR, metadata, write_json, write_text_atomic

SLOPE_TOL = 0.01
CIRCULATION_REL_TOL = 1e-6


def run_node_defect_check(write: bool = True) -> dict:
    scales = representation_scales()
    branch = scales["branch"]
    slope = scales["scaling"]["slope"]
    vortex = scales["vortex"]
    slope_kill = abs(slope + 1.0) > SLOPE_TOL
    circ = vortex["circulation"]
    circ_kill = abs(circ - 2.0 * math.pi) / (2.0 * math.pi) > CIRCULATION_REL_TOL
    loop_kill = (
        abs(vortex["loop_circulation"] - 2.0 * math.pi) / (2.0 * math.pi)
        > CIRCULATION_REL_TOL
    )
    identity_kill = branch["identity_residual"] != 0.0
    density_kill = branch["node_density"] != 0.0
    slip_kill = branch["phase_slip"] != math.pi
    killed = (
        slope_kill
        or circ_kill
        or loop_kill
        or identity_kill
        or density_kill
        or slip_kill
    )
    if killed:
        legs = []
        if identity_kill:
            legs.append(f"identity residual {branch['identity_residual']:.3e} != 0")
        if density_kill:
            legs.append(f"node density {branch['node_density']:.3e} != 0")
        if slip_kill:
            legs.append(f"phase slip {branch['phase_slip']:.6f} != pi")
        if slope_kill:
            legs.append(f"slope {slope:.6f} off -1 by > {SLOPE_TOL}")
        if circ_kill or loop_kill:
            legs.append("circulation/loop off 2pi by > 1e-6 rel")
        status = f"FALSIFIED (two-branch representation; {'; '.join(legs)})"
    else:
        status = "NUMERIC (two-branch representation identities verified)"
    result = {
        "scales": scales,
        "gates": {
            "slope_tol": SLOPE_TOL,
            "circulation_rel_tol": CIRCULATION_REL_TOL,
            "slope_kill": bool(slope_kill),
            "circulation_kill": bool(circ_kill),
            "loop_kill": bool(loop_kill),
        },
        "verdict": {
            "claim_46_status": status,
            "note": (
                "Exact two-branch split psi1=s*|psi1| with Wallstrom "
                "quantization on loops; Q-match at x=0.996 is "
                "correspondence-only, never gated."
            ),
        },
    }
    config = {
        "grids": scales["grids"],
        "loop": scales["loop"],
        "units": scales["units"],
        "slope_tol": SLOPE_TOL,
        "circulation_rel_tol": CIRCULATION_REL_TOL,
        "scope": "representation identities, zero parameters, no dynamics",
    }
    payload = {"meta": metadata(config), "result": result}
    if write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        write_json(RESULTS_DIR / "node_defect.json", payload)
        write_text_atomic(
            RESULTS_DIR / "node_defect.md", render_markdown(payload)
        )
    return payload


def render_markdown(payload: dict) -> str:
    result = payload["result"]
    scales = result["scales"]
    branch = scales["branch"]
    vortex = scales["vortex"]
    verdict = result["verdict"]
    lines = [
        "# Two-branch defect representation (claim 46)",
        "",
        "Exact split psi1 = s*|psi1|; Wallstrom quantization on loops; no dynamics.",
        "",
        "| quantity | value |",
        "|---|---:|",
        f"| identity residual | {branch['identity_residual']:.3e} |",
        f"| node density | {branch['node_density']:.3e} |",
        f"| phase slip | {branch['phase_slip']:.12f} |",
        f"| scaling slope | {scales['scaling']['slope']:.12f} |",
        f"| circulation | {vortex['circulation']:.12f} |",
        f"| loop circulation | {vortex['loop_circulation']:.12f} |",
        f"| most-probable radius | {vortex['most_probable_radius']:.6f} |",
        f"| radial norm | {vortex['radial_norm']:.12f} |",
        "",
        "## Verdict",
        "",
        f"- Claim 46: **{verdict['claim_46_status']}**.",
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
    payload = run_node_defect_check()
    print(payload["result"]["verdict"])
