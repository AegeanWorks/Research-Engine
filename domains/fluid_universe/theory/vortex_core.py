"""HO-1 finite-core node probe (claim 60, ADR-054).

Single-valued regularized defect only (HO-1 1D node). The 2p loop and
2s shell stay queued. Pre-registered core radius eps0 = 0.1 * a0 with
a0 from domains.fluid_universe.theory.hydrogen_fluid.bohr_radius() (never hardcoded, never
scanned). Core form is the complex shift

    psi_eps(x) = A * (x + i*eps) * exp(-x^2/(2*sigma^2)),

so rho_eps = |psi_eps|^2 is nowhere zero, the phase winds smoothly by
pi across the domain, v = (hbar/m) * dS/dx is finite (vmax = hbar/m*eps
in magnitude), and Q_eps(0) = -hbar^2/2m * (1/eps^2 - 1/sigma^2) is
finite. As eps -> 0 the singular HO-1 numbers (claim 24) return.
Naive density-floor control (phase untouched) is kept to prove the
apparatus can still kill (must retain dx^-1 blow-up).
"""

from __future__ import annotations

import math

import numpy as np

GRID_NS = (256, 512, 1024, 2048)
GRID_LENGTH = 20.0
EPS0_FACTOR = 0.1


def core_radius() -> float:
    """Pre-registered core radius eps0 = 0.1 * a0 (predicted, not fit)."""
    from domains.fluid_universe.theory.hydrogen_fluid import bohr_radius

    return EPS0_FACTOR * float(bohr_radius(1.0, 1.0, 1.0))


def ho_sigma(omega: float = 1.0, hbar: float = 1.0, mass: float = 1.0) -> float:
    if omega <= 0.0 or hbar <= 0.0 or mass <= 0.0:
        raise ValueError("omega, hbar and mass must be positive")
    return math.sqrt(hbar / (mass * omega))


def core_norm(eps: float, sigma: float) -> float:
    """Exact L2 norm squared of (x+i*eps)*exp(-x^2/2s^2): s*sqrt(pi)*(s^2/2+eps^2)."""
    if eps < 0.0 or sigma <= 0.0:
        raise ValueError("eps >= 0 and sigma > 0 required")
    return sigma * math.sqrt(math.pi) * (sigma * sigma / 2.0 + eps * eps)


def core_density(
    x: np.ndarray, eps: float, sigma: float = 1.0
) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    raw = (x * x + eps * eps) * np.exp(-x * x / (sigma * sigma))
    return raw / (raw.sum() * (x[1] - x[0])) if x.size > 1 else raw


def core_phase(x: np.ndarray, eps: float) -> np.ndarray:
    """Phase arg(x + i*eps); singular arg(x) at eps = 0."""
    x = np.asarray(x, dtype=float)
    if eps < 0.0:
        raise ValueError("eps must be non-negative")
    return np.arctan2(np.full_like(x, eps), x)


def core_velocity(
    x: np.ndarray, eps: float, hbar: float = 1.0, mass: float = 1.0
) -> np.ndarray:
    """v = (hbar/m) dS/dx with S = arg(x+i*eps): v = -(hbar/m)*eps/(x^2+eps^2)."""
    x = np.asarray(x, dtype=float)
    if eps < 0.0 or hbar <= 0.0 or mass <= 0.0:
        raise ValueError("eps >= 0 and hbar, mass > 0 required")
    return -(hbar / mass) * eps / (x * x + eps * eps)


def core_q_zero(eps: float, sigma: float = 1.0, hbar: float = 1.0, mass: float = 1.0) -> float:
    """Analytic Q at x=0: -hbar^2/2m * (1/eps^2 - 1/sigma^2). eps > 0 required."""
    if eps <= 0.0 or sigma <= 0.0 or hbar <= 0.0 or mass <= 0.0:
        raise ValueError("eps, sigma, hbar, mass must be positive")
    return -(hbar * hbar) / (2.0 * mass) * (1.0 / (eps * eps) - 1.0 / (sigma * sigma))


def fd_q_zero(
    eps: float, n: int, length: float = GRID_LENGTH, sigma: float = 1.0
) -> float:
    """Second-order central FD Q at x=0 from sqrt(rho); N-convergence probe."""
    if eps <= 0.0:
        raise ValueError("eps must be positive for the FD core probe")
    dx = length / n
    x = (np.arange(n) - n // 2) * dx
    rho = (x * x + eps * eps) * np.exp(-x * x / (sigma * sigma))
    rho = rho / (rho.sum() * dx)
    s = np.sqrt(np.maximum(rho, 1e-300))
    i0 = n // 2
    lap = (s[i0 + 1] - 2.0 * s[i0] + s[i0 - 1]) / (dx * dx)
    return float(-0.5 * lap / s[i0])
