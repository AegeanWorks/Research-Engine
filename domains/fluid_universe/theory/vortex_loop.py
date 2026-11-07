"""2p core-threading loop probe (claim 61, ADR-056).

Two single-valued regularizations of the 2p (m=1) vortex at pre-registered
core scale delta0 = 0.1 * a0 (a0 from domains.fluid_universe.theory.hydrogen_fluid.bohr_radius(),
transferred from claim-60 with zero re-fit):

- Blob (phase-capped): u_theta = Gamma/2pi * r/(r^2+delta^2). Loop at
  radius r gives Gamma * r^2/(r^2+delta^2): 0.5/0.8/0.9975 of 2pi at
  r = delta0/2delta0/2. Finite everywhere; umax = Gamma/4pi*delta.
- Floor (density-floored, phase exact): circulation stays exactly 2pi on
  every loop (same quadrature as singular), but velocity is untouched,
  vmax = 1/r_min(N) on an origin-straddling grid and diverges with N.

Scale-transfer justification (predicted, not fit): near the defect both
the HO-1 profile (psi_1 ~ x) and the 2p radial profile (R_21 ~ r) are
locally linear in the transverse coordinate, so the same short-distance
cutoff scale applies; loop radii, peak (4a0) and norm are untouched.

Density-weight objection pre-answered: Wallstrom quantization is a
phase condition independent of density weight, and the regularized core
has rho > 0 everywhere, so the singular-case rho=0 loop exclusion is
unavailable. The mismatch stands regardless of density weight.
"""

from __future__ import annotations

import math

import numpy as np

LOOP_RADII = (0.1, 0.2, 2.0)
LOOP_THETA = math.pi / 2.0
WINDING_M = 1
SAMPLES = 4000
GRID_NS = (256, 512, 1024, 2048)
GRID_LENGTH = 20.0
DELTA_FACTOR = 0.1


def core_scale() -> float:
    """Pre-registered core scale delta0 = 0.1 * a0 (predicted, never scanned)."""
    from domains.fluid_universe.theory.hydrogen_fluid import bohr_radius

    return DELTA_FACTOR * float(bohr_radius(1.0, 1.0, 1.0))


def blob_fraction(r: float, delta: float) -> float:
    """Analytic loop fraction r^2/(r^2+delta^2) for the blob kernel."""
    if r < 0.0 or delta <= 0.0:
        raise ValueError("r >= 0 and delta > 0 required")
    return (r * r) / (r * r + delta * delta)


def blob_loop(r: float, delta: float, gamma: float = 2.0 * math.pi) -> float:
    """Circulation on loop radius r for blob-capped velocity."""
    return gamma * blob_fraction(r, delta)


def blob_umax(delta: float, gamma: float = 2.0 * math.pi) -> float:
    """Finite cap: max of r/(r^2+delta^2) is 1/2delta at r=delta."""
    if delta <= 0.0:
        raise ValueError("delta must be positive")
    return gamma / (2.0 * math.pi) * 0.5 / delta


def floor_vmax(n: int, length: float = GRID_LENGTH) -> float:
    """Constructional divergence: vmax = 1/r_min, r_min = dx/2, hbar=m=1."""
    if n <= 0 or length <= 0.0:
        raise ValueError("n and length must be positive")
    return 1.0 / ((length / n) / 2.0)


def numeric_blob_loop(
    r: float, delta: float, samples: int = SAMPLES, gamma: float = 2.0 * math.pi
) -> float:
    """Own trapezoid quadrature of the blob field (no project imports)."""
    from domains.fluid_universe.theory.hydrogen_vortex import azimuthal_velocity

    if samples < 16:
        raise ValueError("samples must be at least 16")
    phi = np.linspace(0.0, 2.0 * math.pi, samples, endpoint=True)
    v = azimuthal_velocity(r, LOOP_THETA, WINDING_M)
    y = np.full(samples, v * (r * r) / (r * r + delta * delta) * r * math.sin(LOOP_THETA))
    return float(np.trapezoid(y, phi))
