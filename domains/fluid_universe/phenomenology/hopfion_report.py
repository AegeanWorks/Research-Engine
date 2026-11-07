"""Static finite-energy H=1 configuration report."""

from __future__ import annotations

from domains.fluid_universe.theory.hopfion import scaling_study

from .provenance import RESULTS_DIR, metadata, write_json, write_text_atomic


def run_hopfion_check(write: bool = True) -> dict:
    payload = {
        "meta": metadata(
            {
                "K": 1.0,
                "kappa": 1.0,
                "length": 10.0,
                "sizes": [32, 48, 64],
                "model": "Faddeev-Niemi E2 + Skyrme E4, V=0",
            }
        ),
        **scaling_study(sizes=(32, 48, 64), length=10.0),
    }
    if write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        write_json(RESULTS_DIR / "hopfion.json", payload)
        write_text_atomic(RESULTS_DIR / "hopfion.md", render_markdown(payload))
    return payload


def render_markdown(payload: dict) -> str:
    v = payload["verdict"]
    lines = [
        "# Finite-energy H=1 configuration (claim 14b, static)",
        "",
        "Faddeev-Niemi energy E2 + Skyrme E4 with V=0, analytic H=1 map, "
        "smooth vacuum compactification. This is not a relaxation and not a Z3 run.",
        "",
        "| N | E2 | E4 | H | lambda* | (E2-E4)/(E2+E4) | E_min |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in payload["rows"]:
        lines.append(
            f"| {row['n']} | {row['E2']:.9f} | {row['E4']:.9f} | {row['H']:.9f} | "
            f"{row['lambda_star']:.6f} | {row['virial_ratio']:+.6f} | {row['E_min']:.9f} |"
        )
    lines += [
        "",
        f"**Verdict:** finite-energy H=1 configuration: **{v['finite_energy_H1_configuration']}**; "
        f"scaling virial can be satisfied: **{v['scaling_virial_can_be_satisfied']}**; "
        f"full stability: **{v['full_stability_proved']}**; "
        f"Z3 order measured: **{v['z3_order_measured']}**.",
        "",
        f"Claim 14b: **{v['claim_14b_status']}**; claim 15: **{v['claim_15_status']}**.",
        "",
        v["note"],
        "",
        f"- Config SHA-256: `{payload['meta']['config_sha256']}`",
        f"- Git: `{payload['meta']['git']['commit']}` (dirty={payload['meta']['git']['dirty']})",
        "",
    ]
    return "\n".join(lines)
