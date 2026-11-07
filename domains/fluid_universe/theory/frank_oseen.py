"""Linearised Frank-Oseen director modes.

Background n0 = z.  Write n = (a(x), b(x), 1) to first order.  The one-constant
Frank-Oseen energy is

    f = 1/2 [ K1 (div n)^2 + K2 (n . curl n)^2 + K3 |n x curl n|^2 ],

which to quadratic order becomes

    f = 1/2 [ K1 (dx a + dy b)^2 + K2 (dx b - dy a)^2
              + K3 ((dz a)^2 + (dz b)^2) ].

For a plane wave (a,b) ~ exp(i(k.x - omega t)) and kinetic term
(rho/2)[(dt a)^2 + (dt b)^2], the 2x2 elastic matrix is

    M = [[K1 kx^2 + K2 ky^2 + K3 kz^2, (K1-K2) kx ky],
         [(K1-K2) kx ky, K1 ky^2 + K2 kx^2 + K3 kz^2]].

With K1=K2=K3=K, M = K k^2 I: two degenerate transverse modes with
omega^2 = (K/rho) k^2.  This is the only statement claimed as proven.  It is
not an emergent Lorentz invariance: the background n0 selects a preferred
frame, and there is no gauge field or vector potential that could be a photon.
"""

from __future__ import annotations

import math

import numpy as np


def elastic_matrix(
    kx: float, ky: float, kz: float, k1: float, k2: float, k3: float
) -> np.ndarray:
    """2x2 elastic matrix for the two transverse director components."""
    kx2, ky2, kz2 = kx * kx, ky * ky, kz * kz
    return np.array(
        [
            [k1 * kx2 + k2 * ky2 + k3 * kz2, (k1 - k2) * kx * ky],
            [(k1 - k2) * kx * ky, k1 * ky2 + k2 * kx2 + k3 * kz2],
        ],
        dtype=float,
    )


def dispersion(
    kx: float,
    ky: float,
    kz: float,
    k1: float,
    k2: float,
    k3: float,
    rho: float = 1.0,
) -> np.ndarray:
    """omega^2 for the two transverse modes; rho is the effective inertia."""
    if rho <= 0.0:
        raise ValueError("rho must be positive")
    return np.linalg.eigvalsh(elastic_matrix(kx, ky, kz, k1, k2, k3)) / rho


def equal_constant_dispersion(k: float, K: float, rho: float = 1.0) -> float:
    """omega for K1=K2=K3=K: omega = sqrt(K/rho) |k|."""
    if K < 0.0 or rho <= 0.0:
        raise ValueError("K must be non-negative and rho positive")
    return math.sqrt(K / rho) * abs(k)


def anisotropy(
    direction: tuple[float, float, float],
    k1: float,
    k2: float,
    k3: float,
    rho: float = 1.0,
) -> dict:
    """Fractional split of the two omega^2 values at unit |k|."""
    vector = np.asarray(direction, dtype=float)
    norm = float(np.linalg.norm(vector))
    if norm == 0.0:
        raise ValueError("direction must be nonzero")
    unit = vector / norm
    values = dispersion(unit[0], unit[1], unit[2], k1, k2, k3, rho)
    mean = float(np.mean(values))
    split = float((values[1] - values[0]) / mean) if mean > 0.0 else 0.0
    return {
        "direction": [float(x) for x in unit],
        "omega2": [float(x) for x in values],
        "fractional_split": split,
    }


def modes() -> dict:
    """Mode counting and the photon question."""
    return {
        "propagating_modes": 2,
        "polarisations": "two transverse director components (a,b); the longitudinal component is constrained by |n|=1",
        "gauge_field": False,
        "vector_potential": False,
        "electric_charge": 0,
        "can_be_photon": False,
        "reason": (
            "Frank-Oseen describes neutral director fluctuations. A photon requires an "
            "independent U(1) gauge field and a coupling to it; neither is present."
        ),
        "lorentz_invariance": (
            "Not emergent: the background n0 selects a preferred frame even when "
            "K1=K2=K3. The equal-K dispersion is relativistic-looking only for the "
            "two transverse modes."
        ),
    }


def symbolic_elastic_matrix():
    """Sympy Hessian of the quadratic form; equals the numeric matrix."""
    import sympy as sp

    a, b, kx, ky, kz = sp.symbols("a b kx ky kz", real=True)
    k1, k2, k3 = sp.symbols("K1 K2 K3", positive=True)
    f = sp.Rational(1, 2) * (
        k1 * (kx * a + ky * b) ** 2
        + k2 * (kx * b - ky * a) ** 2
        + k3 * kz**2 * (a * a + b * b)
    )
    return sp.Matrix(
        [
            [sp.diff(f, a, 2), sp.diff(f, a, b)],
            [sp.diff(f, b, a), sp.diff(f, b, 2)],
        ]
    )


def symbolic_matches_numeric() -> bool:
    import sympy as sp

    matrix = symbolic_elastic_matrix()
    k1, k2, k3 = sp.symbols("K1 K2 K3", positive=True)
    kx, ky, kz = sp.symbols("kx ky kz", real=True)
    expected = sp.Matrix(
        [
            [k1 * kx**2 + k2 * ky**2 + k3 * kz**2, (k1 - k2) * kx * ky],
            [(k1 - k2) * kx * ky, k1 * ky**2 + k2 * kx**2 + k3 * kz**2],
        ]
    )
    return sp.simplify(matrix - expected) == sp.zeros(2, 2)
