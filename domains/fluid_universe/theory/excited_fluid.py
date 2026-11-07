"""First excited state in the Madelung fluid (claim 24, ADR-015).

The first harmonic-oscillator excited state is

    psi_1(x) = sqrt(2)/(pi^(1/4) sqrt(sigma)) (x/sigma) exp(-x^2/(2 sigma^2)).

Its density vanishes at x=0, so the phase jumps by pi and the Madelung velocity
has a delta-function phase slip.  The regular quantum pressure matches the
analytic expression away from the node, but the node itself is not a regular
fluid point.  This is a limitation of the single-valued fluid representation,
not a failure of the Gaussian reduction.
"""

from __future__ import annotations

import math

import numpy as np


def _sigma(omega: float, hbar: float, mass: float) -> float:
    if omega <= 0.0 or hbar <= 0.0 or mass <= 0.0:
        raise ValueError("omega, hbar and mass must be positive")
    return math.sqrt(hbar / (mass * omega))


def excited_density(
    x: np.ndarray, omega: float, hbar: float = 1.0, mass: float = 1.0
) -> np.ndarray:
    sigma = _sigma(omega, hbar, mass)
    x = np.asarray(x, dtype=float)
    return 2.0 / (math.sqrt(math.pi) * sigma**3) * x * x * np.exp(
        -x * x / (sigma * sigma)
    )


def excited_wavefunction(
    x: np.ndarray, omega: float, hbar: float = 1.0, mass: float = 1.0
) -> np.ndarray:
    sigma = _sigma(omega, hbar, mass)
    x = np.asarray(x, dtype=float)
    return (
        math.sqrt(2.0)
        / (math.pi**0.25 * math.sqrt(sigma))
        * (x / sigma)
        * np.exp(-x * x / (2.0 * sigma * sigma))
    )


def excited_quantum_pressure_regular(
    x: np.ndarray, omega: float, hbar: float = 1.0, mass: float = 1.0
) -> np.ndarray:
    """Regular part of Q away from the node; at x=0 the limit is returned."""
    sigma = _sigma(omega, hbar, mass)
    x = np.asarray(x, dtype=float)
    return (hbar * hbar) / (2.0 * mass * sigma * sigma) * (
        3.0 - x * x / (sigma * sigma)
    )


def phase_slip(psi: np.ndarray) -> float:
    psi = np.asarray(psi)
    phase = np.angle(psi)
    return float(np.max(phase) - np.min(phase))


def phase_gradient_max(psi: np.ndarray, dx: float) -> float:
    if dx <= 0.0:
        raise ValueError("dx must be positive")
    phase = np.angle(np.asarray(psi))
    return float(np.max(np.abs(np.gradient(phase, dx))))


def scaling_slope(dx_values: np.ndarray, maxima: np.ndarray) -> float:
    dx_values = np.asarray(dx_values, dtype=float)
    maxima = np.asarray(maxima, dtype=float)
    if dx_values.shape != maxima.shape or dx_values.size < 2:
        raise ValueError("dx_values and maxima must have the same length >= 2")
    return float(np.polyfit(np.log(dx_values), np.log(maxima), 1)[0])
