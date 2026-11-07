"""Hopf estimator resolution report."""

from __future__ import annotations

from domains.fluid_universe.theory.hopf import resolution_study

from .provenance import RESULTS_DIR, metadata, write_json, write_text_atomic


def run_hopf_resolution_check(write: bool = True) -> dict:
    payload = {
        "meta": metadata({"length": 10.0, "model": "analytic H=1 map"}),
        **resolution_study(),
    }
    if write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        write_json(RESULTS_DIR / "hopf_resolution.json", payload)
        write_text_atomic(RESULTS_DIR / "hopf_resolution.md", render_markdown(payload))
    return payload


def render_markdown(payload: dict) -> str:
    v = payload["verdict"]
    lines = [
        "# Hopf grid resolution (analytic H=1 map)",
        "",
        "| N | H_grid | abs error vs preimage |",
        "|---:|---:|---:|",
    ]
    for row in payload["rows"]:
        lines.append(
            f"| {row['n']} | {row['H_grid']:.9f} | {row['abs_error_vs_preimage']:.3e} |"
        )
    lines += [
        "",
        f"Preimage linking: H = {payload['preimage']:.9f}.",
        "",
        f"Coarse (N<32) under-resolved: **{v['coarse_under_resolved']}**; "
        f"fine (N>=32) within 1e-3: **{v['fine_within_1e_3']}**.",
        "",
        v["note"],
        "",
        f"- Config SHA-256: `{payload['meta']['config_sha256']}`",
        f"- Git: `{payload['meta']['git']['commit']}` (dirty={payload['meta']['git']['dirty']})",
        "",
    ]
    return "\n".join(lines)
