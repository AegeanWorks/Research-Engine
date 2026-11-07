"""Nelson stochastic kinematics for the quantum fluid (claim 21, ADR-012).

A Brownian particle with diffusion D = hbar/(2m) has the osmotic velocity

    u = D d_x ln(rho).

For the harmonic-oscillator ground state u = -omega x, so the stochastic
process is an Ornstein-Uhlenbeck process with variance hbar/(2 m omega).  For a
free Gaussian packet the exact density and current velocity give the forward
drift b_+ = v + u.

The drift uses the exact quantum density: this validates the stochastic
kinematics, not a self-consistent derivation of the density.
"""

from __future__ import annotations

import math

import numpy as np

from domains.fluid_universe.theory.madelung import free_gaussian_density


def ground_state_width(omega: float, hbar: float = 1.0, mass: float = 1.0) -> float:
    if omega <= 0.0 or hbar <= 0.0 or mass <= 0.0:
        raise ValueError("omega, hbar and mass must be positive")
    return math.sqrt(hbar / (2.0 * mass * omega))


def ground_state_density(
    x: np.ndarray, omega: float, hbar: float = 1.0, mass: float = 1.0
) -> np.ndarray:
    width = ground_state_width(omega, hbar, mass)
    return np.exp(-(x * x) / (2.0 * width * width)) / (
        math.sqrt(2.0 * math.pi) * width
    )


def osmotic_velocity(
    rho: np.ndarray, dx: float, hbar: float = 1.0, mass: float = 1.0
) -> np.ndarray:
    if dx <= 0.0:
        raise ValueError("dx must be positive")
    safe = np.maximum(np.asarray(rho, dtype=float), 1e-300)
    gradient = np.gradient(np.log(safe), dx)
    return (hbar / (2.0 * mass)) * gradient


def simulate_ou(
    particles: int,
    omega: float,
    hbar: float = 1.0,
    mass: float = 1.0,
    dt: float = 1e-3,
    steps: int = 1000,
    seed: int = 20261030,
) -> np.ndarray:
    """Euler-Maruyama for dX = -omega X dt + sqrt(hbar/m) dW."""
    if particles < 1 or steps < 1 or dt <= 0.0:
        raise ValueError("particles, steps and dt must be positive")
    rng = np.random.default_rng(seed)
    x = rng.normal(scale=ground_state_width(omega, hbar, mass), size=particles)
    noise_scale = math.sqrt(hbar / mass * dt)
    for _ in range(steps):
        x += -omega * x * dt + noise_scale * rng.standard_normal(particles)
    return x


def free_packet_drift(
    x: np.ndarray,
    t: float,
    sigma: float,
    hbar: float = 1.0,
    mass: float = 1.0,
) -> np.ndarray:
    """Forward drift b_+ = v + D d_x ln(rho) for the free Gaussian."""
    if sigma <= 0.0:
        raise ValueError("sigma must be positive")
    tau = hbar * t / (2.0 * mass * sigma * sigma)
    width = sigma * math.sqrt(1.0 + tau * tau)
    velocity = (hbar / mass) * tau / (2.0 * sigma * sigma * (1.0 + tau * tau)) * x
    osmotic = -(hbar / (2.0 * mass)) * x / (width * width)
    return velocity + osmotic


def simulate_free_packet(
    particles: int,
    t: float,
    sigma: float,
    hbar: float = 1.0,
    mass: float = 1.0,
    steps: int = 1000,
    seed: int = 20261030,
) -> np.ndarray:
    if particles < 1 or steps < 1 or t <= 0.0:
        raise ValueError("particles, steps and t must be positive")
    rng = np.random.default_rng(seed)
    x = rng.normal(scale=sigma, size=particles)
    dt = t / steps
    noise_scale = math.sqrt(hbar / mass * dt)
    for step in range(steps):
        x += free_packet_drift(x, step * dt, sigma, hbar, mass) * dt
        x += noise_scale * rng.standard_normal(particles)
    return x


def histogram_density(
    samples: np.ndarray, bins: int = 80, span: float = 6.0
) -> tuple[np.ndarray, np.ndarray, float]:
    if bins < 2 or span <= 0.0:
        raise ValueError("bins and span must be positive")
    density, edges = np.histogram(samples, bins=bins, range=(-span, span), density=True)
    centers = 0.5 * (edges[:-1] + edges[1:])
    width = float(edges[1] - edges[0])
    return density, centers, width


def l1_error(density: np.ndarray, exact: np.ndarray, width: float) -> float:
    if density.shape != exact.shape:
        raise ValueError("density and exact must have the same shape")
    return float(np.sum(np.abs(density - exact)) * width)
