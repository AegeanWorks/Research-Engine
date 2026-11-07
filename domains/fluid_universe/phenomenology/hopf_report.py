"""Hopf estimator validation result payload."""

from __future__ import annotations

from domains.fluid_universe.theory.hopf import validate

from .provenance import RESULTS_DIR, metadata, write_json, write_text_atomic


def run_hopf_check(write: bool = True) -> dict:
    payload = {"meta": metadata({"source": "analytic H=1 Hopf map"}), **validate()}
    if write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        write_json(RESULTS_DIR / "hopf.json", payload)
        write_text_atomic(RESULTS_DIR / "hopf.md", render_markdown(payload))
    return payload


def render_markdown(payload: dict) -> str:
    v = payload["verdict"]
    lines = [
        "# Hopf-charge estimator validation (claim 15, baseline 4)",
        "",
        "Analytic Hopf map on R^3 with n -> (0,0,1) at infinity.",
        "",
        "## Preimage linking (validated)",
        "",
        "| samples | H |",
        "|---:|---:|",
    ]
    for samples, value in payload["preimage"].items():
        lines.append(f"| {samples} | {value:.9f} |")
    lines += [
        "",
        f"- Second target pair: H = {payload['target_pair']:.9f}.",
        f"- Reflection: H = {payload['reflection']:.9f} (sign flip).",
        f"- Rotation: H = {payload['rotation']:.9f}.",
        f"- Shear: H = {payload['shear']:.9f}.",
        "",
        "## Grid Chern-Simons integral (validated, normalized)",
        "",
        "| N | H |",
        "|---:|---:|",
    ]
    for n, value in payload["grid"].items():
        lines.append(f"| {n} | {value:.9f} |")
    lines += [
        "",
        f"- Reflected map: H = {payload['grid_reflection']:.9f} (sign flip).",
        "",
        f"**Verdict:** preimage converges to 1: **{v['preimage_converges_to_one']}**; "
        f"sign flips under reflection: **{v['reflection_flips_sign']}**; "
        f"rotation invariant: **{v['rotation_invariant']}**; shear invariant: **{v['shear_invariant']}**.",
        "",
        f"Grid integral matches 1: **{v['grid_integral_matches_one']}**; "
        f"two-method agreement: **{v['two_method_agreement']}**; "
        f"baseline 4 pass: **{v['baseline_4_pass']}**; "
        f"claim 15: **{v['claim_15_status']}**.",
        "",
        v["note"],
        "",
        f"- Config SHA-256: `{payload['meta']['config_sha256']}`",
        f"- Git: `{payload['meta']['git']['commit']}` (dirty={payload['meta']['git']['dirty']})",
        "",
    ]
    return "\n".join(lines)
