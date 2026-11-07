"""Resolution report for claim 15: N=64 versus N=96 at the same physical time.

The pre-registered N=96 check is in ADR-002.  Both scans use the production
runner unchanged (same length, mu, steps, dt, seed, fixed vacuum faces and 2x
spectral upsampling), run in one process under the 900 s G-003 budget, and are
compared by the pure `sims.convergence.compare_scans`.  The report cannot
promote claim 15: the N=96 run must satisfy the unchanged production criteria
itself.
"""

from __future__ import annotations

import time

from domains.fluid_universe.sims.convergence import compare_scans
from domains.fluid_universe.sims.production import MAX_WALL_SECONDS, run_production

from .provenance import RESULTS_DIR, metadata, write_json, write_text_atomic

N_LOW = 64
N_HIGH = 96
LENGTH = 10.0
MU = 20.0
STEPS = 3000
DT = 5.0e-4
SEED = 20261026
UPSAMPLE_FACTOR = 2
CHUNK = 600


def _run(n: int, deadline: float) -> tuple[dict, float]:
    started = time.perf_counter()
    payload = run_production(
        n=n,
        length=LENGTH,
        mu=MU,
        steps=STEPS,
        dt=DT,
        seed=SEED,
        perturbation=0.0,
        upsample_factor=UPSAMPLE_FACTOR,
        chunk=CHUNK,
        max_wall_seconds=max(1.0, deadline - started),
    )
    payload.pop("history", None)
    return payload, float(time.perf_counter() - started)


def run_convergence_check(write: bool = True) -> dict:
    t0 = time.perf_counter()
    deadline = t0 + MAX_WALL_SECONDS
    low, low_seconds = _run(N_LOW, deadline)
    high, high_seconds = _run(N_HIGH, deadline)
    comparison = compare_scans(low, high)
    config = {
        "n_low": N_LOW,
        "n_high": N_HIGH,
        "length": LENGTH,
        "mu": MU,
        "steps": STEPS,
        "dt": DT,
        "seed": SEED,
        "upsample_factor": UPSAMPLE_FACTOR,
        "chunk": CHUNK,
        "max_wall_seconds": MAX_WALL_SECONDS,
        "boundary": "fixed vacuum faces",
        "scope": "resolution diagnostic; not part of make results",
    }
    payload = {
        "meta": metadata(config),
        "low": low,
        "high": high,
        "comparison": comparison,
        "timing": {
            "n64_seconds": low_seconds,
            "n96_seconds": high_seconds,
            "total_seconds": float(time.perf_counter() - t0),
        },
    }
    if write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        write_json(RESULTS_DIR / "hopfion3d_convergence.json", payload)
        write_text_atomic(
            RESULTS_DIR / "hopfion3d_convergence.md", render_markdown(payload)
        )
    return payload


def render_markdown(payload: dict) -> str:
    low = payload["low"]
    high = payload["high"]
    comparison = payload["comparison"]
    criteria = comparison["criteria"]
    lines = [
        "# Resolution check for the 3D scan (claim 15)",
        "",
        f"N={low['n']} and N={high['n']} at the same physical time: "
        f"mu={high['mu']:.3g}, steps={high['steps']}, dt={high['dt']:.1e}, "
        "fixed vacuum faces, 2x spectral upsampling.",
        "",
        "The 3600-step production scan remains the primary claim-15 evidence. "
        "This check uses 3000 steps so both resolutions fit one G-003 process; "
        "no acceptance criterion changes.",
        "",
        "## Pre-registered resolution criteria",
        "",
        f"- |dH| <= {comparison['tolerances']['H']:.1e} and "
        f"|dH_upsampled| <= {comparison['tolerances']['H']:.1e}.",
        f"- |dZ3| <= {comparison['tolerances']['Z3']:.1e}.",
        "- force RMS and max bond do not increase with resolution.",
        "",
        "## Results",
        "",
        "| N | H | H upsampled | Z3 | force RMS | max bond | energy | min pre-norm | seconds |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for scan, seconds in (
        (low, payload["timing"]["n64_seconds"]),
        (high, payload["timing"]["n96_seconds"]),
    ):
        final = scan["final"]
        lines.append(
            f"| {scan['n']} | {final['H']:.9f} | {final['H_upsampled']:.9f} | "
            f"{final['Z3']:.6f} | {final['force_rms']:.3e} | "
            f"{final['max_bond']:.3f} | {final['E']:.3f} | "
            f"{scan['min_pre_norm']:.6f} | {seconds:.1f} |"
        )
    lines += [
        "",
        f"Deltas (N={high['n']} minus N={low['n']}): "
        f"H {comparison['deltas']['H']:+.6f}, "
        f"H upsampled {comparison['deltas']['H_upsampled']:+.6f}, "
        f"Z3 {comparison['deltas']['Z3']:+.6f}, "
        f"force {comparison['deltas']['force_rms']:+.3e}, "
        f"max bond {comparison['deltas']['max_bond']:+.3f}.",
        "",
        f"**Resolution verdict:** converged: "
        f"**{comparison['resolution_converged']}**; native H toward 1: "
        f"**{criteria['H_toward_one']}**; upsampled H toward 1: "
        f"**{criteria['H_upsampled_toward_one']}**.",
        "",
        "| criterion | value |",
        "|---|---|",
    ]
    for key, value in criteria.items():
        lines.append(f"| {key} | {value} |")
    lines += [
        "",
        f"**Claim 15 stays {comparison['claim_15_status']}.** "
        f"Production ready: **{high['verdict']['production_ready']}**.",
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
    result = run_convergence_check()
    print(result["comparison"])
