"""Resolution comparison for the claim-15 production scan (ADR-002).

The N=64 production scan has a native Hopf estimate below 1 while the 2x
upsampled estimate is close to 1, so one grid cannot separate a grid-scale
estimator artifact from a real failure of the configuration.  This module
compares two production payloads at the same physical time and reports whether
the native and upsampled estimates, the Z3 order, the residual force and the
field smoothness improve with resolution.

The comparison is deliberately pure: it never imports JAX or runs a scan, and it
never promotes claim 15.  The pre-registered tolerances are fixed in ADR-002.
`compare_temporal` holds the grid fixed and compares two timesteps at one
physical time, as pre-registered in ADR-003.
"""

from __future__ import annotations

H_RESOLUTION_TOL = 1.0e-2
H_TEMPORAL_TOL = 5.0e-3
Z3_RESOLUTION_TOL = 2.0e-2
Z3_TEMPORAL_TOL = 2.0e-2
_SAME_PROBLEM_KEYS = ("length", "mu", "steps", "dt")


def _require_same_problem(low: dict, high: dict) -> None:
    if low["n"] >= high["n"]:
        raise ValueError("low resolution must have the smaller n")
    for key in _SAME_PROBLEM_KEYS:
        if low[key] != high[key]:
            raise ValueError(
                "scans must solve the same physical problem: "
                f"{key} differs ({low[key]!r} != {high[key]!r})"
            )


def compare_scans(low: dict, high: dict) -> dict:
    """Compare a coarse and a fine production payload at the same physical time."""
    _require_same_problem(low, high)
    coarse = low["final"]
    fine = high["final"]

    delta_h = fine["H"] - coarse["H"]
    delta_h_up = fine["H_upsampled"] - coarse["H_upsampled"]
    delta_z3 = fine["Z3"] - coarse["Z3"]
    delta_force = fine["force_rms"] - coarse["force_rms"]
    delta_bond = fine["max_bond"] - coarse["max_bond"]

    criteria = {
        "H_agrees": abs(delta_h) <= H_RESOLUTION_TOL,
        "H_upsampled_agrees": abs(delta_h_up) <= H_RESOLUTION_TOL,
        "Z3_agrees": abs(delta_z3) <= Z3_RESOLUTION_TOL,
        "force_not_worse": delta_force <= 0.0,
        "max_bond_not_worse": delta_bond <= 0.0,
        "H_toward_one": abs(fine["H"] - 1.0) <= abs(coarse["H"] - 1.0),
        "H_upsampled_toward_one": abs(fine["H_upsampled"] - 1.0)
        <= abs(coarse["H_upsampled"] - 1.0),
    }
    resolution_converged = all(
        criteria[key]
        for key in (
            "H_agrees",
            "H_upsampled_agrees",
            "Z3_agrees",
            "force_not_worse",
            "max_bond_not_worse",
        )
    )
    return {
        "n_low": low["n"],
        "n_high": high["n"],
        "steps": high["steps"],
        "dt": high["dt"],
        "deltas": {
            "H": delta_h,
            "H_upsampled": delta_h_up,
            "Z3": delta_z3,
            "force_rms": delta_force,
            "max_bond": delta_bond,
        },
        "tolerances": {
            "H": H_RESOLUTION_TOL,
            "Z3": Z3_RESOLUTION_TOL,
        },
        "criteria": criteria,
        "resolution_converged": bool(resolution_converged),
        "claim_15_status": high["verdict"]["claim_15_status"],
        "note": (
            "Resolution convergence is a diagnostic, not claim verification: "
            "the fine run must still satisfy the unchanged production criteria."
        ),
    }


def compare_temporal(coarse: dict, fine: dict) -> dict:
    """Compare two N=64 payloads at the same physical time but different dt."""
    if coarse["n"] != fine["n"]:
        raise ValueError(
            "same n required: a dt check holds the grid fixed "
            f"({coarse['n']} != {fine['n']})"
        )
    for key in ("length", "mu"):
        if coarse[key] != fine[key]:
            raise ValueError(
                "scans must solve the same physical problem: "
                f"{key} differs ({coarse[key]!r} != {fine[key]!r})"
            )
    coarse_time = coarse["steps"] * coarse["dt"]
    fine_time = fine["steps"] * fine["dt"]
    if abs(coarse_time - fine_time) > 1e-12:
        raise ValueError(
            "scans must reach the same physical time: "
            f"{coarse_time!r} != {fine_time!r}"
        )
    if coarse["dt"] <= fine["dt"]:
        raise ValueError("coarse dt must be larger than fine dt")

    coarse_final = coarse["final"]
    fine_final = fine["final"]
    delta_h = fine_final["H"] - coarse_final["H"]
    delta_h_up = fine_final["H_upsampled"] - coarse_final["H_upsampled"]
    delta_z3 = fine_final["Z3"] - coarse_final["Z3"]
    criteria = {
        "H_agrees": abs(delta_h) <= H_TEMPORAL_TOL,
        "H_upsampled_agrees": abs(delta_h_up) <= H_TEMPORAL_TOL,
        "Z3_agrees": abs(delta_z3) <= Z3_TEMPORAL_TOL,
        "force_not_worse": fine_final["force_rms"] <= coarse_final["force_rms"],
        "max_bond_not_worse": fine_final["max_bond"] <= coarse_final["max_bond"],
    }
    temporal_converged = all(
        criteria[key] for key in ("H_agrees", "H_upsampled_agrees", "Z3_agrees")
    )
    return {
        "n": fine["n"],
        "physical_time": fine_time,
        "dt_coarse": coarse["dt"],
        "dt_fine": fine["dt"],
        "deltas": {
            "H": delta_h,
            "H_upsampled": delta_h_up,
            "Z3": delta_z3,
            "force_rms": fine_final["force_rms"] - coarse_final["force_rms"],
            "max_bond": fine_final["max_bond"] - coarse_final["max_bond"],
        },
        "tolerances": {"H": H_TEMPORAL_TOL, "Z3": Z3_TEMPORAL_TOL},
        "criteria": criteria,
        "temporal_converged": bool(temporal_converged),
        "claim_15_status": fine["verdict"]["claim_15_status"],
        "note": (
            "Temporal convergence is a diagnostic, not claim verification: "
            "if it fails, the spatial resolution comparison is confounded."
        ),
    }


def summarize_trend(
    rows: list[dict],
    z3_target: float = 0.5,
    force_tol: float = 1.0e-2,
) -> dict:
    """Summarise a multi-chunk trend and project the two claim-15 thresholds.

    The projections are linear diagnostics, not claims.  A target that is
    already met projects to zero steps; a trend moving away from the target
    projects to None.
    """
    if len(rows) < 2:
        raise ValueError("at least two rows are required for a trend")
    steps = [int(row["steps"]) for row in rows]
    times = [float(row["t"]) for row in rows]
    z3_values = [float(row["Z3"]) for row in rows]
    force_values = [float(row["force_rms"]) for row in rows]
    delta_steps = steps[-1] - steps[0]
    if delta_steps <= 0:
        raise ValueError("steps must increase between rows")

    z3_slope = (z3_values[-1] - z3_values[0]) / delta_steps
    force_slope = (force_values[-1] - force_values[0]) / delta_steps
    dt_effective = (times[-1] - times[0]) / delta_steps

    def projection(current: float, target: float, slope: float, rising: bool):
        if rising and current >= target:
            return 0.0
        if not rising and current <= target:
            return 0.0
        if (rising and slope <= 0.0) or (not rising and slope >= 0.0):
            return None
        return (target - current) / slope

    z3_steps = projection(z3_values[-1], z3_target, z3_slope, rising=True)
    force_steps = projection(force_values[-1], force_tol, force_slope, rising=False)
    return {
        "rows": len(rows),
        "steps_total": steps[-1],
        "physical_time": times[-1],
        "dt_effective": dt_effective,
        "z3_slope_per_step": z3_slope,
        "force_slope_per_step": force_slope,
        "z3_monotone": all(
            later >= earlier for earlier, later in zip(z3_values, z3_values[1:])
        ),
        "force_monotone": all(
            later <= earlier
            for earlier, later in zip(force_values, force_values[1:])
        ),
        "projected_steps_to_z3_target": z3_steps,
        "projected_time_to_z3_target": (
            None if z3_steps is None else times[-1] + z3_steps * dt_effective
        ),
        "projected_steps_to_force_tol": force_steps,
        "projected_time_to_force_tol": (
            None if force_steps is None else times[-1] + force_steps * dt_effective
        ),
        "claim_15_status": rows[-1].get("claim_15_status", ""),
        "note": (
            "Linear projections are diagnostics, not claims; claim 15 is "
            "verified only when the final state satisfies the production rule."
        ),
    }
