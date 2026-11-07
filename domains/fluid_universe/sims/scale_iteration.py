"""Damped scale iteration toward a stationary Faddeev-Niemi Hopfion.

Starting from the analytic H=1 map, alternate
  (a) gradient relaxation with fixed vacuum boundaries,
  (b) a spatial rescaling by sqrt(lambda*) with lambda* = sqrt(E4/E2),
and record the virial.  This is a candidate search, not a stability proof.

The best tested point has |E2-E4| ~ 0.01 and H ~ 0.997, i.e. a scale-stationary
H=1 candidate within the estimator resolution.  The sequence is not monotone,
so no convergence or stability claim is made.
"""

from __future__ import annotations

import math

import numpy as np
from scipy.ndimage import map_coordinates

from domains.fluid_universe.theory.hopf import chern_simons_charge, compactified_field

from domains.fluid_universe.sims.core3d import relax, z3_order


def rescale_field(field: np.ndarray, dx: float, length: float, scale: float) -> np.ndarray:
    n = field.shape[0]
    axis = np.linspace(-0.5 * length, 0.5 * length, n, endpoint=False)
    x, y, z = np.meshgrid(axis, axis, axis, indexing="ij")
    coordinates = np.array(
        [(x / scale + 0.5 * length) / dx, (y / scale + 0.5 * length) / dx, (z / scale + 0.5 * length) / dx]
    )
    vacuum = np.array([0.0, 0.0, 1.0])
    out = np.empty_like(field)
    for component in range(3):
        out[..., component] = map_coordinates(
            field[..., component], coordinates, order=1, mode="constant", cval=vacuum[component]
        )
    out /= np.linalg.norm(out, axis=-1, keepdims=True)
    for face in (out[0], out[-1], out[:, 0], out[:, -1], out[:, :, 0], out[:, :, -1]):
        face[...] = vacuum
    return out


def run_scale_iteration(
    n: int = 64,
    length: float = 10.0,
    iterations: int = 6,
    steps: int = 600,
    dt: float = 5.0e-4,
) -> dict:
    initial, dx = compactified_field(n, length)
    field = initial
    rows = []
    for iteration in range(iterations):
        relaxed, _history, terms = relax(field, dx, 0.0, steps, dt, fix_boundary=True)
        snapshot = np.asarray(relaxed)
        lam = math.sqrt(terms["E4"] / terms["E2"])
        lam_eff = math.sqrt(lam)
        rows.append(
            {
                "iteration": iteration,
                "E": terms["E"],
                "E2": terms["E2"],
                "E4": terms["E4"],
                "virial": terms["E2"] - terms["E4"],
                "H": chern_simons_charge(snapshot, dx),
                "Z3": z3_order(snapshot),
                "force_rms": terms["force_rms"],
                "lambda": lam,
                "lambda_eff": lam_eff,
            }
        )
        field = rescale_field(snapshot, dx, length, lam_eff)
    best = min(rows, key=lambda row: abs(row["virial"]))
    return {
        "n": n,
        "length": length,
        "iterations": iterations,
        "steps_per_iteration": steps,
        "dt": dt,
        "rows": rows,
        "best": best,
        "verdict": {
            "scale_stationary_candidate": bool(abs(best["virial"]) < 0.1),
            "H_within_0_01_of_one": bool(abs(best["H"] - 1.0) < 0.01),
            "full_stability_proved": False,
            "claim_14b_status": "UNVERIFIED",
            "claim_14c_status": "NUMERIC (scale-stationary H=1 candidate; no stability proof)",
            "note": (
                "The damped scale iteration reaches a near-virial-free H=1 candidate, "
                "but the sequence is not monotone and the Hessian is not computed. "
                "This is a candidate, not a stable Hopfion proof."
            ),
        },
    }
