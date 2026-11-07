"""VDE and 1.7 eV absorption constrain the finite well (claim 35, ADR-026).

The measured vertical detachment energy of the hydrated electron is
3.27 +/- 0.10 eV (Tang et al., PCCP 12, 3653, 2010).  A 1.7 eV photon is
below that threshold, so the 1.7 eV absorption must be bound-bound.  For each
radius, solve the well depth that gives a 1s binding of 3.27 eV, then invert
for the radius where the 1s->1p gap is 1.7 eV.

The finite well satisfies both at R = 3.732 Angstrom and V0 = 4.998 eV,
with E_1s = -3.27 eV and E_1p = -1.57 eV.  The capillary/Born cavity is
R = 2.858 Angstrom and V0 = 2.487 eV, far outside this solution.  The minimal
cavity therefore cannot explain both observables; a larger, much deeper well
(soft wall or polaron) is required.
"""

from __future__ import annotations

import math

from domains.fluid_universe.theory.water_electron import capillary_cavity_radius
from domains.fluid_universe.theory.water_well import (
    BORN_COEFFICIENT_EV_ANGSTROM,
    EPSILON_OPTICAL,
    EPSILON_WATER,
    born_depth_ev,
    well_roots,
)

VDE_EV = 3.27
VDE_UNCERTAINTY_EV = 0.10
OBSERVED_ABSORPTION_EV = 1.7


def depth_for_binding(radius_m: float, binding_ev: float) -> float:
    """Well depth that gives a 1s binding energy of binding_ev."""
    if radius_m <= 0.0:
        raise ValueError("radius must be positive")
    if binding_ev <= 0.0:
        raise ValueError("binding must be positive")
    lower = 0.0
    upper = max(2.0 * binding_ev, binding_ev + 10.0)
    while True:
        roots = well_roots(radius_m, upper)
        if (
            roots["energy_1s_ev"] is not None
            and -roots["energy_1s_ev"] >= binding_ev
        ):
            break
        upper *= 2.0
        if upper > 1.0e6:
            raise ValueError("binding energy is not reachable")
    for _ in range(70):
        middle = 0.5 * (lower + upper)
        roots = well_roots(radius_m, middle)
        if (
            roots["energy_1s_ev"] is None
            or -roots["energy_1s_ev"] < binding_ev
        ):
            lower = middle
        else:
            upper = middle
    return 0.5 * (lower + upper)


def _gap_at_radius(radius_m: float, binding_ev: float) -> float | None:
    depth = depth_for_binding(radius_m, binding_ev)
    return well_roots(radius_m, depth)["transition_ev"]


def cavity_for_observables(
    binding_ev: float = VDE_EV, gap_ev: float = OBSERVED_ABSORPTION_EV
) -> dict:
    """Finite well satisfying the VDE and the 1.7 eV 1s->1p gap."""
    if binding_ev <= 0.0:
        raise ValueError("binding must be positive")
    if gap_ev <= 0.0:
        raise ValueError("gap must be positive")
    lower = 2.5e-10
    upper = 6.0e-10
    for _ in range(40):
        middle = 0.5 * (lower + upper)
        gap = _gap_at_radius(middle, binding_ev)
        if gap is None or gap > gap_ev:
            lower = middle
        else:
            upper = middle
    radius = 0.5 * (lower + upper)
    depth = depth_for_binding(radius, binding_ev)
    roots = well_roots(radius, depth)
    born = born_depth_ev(radius)
    return {
        "radius_m": radius,
        "depth_ev": depth,
        "binding_ev": -roots["energy_1s_ev"],
        "gap_ev": roots["transition_ev"],
        "u_1s": roots["u_1s"],
        "u_1p": roots["u_1p"],
        "energy_1s_ev": roots["energy_1s_ev"],
        "energy_1p_ev": roots["energy_1p_ev"],
        "born_depth_ev": born,
        "excess_ev": depth - born,
    }


def vde_scales() -> dict:
    """Collect the two-observable inversion and the capillary comparison."""
    central = cavity_for_observables(VDE_EV, OBSERVED_ABSORPTION_EV)
    lower = cavity_for_observables(
        VDE_EV - VDE_UNCERTAINTY_EV, OBSERVED_ABSORPTION_EV
    )
    upper = cavity_for_observables(
        VDE_EV + VDE_UNCERTAINTY_EV, OBSERVED_ABSORPTION_EV
    )
    radius = capillary_cavity_radius()
    born = born_depth_ev(radius)
    roots = well_roots(radius, born)
    reorganization = (
        BORN_COEFFICIENT_EV_ANGSTROM
        / (2.0 * central["radius_m"] / 1.0e-10)
        * (1.0 / EPSILON_OPTICAL - 1.0 / EPSILON_WATER)
    )
    return {
        "vde_ev": VDE_EV,
        "vde_uncertainty_ev": VDE_UNCERTAINTY_EV,
        "observed_absorption_ev": OBSERVED_ABSORPTION_EV,
        "central": central,
        "lower": lower,
        "upper": upper,
        "reorganization_ev": reorganization,
        "excess_to_reorganization": central["excess_ev"] / reorganization,
        "capillary": {
            "radius_m": radius,
            "born_depth_ev": born,
            "binding_ev": -roots["energy_1s_ev"],
            "gap_ev": roots["transition_ev"],
            "radius_ratio": central["radius_m"] / radius,
            "radius_excess_m": central["radius_m"] - radius,
            "depth_ratio": central["depth_ev"] / born,
            "depth_excess_ev": central["depth_ev"] - born,
        },
    }
