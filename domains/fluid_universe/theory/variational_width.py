"""Gaussian Ritz width-selection: G-M vs Yasui (claim 49, ADR-041).

Zero free parameters, no dynamics asserted beyond the stationary
Gaussian trial class (v = 0). For variance s2 with nu = hbar/(2*m):

    J_G(s2)  = -m*nu^2/(2*s2) - m*omega^2*s2/2   (Guerra-Morato)
    J_Y(s2)  = +m*nu^2/(2*s2) - m*omega^2*s2/2   (Yasui)

G-M has the unique global maximum at s2* = nu/omega (strictly concave
in s2); Yasui is strictly decreasing on s2 > 0 (no finite extremum).
The location coincides with the Ermakov fixed point sigma^2 =
hbar/(2*m*omega) from claim 22 — same fixed point from the stochastic
action as from the fluid reduction. The full J_G == -V(sigma) identity
holds only at m = 1 and is a remark, never used; all formulas below
are general in (m, omega, hbar).

Curvature convention (frozen): second derivative with respect to s2,
d2J_G/d(s2)^2 = -m*nu^2/s2^3 = -2.0 at the frozen-input extremum.
The sigma-parametrized form d2J_G/d(sigma)^2 = -4.0 is reported as a
cross-check only.

Scope: Ritz-restricted trial class only. The full infinite-dimensional
variation and the Loffredo-Morato parameter are untested here (the
parameter has no width selector; excluded with reason in ADR-041).
"""

from __future__ import annotations

import math

import numpy as np

from domains.fluid_universe.theory.gaussian_fluid import effective_potential, quantum_width

GRID_S2 = tuple(float(v) for v in np.linspace(0.125, 2.0, 2001))
BASE = {"omega": 1.0, "hbar": 1.0, "mass": 1.0}
SCALINGS = (
    {"omega": 2.0, "hbar": 1.0, "mass": 1.0},
    {"omega": 1.0, "hbar": 1.0, "mass": 2.0},
)
NEWTON_STEPS = 8


def diffusivity(hbar: float, mass: float) -> float:
    if hbar <= 0.0 or mass <= 0.0:
        raise ValueError("hbar and mass must be positive")
    return hbar / (2.0 * mass)


def action_gm(s2: float, omega: float, hbar: float, mass: float) -> float:
    if s2 <= 0.0 or omega <= 0.0:
        raise ValueError("s2 and omega must be positive")
    nu = diffusivity(hbar, mass)
    return -mass * nu * nu / (2.0 * s2) - 0.5 * mass * omega * omega * s2


def action_yasui(s2: float, omega: float, hbar: float, mass: float) -> float:
    if s2 <= 0.0 or omega <= 0.0:
        raise ValueError("s2 and omega must be positive")
    nu = diffusivity(hbar, mass)
    return mass * nu * nu / (2.0 * s2) - 0.5 * mass * omega * omega * s2


def d_action_gm(s2: float, omega: float, hbar: float, mass: float) -> float:
    if s2 <= 0.0 or omega <= 0.0:
        raise ValueError("s2 and omega must be positive")
    nu = diffusivity(hbar, mass)
    return mass * nu * nu / (2.0 * s2 * s2) - 0.5 * mass * omega * omega


def d_action_yasui(s2: float, omega: float, hbar: float, mass: float) -> float:
    if s2 <= 0.0 or omega <= 0.0:
        raise ValueError("s2 and omega must be positive")
    nu = diffusivity(hbar, mass)
    return -mass * nu * nu / (2.0 * s2 * s2) - 0.5 * mass * omega * omega


def d2_action_gm_s2(s2: float, omega: float, hbar: float, mass: float) -> float:
    """Curvature with respect to s2 (gate variable): -m*nu^2/s2^3."""
    if s2 <= 0.0 or omega <= 0.0:
        raise ValueError("s2 and omega must be positive")
    nu = diffusivity(hbar, mass)
    return -mass * nu * nu / (s2 * s2 * s2)


def d2_action_gm_sigma(sigma: float, omega: float, hbar: float, mass: float) -> float:
    """Curvature with respect to sigma (record only): -3m*nu^2/s^4-m*w^2."""
    if sigma <= 0.0 or omega <= 0.0:
        raise ValueError("sigma and omega must be positive")
    nu = diffusivity(hbar, mass)
    return -3.0 * mass * nu * nu / (sigma**4) - mass * omega * omega


def extremum_s2(omega: float, hbar: float, mass: float) -> float:
    """Analytic G-M maximizer s2 = nu/omega with nu = hbar/(2*mass)."""
    if omega <= 0.0 or hbar <= 0.0 or mass <= 0.0:
        raise ValueError("omega, hbar and mass must be positive")
    return diffusivity(hbar, mass) / omega


def newton_refine(
    start: float,
    omega: float,
    hbar: float,
    mass: float,
    steps: int = NEWTON_STEPS,
) -> float:
    """Newton iterations on dJ_G/d(s2) = 0 from a grid argmax start."""
    s2 = float(start)
    nu = diffusivity(hbar, mass)
    for _ in range(steps):
        first = mass * nu * nu / (2.0 * s2 * s2) - 0.5 * mass * omega * omega
        second = -mass * nu * nu / (s2 * s2 * s2)
        s2 -= first / second
    return s2


def grid_maximum(
    s2_values: np.ndarray, omega: float, hbar: float, mass: float
) -> dict:
    """Grid argmax of J_G plus Newton refinement (not single parabola)."""
    s2_values = np.asarray(s2_values, dtype=float)
    values = np.array(
        [action_gm(s, omega, hbar, mass) for s in s2_values]
    )
    peak = int(np.argmax(values))
    step = float(s2_values[1] - s2_values[0])
    refined = newton_refine(float(s2_values[peak]), omega, hbar, mass)
    return {
        "grid_argmax": float(s2_values[peak]),
        "grid_step": step,
        "grid_max_value": float(values[peak]),
        "refined": refined,
    }


def yasui_monotone(
    s2_values: np.ndarray, omega: float, hbar: float, mass: float
) -> dict:
    """Yasui derivative sign over the frozen grid (must stay negative)."""
    s2_values = np.asarray(s2_values, dtype=float)
    derivs = np.array(
        [d_action_yasui(s, omega, hbar, mass) for s in s2_values]
    )
    diffs = np.diff(
        np.array([action_yasui(s, omega, hbar, mass) for s in s2_values])
    )
    return {
        "max_derivative": float(np.max(derivs)),
        "min_derivative": float(np.min(derivs)),
        "all_negative": bool(np.all(derivs < 0.0)),
        "max_diff": float(np.max(diffs)),
    }


def ermakov_cross_check() -> dict:
    """Independent argmin of V(sigma) vs analytic G-M maximizer."""
    width = quantum_width(1.0)
    grid = np.linspace(0.2, 1.4, 2401)
    values = np.array([effective_potential(s, 1.0) for s in grid])
    best = int(np.argmin(values))
    return {
        "quantum_width": float(width),
        "width_squared": float(width * width),
        "potential_argmin": float(grid[best]),
        "potential_min_value": float(values[best]),
    }


def selection_scales() -> dict:
    """Collect the Ritz correspondence bundle (no verdict)."""
    grid = np.array(GRID_S2)
    omega, hbar, mass = BASE["omega"], BASE["hbar"], BASE["mass"]
    star = extremum_s2(omega, hbar, mass)
    peak = grid_maximum(grid, omega, hbar, mass)
    yasui = yasui_monotone(grid, omega, hbar, mass)
    scalings = []
    for params in SCALINGS:
        entry = dict(params)
        entry["predicted"] = extremum_s2(
            params["omega"], params["hbar"], params["mass"]
        )
        peak_p = grid_maximum(
            grid, params["omega"], params["hbar"], params["mass"]
        )
        entry["grid_argmax"] = peak_p["grid_argmax"]
        entry["refined"] = peak_p["refined"]
        entry["curvature_s2"] = d2_action_gm_s2(
            entry["predicted"],
            params["omega"],
            params["hbar"],
            params["mass"],
        )
        scalings.append(entry)
    return {
        "grids": {"s2": list(GRID_S2)},
        "base": dict(BASE),
        "analytic": {
            "sigma_star_sq": star,
            "curvature_s2": d2_action_gm_s2(star, omega, hbar, mass),
            "curvature_sigma": d2_action_gm_sigma(
                math.sqrt(star), omega, hbar, mass
            ),
        },
        "grid": peak,
        "yasui": yasui,
        "scalings": scalings,
        "ermakov": ermakov_cross_check(),
    }
