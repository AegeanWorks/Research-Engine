"""Soft-wall cavity and the hard VDE depth bound (claim 36, ADR-027).

The hydrated-electron VDE is 3.27 +/- 0.10 eV.  A bound state cannot have a
binding energy larger than the well depth, so the Born depth 2.486988 eV is
already 0.783012 eV too shallow, independent of the cavity shape.  A
Woods-Saxon well

    V(r) = -V0 (1 + exp(-R/a)) / (1 + exp((r-R)/a))

is solved on a finite-difference radial grid, validated against the square
well.  Increasing the diffuseness a reduces the radius needed for a 1.7 eV
1s->1p gap but increases the required depth: at a=1.0 Angstrom the
two-observable solution is R=3.687 Angstrom, V0=5.920 eV; at a=1.5 Angstrom
it is R=3.078 Angstrom, V0=6.643 eV.  Softness does not rescue the
capillary/Born cavity.
"""

from __future__ import annotations

import math

import numpy as np
from scipy.linalg import eigh_tridiagonal

from domains.fluid_universe.theory.water_electron import capillary_cavity_radius
from domains.fluid_universe.theory.water_well import born_depth_ev

HARTREE_EV = 27.211386245988
BOHR_M = 5.29177210903e-11
VDE_EV = 3.27
VDE_UNCERTAINTY_EV = 0.10
OBSERVED_ABSORPTION_EV = 1.7


def woods_saxon_level(
    radius_m: float,
    depth_ev: float,
    diffuseness_m: float,
    angular_momentum: int,
    grid: int = 1600,
    r_max_m: float = 30.0e-10,
) -> float:
    """Lowest bound radial eigenvalue of the Woods-Saxon well, in eV."""
    if radius_m <= 0.0:
        raise ValueError("radius must be positive")
    if depth_ev <= 0.0:
        raise ValueError("depth must be positive")
    if diffuseness_m <= 0.0:
        raise ValueError("diffuseness must be positive")
    if angular_momentum not in (0, 1):
        raise ValueError("angular momentum must be 0 or 1")
    if grid < 256:
        raise ValueError("grid must be at least 256")
    if r_max_m <= radius_m:
        raise ValueError("r_max must exceed the radius")
    radius = radius_m / BOHR_M
    depth = depth_ev / HARTREE_EV
    diffuseness = diffuseness_m / BOHR_M
    r_max = r_max_m / BOHR_M
    spacing = r_max / (grid + 1)
    radial = np.arange(1, grid + 1) * spacing
    prefactor = depth * (1.0 + math.exp(-radius / diffuseness))
    with np.errstate(over="ignore"):
        potential = -prefactor / (
            1.0 + np.exp((radial - radius) / diffuseness)
        )
    diagonal = (
        1.0 / (spacing * spacing)
        + potential
        + angular_momentum
        * (angular_momentum + 1)
        / (2.0 * radial * radial)
    )
    off_diagonal = -0.5 / (spacing * spacing) * np.ones(grid - 1)
    values = eigh_tridiagonal(
        diagonal,
        off_diagonal,
        select="i",
        select_range=(0, 0),
    )[0]
    return float(values[0] * HARTREE_EV)


def depth_for_binding(
    radius_m: float,
    diffuseness_m: float,
    binding_ev: float,
    grid: int = 1600,
) -> float:
    """Well depth giving a 1s binding of binding_ev for a soft wall."""
    if radius_m <= 0.0:
        raise ValueError("radius must be positive")
    if diffuseness_m <= 0.0:
        raise ValueError("diffuseness must be positive")
    if binding_ev <= 0.0:
        raise ValueError("binding must be positive")
    lower = binding_ev * 1.0000001
    upper = binding_ev + 12.0
    while -woods_saxon_level(
        radius_m, upper, diffuseness_m, 0, grid=grid
    ) < binding_ev:
        upper += 5.0
        if upper > 200.0:
            raise ValueError("binding energy is not reachable")
    for _ in range(36):
        middle = 0.5 * (lower + upper)
        if -woods_saxon_level(
            radius_m, middle, diffuseness_m, 0, grid=grid
        ) < binding_ev:
            lower = middle
        else:
            upper = middle
    return 0.5 * (lower + upper)


def cavity_for_observables(
    diffuseness_m: float,
    binding_ev: float = VDE_EV,
    gap_ev: float = OBSERVED_ABSORPTION_EV,
    grid: int = 1600,
) -> dict:
    """Woods-Saxon cavity satisfying the VDE and the 1.7 eV gap."""
    if diffuseness_m <= 0.0:
        raise ValueError("diffuseness must be positive")
    if binding_ev <= 0.0:
        raise ValueError("binding must be positive")
    if gap_ev <= 0.0:
        raise ValueError("gap must be positive")
    lower = 2.5e-10
    upper = 8.0e-10

    def gap_at(radius_m: float) -> float | None:
        depth = depth_for_binding(
            radius_m, diffuseness_m, binding_ev, grid=grid
        )
        e_1s = woods_saxon_level(
            radius_m, depth, diffuseness_m, 0, grid=grid
        )
        e_1p = woods_saxon_level(
            radius_m, depth, diffuseness_m, 1, grid=grid
        )
        if e_1p >= 0.0:
            return None
        return e_1p - e_1s

    gap_lower = gap_at(lower)
    gap_upper = gap_at(upper)
    if gap_lower is None or gap_lower <= gap_ev:
        raise ValueError("no upper bracket in radius")
    if gap_upper is not None and gap_upper >= gap_ev:
        raise ValueError("no lower bracket in radius")
    for _ in range(30):
        middle = 0.5 * (lower + upper)
        gap = gap_at(middle)
        if gap is None or gap > gap_ev:
            lower = middle
        else:
            upper = middle
    radius = 0.5 * (lower + upper)
    depth = depth_for_binding(radius, diffuseness_m, binding_ev, grid=grid)
    e_1s = woods_saxon_level(radius, depth, diffuseness_m, 0, grid=grid)
    e_1p = woods_saxon_level(radius, depth, diffuseness_m, 1, grid=grid)
    born = born_depth_ev(radius)
    return {
        "diffuseness_m": diffuseness_m,
        "radius_m": radius,
        "depth_ev": depth,
        "energy_1s_ev": e_1s,
        "energy_1p_ev": e_1p,
        "gap_ev": e_1p - e_1s if e_1p < 0.0 else None,
        "born_depth_ev": born,
        "excess_ev": depth - born,
    }


def softwall_scales() -> dict:
    """Collect the hard depth bound and the Woods-Saxon scan."""
    radius = capillary_cavity_radius()
    born = born_depth_ev(radius)
    scans = []
    for diffuseness_angstrom in (0.001, 0.2, 0.5, 0.8, 1.0, 1.2, 1.5):
        cavity = cavity_for_observables(
            diffuseness_angstrom * 1.0e-10, VDE_EV, OBSERVED_ABSORPTION_EV
        )
        scans.append(
            {
                "diffuseness_angstrom": diffuseness_angstrom,
                **cavity,
            }
        )
    closest = min(
        scans[1:],
        key=lambda row: abs(row["radius_m"] - radius),
    )
    return {
        "vde_ev": VDE_EV,
        "vde_uncertainty_ev": VDE_UNCERTAINTY_EV,
        "observed_absorption_ev": OBSERVED_ABSORPTION_EV,
        "hard_bound": {
            "born_depth_ev": born,
            "vde_ev": VDE_EV,
            "difference_ev": VDE_EV - born,
            "ratio": VDE_EV / born,
        },
        "scans": scans,
        "closest": closest,
        "capillary": {
            "radius_m": radius,
            "born_depth_ev": born,
            "maximum_binding_ev": born,
        },
    }
