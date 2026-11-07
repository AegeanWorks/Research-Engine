"""Hydrogen 1s Madelung reduction (claim 25, ADR-016).

For the nodeless 1s density

    rho(r) = exp(-2 r / a0) / (pi a0^3),

the quantum pressure is

    Q = -hbar^2/(2 m a0^2) + hbar^2/(m a0 r).

The stationary Euler equation V + Q = mu has cancelling 1/r terms exactly at
the Bohr radius a0 = hbar^2/(m e^2), leaving mu = -hbar^2/(2 m a0^2).  The
Bohr radius is therefore derived from the fluid force balance, not inserted
from the Schrodinger wavefunction.
"""

from __future__ import annotations

import math

import numpy as np

HBAR_SI = 1.054571817e-34
MASS_SI = 9.1093837015e-31
COULOMB_SI = 2.307077e-28
EV_JOULE = 1.602176634e-19


def bohr_radius(hbar: float = 1.0, mass: float = 1.0, coupling: float = 1.0) -> float:
    if hbar <= 0.0 or mass <= 0.0 or coupling <= 0.0:
        raise ValueError("hbar, mass and coupling must be positive")
    return hbar * hbar / (mass * coupling)


def ground_energy(
    radius: float, hbar: float = 1.0, mass: float = 1.0
) -> float:
    if radius <= 0.0:
        raise ValueError("radius must be positive")
    return -hbar * hbar / (2.0 * mass * radius * radius)


def hydrogen_density(r: np.ndarray, radius: float) -> np.ndarray:
    if radius <= 0.0:
        raise ValueError("radius must be positive")
    r = np.asarray(r, dtype=float)
    return np.exp(-2.0 * r / radius) / (math.pi * radius**3)


def quantum_pressure(
    r: np.ndarray,
    radius: float,
    hbar: float = 1.0,
    mass: float = 1.0,
) -> np.ndarray:
    if radius <= 0.0:
        raise ValueError("radius must be positive")
    r = np.asarray(r, dtype=float)
    if np.any(r <= 0.0):
        raise ValueError("r must be positive")
    return -hbar * hbar / (2.0 * mass * radius * radius) + (
        hbar * hbar / (mass * radius * r)
    )


def coulomb_potential(r: np.ndarray, coupling: float = 1.0) -> np.ndarray:
    r = np.asarray(r, dtype=float)
    if np.any(r <= 0.0):
        raise ValueError("r must be positive")
    return -coupling / r


def force_balance(
    r: np.ndarray,
    radius: float,
    hbar: float = 1.0,
    mass: float = 1.0,
    coupling: float = 1.0,
) -> np.ndarray:
    """V + Q - mu; zero when radius is the Bohr radius."""
    return (
        coulomb_potential(r, coupling)
        + quantum_pressure(r, radius, hbar, mass)
        - ground_energy(radius, hbar, mass)
    )


def si_values() -> dict:
    radius = bohr_radius(HBAR_SI, MASS_SI, COULOMB_SI)
    energy_joule = ground_energy(radius, HBAR_SI, MASS_SI)
    return {
        "bohr_radius_m": radius,
        "ground_energy_joule": energy_joule,
        "ground_energy_ev": energy_joule / EV_JOULE,
    }
