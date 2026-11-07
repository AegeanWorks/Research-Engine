"""Pure-Faddeev-Niemi N=64 candidate Hessian (ADR-005, claims 14b/14d).

The candidate is the 1200-step, mu=0 relax of the analytic H=1 map, a different
field from the scale-iteration saddle tested in 14d.  The report validates the
tangent operator at N=8 and computes the eight lowest eigenvalues at N=64.  A
positive spectrum is numerical local-minimum evidence at one grid, never a
stability proof.
"""

from __future__ import annotations

import time

from domains.fluid_universe.sims.production import MAX_WALL_SECONDS, run_production
from domains.fluid_universe.sims.stability import classify_candidate, hessian_spectrum, validate_operator

from .provenance import RESULTS_DIR, metadata, write_json, write_text_atomic

N = 64
LENGTH = 10.0
STEPS = 1200
DT = 5.0e-4
SEED = 20261026
K_EIGENVALUES = 8


def run_purefn_check(write: bool = True) -> dict:
    t0 = time.perf_counter()
    payload = run_production(
        n=N,
        length=LENGTH,
        mu=0.0,
        steps=STEPS,
        dt=DT,
        seed=SEED,
        perturbation=0.0,
        upsample_factor=2,
        chunk=600,
        max_wall_seconds=MAX_WALL_SECONDS,
        return_field=True,
    )
    field = payload.pop("field")
    dx = payload["dx"]
    validation = validate_operator(n=8)
    spectrum = hessian_spectrum(field, dx, k=K_EIGENVALUES)
    elapsed = float(time.perf_counter() - t0)
    if elapsed > MAX_WALL_SECONDS:
        raise TimeoutError(
            "What: pure-FN Hessian exceeded the wall-clock limit.\n"
            "Why: project guideline G-003 caps every diagnostic at 900 s.\n"
            "Fix: reduce N or the requested eigenvalue count."
        )
    final = payload["final"]
    candidate = {
        key: float(final[key])
        for key in (
            "E",
            "E2",
            "E4",
            "V",
            "H",
            "H_upsampled",
            "Z3",
            "force_rms",
            "max_bond",
        )
    }
    candidate["virial"] = float(final["E2"] - final["E4"])
    candidate["min_pre_norm"] = float(payload["min_pre_norm"])
    config = {
        "n": N,
        "length": LENGTH,
        "mu": 0.0,
        "steps": STEPS,
        "dt": DT,
        "seed": SEED,
        "upsample_factor": 2,
        "k_eigenvalues": K_EIGENVALUES,
        "max_wall_seconds": MAX_WALL_SECONDS,
        "boundary": "fixed vacuum faces",
        "scope": "pure-FN candidate Hessian; evidence at one grid, not a proof",
    }
    result = {
        "meta": metadata(config),
        "candidate": candidate,
        "validation": validation,
        "spectrum": spectrum,
        "verdict": classify_candidate(validation, spectrum),
        "elapsed_seconds": elapsed,
    }
    if write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        write_json(RESULTS_DIR / "hopfion_purefn_stability.json", result)
        write_text_atomic(
            RESULTS_DIR / "hopfion_purefn_stability.md", render_markdown(result)
        )
    return result


def render_markdown(result: dict) -> str:
    candidate = result["candidate"]
    validation = result["validation"]
    spectrum = result["spectrum"]
    verdict = result["verdict"]
    lines = [
        "# Pure-FN candidate Hessian (claims 14b/14d)",
        "",
        f"N={N}, length={LENGTH:.3g}, mu=0, {STEPS} steps at dt={DT:.1e}, "
        "fixed vacuum faces, 2x spectral upsampling.",
        "",
        "## Candidate",
        "",
        "| E | E2 | E4 | virial | H | H upsampled | Z3 | force RMS | max bond |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        f"| {candidate['E']:.3f} | {candidate['E2']:.3f} | {candidate['E4']:.3f} | "
        f"{candidate['virial']:+.6f} | {candidate['H']:.9f} | "
        f"{candidate['H_upsampled']:.9f} | {candidate['Z3']:.6f} | "
        f"{candidate['force_rms']:.3e} | {candidate['max_bond']:.3f} |",
        "",
        "## Operator validation (N=8)",
        "",
        f"- Passed: **{validation['passed']}**; max absolute error: "
        f"{validation['max_abs_error']:.3e}; symmetry error: "
        f"{validation['symmetry_error']:.3e}.",
        "",
        "## Spectrum (N=64)",
        "",
        f"- Tangent dimension: {spectrum['dimension']}; requested modes: "
        f"{spectrum['requested_k']}; negative modes: {spectrum['negative_count']}.",
        f"- Smallest eigenvalues: "
        + ", ".join(f"{value:.6f}" for value in spectrum["smallest_eigenvalues"]),
        "",
        f"**Minimum eigenvalue:** {spectrum['min_eigenvalue']:.6f}.",
        "",
        "## Verdict",
        "",
        f"- Claim 14b: **{verdict['claim_14b_status']}**.",
        f"- Claim 14e: **{verdict['candidate_status']}**.",
        f"- Local minimum at N=64: **{verdict['local_minimum_at_N64']}**; "
        f"stability proved: **{verdict['stable_at_N64_proved']}**.",
        "",
        verdict["note"],
        "",
        f"- Elapsed: {result['elapsed_seconds']:.1f} s "
        f"(G-003 cap {MAX_WALL_SECONDS:.0f} s).",
        f"- Config SHA-256: `{result['meta']['config_sha256']}`",
        f"- Git: `{result['meta']['git']['commit']}` "
        f"(dirty={result['meta']['git']['dirty']})",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    result = run_purefn_check()
    print(result["verdict"])
