"""Report for the damped scale-iteration candidate."""

from __future__ import annotations

from domains.fluid_universe.sims.scale_iteration import run_scale_iteration

from .provenance import RESULTS_DIR, metadata, write_json, write_text_atomic


def run_scale_check(write: bool = True) -> dict:
    payload = {
        "meta": metadata(
            {
                "n": 64,
                "length": 10.0,
                "iterations": 6,
                "steps_per_iteration": 600,
                "dt": 5e-4,
                "damping": "sqrt(lambda*)",
                "scope": "candidate search; not part of make results; not stability proof",
            }
        ),
        **run_scale_iteration(),
    }
    if write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        write_json(RESULTS_DIR / "hopfion_scale.json", payload)
        write_text_atomic(RESULTS_DIR / "hopfion_scale.md", render_markdown(payload))
    return payload


def render_markdown(payload: dict) -> str:
    v = payload["verdict"]
    best = payload["best"]
    lines = [
        "# Damped scale iteration (claim 14b/14c)",
        "",
        "N=64, 600 steps per iteration, fixed vacuum boundaries. "
        "A candidate search, not a stability proof.",
        "",
        "| iter | E | E2-E4 | H | Z3 | force RMS | lambda |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in payload["rows"]:
        lines.append(
            f"| {row['iteration']} | {row['E']:.6f} | {row['virial']:+.6f} | "
            f"{row['H']:.9f} | {row['Z3']:.6f} | {row['force_rms']:.3e} | {row['lambda']:.6f} |"
        )
    lines += [
        "",
        f"Best |virial| at iteration {best['iteration']}: virial = {best['virial']:+.6f}, "
        f"H = {best['H']:.9f}, force RMS = {best['force_rms']:.3e}.",
        "",
        f"Scale-stationary candidate: **{v['scale_stationary_candidate']}**; "
        f"H within 0.01 of 1: **{v['H_within_0_01_of_one']}**; "
        f"full stability: **{v['full_stability_proved']}**.",
        "",
        f"Claim 14b: **{v['claim_14b_status']}**; "
        f"claim 14c: **{v['claim_14c_status']}**.",
        "",
        v["note"],
        "",
        f"- Config SHA-256: `{payload['meta']['config_sha256']}`",
        f"- Git: `{payload['meta']['git']['commit']}` (dirty={payload['meta']['git']['dirty']})",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    print(run_scale_check()["verdict"])
