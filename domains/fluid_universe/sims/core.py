"""Validated 1D core for the Z3 sine-Gordon sector.

This is the first simulation baseline, not a 3D Hopfion run.  It implements the
1D energy

    E = int dx [ 1/2 (d phi/dx)^2 + mu (1 - cos 3 phi) ]

on a finite interval with Dirichlet boundary values taken from the analytic
kink.  The analytic kink is

    phi(x) = (4/3) arctan(exp(3 sqrt(mu) (x - x0))),

with tension T = (8/3) sqrt(mu).

Baselines implemented here:
  1. kink profile and tension convergence,
  2. analytic force vs finite difference of the discrete energy,
  3. monotone energy decrease under gradient flow,
  6. rotor Fourier spectrum vs a finite-difference grid,
  7. Hessian symmetry and stability (zero-mode counting is not yet implemented).

No production or 3D result is produced.
"""

from __future__ import annotations

import math

import numpy as np
from scipy.optimize import minimize


def grid(length: float, n: int) -> tuple[np.ndarray, float]:
    if length <= 0.0 or n < 3:
        raise ValueError("length must be positive and n >= 3")
    x = np.linspace(-0.5 * length, 0.5 * length, n)
    dx = length / (n - 1)
    return x, dx


def potential(phi: np.ndarray | float, mu: float) -> np.ndarray:
    phi = np.asarray(phi, dtype=float)
    return mu * (1.0 - np.cos(3.0 * phi))


def potential_prime(phi: np.ndarray | float, mu: float) -> np.ndarray:
    phi = np.asarray(phi, dtype=float)
    return 3.0 * mu * np.sin(3.0 * phi)


def potential_second(phi: np.ndarray | float, mu: float) -> np.ndarray:
    phi = np.asarray(phi, dtype=float)
    return 9.0 * mu * np.cos(3.0 * phi)


def analytic_kink(x: np.ndarray, mu: float, x0: float = 0.0) -> np.ndarray:
    if mu <= 0.0:
        raise ValueError("mu must be positive for a kink")
    x = np.asarray(x, dtype=float)
    return (4.0 / 3.0) * np.arctan(np.exp(3.0 * math.sqrt(mu) * (x - x0)))


def kink_tension(mu: float) -> float:
    if mu < 0.0:
        raise ValueError("mu must be non-negative")
    return (8.0 / 3.0) * math.sqrt(mu)


def energy(phi: np.ndarray, dx: float, mu: float) -> float:
    phi = np.asarray(phi, dtype=float)
    gradient = np.diff(phi) / dx
    values = potential(phi, mu)
    integral = dx * (0.5 * values[0] + np.sum(values[1:-1]) + 0.5 * values[-1])
    return float(0.5 * dx * np.sum(gradient * gradient) + integral)


def force(phi: np.ndarray, dx: float, mu: float) -> np.ndarray:
    """- (1/dx) dE/dphi on interior nodes; boundaries are fixed."""
    phi = np.asarray(phi, dtype=float)
    out = np.zeros_like(phi)
    out[1:-1] = (
        (phi[2:] - 2.0 * phi[1:-1] + phi[:-2]) / dx**2
        - potential_prime(phi[1:-1], mu)
    )
    return out


def gradient_error(phi: np.ndarray, dx: float, mu: float, eps: float = 1e-6) -> float:
    """Max relative error between the analytic force and a central difference."""
    phi = np.asarray(phi, dtype=float).copy()
    analytic = force(phi, dx, mu)
    errors = []
    for index in range(2, phi.size - 2, 7):
        original = phi[index]
        phi[index] = original + eps
        plus = energy(phi, dx, mu)
        phi[index] = original - eps
        minus = energy(phi, dx, mu)
        phi[index] = original
        numeric = -(plus - minus) / (2.0 * eps * dx)
        scale = max(1.0, abs(analytic[index]))
        errors.append(abs(numeric - analytic[index]) / scale)
    return float(max(errors)) if errors else 0.0


def gradient_flow(
    phi: np.ndarray,
    dx: float,
    mu: float,
    dt: float,
    steps: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Explicit Euler flow dphi/dt = force; boundaries fixed."""
    phi = np.asarray(phi, dtype=float).copy()
    energies = np.empty(steps + 1)
    energies[0] = energy(phi, dx, mu)
    for step in range(steps):
        update = force(phi, dx, mu)
        phi[1:-1] += dt * update[1:-1]
        energies[step + 1] = energy(phi, dx, mu)
    return phi, energies


def relax_kink(
    phi: np.ndarray, dx: float, mu: float, tolerance: float = 1e-12
) -> tuple[np.ndarray, dict]:
    """Minimise the discrete energy on interior nodes (L-BFGS-B)."""
    phi = np.asarray(phi, dtype=float).copy()
    initial = phi[1:-1].copy()

    def objective(values: np.ndarray) -> float:
        trial = phi.copy()
        trial[1:-1] = values
        return energy(trial, dx, mu)

    def gradient(values: np.ndarray) -> np.ndarray:
        trial = phi.copy()
        trial[1:-1] = values
        return -dx * force(trial, dx, mu)[1:-1]

    result = minimize(
        objective,
        initial,
        jac=gradient,
        method="L-BFGS-B",
        options={"gtol": tolerance, "ftol": 1e-15, "maxiter": 5000},
    )
    phi[1:-1] = result.x
    return phi, {
        "success": bool(result.success),
        "message": str(result.message),
        "iterations": int(result.nit),
        "energy": float(result.fun),
        "force_max": float(np.max(np.abs(force(phi, dx, mu)))),
    }


def hessian(phi: np.ndarray, dx: float, mu: float) -> np.ndarray:
    """Hessian of E/dx on interior nodes (Dirichlet boundaries)."""
    phi = np.asarray(phi, dtype=float)
    interior = phi[1:-1]
    size = interior.size
    matrix = np.diag(np.full(size, 2.0 / dx**2) + potential_second(interior, mu))
    off = np.full(size - 1, -1.0 / dx**2)
    matrix += np.diag(off, 1) + np.diag(off, -1)
    return matrix


def kink_convergence(
    mu: float = 1.0,
    length: float = 30.0,
    sizes: tuple[int, ...] = (201, 401, 801, 1601),
) -> dict:
    tension = kink_tension(mu)
    rows = []
    for n in sizes:
        x, dx = grid(length, n)
        phi = analytic_kink(x, mu)
        value = energy(phi, dx, mu)
        rows.append(
            {
                "n": n,
                "dx": dx,
                "energy": value,
                "error_vs_tension": value - tension,
                "relative_error": (value - tension) / tension,
            }
        )
    orders = []
    for first, second in zip(rows, rows[1:]):
        numerator = abs(first["error_vs_tension"])
        denominator = abs(second["error_vs_tension"])
        ratio = numerator / denominator if denominator else float("inf")
        orders.append(math.log2(ratio) if ratio > 0.0 else float("nan"))
    return {"tension": tension, "rows": rows, "observed_orders": orders}


def rotor_crosscheck() -> dict:
    from domains.fluid_universe.theory.rotor import grid_spectrum, spectrum

    exact = spectrum(I=1.0, mu=1.0, n_cutoff=120)
    grid_values = grid_spectrum(I=1.0, mu=1.0, n_grid=2048, count=3)
    return {
        "E0_fourier": float(exact.lowest(0, 1)[0]),
        "E0_grid": float(grid_values[0]),
        "E1_fourier": float(exact.lowest(1, 1)[0]),
        "E1_grid": float(grid_values[1]),
        "abs_delta_E0": abs(float(exact.lowest(0, 1)[0]) - float(grid_values[0])),
        "abs_delta_E1": abs(float(exact.lowest(1, 1)[0]) - float(grid_values[1])),
    }
