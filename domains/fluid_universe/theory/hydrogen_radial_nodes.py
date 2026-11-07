"""Hydrogen-2s radial-node two-branch representation (claim 47, ADR-039).

Representation-only, zero free parameters, no dynamics. The 2s radial
function is written as the exact two-branch split

    R_20(r) = s(r) * |R_20(r)|,   s(r) = sign(R_20(r)),

so the pi phase slip across the r = 2*a0 nodal shell lives in the
branch datum s(r), while |R_20| is smooth. The shell itself (rho=0)
is excluded from fluid-point claims, per claims 24/46. The radius
is not inserted: a0 comes from domains.fluid_universe.theory.hydrogen_fluid.bohr_radius()
(claim-25 derived force balance). No circulation is claimed for the
shell (m=0 loops give 0; L3 gate): the Wallstrom content here is the
imposed pi discontinuity, and the 2p vortex numbers are preserved
untouched as the no-disturbance control alongside the 1s balance.

Correspondence (frozen numbers, recomputed live, never refit):
- node at r = 2*a0 exactly; slip pi; radial norm 1.0;
  1s-2s overlap 0; probability peaks at (3+-sqrt(5))*a0;
- 1s force-balance residuals 0 at r = 0.5, 1, 2, 5 (claim 25);
- 2p circulation 2*pi, loop integral equal (claim 26).
"""

from __future__ import annotations

import math

import numpy as np

from domains.fluid_universe.theory.hydrogen_fluid import bohr_radius, force_balance
from domains.fluid_universe.theory.hydrogen_vortex import loop_circulation

RADIUS = bohr_radius()
LOOP_R = 2.0
LOOP_THETA = math.pi / 2.0
WINDING_M = 1
BALANCE_RADII = (0.5, 1.0, 2.0, 5.0)


def radial_10(r: np.ndarray, radius: float = RADIUS) -> np.ndarray:
    """Hydrogen 1s radial function, normalized as int r^2 R^2 dr = 1."""
    if radius <= 0.0:
        raise ValueError("radius must be positive")
    r = np.asarray(r, dtype=float)
    return 2.0 * radius**-1.5 * np.exp(-r / radius)


def radial_20(r: np.ndarray, radius: float = RADIUS) -> np.ndarray:
    """Hydrogen 2s radial function, normalized as int r^2 R^2 dr = 1."""
    if radius <= 0.0:
        raise ValueError("radius must be positive")
    r = np.asarray(r, dtype=float)
    return (
        1.0
        / (2.0 * math.sqrt(2.0) * radius**1.5)
        * (2.0 - r / radius)
        * np.exp(-r / (2.0 * radius))
    )


def radial_probability_20(r: np.ndarray, radius: float = RADIUS) -> np.ndarray:
    r = np.asarray(r, dtype=float)
    return r * r * radial_20(r, radius) ** 2


def branch_split_20(
    r: np.ndarray, radius: float = RADIUS
) -> dict:
    """Exact two-branch split of R_20; residual is zero by construction."""
    r = np.asarray(r, dtype=float)
    radial = radial_20(r, radius)
    magnitude = np.abs(radial)
    sign = np.sign(radial)
    residual = float(np.max(np.abs(radial - sign * magnitude)))
    return {
        "sign": sign,
        "magnitude": magnitude,
        "identity_residual": residual,
    }


def node_position(radius: float = RADIUS) -> float:
    """Analytic nodal-shell radius (zero of the 2 - r/a0 factor)."""
    if radius <= 0.0:
        raise ValueError("radius must be positive")
    return 2.0 * radius


def phase_slip_20(
    r: np.ndarray, radius: float = RADIUS
) -> float:
    """Phase jump across the shell from the sign of R_20 (0 or pi)."""
    r = np.asarray(r, dtype=float)
    phase = np.where(radial_20(r, radius) >= 0.0, 0.0, math.pi)
    return float(np.max(phase) - np.min(phase))


def overlap_10_20(radius: float = RADIUS) -> float:
    """1s-2s radial overlap integral (analytic: 0 for n != n')."""
    r = np.linspace(0.0, 120.0, 120001)
    return float(
        np.trapezoid(radial_10(r, radius) * radial_20(r, radius) * r * r, r)
    )


def norm_20(radius: float = RADIUS) -> float:
    r = np.linspace(0.0, 120.0, 120001)
    return float(np.trapezoid(radial_probability_20(r, radius), r))


def peak_radii_20(radius: float = RADIUS) -> tuple:
    """Analytic probability-peak radii (3 +- sqrt(5)) * a0."""
    if radius <= 0.0:
        raise ValueError("radius must be positive")
    return ((3.0 - math.sqrt(5.0)) * radius, (3.0 + math.sqrt(5.0)) * radius)


def balance_preserved() -> dict:
    """Frozen 1s/2p numbers recomputed through the shared modules."""
    r = np.array(list(BALANCE_RADII))
    return {
        "balance_residuals": [float(v) for v in force_balance(r, RADIUS)],
        "loop_circulation": loop_circulation(
            LOOP_R, LOOP_THETA, WINDING_M
        ),
    }


def representation_scales() -> dict:
    """Collect the representation correspondence bundle (no verdict)."""
    r = np.linspace(0.0, 60.0, 60001)
    split = branch_split_20(r)
    inner, outer = peak_radii_20()
    preserved = balance_preserved()
    return {
        "radius_source": "theory.hydrogen_fluid.bohr_radius (claim-25 derived)",
        "radius": RADIUS,
        "loop": {"r": LOOP_R, "theta": LOOP_THETA, "m": WINDING_M},
        "branch": {
            "identity_residual": split["identity_residual"],
            "node_radius": node_position(),
            "phase_slip": phase_slip_20(r),
        },
        "radial": {
            "norm": norm_20(),
            "overlap_10_20": overlap_10_20(),
            "inner_peak": inner,
            "outer_peak": outer,
        },
        "preserved": preserved,
    }
