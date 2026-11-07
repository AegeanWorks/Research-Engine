"""Pinned-endpoint Yasue-bridge action stationarity (claim 57, ADR-049).

Zero free parameters, no full-field claims. The discrete midpoint
Yasue action J_d[s] = sum(0.5*m*v^2 + m*nu^2/(2*mid^2)
- 0.5*m*w^2*mid^2)*dt has the discrete EL residual solved by the
span-56 Newton code as its exact stationarity condition (R1 verified
the gradient identity to ~2e-8; Stage-2 algebra shows it term by term).
The continuous action J_Y[s] = int(m*s_dot^2/2 + m*nu^2/2*s^2
- m*w^2*s^2/2)dt is evaluated by high-accuracy quadrature on the
analytic B_1 arc. The nu -> 0 fixed-endpoint classical action is
J_class = -m*w*a^2*alpha with alpha = sqrt(2)-1 (two independent
derivations in the swarm record; NOT the a^2 = 1 value).

Trial-BVP action consistency only. The B_2 form takes s^2 < 0
mid-interval, so no action exists there (structural, recorded).
"""

from __future__ import annotations

import math

import numpy as np

GRID_N = 401
RESID_TOL = 1e-9
ACTION_TOL = 1e-4
PROBE_TOL = 1e-6
QUAD_N = 200001
BASE = {"omega": 1.0, "hbar": 1.0, "mass": 1.0}
NU_SERIES = (0.5, 0.25, 0.125, 0.0)
FIXED_A = math.sqrt(0.5)
S1_S0_FACTORS = (1.0, 1.1, 1.2)
S1_HORIZON_FACTORS = (2.0 / 3.0, 1.0, 4.0 / 3.0)
GRID_STARTS = ("linear", "bump")
TARGET_STARTS = ("const_s0", "const_sT", "linear", "bump")
PROBE_BUMPS = ("fundamental", "harmonic")
PROBE_LAMS = (-0.02, -0.01, 0.0, 0.01, 0.02)
PROBE_AMP = 0.05


def yasue_discrete_action(
    full_path: np.ndarray,
    omega: float,
    hbar: float,
    mass: float,
    nu: float,
    dt: float,
) -> float:
    """Midpoint discrete Yasue action (own density: +m*nu^2/2mid^2).

    Never the G-M function: the osmotic sign is load-bearing.
    """
    s = np.asarray(full_path, dtype=float)
    vel = (s[1:] - s[:-1]) / dt
    mid = 0.5 * (s[:-1] + s[1:])
    dens = (
        0.5 * mass * vel * vel
        + mass * nu * nu / (2.0 * mid * mid)
        - 0.5 * mass * omega * omega * mid * mid
    )
    return float(np.sum(dens) * dt)


def yasue_analytic_action(
    coeffs: dict,
    omega: float,
    hbar: float,
    mass: float,
    nu: float,
    horizon_T: float,
    n: int = QUAD_N,
) -> float:
    """High-accuracy quadrature of the continuous Yasue action on a branch."""
    from domains.fluid_universe.theory.yasue_bridge import pinney_path

    t = np.linspace(0.0, horizon_T, n)
    dt = float(t[1] - t[0])
    s = pinney_path(coeffs, t, omega)
    vel = np.gradient(s, dt)
    dens = (
        0.5 * mass * vel * vel
        + mass * nu * nu / (2.0 * s * s)
        - 0.5 * mass * omega * omega * s * s
    )
    return float(np.trapezoid(dens, t))


def classical_bridge_action(a: float, omega: float, mass: float) -> dict:
    """Closed-form nu = 0 fixed-endpoint action J = -m*w*a^2*alpha."""
    alpha = math.sqrt(2.0) - 1.0
    return {"alpha": alpha, "value": -mass * omega * a * a * alpha}


def variation_probe(
    base_path: np.ndarray, horizon_T: float, bump_kind: str
) -> dict:
    """Discrete Yasue J along base + lam*amp*bump (own bump family)."""
    t = np.linspace(0.0, horizon_T, len(base_path))
    if bump_kind == "fundamental":
        bump = np.sin(math.pi * t / horizon_T)
    elif bump_kind == "harmonic":
        bump = np.sin(2.0 * math.pi * t / horizon_T)
    else:
        raise ValueError(f"unknown bump kind: {bump_kind}")
    return {"t": t, "bump": bump}


def probe_slope(
    base_path: np.ndarray,
    bump: np.ndarray,
    omega: float,
    hbar: float,
    mass: float,
    nu: float,
    dt: float,
    lam: float = 0.01,
    amp: float = PROBE_AMP,
) -> dict:
    low = yasue_discrete_action(
        np.asarray(base_path) - lam * amp * np.asarray(bump),
        omega,
        hbar,
        mass,
        nu,
        dt,
    )
    high = yasue_discrete_action(
        np.asarray(base_path) + lam * amp * np.asarray(bump),
        omega,
        hbar,
        mass,
        nu,
        dt,
    )
    return {"slope": (high - low) / (2.0 * lam), "j_low": low, "j_high": high}
