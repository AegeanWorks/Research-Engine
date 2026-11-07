"""Hydrogen-2s radial-node representation check (claim 47, ADR-039).

Representation-only, zero free parameters, no dynamics. Recomputes
the frozen correspondence numbers live from domains.fluid_universe.theory.hydrogen_radial_nodes
(radius via theory.hydrogen_fluid.bohr_radius, claim-25 derived):

- branch identities: residual 0, node at r=2a0, slip pi;
- radial: norm 1.0 (rel 1e-6), 1s-2s overlap 0 (abs 1e-6),
  peaks (3+-sqrt(5))a0 (rel 1e-6 on the outer peak);
- preserved: 1s balance residuals 0 at r=0.5,1,2,5 (atol 1e-12),
  2p loop circulation 2pi (rel 1e-6).
"""

from __future__ import annotations

import math

from domains.fluid_universe.theory.hydrogen_radial_nodes import representation_scales

from .provenance import RESULTS_DIR, metadata, write_json, write_text_atomic

NODE_ABS_TOL = 1e-9
NORM_REL_TOL = 1e-6
OVERLAP_ABS_TOL = 1e-6
PEAK_REL_TOL = 1e-6
BALANCE_ATOL = 1e-12
LOOP_REL_TOL = 1e-6


def run_radial_node_check(write: bool = True) -> dict:
    scales = representation_scales()
    branch = scales["branch"]
    radial = scales["radial"]
    preserved = scales["preserved"]
    node_kill = abs(branch["node_radius"] - 2.0 * scales["radius"]) > NODE_ABS_TOL
    slip_kill = branch["phase_slip"] != math.pi
    identity_kill = branch["identity_residual"] != 0.0
    norm_kill = (
        abs(radial["norm"] - 1.0) / 1.0 > NORM_REL_TOL
    )
    overlap_kill = abs(radial["overlap_10_20"]) > OVERLAP_ABS_TOL
    outer = radial["outer_peak"]
    peak_kill = abs(outer - (3.0 + math.sqrt(5.0))) / (
        3.0 + math.sqrt(5.0)
    ) > PEAK_REL_TOL
    balance_kill = not all(abs(v) <= BALANCE_ATOL for v in preserved["balance_residuals"])
    loop_kill = (
        abs(preserved["loop_circulation"] - 2.0 * math.pi) / (2.0 * math.pi)
        > LOOP_REL_TOL
    )
    killed = (
        node_kill
        or slip_kill
        or identity_kill
        or norm_kill
        or overlap_kill
        or peak_kill
        or balance_kill
        or loop_kill
    )
    if killed:
        legs = []
        if identity_kill:
            legs.append(f"identity residual {branch['identity_residual']:.3e} != 0")
        if node_kill:
            legs.append(f"node radius {branch['node_radius']:.12f} != 2a0")
        if slip_kill:
            legs.append(f"phase slip {branch['phase_slip']:.6f} != pi")
        if norm_kill or overlap_kill:
            legs.append("norm/overlap off")
        if peak_kill:
            legs.append(f"outer peak {outer:.6f} off 3+sqrt(5)")
        if balance_kill or loop_kill:
            legs.append("1s/2p preserved numbers disturbed")
        status = f"FALSIFIED (radial-node representation; {'; '.join(legs)})"
    else:
        status = "NUMERIC (radial-node representation identities verified)"
    result = {
        "scales": scales,
        "gates": {
            "node_abs_tol": NODE_ABS_TOL,
            "norm_rel_tol": NORM_REL_TOL,
            "overlap_abs_tol": OVERLAP_ABS_TOL,
            "peak_rel_tol": PEAK_REL_TOL,
            "balance_atol": BALANCE_ATOL,
            "loop_rel_tol": LOOP_REL_TOL,
            "kills": {
                "node": bool(node_kill),
                "slip": bool(slip_kill),
                "identity": bool(identity_kill),
                "norm": bool(norm_kill),
                "overlap": bool(overlap_kill),
                "peak": bool(peak_kill),
                "balance": bool(balance_kill),
                "loop": bool(loop_kill),
            },
        },
        "verdict": {
            "claim_47_status": status,
            "note": (
                "Exact two-branch split R_20=s*|R_20| with radius from "
                "bohr_radius(); shell slip pi, no circulation claimed; "
                "1s/2p numbers preserved via shared modules."
            ),
        },
    }
    config = {
        "radius_source": scales["radius_source"],
        "loop": scales["loop"],
        "gates": {
            "node_abs_tol": NODE_ABS_TOL,
            "norm_rel_tol": NORM_REL_TOL,
            "overlap_abs_tol": OVERLAP_ABS_TOL,
            "peak_rel_tol": PEAK_REL_TOL,
            "balance_atol": BALANCE_ATOL,
            "loop_rel_tol": LOOP_REL_TOL,
        },
        "scope": "representation identities, zero parameters, no dynamics",
    }
    payload = {"meta": metadata(config), "result": result}
    if write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        write_json(RESULTS_DIR / "radial_node.json", payload)
        write_text_atomic(
            RESULTS_DIR / "radial_node.md", render_markdown(payload)
        )
    return payload


def render_markdown(payload: dict) -> str:
    result = payload["result"]
    scales = result["scales"]
    branch = scales["branch"]
    radial = scales["radial"]
    verdict = result["verdict"]
    lines = [
        "# Hydrogen-2s radial-node representation (claim 47)",
        "",
        "Exact split R_20 = s*|R_20|; shell slip pi; no circulation claimed.",
        "",
        "| quantity | value |",
        "|---|---:|",
        f"| identity residual | {branch['identity_residual']:.3e} |",
        f"| node radius | {branch['node_radius']:.12f} |",
        f"| phase slip | {branch['phase_slip']:.12f} |",
        f"| radial norm | {radial['norm']:.12f} |",
        f"| 1s-2s overlap | {radial['overlap_10_20']:.3e} |",
        f"| outer peak | {radial['outer_peak']:.12f} |",
        f"| inner peak | {radial['inner_peak']:.12f} |",
        "",
        "## Verdict",
        "",
        f"- Claim 47: **{verdict['claim_47_status']}**.",
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
    payload = run_radial_node_check()
    print(payload["result"]["verdict"])
