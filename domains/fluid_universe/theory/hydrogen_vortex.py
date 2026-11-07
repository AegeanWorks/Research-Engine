"""Hydrogen 2p vortex identification (claim 26, ADR-017).

The 2p_(m=+-1) state has an angular node at the origin.  The phase winds
by 2 pi m, so the density node is a quantized vortex with circulation
2 pi hbar m / m_e, not a radial node.  The radial density is nodeless and
peaks at 4 a0.
"""

from __future__ import annotations

import math

import numpy as np


def radial_2p(r: np.ndarray, radius: float) -> np.ndarray:
    """Hydrogen 2p radial function R_21(r), normalized as int r^2 R^2 dr = 1."""
    if radius <= 0.0:
        raise ValueError("radius must be positive")
    r = np.asarray(r, dtype=float)
    return (
        1.0
        / (2.0 * math.sqrt(6.0) * radius**1.5)
        * (r / radius)
        * np.exp(-r / (2.0 * radius))
    )


def radial_probability(r: np.ndarray, radius: float) -> np.ndarray:
    r = np.asarray(r, dtype=float)
    return r * r * radial_2p(r, radius) ** 2


def most_probable_radius(radius: float) -> float:
    if radius <= 0.0:
        raise ValueError("radius must be positive")
    return 4.0 * radius


def azimuthal_velocity(
    r: float,
    theta: float,
    m: int,
    hbar: float = 1.0,
    mass: float = 1.0,
) -> float:
    if r <= 0.0 or hbar <= 0.0 or mass <= 0.0:
        raise ValueError("r, hbar and mass must be positive")
    sine = math.sin(theta)
    if abs(sine) < 1e-12:
        raise ValueError("theta must be away from the poles")
    return hbar * m / (mass * r * sine)


def circulation(m: int, hbar: float = 1.0, mass: float = 1.0) -> float:
    if hbar <= 0.0 or mass <= 0.0:
        raise ValueError("hbar and mass must be positive")
    return 2.0 * math.pi * hbar * m / mass


def loop_circulation(
    r: float,
    theta: float,
    m: int,
    hbar: float = 1.0,
    mass: float = 1.0,
    samples: int = 4000,
) -> float:
    if samples < 16:
        raise ValueError("samples must be at least 16")
    phi = np.linspace(0.0, 2.0 * math.pi, samples, endpoint=True)
    velocity = azimuthal_velocity(r, theta, m, hbar, mass)
    return float(np.trapezoid(np.full(samples, velocity * r * math.sin(theta)), phi))


def angular_momentum(m: int, hbar: float = 1.0) -> float:
    if hbar <= 0.0:
        raise ValueError("hbar must be positive")
    return hbar * m
