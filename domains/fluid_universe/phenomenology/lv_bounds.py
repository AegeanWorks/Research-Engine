"""Residual anisotropy and Lorentz-violation bounds (claims 11-12)."""

from __future__ import annotations

from domains.fluid_universe.theory.lorentz import (
    BOUNDS,
    axis_speeds,
    conditional_bound,
    residual_anisotropy,
    verdict,
)

from .provenance import RESULTS_DIR, metadata, write_json, write_text_atomic


def run_lorentz_check(write: bool = True) -> dict:
    equal = residual_anisotropy(2.0, 2.0, 2.0)
    unequal = residual_anisotropy(1.0, 2.0, 3.0)
    payload = {
        "meta": metadata(
            {
                "equal_K": [2.0, 2.0, 2.0],
                "unequal_K": [1.0, 2.0, 3.0],
                "rho": 1.0,
                "n_samples": equal["n_samples"],
                "seed": equal["seed"],
                "bounds": "order-of-magnitude experimental limits; see theory/lorentz.py",
            }
        ),
        "axis_speeds_equal": axis_speeds(2.0, 2.0, 2.0),
        "axis_speeds_unequal": axis_speeds(1.0, 2.0, 3.0),
        "anisotropy_equal": equal,
        "anisotropy_unequal": unequal,
        "bounds": BOUNDS,
        "conditional_unequal": conditional_bound(1.0, 2.0, 3.0),
        "verdict_equal": verdict(2.0, 2.0, 2.0),
        "verdict_unequal": verdict(1.0, 2.0, 3.0),
    }
    if write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        write_json(RESULTS_DIR / "lorentz.json", payload)
        write_text_atomic(RESULTS_DIR / "lorentz.md", render_markdown(payload))
    return payload


def render_markdown(payload: dict) -> str:
    equal = payload["anisotropy_equal"]
    unequal = payload["anisotropy_unequal"]
    v = payload["verdict_unequal"]
    lines = [
        "# Residual anisotropy and Lorentz-violation bounds (claims 11-12)",
        "",
        "The two transverse director modes have direction-dependent speeds unless "
        "K1=K2=K3. The residual anisotropy is "
        "xi = (c_max^2 - c_min^2)/mean(c^2), sampled over 4000 directions.",
        "",
        "| K | xi | c2 min | c2 max |",
        "|---|---:|---:|---:|",
        f"| (2,2,2) | {equal['xi']:.3e} | {equal['c2_min']:.6f} | {equal['c2_max']:.6f} |",
        f"| (1,2,3) | {unequal['xi']:.6f} | {unequal['c2_min']:.6f} | {unequal['c2_max']:.6f} |",
        "",
        "## Experimental limits",
        "",
        "| bound | quantity | order | applies directly? | why |",
        "|---|---|---:|---|---|",
    ]
    for bound in payload["bounds"]:
        lines.append(
            f"| {bound['name']} | {bound['quantity']} | {bound['limit_order']} | "
            f"{bound['applies_to_director_modes']} | {bound['why']} |"
        )
    lines += [
        "",
        "## Conditional check",
        "",
        "If a model identified the director modes with photons with O(1) coupling:",
        "",
        "| bound | limit | xi (K=1,2,3) | passes? |",
        "|---|---:|---:|---|",
    ]
    for check in payload["conditional_unequal"]["checks"]:
        lines.append(
            f"| {check['name']} | {check['limit']:.0e} | {check['xi']:.6f} | "
            f"{check['passes_if_photon']} |"
        )
    lines += [
        "",
        f"**Verdict.** Emergent metric at tree level: **{v['11a_emergent_metric_at_tree_level']}**. "
        f"One-loop RG to a Lorentz-invariant IR point: **{v['11b_one_loop_RG_to_Lorentz_invariant_IR']}**. "
        f"Direct application of photon bounds: **{v['12_lv_bounds_directly_applicable']}**. "
        f"Conditional equal-K pass: **{v['12_equal_K_is_isotropic']}**; "
        f"conditional O(1) anisotropy excluded: **{v['12_conditional_xi_above_grb_bound']}**.",
        "",
        v["note"],
        "",
        f"- Config SHA-256: `{payload['meta']['config_sha256']}`",
        f"- Git: `{payload['meta']['git']['commit']}` (dirty={payload['meta']['git']['dirty']})",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    result = run_lorentz_check()
    print(result["verdict_unequal"])
