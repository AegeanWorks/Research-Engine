"""Report for the validated tangent-space Hessian of the scale candidate."""

from __future__ import annotations

from domains.fluid_universe.sims.stability import run_stability_check

from .provenance import RESULTS_DIR, metadata, write_json, write_text_atomic


def run_stability_report(write: bool = True) -> dict:
    payload = {
        "meta": metadata(
            {
                "n": 64,
                "length": 10.0,
                "iterations": 5,
                "steps_per_iteration": 600,
                "dt": 5e-4,
                "k_eigenvalues": 8,
                "dense_validation_n": 8,
                "boundary": "fixed vacuum faces",
                "scope": "tangent-space Hessian; evidence at one grid, not a proof",
            }
        ),
        **run_stability_check(
            n=64, length=10.0, iterations=5, steps=600, k=8, validate_n=8
        ),
    }
    if write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        write_json(RESULTS_DIR / "hopfion_stability.json", payload)
        write_text_atomic(
            RESULTS_DIR / "hopfion_stability.md", render_markdown(payload)
        )
    return payload


def render_markdown(payload: dict) -> str:
    candidate = payload["candidate"]
    validation = payload["dense_validation"]
    spectrum = payload["spectrum"]
    verdict = payload["verdict"]
    lines = [
        "# Tangent-space Hessian of the scale-stationary candidate (claim 14d)",
        "",
        "The Hessian is computed on the two-dimensional tangent space of the unit "
        "sphere at every interior site, so the radial normalization modes are "
        "removed. This is evidence at one grid, not a stability proof.",
        "",
        f"Candidate: H={candidate['H']:.9f}, Z3={candidate['Z3']:.3e}, "
        f"E2-E4={candidate['virial']:+.6f}, force RMS={candidate['force_rms']:.3e}.",
        "",
        "## Dense validation",
        "",
        f"- N={validation['n']}, tangent dimension {validation['dimension']}.",
        f"- Maximum |dense - matrix-free|: {validation['max_abs_error']:.3e}.",
        f"- Symmetry error: {validation['symmetry_error']:.3e}.",
        f"- Passed (both below 1e-8): **{validation['passed']}**.",
        "",
        "## N=64 spectrum",
        "",
        f"- Tangent dimension: {spectrum['dimension']}.",
        f"- Requested eigenvalues: {spectrum['requested_k']}.",
        f"- Minimum eigenvalue: {spectrum['min_eigenvalue']:+.6f}.",
        f"- Negative eigenvalues in the requested set: {spectrum['negative_count']}.",
        f"- Near-zero eigenvalues: {spectrum['near_zero_count']}.",
        "",
        "Smallest eigenvalues: "
        + ", ".join(f"{value:+.6f}" for value in spectrum["smallest_eigenvalues"])
        + ".",
        "",
        f"**Verdict:** operator validated: **{verdict['operator_validated']}**; "
        f"local minimum at N=64: **{verdict['local_minimum_at_N64']}**; "
        f"claim 14d: **{verdict['claim_14d_status']}**; "
        f"claim 14b: **{verdict['claim_14b_status']}**.",
        "",
        verdict["note"],
        "",
        f"- Config SHA-256: `{payload['meta']['config_sha256']}`",
        f"- Git: `{payload['meta']['git']['commit']}` (dirty={payload['meta']['git']['dirty']})",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    print(run_stability_report()["verdict"])
