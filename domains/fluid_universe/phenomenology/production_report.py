"""Production claim-15 report: resolved Hopf charge and Z3 order.

The main scan is deliberately separate from the fast canonical results. It
runs at N=64 (3600 steps) with fixed vacuum faces and checks the Hopf estimator
against a 2x spectrally upsampled field (N=128) within the 15-minute (900 s)
wall-clock limit (project guideline G-003). A short dt check at N=48 and two
perturbed seeds at N=32 are included as robustness diagnostics; the Z3
potential is explicit, so this is not a spontaneous-ordering claim.
"""

from __future__ import annotations

import time

from domains.fluid_universe.sims.production import MAX_WALL_SECONDS, run_production

from .provenance import RESULTS_DIR, metadata, write_json, write_text_atomic


def run_production_check(write: bool = True) -> dict:
    t0 = time.perf_counter()
    config = {
        "n": 64,
        "length": 10.0,
        "mu": 20.0,
        "steps": 3600,
        "dt": 5e-4,
        "seed": 20261026,
        "perturbation": 0.0,
        "upsample_factor": 2,
        "chunk": 600,
        "max_wall_seconds": MAX_WALL_SECONDS,
        "boundary": "fixed vacuum faces",
        "scope": "production diagnostic; not part of make results",
    }
    main = run_production(
        n=config["n"],
        length=config["length"],
        mu=config["mu"],
        steps=config["steps"],
        dt=config["dt"],
        seed=config["seed"],
        perturbation=config["perturbation"],
        upsample_factor=config["upsample_factor"],
        chunk=config["chunk"],
        max_wall_seconds=max(1.0, MAX_WALL_SECONDS - (time.perf_counter() - t0)),
    )
    main["max_wall_seconds"] = MAX_WALL_SECONDS
    main.pop("history", None)
    dt_fast = run_production(
        n=48,
        length=10.0,
        mu=20.0,
        steps=300,
        dt=5e-4,
        seed=config["seed"],
        upsample_factor=1,
        chunk=300,
        max_wall_seconds=max(1.0, MAX_WALL_SECONDS - (time.perf_counter() - t0)),
    )
    dt_slow = run_production(
        n=48,
        length=10.0,
        mu=20.0,
        steps=600,
        dt=2.5e-4,
        seed=config["seed"],
        upsample_factor=1,
        chunk=300,
        max_wall_seconds=max(1.0, MAX_WALL_SECONDS - (time.perf_counter() - t0)),
    )
    seeds = [
        run_production(
            n=32,
            length=10.0,
            mu=20.0,
            steps=300,
            dt=5e-4,
            seed=seed,
            perturbation=1e-3,
            upsample_factor=1,
            chunk=300,
            max_wall_seconds=max(1.0, MAX_WALL_SECONDS - (time.perf_counter() - t0)),
        )
        for seed in (1, 2)
    ]
    dt_h = abs(dt_fast["final"]["H"] - dt_slow["final"]["H"])
    dt_z3 = abs(dt_fast["final"]["Z3"] - dt_slow["final"]["Z3"])
    dt_converged = bool(dt_h <= 5e-3 and dt_z3 <= 0.02)
    main["verdict"]["dt_converged"] = dt_converged
    if not dt_converged:
        main["verdict"]["production_ready"] = False
        if main["verdict"]["claim_15_status"].startswith("VERIFIED"):
            main["verdict"]["claim_15_status"] = "UNVERIFIED (dt not converged)"
    payload = {
        "meta": metadata(config),
        "main": main,
        "dt_check": {
            "n": 48,
            "physical_time": 0.15,
            "dt_5e_4": {key: dt_fast["final"][key] for key in ("H", "Z3", "force_rms")},
            "dt_2p5e_4": {
                key: dt_slow["final"][key] for key in ("H", "Z3", "force_rms")
            },
            "H_difference": dt_h,
            "Z3_difference": dt_z3,
            "force_difference": abs(
                dt_fast["final"]["force_rms"] - dt_slow["final"]["force_rms"]
            ),
            "converged": dt_converged,
        },
        "seed_check": [
            {
                "seed": item["seed"],
                "perturbation": item["perturbation"],
                "H": item["final"]["H"],
                "Z3": item["final"]["Z3"],
                "force_rms": item["final"]["force_rms"],
            }
            for item in seeds
        ],
    }
    if write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        write_json(RESULTS_DIR / "hopfion3d_production.json", payload)
        write_text_atomic(
            RESULTS_DIR / "hopfion3d_production.md", render_markdown(payload)
        )
    return payload


def render_markdown(payload: dict) -> str:
    main = payload["main"]
    final = main["final"]
    verdict = main["verdict"]
    lines = [
        "# Production 3D scan (claim 15)",
        "",
        "Fixed vacuum faces. The main run relaxes the analytic H=1 map at "
        f"N={main['n']}, mu={main['mu']:.3g}, dt={main['dt']:.1e}. It is a "
        "production diagnostic, not part of `make results`.",
        "",
        "## Pre-registered acceptance criteria",
        "",
        f"- H within {main['criteria']['H_TOL']:.1e} of 1 and the native and "
        "upsampled estimates agree within the same tolerance.",
        f"- Z3 >= {main['criteria']['Z3_MIN']:.1f}.",
        f"- Force RMS <= {main['criteria']['FORCE_TOL']:.1e} and relative "
        f"energy drift over the last chunk <= {main['criteria']['DRIFT_TOL']:.1e}.",
        f"- Maximum bond difference <= {main['criteria']['BOND_TOL']:.2f} "
        "(at least two grid points per feature).",
        "",
        "## Main run",
        "",
        "| step | E | H | Z3 | force RMS | max bond | min pre-norm | monotone |",
        "|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in main["rows"]:
        lines.append(
            f"| {row['step']} | {row['E']:.3f} | {row['H']:.9f} | "
            f"{row['Z3']:.6f} | {row['force_rms']:.3e} | {row['max_bond']:.3f} | "
            f"{row['min_pre_norm']:.6f} | {row['monotone']} |"
        )
    lines += [
        "",
        f"Final native H: {final['H']:.9f}; upsampled H: "
        f"{final['H_upsampled']:.9f}; Z3: {final['Z3']:.6f}; "
        f"force RMS: {final['force_rms']:.3e}; max bond: {final['max_bond']:.3f}.",
        "",
        f"**Verdict:** coexistence: **{verdict['coexistence_H_and_Z3']}**; "
        f"converged: **{verdict['converged']}**; resolved: "
        f"**{verdict['resolved']}**; topology preserved: "
        f"**{verdict['topology_preserved']}**; claim 15: "
        f"**{verdict['claim_15_status']}**.",
        "",
        verdict["note"],
        "",
        "## dt check (N=48, same physical time)",
        "",
        "| dt | H | Z3 | force RMS |",
        "|---:|---:|---:|---:|",
        f"| 5e-4 | {payload['dt_check']['dt_5e_4']['H']:.9f} | "
        f"{payload['dt_check']['dt_5e_4']['Z3']:.6f} | "
        f"{payload['dt_check']['dt_5e_4']['force_rms']:.3e} |",
        f"| 2.5e-4 | {payload['dt_check']['dt_2p5e_4']['H']:.9f} | "
        f"{payload['dt_check']['dt_2p5e_4']['Z3']:.6f} | "
        f"{payload['dt_check']['dt_2p5e_4']['force_rms']:.3e} |",
        "",
        f"Differences: H {payload['dt_check']['H_difference']:.3e}, "
        f"Z3 {payload['dt_check']['Z3_difference']:.3e}, force "
        f"{payload['dt_check']['force_difference']:.3e}.",
        "",
        "## Seed check (N=32, 300 steps, perturbation 1e-3)",
        "",
        "| seed | H | Z3 | force RMS |",
        "|---:|---:|---:|---:|",
    ]
    for row in payload["seed_check"]:
        lines.append(
            f"| {row['seed']} | {row['H']:.9f} | {row['Z3']:.6f} | "
            f"{row['force_rms']:.3e} |"
        )
    lines += [
        "",
        "The potential breaks the azimuthal symmetry explicitly; the seed check "
        "is a robustness diagnostic, not a spontaneous-ordering test.",
        "",
        f"- Config SHA-256: `{payload['meta']['config_sha256']}`",
        f"- Git: `{payload['meta']['git']['commit']}` "
        f"(dirty={payload['meta']['git']['dirty']})",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    result = run_production_check()
    print(result["main"]["verdict"])
