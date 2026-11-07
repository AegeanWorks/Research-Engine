"""Targeted N=64 diagnostic for the 3D E2+E4+Z3 pilot.

This is deliberately separate from the fast canonical results: it takes several
minutes.  It uses fixed vacuum boundaries and reports the H/Z3 trend at N=64.
It is still not a production run and does not claim convergence.
"""

from __future__ import annotations

import numpy as np

from domains.fluid_universe.sims.core3d import relax, z3_order
from domains.fluid_universe.theory.hopf import chern_simons_charge, compactified_field

from .provenance import RESULTS_DIR, metadata, write_json, write_text_atomic


def run_n64_check(write: bool = True) -> dict:
    n = 64
    length = 10.0
    initial, dx = compactified_field(n, length)
    rows = []
    for mu, steps in ((0.0, 1200), (20.0, 1200), (20.0, 2400), (20.0, 3600)):
        relaxed, history, terms = relax(
            initial, dx, mu, steps, 5e-4, fix_boundary=True
        )
        field = np.asarray(relaxed)
        rows.append(
            {
                "mu": mu,
                "steps": steps,
                "E2": terms["E2"],
                "E4": terms["E4"],
                "V": terms["V"],
                "E": terms["E"],
                "H": chern_simons_charge(field, dx),
                "Z3": z3_order(field),
                "force_rms": terms["force_rms"],
                "monotone": bool(np.all(np.diff(history) <= 1e-8)),
            }
        )
    coexistence = any(row["H"] >= 1.0 and row["Z3"] >= 0.5 for row in rows)
    payload = {
        "meta": metadata(
            {
                "n": n,
                "length": length,
                "dt": 5e-4,
                "mu_steps": [[0.0, 1200], [20.0, 1200], [20.0, 2400], [20.0, 3600]],
                "boundary": "fixed vacuum faces",
                "scope": "targeted diagnostic; not part of make results; not production",
            }
        ),
        "rows": rows,
        "verdict": {
            "coexistence_H_and_Z3": coexistence,
            "converged": bool(all(row["force_rms"] < 1e-2 for row in rows)),
            "production_ready": False,
            "claim_15_status": "UNVERIFIED (N=64 diagnostic; not converged)",
            "note": (
                "At N=64 the H/Z3 trend is resolved better than N=32, but the "
                "force RMS is still above 1e-2 at 3600 steps. No coexistence is "
                "seen; no production or spontaneous-order claim."
            ),
        },
    }
    if write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        write_json(RESULTS_DIR / "hopfion3d_n64.json", payload)
        write_text_atomic(RESULTS_DIR / "hopfion3d_n64.md", render_markdown(payload))
    return payload


def render_markdown(payload: dict) -> str:
    v = payload["verdict"]
    lines = [
        "# Targeted N=64 3D diagnostic (claim 15)",
        "",
        "Fixed vacuum boundaries, dt=5e-4. This is a diagnostic, not part of `make results`.",
        "",
        "| mu | steps | E | H | Z3 | force RMS | monotone |",
        "|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in payload["rows"]:
        lines.append(
            f"| {row['mu']:.3g} | {row['steps']} | {row['E']:.6f} | {row['H']:.9f} | "
            f"{row['Z3']:.6f} | {row['force_rms']:.3e} | {row['monotone']} |"
        )
    lines += [
        "",
        f"**Verdict:** coexistence: **{v['coexistence_H_and_Z3']}**; "
        f"converged: **{v['converged']}**; claim 15: **{v['claim_15_status']}**.",
        "",
        v["note"],
        "",
        f"- Config SHA-256: `{payload['meta']['config_sha256']}`",
        f"- Git: `{payload['meta']['git']['commit']}` (dirty={payload['meta']['git']['dirty']})",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    print(run_n64_check()["verdict"])
