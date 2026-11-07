"""Self-consistent finite-well pressure balance (claim 37, ADR-028).

The cavity radius is not fixed at the capillary value: at fixed well depth it
minimizes the finite-well 1s energy plus the surface energy,

    E_tot(R, V0) = E_1s(R, V0) + 4 pi gamma R^2.

Minimizing this at the Born depth gives R = 3.973 Angstrom (not 2.858),
E_1s = -1.177 eV, and a 1s->1p gap of 1.133 eV.  At the VDE-matched depth
V0 = 4.611 eV the minimum is R = 4.336 Angstrom and the gap is 1.344 eV,
not 1.7 eV.  The pressure-balanced cavity is larger than the fixed-radius
estimate and its gap is smaller.

The well depth is treated as a fixed material property.  Adding the
R-dependent Born solvation -C/R separately double-counts the solvation and
collapses the cavity; it is not included here.
"""

from __future__ import annotations

import math

from scipy.optimize import minimize_scalar

from domains.fluid_universe.theory.water_electron import capillary_cavity_radius
from domains.fluid_universe.theory.water_well import born_depth_ev, well_roots

EV_JOULE = 1.602176634e-19
GAMMA_WATER = 0.0728
VDE_EV = 3.27


def surface_energy_ev(radius_m: float) -> float:
    """Surface energy 4 pi gamma R^2, in eV."""
    if radius_m <= 0.0:
        raise ValueError("radius must be positive")
    return 4.0 * math.pi * GAMMA_WATER * radius_m * radius_m / EV_JOULE


def total_energy_ev(radius_m: float, depth_ev: float) -> float | None:
    """Finite-well 1s plus surface energy, or None if the well is unbound."""
    if radius_m <= 0.0:
        raise ValueError("radius must be positive")
    if depth_ev <= 0.0:
        raise ValueError("depth must be positive")
    roots = well_roots(radius_m, depth_ev)
    if roots["energy_1s_ev"] is None:
        return None
    return roots["energy_1s_ev"] + surface_energy_ev(radius_m)


def equilibrium_radius(
    depth_ev: float,
    lower_m: float = 1.5e-10,
    upper_m: float = 6.0e-10,
) -> dict:
    """Radius minimizing the finite-well plus surface energy."""
    if depth_ev <= 0.0:
        raise ValueError("depth must be positive")
    if lower_m <= 0.0 or upper_m <= lower_m:
        raise ValueError("invalid radius bounds")

    def objective(radius_m: float) -> float:
        energy = total_energy_ev(radius_m, depth_ev)
        return 1.0e6 if energy is None else energy

    result = minimize_scalar(
        objective,
        bounds=(lower_m, upper_m),
        method="bounded",
        options={"xatol": 1.0e-14},
    )
    radius_m = float(result.x)
    roots = well_roots(radius_m, depth_ev)
    return {
        "radius_m": radius_m,
        "depth_ev": depth_ev,
        "energy_1s_ev": roots["energy_1s_ev"],
        "energy_1p_ev": roots["energy_1p_ev"],
        "binding_ev": -roots["energy_1s_ev"],
        "gap_ev": roots["transition_ev"],
        "u_1s": roots["u_1s"],
        "u_1p": roots["u_1p"],
        "surface_energy_ev": surface_energy_ev(radius_m),
        "total_energy_ev": float(result.fun),
    }


def vde_matched_depth(binding_ev: float = VDE_EV) -> dict:
    """Depth whose pressure-balanced cavity has the requested 1s binding."""
    if binding_ev <= 0.0:
        raise ValueError("binding must be positive")
    lower = binding_ev
    upper = binding_ev + 5.0
    for _ in range(60):
        middle = 0.5 * (lower + upper)
        binding = equilibrium_radius(middle)["binding_ev"]
        if binding < binding_ev:
            lower = middle
        else:
            upper = middle
    depth = 0.5 * (lower + upper)
    return equilibrium_radius(depth)


def pressure_scales() -> dict:
    """Collect the pressure-balanced scan and the VDE-matched point."""
    radius = capillary_cavity_radius()
    born = born_depth_ev(radius)
    scans = []
    for depth in (born, 3.27, 4.0, 4.5, 5.0, 5.5, 6.0):
        scans.append(equilibrium_radius(depth))
    fixed_energy = total_energy_ev(radius, born)
    return {
        "gamma_water_n_m": GAMMA_WATER,
        "born_depth_ev": born,
        "scans": scans,
        "vde_matched": vde_matched_depth(VDE_EV),
        "crude_capillary": {
            "radius_m": radius,
            "total_energy_ev": fixed_energy,
        },
    }
