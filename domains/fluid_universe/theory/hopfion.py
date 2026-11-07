"""Finite-energy H=1 configuration for the Faddeev-Niemi energy.

This is a static energy/virial check, not a relaxation and not a Z3-order run.

Energy:
    E2 = (K/2) int |grad n|^2,
    E4 = (kappa/2) int sum_{i<j} F_ij^2,
    F_ij = n . (d_i n x d_j n).

For any configuration with E2,E4 > 0, the rescaled field n(lambda x) has
E2(lambda)=lambda E2 and E4(lambda)=E4/lambda, so the Derrick virial can be
satisfied at lambda^2 = E4/E2 and E_min = 2 sqrt(E2 E4).  This says nothing
about stability under non-scale deformations.  No Hopfion solution is claimed.
"""

from __future__ import annotations

import math

import numpy as np

from domains.fluid_universe.theory.hopf import compactified_field, grid_charge, spectral_derivatives


def energies(n: int = 48, length: float = 10.0, K: float = 1.0, kappa: float = 1.0) -> dict:
    if K <= 0.0 or kappa <= 0.0:
        raise ValueError("K and kappa must be positive")
    nfield, dx = compactified_field(n, length)
    derivatives = spectral_derivatives(nfield, dx)
    gradient_squared = sum(np.sum(vector * vector, axis=-1) for vector in derivatives)
    e2 = 0.5 * K * float(np.sum(gradient_squared) * dx**3)
    f_tensor = np.empty(nfield.shape[:3] + (3, 3))
    for i in range(3):
        for j in range(3):
            f_tensor[..., i, j] = np.sum(
                nfield * np.cross(derivatives[i], derivatives[j]), axis=-1
            )
    skyrme = 0.0
    for i in range(3):
        for j in range(i + 1, 3):
            skyrme += np.sum(f_tensor[..., i, j] ** 2)
    e4 = 0.5 * kappa * float(skyrme * dx**3)
    return {
        "n": n,
        "dx": dx,
        "E2": e2,
        "E4": e4,
        "H": grid_charge(n, length),
        "lambda_star": math.sqrt(e4 / e2) if e2 > 0.0 else float("inf"),
        "virial_at_one": e2 - e4,
        "virial_ratio": (e2 - e4) / (e2 + e4) if (e2 + e4) > 0.0 else 0.0,
        "E_min": 2.0 * math.sqrt(e2 * e4) if e2 > 0.0 and e4 > 0.0 else 0.0,
    }


def scaling_study(
    sizes: tuple[int, ...] = (32, 48, 64), length: float = 10.0
) -> dict:
    rows = [energies(n=n, length=length) for n in sizes]
    return {
        "rows": rows,
        "verdict": {
            "finite_energy_H1_configuration": bool(
                all(row["E2"] > 0.0 and row["E4"] > 0.0 for row in rows)
                and abs(rows[-1]["H"] - 1.0) < 0.01
            ),
            "scaling_virial_can_be_satisfied": True,
            "full_stability_proved": False,
            "z3_order_measured": False,
            "claim_14b_status": "UNVERIFIED",
            "claim_15_status": "NOT ACHIEVED",
            "note": (
                "The analytic H=1 map has finite E2 and E4, and a scale "
                "transformation can satisfy the Derrick virial. This is not a "
                "stationary solution under non-scale deformations, not a "
                "stability proof, and not a Z3-order measurement."
            ),
        },
    }
