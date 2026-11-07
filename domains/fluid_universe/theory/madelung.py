"""Madelung fluid dictionary for the Schrodinger equation (claim 20, ADR-011).

Writing psi = sqrt(rho) exp(i S / hbar) turns

    i hbar d_t psi = -hbar^2/(2m) d_x^2 psi + V psi

into a continuity equation and an Euler equation with the quantum pressure

    Q = -hbar^2/(2m) (d_x^2 sqrt(rho)) / sqrt(rho).

The quantum pressure is nonlocal and singular at nodes, so the dictionary is
integrated in its equivalent Schrodinger form with a split-step Fourier method.
The fluid fields and residuals are then checked against exact Gaussian
solutions.  This is an exact representation, not a microphysical derivation.
"""

from __future__ import annotations

import math

import numpy as np

_FLOOR = 1e-30


def _wave_numbers(n: int, dx: float) -> np.ndarray:
    return 2.0 * math.pi * np.fft.fftfreq(n, d=dx)


def _derivative(values: np.ndarray, k: np.ndarray) -> np.ndarray:
    return np.fft.ifft(1.0j * k * np.fft.fft(values)).real


def split_step(
    psi: np.ndarray,
    potential,
    dt: float,
    steps: int,
    dx: float,
    hbar: float = 1.0,
    mass: float = 1.0,
) -> np.ndarray:
    """Strang split-step integration of the equivalent Schrodinger equation."""
    if dt <= 0.0:
        raise ValueError("dt must be positive")
    if steps < 0:
        raise ValueError("steps must be non-negative")
    if hbar <= 0.0 or mass <= 0.0:
        raise ValueError("hbar and mass must be positive")
    n = psi.size
    k = _wave_numbers(n, dx)
    kinetic = np.exp(-0.5j * hbar * k * k * dt / mass)
    potential = np.asarray(potential, dtype=float)
    if potential.ndim == 0:
        half_potential = np.exp(-0.5j * float(potential) * dt / hbar)
    else:
        half_potential = np.exp(-0.5j * potential * dt / hbar)
    current = np.asarray(psi, dtype=complex)
    for _ in range(steps):
        current = half_potential * current
        current = np.fft.ifft(kinetic * np.fft.fft(current))
        current = half_potential * current
    return current


def fluid_fields(
    psi: np.ndarray, dx: float, hbar: float = 1.0, mass: float = 1.0
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return density, velocity and quantum pressure of a wavefunction."""
    if hbar <= 0.0 or mass <= 0.0:
        raise ValueError("hbar and mass must be positive")
    psi = np.asarray(psi, dtype=complex)
    n = psi.size
    k = _wave_numbers(n, dx)
    rho = np.abs(psi) ** 2
    dpsi = np.fft.ifft(1.0j * k * np.fft.fft(psi))
    velocity = (hbar / mass) * np.imag(np.conj(psi) * dpsi) / np.maximum(rho, _FLOOR)
    safe = np.maximum(rho, _FLOOR)
    rho_x = _derivative(safe, k)
    rho_xx = _derivative(rho_x, k)
    quantum = -(hbar * hbar) / (2.0 * mass) * (
        rho_xx / (2.0 * safe) - rho_x * rho_x / (4.0 * safe * safe)
    )
    return rho, velocity, quantum


def free_gaussian_density(
    x: np.ndarray,
    t: float,
    sigma: float,
    hbar: float = 1.0,
    mass: float = 1.0,
) -> np.ndarray:
    if sigma <= 0.0:
        raise ValueError("sigma must be positive")
    width = sigma * math.sqrt(1.0 + (hbar * t / (2.0 * mass * sigma * sigma)) ** 2)
    return np.exp(-x * x / (2.0 * width * width)) / (
        math.sqrt(2.0 * math.pi) * width
    )


def coherent_state_density(
    x: np.ndarray,
    t: float,
    x0: float,
    omega: float = 1.0,
    hbar: float = 1.0,
    mass: float = 1.0,
) -> np.ndarray:
    if omega <= 0.0:
        raise ValueError("omega must be positive")
    sigma = math.sqrt(hbar / (2.0 * mass * omega))
    center = x0 * math.cos(omega * t)
    return np.exp(-((x - center) ** 2) / (2.0 * sigma * sigma)) / (
        math.sqrt(2.0 * math.pi) * sigma
    )


def continuity_residual(
    psi0: np.ndarray,
    psi1: np.ndarray,
    dt: float,
    dx: float,
    hbar: float = 1.0,
    mass: float = 1.0,
) -> float:
    rho0, v0, _ = fluid_fields(psi0, dx, hbar, mass)
    rho1, v1, _ = fluid_fields(psi1, dx, hbar, mass)
    k = _wave_numbers(psi0.size, dx)
    rho = 0.5 * (rho0 + rho1)
    velocity = 0.5 * (v0 + v1)
    time_derivative = (rho1 - rho0) / dt
    residual = time_derivative + _derivative(rho * velocity, k)
    scale = max(float(np.max(np.abs(time_derivative))), 1e-12)
    return float(np.max(np.abs(residual)) / scale)


def free_gaussian_fields(
    x: np.ndarray,
    t: float,
    sigma: float,
    hbar: float = 1.0,
    mass: float = 1.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Exact density, velocity and quantum pressure of a free Gaussian."""
    if sigma <= 0.0:
        raise ValueError("sigma must be positive")
    tau = hbar * t / (2.0 * mass * sigma * sigma)
    width = sigma * math.sqrt(1.0 + tau * tau)
    rho = np.exp(-x * x / (2.0 * width * width)) / (
        math.sqrt(2.0 * math.pi) * width
    )
    velocity = (hbar / mass) * tau / (2.0 * sigma * sigma * (1.0 + tau * tau)) * x
    quantum = (hbar * hbar) / (4.0 * mass * width * width) * (
        1.0 - x * x / (2.0 * width * width)
    )
    return rho, velocity, quantum


def euler_residual_fields(
    rho0: np.ndarray,
    v0: np.ndarray,
    q0: np.ndarray,
    rho1: np.ndarray,
    v1: np.ndarray,
    q1: np.ndarray,
    dt: float,
    dx: float,
    potential=0.0,
    mass: float = 1.0,
    density_floor: float = 1e-3,
) -> float:
    """Relative Euler residual on the core where the density is resolved."""
    if dt <= 0.0 or mass <= 0.0:
        raise ValueError("dt and mass must be positive")
    k = _wave_numbers(rho0.size, dx)
    rho = 0.5 * (rho0 + rho1)
    velocity = 0.5 * (v0 + v1)
    quantum = 0.5 * (q0 + q1)
    time_derivative = (v1 - v0) / dt
    advection = -velocity * _derivative(velocity, k)
    force = -_derivative(quantum, k) / mass
    potential = np.asarray(potential, dtype=float)
    if potential.ndim > 0:
        force -= _derivative(potential, k) / mass
    residual = time_derivative - (advection + force)
    mask = rho > density_floor * float(np.max(rho))
    scale = max(
        float(np.max(np.abs(time_derivative[mask]))),
        float(np.max(np.abs(advection[mask]))),
        float(np.max(np.abs(force[mask]))),
        1e-12,
    )
    return float(np.max(np.abs(residual[mask])) / scale)
