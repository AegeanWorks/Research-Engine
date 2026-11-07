"""Exact algebra of the Hermitian 3x3 circulant mass matrix.

Conventions
-----------
M = circ(a, b, b*) with b = c*exp(i*delta), a, c, delta real, c >= 0.
The first row is (a, b, b*).  Eigenvalues:

    lam_k = a + 2*c*cos(delta + 2*pi*k/3),  k = 0, 1, 2

and the eigenvectors are the DFT columns

    v_k = (1, w**k, w**(2k)) / sqrt(3),  w = exp(2*pi*i/3),

independent of delta.

The eigenvalues are the *signed* square roots of the masses.  The identity
Q = 1/3 + 2*c**2/(3*a**2) is an identity for those signed roots; the physical
Koide ratio uses |lam_k| and agrees only when every lam_k >= 0.  See
``q_physical`` and the sign-caveat test.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

OMEGA = np.exp(2j * np.pi / 3.0)


def circulant_matrix(a: float, c: float, delta: float) -> np.ndarray:
    """Return the Hermitian circulant M = circ(a, c e^{i delta}, c e^{-i delta})."""
    b = c * np.exp(1j * delta)
    return np.array(
        [
            [a, b, np.conjugate(b)],
            [np.conjugate(b), a, b],
            [b, np.conjugate(b), a],
        ],
        dtype=complex,
    )


def eigenvalues(a: float, c: float, delta: float) -> np.ndarray:
    """Signed eigenvalues of the Hermitian circulant, in the k = 0,1,2 order."""
    k = np.arange(3)
    return a + 2.0 * c * np.cos(delta + 2.0 * np.pi * k / 3.0)


def dft_vectors() -> np.ndarray:
    """Columns are the three DFT eigenvectors v_k, each normalised to unit norm."""
    k = np.arange(3)
    return np.array(
        [[OMEGA ** (k * n) for k in range(3)] for n in range(3)],
        dtype=complex,
    ) / np.sqrt(3.0)


def q_signed(x: np.ndarray | list[float]) -> float:
    """Q for signed square roots: sum(x^2) / (sum(x))^2."""
    x = np.asarray(x, dtype=float)
    return float(np.sum(x * x) / np.sum(x) ** 2)


def q_masses(m: np.ndarray | list[float]) -> float:
    """Physical Koide Q for positive masses."""
    m = np.asarray(m, dtype=float)
    return float(np.sum(m) / np.sum(np.sqrt(m)) ** 2)


def q_physical_from_roots(x: np.ndarray | list[float]) -> float:
    """Physical Q when x are signed square roots: sum(x^2) / (sum(|x|))^2."""
    x = np.asarray(x, dtype=float)
    return float(np.sum(x * x) / np.sum(np.abs(x)) ** 2)


def q_from_ac(a: float, c: float) -> float:
    """The algebraic identity Q = 1/3 + 2 c^2 / (3 a^2)."""
    return float(1.0 / 3.0 + 2.0 * c * c / (3.0 * a * a))


def extract_ac_delta(x: np.ndarray | list[float]) -> tuple[float, float, float]:
    """Inverse DFT: return (a, c, delta) from three signed roots x_k.

    x_k = a + 2 c cos(delta + 2 pi k / 3),
    so (1/3) sum_k x_k w^{-k} = c e^{i delta}.
    """
    x = np.asarray(x, dtype=float)
    if x.shape != (3,):
        raise ValueError("expected exactly three roots")
    a = float(np.mean(x))
    z = np.sum(x * np.conjugate(OMEGA) ** np.arange(3)) / 3.0
    c = float(abs(z))
    delta = float(np.angle(z) % (2.0 * np.pi))
    if c < 1e-14:
        delta = 0.0
    return a, c, delta


def fit_masses(m: np.ndarray | list[float]) -> dict[str, float]:
    """Fit (a, c, delta) to positive masses and return Q, r, delta, residuals."""
    m = np.asarray(m, dtype=float)
    if np.any(m <= 0.0):
        raise ValueError("masses must be positive")
    x = np.sqrt(m)
    a, c, delta = extract_ac_delta(x)
    fitted = a + 2.0 * c * np.cos(delta + 2.0 * np.pi * np.arange(3) / 3.0)
    residual = fitted - x
    return {
        "a": a,
        "c": c,
        "delta": delta,
        "r": c / a,
        "Q": q_masses(m),
        "Q_from_ac": q_from_ac(a, c),
        "max_abs_residual": float(np.max(np.abs(residual))),
        "all_roots_positive": bool(np.all(fitted >= 0.0)),
    }


def koide_tau_prediction(m_e: float, m_mu: float) -> float:
    """Solve Q=2/3 for m_tau given m_e and m_mu.

    The quadratic has two positive roots; the physical branch is the larger one
    (the smaller root lies below sqrt(m_mu)).
    """
    s = np.sqrt(m_e) + np.sqrt(m_mu)
    # x^2 - 4 s x + 3 (m_e + m_mu) - 2 s^2 = 0, x = sqrt(m_tau)
    b = -4.0 * s
    c = 3.0 * (m_e + m_mu) - 2.0 * s * s
    disc = b * b - 4.0 * c
    roots = (-b + np.array([-1.0, 1.0]) * np.sqrt(disc)) / 2.0
    positive = roots[roots > 0.0]
    if positive.size == 0:
        raise ValueError("no positive tau root")
    # The quadratic has two positive roots; the physical tau is the larger one
    # (the smaller root lies below sqrt(m_mu)).
    return float(np.max(positive) ** 2)


# ---------------------------------------------------------------------------
# Symbolic versions (sympy), used by the tests.
# ---------------------------------------------------------------------------


def _sympy_symbols():
    import sympy as sp

    a, c, delta = sp.symbols("a c delta", real=True)
    return sp, a, c, delta


def circulant_symbolic():
    """Return (M, a, c, delta) as sympy objects."""
    sp, a, c, delta = _sympy_symbols()
    b = c * sp.exp(sp.I * delta)
    bc = c * sp.exp(-sp.I * delta)
    M = sp.Matrix([[a, b, bc], [bc, a, b], [b, bc, a]])
    return M, a, c, delta


def eigenvalues_symbolic():
    sp, a, c, delta = _sympy_symbols()
    return [a + 2 * c * sp.cos(delta + 2 * sp.pi * k / 3) for k in range(3)]


def q_identity_symbolic():
    """Return the expression Q_signed - (1/3 + 2c^2/(3a^2)); simplifies to 0."""
    sp, a, c, delta = _sympy_symbols()
    x = eigenvalues_symbolic()
    expr = sum(xi**2 for xi in x) / sum(x) ** 2
    return sp.simplify(sp.expand_trig(expr - (sp.Rational(1, 3) + 2 * c**2 / (3 * a**2))))
