"""Water reorganization and the VDE-optical difference (claim 38, ADR-029).

Water's static and optical dielectric constants differ strongly.  The
reorganization energy

    lambda(R) = e^2 (1/eps_inf - 1/eps_s) / (8 pi eps0 R)

is the natural link between the vertical detachment energy and the optical
absorption.  At the capillary radius R = 2.858 Angstrom, lambda = 1.383 eV,
while the measured difference is 3.27 - 1.70 = 1.57 eV; the residual is
0.187 eV (11.9%).  The difference matches lambda at R = 2.518 Angstrom,
0.881x the capillary radius.  The pressure-balanced radius 3.973 Angstrom
gives only 0.995 eV and is inconsistent.

This is a phenomenological relation, not a full two-state Marcus
calculation.  The predicted VDE at the capillary radius is 3.083 eV,
1.87 sigma below the measured 3.27 +/- 0.10 eV.
"""

from __future__ import annotations

import math

from domains.fluid_universe.theory.water_electron import capillary_cavity_radius
from domains.fluid_universe.theory.water_pressure import equilibrium_radius
from domains.fluid_universe.theory.water_well import (
    BORN_COEFFICIENT_EV_ANGSTROM,
    EPSILON_OPTICAL,
    EPSILON_WATER,
    born_depth_ev,
)

VDE_EV = 3.27
VDE_UNCERTAINTY_EV = 0.10
OPTICAL_EV = 1.70
_ANGSTROM = 1.0e-10


def _dielectric_contrast(
    epsilon_s: float = EPSILON_WATER, epsilon_opt: float = EPSILON_OPTICAL
) -> float:
    if epsilon_s <= 1.0:
        raise ValueError("epsilon_s must exceed 1")
    if epsilon_opt <= 0.0 or epsilon_opt >= epsilon_s:
        raise ValueError("epsilon_opt must lie between 0 and epsilon_s")
    return 1.0 / epsilon_opt - 1.0 / epsilon_s


def reorganization_energy_ev(
    radius_m: float,
    epsilon_s: float = EPSILON_WATER,
    epsilon_opt: float = EPSILON_OPTICAL,
) -> float:
    """Solvent reorganization energy for a cavity of radius R, in eV."""
    if radius_m <= 0.0:
        raise ValueError("radius must be positive")
    contrast = _dielectric_contrast(epsilon_s, epsilon_opt)
    radius_angstrom = radius_m / _ANGSTROM
    return BORN_COEFFICIENT_EV_ANGSTROM * contrast / (2.0 * radius_angstrom)


def radius_for_difference(
    difference_ev: float,
    epsilon_s: float = EPSILON_WATER,
    epsilon_opt: float = EPSILON_OPTICAL,
) -> float:
    """Radius whose reorganization energy equals difference_ev."""
    if difference_ev <= 0.0:
        raise ValueError("difference must be positive")
    contrast = _dielectric_contrast(epsilon_s, epsilon_opt)
    radius_angstrom = (
        BORN_COEFFICIENT_EV_ANGSTROM * contrast / (2.0 * difference_ev)
    )
    return radius_angstrom * _ANGSTROM


def reorganization_scales() -> dict:
    """Collect the capillary, required and pressure-balanced comparisons."""
    radius = capillary_cavity_radius()
    lambda_capillary = reorganization_energy_ev(radius)
    observed_difference = VDE_EV - OPTICAL_EV
    predicted_vde = OPTICAL_EV + lambda_capillary
    residual = predicted_vde - VDE_EV
    required_radius = radius_for_difference(observed_difference)
    pressure_radius = equilibrium_radius(born_depth_ev(radius))["radius_m"]
    lambda_pressure = reorganization_energy_ev(pressure_radius)
    return {
        "epsilon_s": EPSILON_WATER,
        "epsilon_opt": EPSILON_OPTICAL,
        "vde_ev": VDE_EV,
        "vde_uncertainty_ev": VDE_UNCERTAINTY_EV,
        "optical_ev": OPTICAL_EV,
        "observed_difference_ev": observed_difference,
        "capillary": {
            "radius_m": radius,
            "lambda_ev": lambda_capillary,
            "predicted_vde_ev": predicted_vde,
            "residual_ev": residual,
            "relative_residual": -residual / observed_difference,
            "sigma": -residual / VDE_UNCERTAINTY_EV,
        },
        "required": {
            "radius_m": required_radius,
            "radius_ratio": required_radius / radius,
        },
        "pressure": {
            "radius_m": pressure_radius,
            "lambda_ev": lambda_pressure,
            "lambda_ratio": lambda_pressure / observed_difference,
            "residual_ev": observed_difference - lambda_pressure,
        },
    }
