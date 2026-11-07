"""Self-consistent Born cavity synthesis (claim 39, ADR-030).

The cavity radius is set by the R-dependent Born solvation, not by a fixed
well depth.  Minimize

    E_tot(R) = E_1s(R, Born(R)) + 4 pi gamma R^2.

The equilibrium is R = 2.444456 Angstrom, V0 = Born(R) = 2.907799 eV,
E_1s = -0.436572 eV, with no bound 1p.  The water reorganization energy at
this radius is 1.617133 eV, so the Marcus relation predicts
VDE = 1.70 + 1.617133 = 3.317133 eV, within 0.47 sigma of the measured
3.27 +/- 0.10 eV.  The radius required by the observed VDE-optical
difference is 2.517841 Angstrom, only 3.0% above the equilibrium.

The 1.7 eV feature is a solvent reorganization transition, not a static
1s->1p gap: the well has no bound 1p.
"""

from __future__ import annotations

import math

from scipy.optimize import minimize_scalar

from domains.fluid_universe.theory.water_electron import capillary_cavity_radius
from domains.fluid_universe.theory.water_pressure import equilibrium_radius, surface_energy_ev
from domains.fluid_universe.theory.water_reorganization import (
    radius_for_difference,
    reorganization_energy_ev,
)
from domains.fluid_universe.theory.water_well import born_depth_ev, well_roots

VDE_EV = 3.27
VDE_UNCERTAINTY_EV = 0.10
OPTICAL_EV = 1.70


def born_cavity_energy(radius_m: float) -> float | None:
    """E_1s(R, Born(R)) plus the surface energy, or None if unbound."""
    if radius_m <= 0.0:
        raise ValueError("radius must be positive")
    depth = born_depth_ev(radius_m)
    roots = well_roots(radius_m, depth)
    if roots["energy_1s_ev"] is None:
        return None
    return roots["energy_1s_ev"] + surface_energy_ev(radius_m)


def born_cavity_equilibrium(
    lower_m: float = 1.8e-10, upper_m: float = 4.0e-10
) -> dict:
    """Minimize the Born cavity energy over the radius."""
    if lower_m <= 0.0 or upper_m <= lower_m:
        raise ValueError("invalid radius bounds")

    def objective(radius_m: float) -> float:
        energy = born_cavity_energy(radius_m)
        return 1.0e6 if energy is None else energy

    result = minimize_scalar(
        objective,
        bounds=(lower_m, upper_m),
        method="bounded",
        options={"xatol": 1.0e-14},
    )
    radius_m = float(result.x)
    depth = born_depth_ev(radius_m)
    roots = well_roots(radius_m, depth)
    return {
        "radius_m": radius_m,
        "depth_ev": depth,
        "energy_1s_ev": roots["energy_1s_ev"],
        "energy_1p_ev": roots["energy_1p_ev"],
        "binding_ev": -roots["energy_1s_ev"],
        "gap_ev": roots["transition_ev"],
        "u_1s": roots["u_1s"],
        "u_1p": roots["u_1p"],
        "surface_energy_ev": surface_energy_ev(radius_m),
        "total_energy_ev": float(result.fun),
    }


def born_cavity_scales() -> dict:
    """Collect the Born cavity and the water reorganization synthesis."""
    equilibrium = born_cavity_equilibrium()
    radius = equilibrium["radius_m"]
    lam = reorganization_energy_ev(radius)
    observed_difference = VDE_EV - OPTICAL_EV
    predicted_vde = OPTICAL_EV + lam
    residual = predicted_vde - VDE_EV
    required_radius = radius_for_difference(observed_difference)
    capillary_radius = capillary_cavity_radius()
    pressure_radius = equilibrium_radius(
        born_depth_ev(capillary_radius)
    )["radius_m"]
    return {
        "vde_ev": VDE_EV,
        "vde_uncertainty_ev": VDE_UNCERTAINTY_EV,
        "optical_ev": OPTICAL_EV,
        "observed_difference_ev": observed_difference,
        "equilibrium": equilibrium,
        "synthesis": {
            "lambda_ev": lam,
            "predicted_vde_ev": predicted_vde,
            "residual_ev": residual,
            "sigma": residual / VDE_UNCERTAINTY_EV,
            "required_radius_m": required_radius,
            "required_ratio": required_radius / radius,
            "capillary_ratio": capillary_radius / radius,
            "pressure_ratio": pressure_radius / radius,
        },
    }
