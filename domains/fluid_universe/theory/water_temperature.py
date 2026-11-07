"""Temperature-dependent Born cavity (claim 41, ADR-032).

Water's static dielectric constant and surface tension change with
temperature.  Using

    eps_s(T) = 87.740 - 0.40008 T + 9.398e-4 T^2 - 1.410e-6 T^3,
    gamma(T) = 0.07564 - 1.4e-4 T - 3.0e-7 T^2,

the self-consistent Born cavity moves from R=2.419922 Angstrom at 0 C to
2.481377 Angstrom at 45 C, and lambda falls from 1.637567 to 1.589506 eV.
The slope is -1.068036 meV/K, 38.1%-44.5% of the observed 2.4-2.8 meV/K
peak shift.  The cavity has a nonzero but insufficient temperature
dependence; the residual points toward a temperature-dependent bare gap or
non-cavity structure.
"""

from __future__ import annotations

import math

from scipy.optimize import minimize_scalar

from domains.fluid_universe.theory.water_marcus import marcus_width_ev
from domains.fluid_universe.theory.water_well import (
    BORN_COEFFICIENT_EV_ANGSTROM,
    well_roots,
)

EV_JOULE = 1.602176634e-19
EPSILON_OPTICAL = 1.78
OPTICAL_EV = 1.70
OBSERVED_LOWER_MEV_PER_K = 2.4
OBSERVED_UPPER_MEV_PER_K = 2.8
_ANGSTROM = 1.0e-10


def water_dielectric_constant(temperature_c: float) -> float:
    """Static dielectric constant of water, 0-100 C."""
    if not 0.0 <= temperature_c <= 100.0:
        raise ValueError("temperature must lie between 0 and 100 C")
    return (
        87.740
        - 0.40008 * temperature_c
        + 9.398e-4 * temperature_c * temperature_c
        - 1.410e-6 * temperature_c**3
    )


def water_surface_tension(temperature_c: float) -> float:
    """Surface tension of water in N/m, 0-100 C."""
    if not 0.0 <= temperature_c <= 100.0:
        raise ValueError("temperature must lie between 0 and 100 C")
    return (
        0.07564
        - 1.4e-4 * temperature_c
        - 3.0e-7 * temperature_c * temperature_c
    )


def _born_depth_ev(radius_m: float, epsilon_s: float) -> float:
    radius_angstrom = radius_m / _ANGSTROM
    return (
        BORN_COEFFICIENT_EV_ANGSTROM
        / (2.0 * radius_angstrom)
        * (1.0 - 1.0 / epsilon_s)
    )


def _surface_energy_ev(radius_m: float, gamma: float) -> float:
    return 4.0 * math.pi * gamma * radius_m * radius_m / EV_JOULE


def _reorganization_ev(radius_m: float, epsilon_s: float) -> float:
    radius_angstrom = radius_m / _ANGSTROM
    return (
        BORN_COEFFICIENT_EV_ANGSTROM
        / (2.0 * radius_angstrom)
        * (1.0 / EPSILON_OPTICAL - 1.0 / epsilon_s)
    )


def born_cavity_at_temperature(temperature_c: float) -> dict:
    """Self-consistent Born cavity at a water temperature."""
    epsilon_s = water_dielectric_constant(temperature_c)
    gamma = water_surface_tension(temperature_c)

    def objective(radius_m: float) -> float:
        roots = well_roots(radius_m, _born_depth_ev(radius_m, epsilon_s))
        if roots["energy_1s_ev"] is None:
            return 1.0e6
        return roots["energy_1s_ev"] + _surface_energy_ev(radius_m, gamma)

    result = minimize_scalar(
        objective,
        bounds=(1.8e-10, 4.0e-10),
        method="bounded",
        options={"xatol": 1.0e-14},
    )
    radius_m = float(result.x)
    depth = _born_depth_ev(radius_m, epsilon_s)
    roots = well_roots(radius_m, depth)
    lambda_ev = _reorganization_ev(radius_m, epsilon_s)
    return {
        "temperature_c": temperature_c,
        "epsilon_s": epsilon_s,
        "gamma_n_m": gamma,
        "radius_m": radius_m,
        "depth_ev": depth,
        "energy_1s_ev": roots["energy_1s_ev"],
        "binding_ev": -roots["energy_1s_ev"],
        "u_1p": roots["u_1p"],
        "gap_ev": roots["transition_ev"],
        "lambda_ev": lambda_ev,
        "predicted_vde_ev": OPTICAL_EV + lambda_ev,
        "fwhm_ev": marcus_width_ev(lambda_ev, temperature_c + 273.15),
    }


def temperature_scales() -> dict:
    """Collect the 0-45 C scan and the observed-shift comparison."""
    temperatures = (0.0, 10.0, 20.0, 25.0, 30.0, 37.0, 45.0)
    scan = [born_cavity_at_temperature(temperature) for temperature in temperatures]
    cold = scan[0]
    warm = scan[-1]
    middle = scan[3]
    slope = (warm["lambda_ev"] - cold["lambda_ev"]) / 45.0 * 1000.0
    magnitude = abs(slope)
    radius_slope = (warm["radius_m"] - cold["radius_m"]) / 45.0
    geometric_slope = OPTICAL_EV / middle["radius_m"] * radius_slope * 1000.0
    geometric_magnitude = abs(geometric_slope)
    # The two cavity terms do not add in magnitude: the dielectric slope is negative and the
    # 1/R geometric slope positive, so their signed sum is the shift the model actually predicts.
    net_slope = slope + geometric_slope
    net_magnitude = abs(net_slope)
    return {
        "scan": scan,
        "lambda_slope_mev_per_k": slope,
        "geometric_slope_mev_per_k": geometric_slope,
        "net_cavity_slope_mev_per_k": net_slope,
        "cavity_terms_oppose": slope * geometric_slope < 0.0,
        "observed_shift_mev_per_k": OBSERVED_LOWER_MEV_PER_K,
        "observed_shift_upper_mev_per_k": OBSERVED_UPPER_MEV_PER_K,
        "fraction_of_lower": magnitude / OBSERVED_LOWER_MEV_PER_K,
        "fraction_of_upper": magnitude / OBSERVED_UPPER_MEV_PER_K,
        "coverage_geometric_lower": geometric_magnitude
        / OBSERVED_LOWER_MEV_PER_K,
        "coverage_geometric_upper": geometric_magnitude
        / OBSERVED_UPPER_MEV_PER_K,
        "coverage_net_lower": net_magnitude / OBSERVED_LOWER_MEV_PER_K,
        "coverage_net_upper": net_magnitude / OBSERVED_UPPER_MEV_PER_K,
        "residual_after_lambda_lower": OBSERVED_LOWER_MEV_PER_K - magnitude,
        "residual_after_lambda_upper": OBSERVED_UPPER_MEV_PER_K - magnitude,
        "residual_after_geometric_lower": OBSERVED_LOWER_MEV_PER_K
        - geometric_magnitude,
        "residual_after_geometric_upper": OBSERVED_UPPER_MEV_PER_K
        - geometric_magnitude,
        "residual_after_net_lower": OBSERVED_LOWER_MEV_PER_K - net_slope,
        "residual_after_net_upper": OBSERVED_UPPER_MEV_PER_K - net_slope,
        "width_0c_ev": cold["fwhm_ev"],
        "width_45c_ev": warm["fwhm_ev"],
        "width_change_ev": warm["fwhm_ev"] - cold["fwhm_ev"],
    }
