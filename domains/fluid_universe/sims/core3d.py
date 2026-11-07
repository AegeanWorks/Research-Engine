"""3D JAX pilot: E2 + Skyrme E4 + a Z3 azimuthal potential.

This is a single-seed pilot, not a production run.  It uses the analytic H=1
map as the initial condition, fixes nothing at the boundary beyond the smooth
compactification already present, and relaxes with gradient flow.

Potential (model choice, not derived):
    V = mu * (nx^2 + ny^2) * (1 - cos 3 phi),
    cos 3 phi = (nx^3 - 3 nx ny^2) / (nx^2 + ny^2)^(3/2).
It vanishes at the poles and has three minima in the azimuth.

The pilot finds a trade-off: larger mu increases the Z3 order parameter but
decreases the Hopf charge.  No tested mu reaches both |H| >= 1 and Z3 >= 0.5.
No production claim is made.
"""

from __future__ import annotations

import math

import jax
import jax.numpy as jnp
import numpy as np

jax.config.update("jax_enable_x64", True)

from domains.fluid_universe.theory.hopf import chern_simons_charge, compactified_field


def normalize(field: jnp.ndarray) -> jnp.ndarray:
    return field / jnp.linalg.norm(field, axis=-1, keepdims=True)


def energy_terms(
    field: jnp.ndarray,
    dx: float,
    mu: float,
    K: float = 1.0,
    kappa: float = 1.0,
) -> dict[str, jnp.ndarray]:
    n = normalize(field)
    derivatives = [
        (jnp.roll(n, -1, axis=axis) - jnp.roll(n, 1, axis=axis)) / (2.0 * dx)
        for axis in range(3)
    ]
    gradient_squared = sum(jnp.sum(vector * vector) for vector in derivatives)
    e2 = 0.5 * K * gradient_squared * dx**3
    skyrme = 0.0
    for i in range(3):
        for j in range(i + 1, 3):
            f_ij = jnp.sum(n * jnp.cross(derivatives[i], derivatives[j]), axis=-1)
            skyrme += jnp.sum(f_ij * f_ij)
    e4 = 0.5 * kappa * skyrme * dx**3
    nx, ny = n[..., 0], n[..., 1]
    rho_squared = nx * nx + ny * ny + 1e-12
    cos3 = (nx**3 - 3.0 * nx * ny * ny) / (rho_squared**1.5)
    potential = mu * jnp.sum(rho_squared * (1.0 - cos3)) * dx**3
    return {"E2": e2, "E4": e4, "V": potential, "E": e2 + e4 + potential}


def energy(field: jnp.ndarray, dx: float, K: float, kappa: float, mu: float) -> jnp.ndarray:
    return energy_terms(field, dx, mu, K, kappa)["E"]


def z3_order(field: np.ndarray) -> float:
    nx, ny = field[..., 0], field[..., 1]
    weight = nx * nx + ny * ny
    denominator = np.sum(weight)
    if denominator <= 0.0:
        return 0.0
    phase = (nx + 1j * ny) ** 3 / ((weight + 1e-12) ** 1.5)
    return float(abs(np.sum(weight * phase) / denominator))


def relax(
    field: jnp.ndarray,
    dx: float,
    mu: float,
    steps: int,
    dt: float,
    K: float = 1.0,
    kappa: float = 1.0,
    fix_boundary: bool = False,
) -> tuple[jnp.ndarray, np.ndarray, dict[str, float]]:
    if K <= 0.0 or kappa < 0.0 or mu < 0.0:
        raise ValueError("K>0, kappa>=0, mu>=0 required")
    gradient = jax.jit(jax.grad(energy, argnums=0))
    current = normalize(field)
    if fix_boundary:
        n = current.shape[0]
        mask = np.zeros((n, n, n), dtype=bool)
        mask[0, :, :] = mask[-1, :, :] = True
        mask[:, 0, :] = mask[:, -1, :] = True
        mask[:, :, 0] = mask[:, :, -1] = True
        boundary = jnp.asarray(mask)[..., None]
        vacuum = jnp.asarray([0.0, 0.0, 1.0])
    history = np.empty(steps + 1)
    history[0] = float(energy(current, dx, K, kappa, mu))
    for step in range(steps):
        update = gradient(current, dx, K, kappa, mu)
        if fix_boundary:
            update = jnp.where(boundary, 0.0, update)
        current = normalize(current - dt * update)
        history[step + 1] = float(energy(current, dx, K, kappa, mu))
    terms = energy_terms(current, dx, mu, K, kappa)
    final_gradient = gradient(current, dx, K, kappa, mu)
    result = {key: float(value) for key, value in terms.items()}
    result["force_rms"] = float(jnp.sqrt(jnp.mean(final_gradient * final_gradient)))
    return current, history, result


def gradient_check(n: int = 8, length: float = 6.0, mu: float = 1.0, eps: float = 1e-6) -> float:
    rng = np.random.default_rng(20261025)
    field = rng.normal(size=(n, n, n, 3))
    _, dx = compactified_field(n, length)
    v = jnp.asarray(field)
    analytic = jax.grad(energy, argnums=0)(v, dx, 1.0, 1.0, mu)
    index = (2, 3, 4, 1)
    plus = v.at[index].add(eps)
    minus = v.at[index].add(-eps)
    numeric = (
        energy(plus, dx, 1.0, 1.0, mu) - energy(minus, dx, 1.0, 1.0, mu)
    ) / (2.0 * eps)
    denominator = max(1.0, abs(float(analytic[index])))
    return float(abs(float(numeric) - float(analytic[index])) / denominator)


def convergence_scan(
    n: int = 32,
    length: float = 10.0,
    mu: float = 20.0,
    steps_values: tuple[int, ...] = (300, 600, 1200),
    dt: float = 5.0e-4,
) -> dict:
    """Show that the N=32 pilot is not converged in step count."""
    initial, dx = compactified_field(n, length)
    rows = []
    for steps in steps_values:
        relaxed, history, terms = relax(jnp.asarray(initial), dx, mu, steps, dt)
        field = np.asarray(relaxed)
        rows.append(
            {
                "steps": steps,
                "E": float(history[-1]),
                "H": chern_simons_charge(field, dx),
                "Z3": z3_order(field),
                "force_rms": terms["force_rms"],
            }
        )
    return {
        "n": n,
        "length": length,
        "mu": mu,
        "dt": dt,
        "rows": rows,
        "converged": bool(rows[-1]["force_rms"] < 1e-2),
        "resolution_note": (
            "N=32 is resolution-limited for H: a manual N=64 check gives different "
            "values. No H or Z3 claim is drawn from this scan."
        ),
    }


def pilot_scan(
    n: int = 32,
    length: float = 10.0,
    mu_values: tuple[float, ...] = (0.0, 1.0, 5.0, 20.0),
    steps: int = 300,
    dt: float = 5.0e-4,
) -> dict:
    initial, dx = compactified_field(n, length)
    field = jnp.asarray(initial)
    initial_h = chern_simons_charge(initial, dx)
    initial_z3 = z3_order(initial)
    rows = []
    for mu in mu_values:
        relaxed, history, terms = relax(field, dx, mu, steps, dt)
        field_np = np.asarray(relaxed)
        rows.append(
            {
                "mu": mu,
                "E2": terms["E2"],
                "E4": terms["E4"],
                "V": terms["V"],
                "E_initial": float(history[0]),
                "E_final": float(history[-1]),
                "max_energy_increase": float(np.max(np.diff(history))),
                "monotone": bool(np.all(np.diff(history) <= 1e-8)),
                "H": chern_simons_charge(field_np, dx),
                "Z3": z3_order(field_np),
                "force_rms": terms["force_rms"],
            }
        )
    coexistence = any(row["H"] >= 1.0 and row["Z3"] >= 0.5 for row in rows)
    max_z3_row = max(rows, key=lambda row: row["Z3"])
    return {
        "n": n,
        "length": length,
        "dx": dx,
        "steps": steps,
        "dt": dt,
        "mu_values": list(mu_values),
        "initial": {"H": initial_h, "Z3": initial_z3},
        "rows": rows,
        "verdict": {
            "single_seed_pilot": True,
            "coexistence_H_and_Z3": coexistence,
            "max_Z3": max_z3_row["Z3"],
            "H_at_max_Z3": max_z3_row["H"],
            "mu_at_max_Z3": max_z3_row["mu"],
            "production_ready": False,
            "resolved": False,
            "claim_15_status": "UNVERIFIED (resolution-limited pilot; no conclusion)",
            "note": (
                "The N=32 pilot is not converged: H and Z3 change with step count and "
                "resolution (a manual N=64 check gives different values). The 300-step "
                "trade-off is transient. No coexistence conclusion is drawn; this is not "
                "a production or spontaneous-order claim."
            ),
        },
    }
