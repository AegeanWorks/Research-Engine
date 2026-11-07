"""Checkpointed N=96 extension for claim 15 (ADR-004).

Each invocation runs one 3000-step chunk (about 600 s at N=96), saves the final
field atomically, and appends a row to `results/hopfion3d_extension.json`.  The
next invocation resumes from the saved field.  The extension is a diagnostic:
it cannot promote claim 15 unless the final state itself satisfies the unchanged
production rule.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import numpy as np

from domains.fluid_universe.sims.convergence import summarize_trend
from domains.fluid_universe.sims.production import MAX_WALL_SECONDS, run_production

from .provenance import RESULTS_DIR, metadata, write_json, write_text_atomic

N = 96
LENGTH = 10.0
MU = 20.0
DT = 5.0e-4
STEPS_PER_CHUNK = 3000
SEED = 20261026
CHUNK = 600
UPSAMPLE_FACTOR = 2
MAX_CHUNKS = 4
ACCUMULATOR = RESULTS_DIR / "hopfion3d_extension.json"


def _checkpoint(chunk: int) -> Path:
    return RESULTS_DIR / f"hopfion3d_extension_state_{chunk}.npy"


def _write_npy_atomic(path: Path, array: np.ndarray) -> None:
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "wb") as handle:
        np.save(handle, array)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


def _load_state() -> dict:
    if not ACCUMULATOR.exists():
        return {"meta": None, "rows": [], "trend": None}
    return json.loads(ACCUMULATOR.read_text(encoding="utf-8"))


def _save_state(state: dict) -> None:
    write_json(ACCUMULATOR, state)
    write_text_atomic(
        RESULTS_DIR / "hopfion3d_extension.md", render_markdown(state)
    )


def run_next_chunk(write: bool = True) -> dict:
    state = _load_state()
    rows = state["rows"]
    chunk = len(rows) + 1
    if chunk > MAX_CHUNKS:
        raise ValueError(
            f"extension already has {len(rows)} chunks; MAX_CHUNKS={MAX_CHUNKS}"
        )
    previous = _checkpoint(chunk - 1) if chunk > 1 else None
    if previous is not None and not previous.exists():
        raise FileNotFoundError(
            f"missing checkpoint {previous}; cannot resume chunk {chunk}"
        )
    field = np.load(previous) if previous is not None else None
    started = time.perf_counter()
    payload = run_production(
        n=N,
        length=LENGTH,
        mu=MU,
        steps=STEPS_PER_CHUNK,
        dt=DT,
        seed=SEED,
        perturbation=0.0,
        upsample_factor=UPSAMPLE_FACTOR,
        chunk=CHUNK,
        max_wall_seconds=MAX_WALL_SECONDS,
        initial_field=field,
        return_field=True,
    )
    final_field = payload.pop("field")
    final = payload["final"]
    seconds = float(time.perf_counter() - started)
    row = {
        "chunk": chunk,
        "steps": chunk * STEPS_PER_CHUNK,
        "t": float(chunk * STEPS_PER_CHUNK * DT),
        "H": final["H"],
        "H_upsampled": final["H_upsampled"],
        "Z3": final["Z3"],
        "force_rms": final["force_rms"],
        "max_bond": final["max_bond"],
        "E": final["E"],
        "min_pre_norm": payload["min_pre_norm"],
        "seconds": seconds,
        "production_ready": payload["verdict"]["production_ready"],
        "claim_15_status": payload["verdict"]["claim_15_status"],
    }
    rows.append(row)
    config = {
        "n": N,
        "length": LENGTH,
        "mu": MU,
        "dt": DT,
        "steps_per_chunk": STEPS_PER_CHUNK,
        "max_chunks": MAX_CHUNKS,
        "seed": SEED,
        "upsample_factor": UPSAMPLE_FACTOR,
        "chunk": CHUNK,
        "max_wall_seconds": MAX_WALL_SECONDS,
        "boundary": "fixed vacuum faces",
        "scope": "checkpointed extension; not part of make results",
    }
    state["meta"] = metadata(config)
    state["trend"] = summarize_trend(rows) if len(rows) >= 2 else None
    if write:
        _write_npy_atomic(_checkpoint(chunk), final_field)
        _save_state(state)
        for old in RESULTS_DIR.glob("hopfion3d_extension_state_*.npy"):
            if old.name != _checkpoint(chunk).name:
                old.unlink()
    return state


def render_markdown(state: dict) -> str:
    rows = state["rows"]
    lines = [
        "# Checkpointed N=96 extension (claim 15)",
        "",
        f"N={N}, length={LENGTH:.3g}, mu={MU:.3g}, dt={DT:.1e}, "
        f"{STEPS_PER_CHUNK} steps per chunk, fixed vacuum faces, 2x upsampling.",
        "",
        "Each chunk is one G-003 run; the field is saved atomically and the next "
        "chunk resumes from it.",
        "",
        "## Rows",
        "",
        "| chunk | steps | t | H | H upsampled | Z3 | force RMS | max bond | seconds |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['chunk']} | {row['steps']} | {row['t']:.3g} | "
            f"{row['H']:.9f} | {row['H_upsampled']:.9f} | {row['Z3']:.6f} | "
            f"{row['force_rms']:.3e} | {row['max_bond']:.3f} | "
            f"{row['seconds']:.1f} |"
        )
    lines += ["", "## Trend", ""]
    trend = state.get("trend")
    if trend is None:
        lines.append("At least two chunks are required for a trend.")
    else:
        lines += [
            f"- Z3 slope per step: {trend['z3_slope_per_step']:+.3e}; "
            f"monotone: **{trend['z3_monotone']}**.",
            f"- Force slope per step: {trend['force_slope_per_step']:+.3e}; "
            f"monotone: **{trend['force_monotone']}**.",
            f"- Linear projection to Z3=0.5: "
            f"{_format_projection(trend['projected_steps_to_z3_target'], trend['projected_time_to_z3_target'])}.",
            f"- Linear projection to force=1e-2: "
            f"{_format_projection(trend['projected_steps_to_force_tol'], trend['projected_time_to_force_tol'])}.",
            "",
            trend["note"],
        ]
    if rows:
        lines += [
            "",
            f"**Claim 15: {rows[-1]['claim_15_status']}.** "
            f"Production ready: **{rows[-1]['production_ready']}**.",
        ]
    if state.get("meta"):
        lines += [
            "",
            f"- Config SHA-256: `{state['meta']['config_sha256']}`",
            f"- Git: `{state['meta']['git']['commit']}` "
            f"(dirty={state['meta']['git']['dirty']})",
        ]
    lines.append("")
    return "\n".join(lines)


def _format_projection(steps: float | None, time_value: float | None) -> str:
    if steps is None:
        return "not projected (trend moves away from the target)"
    return f"{steps:.0f} steps, t={time_value:.3g}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the next N=96 extension chunk.")
    parser.add_argument(
        "--status", action="store_true", help="print the stored trend and exit"
    )
    parser.add_argument(
        "--reset", action="store_true", help="delete the checkpoint and accumulator"
    )
    args = parser.parse_args(argv)
    if args.reset:
        for path in RESULTS_DIR.glob("hopfion3d_extension*"):
            path.unlink()
        print("reset the extension checkpoint and accumulator")
        return 0
    if args.status:
        state = _load_state()
        print(json.dumps({"rows": state["rows"], "trend": state["trend"]}, indent=2))
        return 0
    state = run_next_chunk()
    print(json.dumps(state["rows"][-1], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
