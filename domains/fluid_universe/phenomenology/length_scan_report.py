"""Box-length scan of the pure-FN N=64 candidate (ADR-007, claim 14b).

The box length sets the soliton-to-boundary ratio and the virial balance.  This
report relaxes the analytic H=1 map at four pre-registered lengths, tests the
Hessian of every field that keeps H>0.9 and force RMS<0.05, and stops at the
first local minimum.  A positive spectrum is numerical evidence at one grid,
never a proof.
"""

from __future__ import annotations

import time

from domains.fluid_universe.sims.production import MAX_WALL_SECONDS, run_production
from domains.fluid_universe.sims.stability import classify_escape, hessian_spectrum

from .provenance import RESULTS_DIR, metadata, write_json, write_text_atomic

N = 64
LENGTHS = (8.0, 10.0, 12.0, 14.0)
STEPS = 1200
DT = 5.0e-4
SEED = 20261026
K_EIGENVALUES = 8
H_MIN = 0.9
FORCE_MAX = 0.05


def run_length_scan(write: bool = True) -> dict:
    t0 = time.perf_counter()
    deadline = t0 + MAX_WALL_SECONDS
    attempts = []
    for length in LENGTHS:
        if time.perf_counter() > deadline:
            raise TimeoutError(
                "What: length scan exceeded the wall-clock limit.\n"
                "Why: project guideline G-003 caps every diagnostic at 900 s.\n"
                "Fix: reduce the length list or the requested eigenvalue count."
            )
        payload = run_production(
            n=N,
            length=length,
            mu=0.0,
            steps=STEPS,
            dt=DT,
            seed=SEED,
            perturbation=0.0,
            upsample_factor=2,
            chunk=600,
            max_wall_seconds=max(1.0, deadline - time.perf_counter()),
            return_field=True,
        )
        field = payload.pop("field")
        dx = payload["dx"]
        final = payload["final"]
        accepted = bool(final["H"] > H_MIN and final["force_rms"] < FORCE_MAX)
        attempt = {
            "length": length,
            "H": float(final["H"]),
            "H_upsampled": float(final["H_upsampled"]),
            "Z3": float(final["Z3"]),
            "force_rms": float(final["force_rms"]),
            "max_bond": float(final["max_bond"]),
            "E": float(final["E"]),
            "min_pre_norm": float(payload["min_pre_norm"]),
            "accepted": accepted,
            "tested": False,
            "min_eigenvalue": None,
            "negative_count": None,
            "local_minimum": False,
        }
        if accepted:
            if time.perf_counter() > deadline:
                raise TimeoutError(
                    "What: length-scan Hessian exceeded the wall-clock limit.\n"
                    "Why: project guideline G-003 caps every diagnostic at 900 s.\n"
                    "Fix: reduce the requested eigenvalue count."
                )
            spectrum = hessian_spectrum(field, dx, k=K_EIGENVALUES)
            attempt.update(
                {
                    "tested": True,
                    "min_eigenvalue": spectrum["min_eigenvalue"],
                    "negative_count": spectrum["negative_count"],
                    "local_minimum": bool(
                        spectrum["min_eigenvalue"] >= -1e-6
                    ),
                }
            )
        attempts.append(attempt)
        if attempt["local_minimum"]:
            break
    elapsed = float(time.perf_counter() - t0)
    if elapsed > MAX_WALL_SECONDS:
        raise TimeoutError(
            "What: length scan exceeded the wall-clock limit.\n"
            "Why: project guideline G-003 caps every diagnostic at 900 s.\n"
            "Fix: reduce the length list or the requested eigenvalue count."
        )
    config = {
        "n": N,
        "lengths": list(LENGTHS),
        "steps": STEPS,
        "dt": DT,
        "seed": SEED,
        "k_eigenvalues": K_EIGENVALUES,
        "h_min": H_MIN,
        "force_max": FORCE_MAX,
        "max_wall_seconds": MAX_WALL_SECONDS,
        "boundary": "fixed vacuum faces",
        "scope": "box-length scan; evidence at one grid, not a proof",
    }
    result = {
        "meta": metadata(config),
        "attempts": attempts,
        "verdict": classify_escape(
            attempts,
            note=(
                "A positive spectrum at one grid and one box length is "
                "numerical evidence, not a stability proof; a saddle at every "
                "length does not rule out a different ansatz."
            ),
        ),
        "elapsed_seconds": elapsed,
    }
    if write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        write_json(RESULTS_DIR / "hopfion_length_scan.json", result)
        write_text_atomic(
            RESULTS_DIR / "hopfion_length_scan.md", render_markdown(result)
        )
    return result


def render_markdown(result: dict) -> str:
    attempts = result["attempts"]
    verdict = result["verdict"]
    lines = [
        "# Box-length scan of the pure-FN candidate (claim 14b)",
        "",
        f"N={N}, mu=0, {STEPS} steps at dt={DT:.1e}, fixed vacuum faces, "
        "2x spectral upsampling.",
        "",
        "## Attempts",
        "",
        "| length | H | H upsampled | Z3 | force RMS | max bond | accepted | min eigenvalue | negative | local minimum |",
        "|---:|---:|---:|---:|---:|---:|---|---:|---:|---|",
    ]
    for attempt in attempts:
        min_value = (
            f"{attempt['min_eigenvalue']:.6f}"
            if attempt["min_eigenvalue"] is not None
            else "not tested"
        )
        lines.append(
            f"| {attempt['length']:.3g} | {attempt['H']:.9f} | "
            f"{attempt['H_upsampled']:.9f} | {attempt['Z3']:.6f} | "
            f"{attempt['force_rms']:.3e} | {attempt['max_bond']:.3f} | "
            f"{attempt['accepted']} | {min_value} | "
            f"{attempt['negative_count']} | {attempt['local_minimum']} |"
        )
    lines += [
        "",
        "## Verdict",
        "",
        f"- Local minimum found: **{verdict['local_minimum_found']}**.",
        f"- Claim 14b: **{verdict['claim_14b_status']}**.",
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
    result = run_length_scan()
    print(result["verdict"])
