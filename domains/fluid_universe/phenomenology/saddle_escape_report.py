"""Saddle-escape search from the pure-FN N=64 candidate (ADR-006, claim 14b).

The lowest tangent eigenvector gives a descent direction.  The candidate is
perturbed by two pre-registered amplitudes, relaxed, and accepted for a Hessian
test only when it keeps H>0.9 and force RMS<0.05.  A positive spectrum is
numerical local-minimum evidence at one grid, never a proof.
"""

from __future__ import annotations

import time

from domains.fluid_universe.sims.production import MAX_WALL_SECONDS, run_production
from domains.fluid_universe.sims.stability import (
    classify_escape,
    hessian_modes,
    hessian_spectrum,
    perturb_along_mode,
)

from .provenance import RESULTS_DIR, metadata, write_json, write_text_atomic

N = 64
LENGTH = 10.0
BUILD_STEPS = 1200
RELAX_STEPS = 600
DT = 5.0e-4
SEED = 20261026
AMPLITUDES = (0.05, 0.15)
H_MIN = 0.9
FORCE_MAX = 0.05


def _relax(field, steps: int, deadline: float):
    payload = run_production(
        n=N,
        length=LENGTH,
        mu=0.0,
        steps=steps,
        dt=DT,
        seed=SEED,
        perturbation=0.0,
        upsample_factor=2,
        chunk=600,
        max_wall_seconds=max(1.0, deadline - time.perf_counter()),
        initial_field=field,
        return_field=True,
    )
    return payload.pop("field"), payload


def run_escape_check(write: bool = True) -> dict:
    t0 = time.perf_counter()
    deadline = t0 + MAX_WALL_SECONDS
    base, base_payload = _relax(None, BUILD_STEPS, deadline)
    dx = base_payload["dx"]
    modes = hessian_modes(base, dx, k=1)
    base_min = float(modes["eigenvalues"][0])
    mode = modes["modes"][0]
    attempts = []
    for amplitude in AMPLITUDES:
        if time.perf_counter() > deadline:
            raise TimeoutError(
                "What: saddle-escape search exceeded the wall-clock limit.\n"
                "Why: project guideline G-003 caps every diagnostic at 900 s.\n"
                "Fix: reduce the number of amplitudes or the Hessian size."
            )
        perturbed = perturb_along_mode(base, mode, amplitude)
        relaxed, payload = _relax(perturbed, RELAX_STEPS, deadline)
        final = payload["final"]
        accepted = bool(final["H"] > H_MIN and final["force_rms"] < FORCE_MAX)
        attempt = {
            "amplitude": amplitude,
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
                    "What: saddle-escape Hessian exceeded the wall-clock limit.\n"
                    "Why: project guideline G-003 caps every diagnostic at 900 s.\n"
                    "Fix: reduce the requested eigenvalue count."
                )
            spectrum = hessian_spectrum(relaxed, dx, k=8)
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
            "What: saddle-escape search exceeded the wall-clock limit.\n"
            "Why: project guideline G-003 caps every diagnostic at 900 s.\n"
            "Fix: reduce the number of amplitudes or the Hessian size."
        )
    config = {
        "n": N,
        "length": LENGTH,
        "build_steps": BUILD_STEPS,
        "relax_steps": RELAX_STEPS,
        "dt": DT,
        "seed": SEED,
        "amplitudes": list(AMPLITUDES),
        "h_min": H_MIN,
        "force_max": FORCE_MAX,
        "max_wall_seconds": MAX_WALL_SECONDS,
        "boundary": "fixed vacuum faces",
        "scope": "saddle-escape search; evidence at one grid, not a proof",
    }
    result = {
        "meta": metadata(config),
        "base": {
            "H": float(base_payload["final"]["H"]),
            "Z3": float(base_payload["final"]["Z3"]),
            "force_rms": float(base_payload["final"]["force_rms"]),
            "min_eigenvalue": base_min,
        },
        "attempts": attempts,
        "verdict": classify_escape(attempts),
        "elapsed_seconds": elapsed,
    }
    if write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        write_json(RESULTS_DIR / "hopfion_saddle_escape.json", result)
        write_text_atomic(
            RESULTS_DIR / "hopfion_saddle_escape.md", render_markdown(result)
        )
    return result


def render_markdown(result: dict) -> str:
    base = result["base"]
    attempts = result["attempts"]
    verdict = result["verdict"]
    lines = [
        "# Saddle-escape search (claim 14b)",
        "",
        f"N={N}, length={LENGTH:.3g}, mu=0, build {BUILD_STEPS} steps, "
        f"relax {RELAX_STEPS} steps at dt={DT:.1e}.",
        "",
        "## Base candidate",
        "",
        f"H={base['H']:.9f}, Z3={base['Z3']:.6f}, force RMS="
        f"{base['force_rms']:.3e}, lowest tangent eigenvalue="
        f"{base['min_eigenvalue']:.6f}.",
        "",
        "## Attempts",
        "",
        "| amplitude | H | Z3 | force RMS | max bond | accepted | min eigenvalue | negative | local minimum |",
        "|---:|---:|---:|---:|---:|---|---:|---:|---|",
    ]
    for attempt in attempts:
        min_value = (
            f"{attempt['min_eigenvalue']:.6f}"
            if attempt["min_eigenvalue"] is not None
            else "not tested"
        )
        lines.append(
            f"| {attempt['amplitude']:.3g} | {attempt['H']:.9f} | "
            f"{attempt['Z3']:.6f} | {attempt['force_rms']:.3e} | "
            f"{attempt['max_bond']:.3f} | {attempt['accepted']} | "
            f"{min_value} | {attempt['negative_count']} | "
            f"{attempt['local_minimum']} |"
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
    result = run_escape_check()
    print(result["verdict"])
