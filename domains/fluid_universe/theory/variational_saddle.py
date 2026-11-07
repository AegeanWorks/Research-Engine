"""Ritz saddle: G-M stationary point in (s, c) (claim 50, ADR-042).

Zero free parameters, no dynamics asserted beyond the stationary
2D Gaussian trial class (v = c*(-y, x), u = -nu*r/s, s = sigma^2).
With nu = hbar/(2*m), in d = 2 dimensions:

    J_G(s, c) = m*c^2*s - m*nu^2/s - m*omega^2*s   (Guerra-Morato)
    J_Y(s, c) = m*c^2*s + m*nu^2/s - m*omega^2*s   (Yasui)

G-M has the unique stationary point (s*, c*) = (nu/omega, 0) with
MIXED curvature: d2J/ds2 = -2*m*nu^2/s^3 < 0 (maximum, u-sector) and
d2J/dc2 = 2*m*s > 0 (minimum, v-sector) — the Pavon saddle projected
into Ritz. Because it is a saddle, the JOINT box argmax lies on the
boundary with HIGHER action value than the saddle (recorded, never
gated); the correct grid signature is the CONDITIONAL pair: max over
s at c = 0 AND min over c at the maximizing s, each Newton-polished
in 1D (the Hessian decouples: mixed partial 2*m*c = 0 at c* = 0).
Yasui selects c = 0 (minimum in c) but has no finite-s extremum
(dJ/ds < 0 everywhere).

1D-vs-2D firewall: span-49 curvature -2.0 is -m*nu^2/s^3 (one degree
of freedom); here -4.0 is -2*m*nu^2/s^3 (two). The 2D slice at c = 0
is exactly twice the 1D action (test pins the 2x relation; never use
a 1D number in a 2D gate).

Scope: Ritz-restricted trial class only. The full infinite-dimensional
variation, the Morato-Ugolini dynamical flow (which shows transient
increasing vorticity relaxing toward the irrotational plane —
consistent with, not contrary to, the min-in-c signature here), and
the Loffredo-Morato mu parameter are untested and excluded with
reason in ADR-042.
"""

from __future__ import annotations

import numpy as np

GRID_S = tuple(float(v) for v in np.linspace(0.125, 2.0, 2001))
GRID_C = tuple(float(v) for v in np.linspace(-1.0, 1.0, 401))
BASE = {"omega": 1.0, "hbar": 1.0, "mass": 1.0}
SCALING = {"omega": 2.0, "hbar": 1.0, "mass": 1.0}
NEWTON_STEPS = 8


def diffusivity(hbar: float, mass: float) -> float:
    if hbar <= 0.0 or mass <= 0.0:
        raise ValueError("hbar and mass must be positive")
    return hbar / (2.0 * mass)


def action_gm_2d(
    s: float, c: float, omega: float, hbar: float, mass: float
) -> float:
    if s <= 0.0 or omega <= 0.0:
        raise ValueError("s and omega must be positive")
    nu = diffusivity(hbar, mass)
    return mass * c * c * s - mass * nu * nu / s - mass * omega * omega * s


def action_yasui_2d(
    s: float, c: float, omega: float, hbar: float, mass: float
) -> float:
    if s <= 0.0 or omega <= 0.0:
        raise ValueError("s and omega must be positive")
    nu = diffusivity(hbar, mass)
    return mass * c * c * s + mass * nu * nu / s - mass * omega * omega * s


def grad_gm_2d(
    s: float, c: float, omega: float, hbar: float, mass: float
) -> tuple:
    nu = diffusivity(hbar, mass)
    dds = (
        mass * c * c
        + mass * nu * nu / (s * s)
        - mass * omega * omega
    )
    ddc = 2.0 * mass * c * s
    return dds, ddc


def hess_gm_2d(
    s: float, c: float, omega: float, hbar: float, mass: float
) -> tuple:
    nu = diffusivity(hbar, mass)
    d2s = -2.0 * mass * nu * nu / (s * s * s)
    d2c = 2.0 * mass * s
    mixed = 2.0 * mass * c
    return d2s, d2c, mixed


def extremum_sc(omega: float, hbar: float, mass: float) -> tuple:
    """Analytic stationary point (s*, c*) = (nu/omega, 0)."""
    if omega <= 0.0 or hbar <= 0.0 or mass <= 0.0:
        raise ValueError("omega, hbar and mass must be positive")
    return diffusivity(hbar, mass) / omega, 0.0


def newton_refine_s(
    s0: float,
    c_fixed: float,
    omega: float,
    hbar: float,
    mass: float,
    steps: int = NEWTON_STEPS,
) -> float:
    """1D Newton on dJ/ds = 0 at fixed c (definite: maximum in s)."""
    s = float(s0)
    nu = diffusivity(hbar, mass)
    for _ in range(steps):
        first = (
            mass * c_fixed * c_fixed
            + mass * nu * nu / (s * s)
            - mass * omega * omega
        )
        second = -2.0 * mass * nu * nu / (s * s * s)
        s -= first / second
    return s


def newton_refine_c(
    c0: float,
    s_fixed: float,
    omega: float,
    hbar: float,
    mass: float,
    steps: int = NEWTON_STEPS,
) -> float:
    """1D Newton on dJ/dc = 0 at fixed s (definite: minimum in c)."""
    c = float(c0)
    for _ in range(steps):
        first = 2.0 * mass * c * s_fixed
        second = 2.0 * mass * s_fixed
        c -= first / second
    return c


def conditional_extremum(
    s_values: np.ndarray,
    c_values: np.ndarray,
    omega: float,
    hbar: float,
    mass: float,
) -> dict:
    """Saddle signature on the grid: max over s at c = 0, min over c.

    A joint box argmax is the WRONG gate for a saddle (it sits on the
    boundary above the saddle value); it is recorded, never gated.
    """
    s_values = np.asarray(s_values, dtype=float)
    c_values = np.asarray(c_values, dtype=float)
    c0 = int(np.argmin(np.abs(c_values)))
    nu = diffusivity(hbar, mass)
    col = (
        mass * c_values[c0] * c_values[c0] * s_values
        - mass * nu * nu / s_values
        - mass * omega * omega * s_values
    )
    i_peak = int(np.argmax(col))
    row = (
        mass * c_values * c_values * s_values[i_peak]
        - mass * nu * nu / s_values[i_peak]
        - mass * omega * omega * s_values[i_peak]
    )
    j_trough = int(np.argmin(row))
    s_peak = float(s_values[i_peak])
    c_trough = float(c_values[j_trough])
    step_s = float(s_values[1] - s_values[0])
    step_c = float(c_values[1] - c_values[0])
    refined_s = newton_refine_s(s_peak, float(c_values[c0]), omega, hbar, mass)
    refined_c = newton_refine_c(c_trough, refined_s, omega, hbar, mass)
    box = (
        mass
        * np.square(c_values)[None, :]
        * s_values[:, None]
        - mass * nu * nu / s_values[:, None]
        - mass * omega * omega * s_values[:, None]
    )
    flat = int(np.argmax(box))
    bi, bj = divmod(flat, c_values.size)
    box_max = float(box[bi, bj])
    return {
        "grid_s": s_peak,
        "grid_c": c_trough,
        "grid_step_s": step_s,
        "grid_step_c": step_c,
        "refined_s": refined_s,
        "refined_c": refined_c,
        "box_argmax_s": float(s_values[bi]),
        "box_argmax_c": float(c_values[bj]),
        "box_max_value": box_max,
        "saddle_value": float(action_gm_2d(refined_s, refined_c, omega, hbar, mass)),
    }


def yasui_scan(
    s_values: np.ndarray,
    omega: float,
    hbar: float,
    mass: float,
) -> dict:
    """Yasui derivative sign over the frozen grid (must stay negative)."""
    s_values = np.asarray(s_values, dtype=float)
    nu = diffusivity(hbar, mass)
    derivs = -mass * nu * nu / (s_values * s_values) - mass * omega * omega
    base = (
        mass * nu * nu / s_values
        - mass * omega * omega * s_values
    )
    return {
        "max_derivative": float(np.max(derivs)),
        "min_derivative": float(np.min(derivs)),
        "all_negative": bool(np.all(derivs < 0.0)),
        "max_diff": float(np.max(np.diff(base))),
    }


def saddle_scales() -> dict:
    """Collect the saddle correspondence bundle (no verdict)."""
    omega, hbar, mass = BASE["omega"], BASE["hbar"], BASE["mass"]
    star_s, star_c = extremum_sc(omega, hbar, mass)
    grid = conditional_extremum(
        np.array(GRID_S), np.array(GRID_C), omega, hbar, mass
    )
    d2s, d2c, mixed = hess_gm_2d(star_s, star_c, omega, hbar, mass)
    yasui = yasui_scan(np.array(GRID_S), omega, hbar, mass)
    scal = dict(SCALING)
    scal_star_s, scal_star_c = extremum_sc(
        scal["omega"], scal["hbar"], scal["mass"]
    )
    scal_peak = conditional_extremum(
        np.array(GRID_S),
        np.array(GRID_C),
        scal["omega"],
        scal["hbar"],
        scal["mass"],
    )
    scal_d2s, scal_d2c, _ = hess_gm_2d(
        scal_star_s, scal_star_c, scal["omega"], scal["hbar"], scal["mass"]
    )
    return {
        "grids": {"s2": list(GRID_S), "c": list(GRID_C)},
        "base": dict(BASE),
        "analytic": {
            "sigma_star_sq": star_s,
            "c_star": star_c,
            "curvature_s": d2s,
            "curvature_c": d2c,
            "mixed": mixed,
        },
        "grid": grid,
        "yasui": yasui,
        "scalings": dict(
            params=scal,
            predicted_s=scal_star_s,
            grid_s=scal_peak["grid_s"],
            grid_c=scal_peak["grid_c"],
            refined_s=scal_peak["refined_s"],
            refined_c=scal_peak["refined_c"],
            curvature_s=scal_d2s,
            curvature_c=scal_d2c,
        ),
    }
