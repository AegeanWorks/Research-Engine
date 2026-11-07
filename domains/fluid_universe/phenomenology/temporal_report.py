"""Temporal-check report for claim 15: N=64 at two timesteps, same physical time.

ADR-003 pre-registers the check.  The grid is held fixed at N=64, so the only
changed parameter is dt: 3000 steps at 5e-4 versus 6000 steps at 2.5e-4, both
at t=1.5.  The report cannot promote claim 15; it decides whether the N=96
spatial comparison is confounded by the timestep.
"""

from __future__ import annotations

import time

from domains.fluid_universe.sims.convergence import compare_temporal
from domains.fluid_universe.sims.production import MAX_WALL_SECONDS, run_production

from .provenance import RESULTS_DIR, metadata, write_json, write_text_atomic

N = 64
LENGTH = 10.0
MU = 20.0
SEED = 20261026
UPSAMPLE_FACTOR = 2
CHUNK = 600
COARSE_STEPS = 3000
COARSE_DT = 5.0e-4
FINE_STEPS = 6000
FINE_DT = 2.5e-4


def _run(steps: int, dt: float, deadline: float) -> tuple[dict, float]:
    started = time.perf_counter()
    payload = run_production(
        n=N,
        length=LENGTH,
        mu=MU,
        steps=steps,
        dt=dt,
        seed=SEED,
        perturbation=0.0,
        upsample_factor=UPSAMPLE_FACTOR,
        chunk=CHUNK,
        max_wall_seconds=max(1.0, deadline - started),
    )
    payload.pop("history", None)
    payload["max_wall_seconds"] = MAX_WALL_SECONDS
    return payload, float(time.perf_counter() - started)


def run_temporal_check(write: bool = True) -> dict:
    t0 = time.perf_counter()
    deadline = t0 + MAX_WALL_SECONDS
    coarse, coarse_seconds = _run(COARSE_STEPS, COARSE_DT, deadline)
    fine, fine_seconds = _run(FINE_STEPS, FINE_DT, deadline)
    comparison = compare_temporal(coarse, fine)
    config = {
        "n": N,
        "length": LENGTH,
        "mu": MU,
        "coarse_steps": COARSE_STEPS,
        "coarse_dt": COARSE_DT,
        "fine_steps": FINE_STEPS,
        "fine_dt": FINE_DT,
        "seed": SEED,
        "upsample_factor": UPSAMPLE_FACTOR,
        "chunk": CHUNK,
        "max_wall_seconds": MAX_WALL_SECONDS,
        "boundary": "fixed vacuum faces",
        "scope": "temporal diagnostic; not part of make results",
    }
    payload = {
        "meta": metadata(config),
        "coarse": coarse,
        "fine": fine,
        "comparison": comparison,
        "timing": {
            "coarse_seconds": coarse_seconds,
            "fine_seconds": fine_seconds,
            "total_seconds": float(time.perf_counter() - t0),
        },
    }
    if write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        write_json(RESULTS_DIR / "hopfion3d_temporal.json", payload)
        write_text_atomic(
            RESULTS_DIR / "hopfion3d_temporal.md", render_markdown(payload)
        )
    return payload


def render_markdown(payload: dict) -> str:
    coarse = payload["coarse"]
    fine = payload["fine"]
    comparison = payload["comparison"]
    criteria = comparison["criteria"]
    lines = [
        "# Timestep check for the 3D scan (claim 15)",
        "",
        f"N={comparison['n']} held fixed; both runs reach t={comparison['physical_time']:.3g} "
        f"(dt {comparison['dt_coarse']:.1e} for {coarse['steps']} steps versus "
        f"dt {comparison['dt_fine']:.1e} for {fine['steps']} steps).",
        "",
        "## Pre-registered temporal criteria",
        "",
        f"- |dH| <= {comparison['tolerances']['H']:.1e} and "
        f"|dH_upsampled| <= {comparison['tolerances']['H']:.1e}.",
        f"- |dZ3| <= {comparison['tolerances']['Z3']:.1e}.",
        "",
        "## Results",
        "",
        "| dt | steps | H | H upsampled | Z3 | force RMS | max bond | energy | seconds |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for scan, seconds in (
        (coarse, payload["timing"]["coarse_seconds"]),
        (fine, payload["timing"]["fine_seconds"]),
    ):
        final = scan["final"]
        lines.append(
            f"| {scan['dt']:.1e} | {scan['steps']} | {final['H']:.9f} | "
            f"{final['H_upsampled']:.9f} | {final['Z3']:.6f} | "
            f"{final['force_rms']:.3e} | {final['max_bond']:.3f} | "
            f"{final['E']:.3f} | {seconds:.1f} |"
        )
    lines += [
        "",
        f"Deltas (fine dt minus coarse dt): "
        f"H {comparison['deltas']['H']:+.6f}, "
        f"H upsampled {comparison['deltas']['H_upsampled']:+.6f}, "
        f"Z3 {comparison['deltas']['Z3']:+.6f}, "
        f"force {comparison['deltas']['force_rms']:+.3e}, "
        f"max bond {comparison['deltas']['max_bond']:+.3f}.",
        "",
        f"**Temporal verdict:** converged: **{comparison['temporal_converged']}**.",
        "",
        "| criterion | value |",
        "|---|---|",
    ]
    for key, value in criteria.items():
        lines.append(f"| {key} | {value} |")
    lines += [
        "",
        f"**Claim 15 stays {comparison['claim_15_status']}.** "
        f"Production ready (fine dt): **{fine['verdict']['production_ready']}**.",
        "",
        comparison["note"],
        "",
        f"- Config SHA-256: `{payload['meta']['config_sha256']}`",
        f"- Git: `{payload['meta']['git']['commit']}` "
        f"(dirty={payload['meta']['git']['dirty']})",
        f"- Total wall time: {payload['timing']['total_seconds']:.1f} s "
        f"(G-003 cap {MAX_WALL_SECONDS:.0f} s).",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    result = run_temporal_check()
    print(result["comparison"])
