"""3D pilot report for the E2+E4+Z3 model."""

from __future__ import annotations

from domains.fluid_universe.sims.core3d import convergence_scan, pilot_scan

from .provenance import RESULTS_DIR, metadata, write_json, write_text_atomic


def run_hopfion3d_check(write: bool = True) -> dict:
    payload = {
        "meta": metadata(
            {
                "model": "E2 + Skyrme E4 + mu rho^2 (1-cos3phi)",
                "K": 1.0,
                "kappa": 1.0,
                "n": 32,
                "length": 10.0,
                "steps": 1200,
                "dt": 5e-4,
                "seed": "deterministic analytic H=1 initial condition",
                "scope": "single-seed pilot; not production",
            }
        ),
        **pilot_scan(n=32, length=10.0, mu_values=(0.0, 1.0, 5.0, 20.0), steps=1200, dt=5e-4),
        "convergence": convergence_scan(n=32, length=10.0, mu=20.0, steps_values=(300, 600, 1200), dt=5e-4),
    }
    if write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        write_json(RESULTS_DIR / "hopfion3d.json", payload)
        write_text_atomic(RESULTS_DIR / "hopfion3d.md", render_markdown(payload))
    return payload


def render_markdown(payload: dict) -> str:
    v = payload["verdict"]
    initial = payload["initial"]
    lines = [
        "# 3D E2+E4+Z3 pilot (claim 15)",
        "",
        "Single-seed pilot, N=32, L=10, dt=5e-4, 1200 gradient steps. "
        "The initial condition is the analytic H=1 map with a smooth vacuum compactification. "
        "This is not a production run and is not converged (see the convergence table).",
        "",
        f"Initial: H = {initial['H']:.9f}, Z3 = {initial['Z3']:.3e}.",
        "",
        "| mu | E2 | E4 | V | H | Z3 | monotone | max dE |",
        "|---:|---:|---:|---:|---:|---:|---|---:|",
    ]
    for row in payload["rows"]:
        lines.append(
            f"| {row['mu']:.3g} | {row['E2']:.6f} | {row['E4']:.6f} | {row['V']:.6f} | "
            f"{row['H']:.9f} | {row['Z3']:.6f} | {row['monotone']} | "
            f"{row['max_energy_increase']:+.3e} |"
        )
    convergence = payload["convergence"]
    lines += [
        "",
        "## Step-count convergence at mu=20",
        "",
        "| steps | E | H | Z3 | force RMS |",
        "|---:|---:|---:|---:|---:|",
    ]
    for row in convergence["rows"]:
        lines.append(
            f"| {row['steps']} | {row['E']:.6f} | {row['H']:.9f} | {row['Z3']:.6f} | "
            f"{row['force_rms']:.3e} |"
        )
    lines += [
        "",
        f"Converged (force RMS < 1e-2): **{convergence['converged']}**.",
        "",
        f"**Verdict:** at 1200 steps, coexistence is {v['coexistence_H_and_Z3']} as a "
        "numerical diagnostic, but the pilot is unresolved and no coexistence conclusion is drawn. "
        f"Claim 15: **{v['claim_15_status']}**.",
        "",
        v["note"],
        "",
        f"- Config SHA-256: `{payload['meta']['config_sha256']}`",
        f"- Git: `{payload['meta']['git']['commit']}` (dirty={payload['meta']['git']['dirty']})",
        "",
    ]
    return "\n".join(lines)
