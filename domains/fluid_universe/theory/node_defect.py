"""Two-branch defect representation of nodal states (claim 46, ADR-038).

Representation-only, zero free parameters. The first-excited
harmonic-oscillator state is written as an exact two-branch split

    psi_1(x) = s(x) * |psi_1(x)|,   s(x) = sign(x),

so the pi phase slip across the x=0 node lives in the branch datum
s(x), while |psi_1| is smooth. Both branches share the regular
quantum pressure away from the node; the node itself (rho=0) is
excluded from fluid-point claims, per claim 24. Single-valuedness
of psi is enforced by the Wallstrom quantization condition on
closed loops (L2 gate): circulation is 2*pi*hbar*m/m_e, atomic
units 2*pi*m. No dynamics through the node is asserted; the
ground-state Ermakov reduction (claims 22-23) and the hydrogen-2p
vortex identification (claim 26) are preserved untouched.

Correspondence (frozen numbers, recomputed live from existing
modules, never refit):
- node: density 0 at x=0, phase slip pi, gradient max pi/(2*dx),
  log-log slope -1 over N=256/512/1024/2048 (claim 24);
- 2p: circulation 2*pi, loop integral at r=2,theta=pi/2 equal,
  azimuthal velocity 0.5, angular momentum 1.0, most-probable
  radius 4*a0, radial norm 1.0 (claim 26);
- node-free control: Gaussian variance hbar/(2*m*omega) = 0.5
  (Nelson OU reference, L4), Ermakov fixed point unchanged.
"""

from __future__ import annotations

import math

import numpy as np

from domains.fluid_universe.theory.excited_fluid import (
    excited_density,
    excited_quantum_pressure_regular,
    excited_wavefunction,
    phase_gradient_max,
    phase_slip,
    scaling_slope,
)
from domains.fluid_universe.theory.hydrogen_vortex import (
    angular_momentum,
    azimuthal_velocity,
    circulation,
    loop_circulation,
    most_probable_radius,
    radial_probability,
)

GRID_NS = (256, 512, 1024, 2048)
GRID_LENGTH = 20.0
LOOP_R = 2.0
LOOP_THETA = math.pi / 2.0
WINDING_M = 1


def branch_split(
    x: np.ndarray, omega: float, hbar: float = 1.0, mass: float = 1.0
) -> dict:
    """Exact two-branch split of the first-excited state.

    Returns sign branch s(x), smooth magnitude |psi|, and the
    identity residual max|psi - s*|psi||, which is zero by
    construction (no fit, no smoothing parameter).
    """
    x = np.asarray(x, dtype=float)
    psi = excited_wavefunction(x, omega, hbar, mass)
    magnitude = np.abs(psi)
    sign = np.sign(psi)
    residual = float(np.max(np.abs(psi - sign * magnitude)))
    return {
        "sign": sign,
        "magnitude": magnitude,
        "identity_residual": residual,
        "node_density": float(excited_density(np.array([0.0]), omega, hbar, mass)[0]),
        "phase_slip": phase_slip(psi),
    }


def branch_regular_pressure_match(
    x: np.ndarray, omega: float, hbar: float = 1.0, mass: float = 1.0
) -> dict:
    """Regular quantum pressure evaluated branch-wise away from node.

    The regular form is shared by both branches; points with
    x == 0 are excluded (defect, not a fluid point).
    """
    x = np.asarray(x, dtype=float)
    mask = x != 0.0
    pressure = excited_quantum_pressure_regular(x[mask], omega, hbar, mass)
    return {
        "n_branch_points": int(np.count_nonzero(mask)),
        "n_excluded": int(x.size - np.count_nonzero(mask)),
        "pressure finite": bool(np.all(np.isfinite(pressure))),
    }


def node_scaling() -> dict:
    """Phase-gradient maximum scaling over the frozen grid set."""
    dx_values = []
    maxima = []
    for n in GRID_NS:
        dx = GRID_LENGTH / n
        x = (np.arange(n) - n // 2) * dx
        dx_values.append(dx)
        maxima.append(
            phase_gradient_max(excited_wavefunction(x, 1.0), dx)
        )
    return {
        "grid_ns": list(GRID_NS),
        "grid_length": GRID_LENGTH,
        "dx_values": [float(v) for v in dx_values],
        "maxima": [float(v) for v in maxima],
        "slope": scaling_slope(np.array(dx_values), np.array(maxima)),
    }


def vortex_gate() -> dict:
    """Frozen 2p vortex numbers, recomputed from the existing module."""
    r = np.linspace(0.0, 80.0, 160001)
    return {
        "circulation": circulation(WINDING_M),
        "loop_circulation": loop_circulation(
            LOOP_R, LOOP_THETA, WINDING_M
        ),
        "azimuthal_velocity": azimuthal_velocity(
            LOOP_R, LOOP_THETA, WINDING_M
        ),
        "angular_momentum": angular_momentum(WINDING_M),
        "most_probable_radius": most_probable_radius(1.0),
        "radial_norm": float(np.trapezoid(radial_probability(r, 1.0), r)),
    }


def representation_scales() -> dict:
    """Collect the representation correspondence bundle (no verdict)."""
    x256 = (np.arange(256) - 128) * (GRID_LENGTH / 256)
    split = branch_split(x256, 1.0)
    return {
        "grids": {"ns": list(GRID_NS), "length": GRID_LENGTH},
        "loop": {"r": LOOP_R, "theta": LOOP_THETA, "m": WINDING_M},
        "units": {"omega": 1.0, "hbar": 1.0, "mass": 1.0},
        "branch": {
            "identity_residual": split["identity_residual"],
            "node_density": split["node_density"],
            "phase_slip": split["phase_slip"],
        },
        "scaling": node_scaling(),
        "vortex": vortex_gate(),
    }
