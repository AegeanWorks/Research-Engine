"""Bound-free absorption in the finite spherical well (claim 34, ADR-025).

The hydrated-electron band is broad, so the natural alternative to the
bound-bound 1s->1p line is a bound-free 1s->p transition.  The same finite
well is used: the 1s state from ``theory.water_well`` and the p-wave
continuum, matched at the cavity radius and normalized asymptotically.

The oscillator strength is

    f(omega) = (2/3) omega |<f|r|i>|^2

in atomic units.  The TRK sum rule (integrated to 5 Hartree) is about 0.992
for the Born-depth well, which validates the continuum normalization.

At the capillary radius and Born depth the continuum peaks at 1.025 eV,
not 1.7 eV.  A 1.7 eV peak needs an extra 1.198 eV of well depth
(V0 = 3.685 eV), about 0.87 of the optical reorganization energy.  This is a
target for a band-offset or polaron correction, not a fitted parameter.
"""

from __future__ import annotations

import math

import numpy as np

from domains.fluid_universe.theory.water_electron import capillary_cavity_radius
from domains.fluid_universe.theory.water_well import (
    BORN_COEFFICIENT_EV_ANGSTROM,
    EPSILON_OPTICAL,
    EPSILON_WATER,
    born_depth_ev,
    well_roots,
)

HARTREE_EV = 27.211386245988
BOHR_M = 5.29177210903e-11
_ANGSTROM = 1.0e-10


def _j1(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        result = np.sin(x) / (x * x) - np.cos(x) / x
    return np.where(x == 0.0, 0.0, result)


def _y1(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        return -np.cos(x) / (x * x) - np.sin(x) / x


def _j1_prime(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        result = np.sin(x) / x - 2.0 * _j1(x) / x
    return np.where(x == 0.0, 1.0 / 3.0, result)


def _y1_prime(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        return -np.cos(x) / x - 2.0 * _y1(x) / x


def bound_state(radius_m: float, depth_ev: float, grid: int = 20000) -> dict:
    """Return the normalized 1s state of the finite well."""
    if radius_m <= 0.0:
        raise ValueError("radius must be positive")
    if depth_ev <= 0.0:
        raise ValueError("depth must be positive")
    if grid < 256:
        raise ValueError("grid must be at least 256")
    roots = well_roots(radius_m, depth_ev)
    if roots["u_1s"] is None:
        raise ValueError("the well has no bound 1s state")
    radius_bohr = radius_m / BOHR_M
    u_1s = roots["u_1s"]
    k_in = u_1s / radius_bohr
    energy_ha = roots["energy_1s_ev"] / HARTREE_EV
    kappa = math.sqrt(-2.0 * energy_ha)
    radial = np.linspace(0.0, radius_bohr, grid)
    inside = np.trapezoid(np.sin(k_in * radial) ** 2, radial)
    outside = math.sin(k_in * radius_bohr) ** 2 / (2.0 * kappa)
    amplitude = 1.0 / math.sqrt(inside + outside)
    norm = amplitude * amplitude * (inside + outside)
    return {
        "radius_m": radius_m,
        "depth_ev": depth_ev,
        "u_1s": u_1s,
        "energy_ev": roots["energy_1s_ev"],
        "k_in": k_in,
        "kappa_out": kappa,
        "amplitude": amplitude,
        "norm": norm,
        "threshold_ev": -roots["energy_1s_ev"],
    }


def _dipole_from_state(state: dict, photon_ev: float, grid: int) -> float:
    radius_bohr = state["radius_m"] / BOHR_M
    depth_ha = state["depth_ev"] / HARTREE_EV
    energy_ha = state["energy_ev"] / HARTREE_EV
    omega_ha = photon_ev / HARTREE_EV
    final_ha = energy_ha + omega_ha
    if final_ha <= 0.0:
        return 0.0
    k_out = math.sqrt(2.0 * final_ha)
    k_in = math.sqrt(2.0 * (final_ha + depth_ha))
    x_out = k_out * radius_bohr
    x_in = k_in * radius_bohr
    log_in = k_in * _j1_prime(x_in) / _j1(x_in)
    alpha = (log_in * _j1(x_out) - k_out * _j1_prime(x_out)) / (
        k_out * _y1_prime(x_out) - log_in * _y1(x_out)
    )
    normalization = math.sqrt(2.0 * k_out / math.pi) / math.sqrt(
        1.0 + alpha * alpha
    )
    inside_amplitude = (
        normalization
        * (_j1(x_out) + alpha * _y1(x_out))
        / _j1(x_in)
    )
    radial_in = np.linspace(0.0, radius_bohr, grid)
    bound_in = state["amplitude"] * np.sin(state["k_in"] * radial_in)
    continuum_in = inside_amplitude * radial_in * _j1(k_in * radial_in)
    integral_in = np.trapezoid(
        continuum_in * radial_in * bound_in, radial_in
    )
    tail = 20.0 / state["kappa_out"]
    radial_out = np.linspace(radius_bohr, radius_bohr + tail, grid)
    bound_out = (
        state["amplitude"]
        * math.sin(state["k_in"] * radius_bohr)
        * np.exp(-state["kappa_out"] * (radial_out - radius_bohr))
    )
    continuum_out = (
        normalization
        * radial_out
        * (_j1(k_out * radial_out) + alpha * _y1(k_out * radial_out))
    )
    integral_out = np.trapezoid(
        continuum_out * radial_out * bound_out, radial_out
    )
    return float(integral_in + integral_out)


def dipole_integral(
    radius_m: float,
    depth_ev: float,
    photon_ev: float,
    points: int = 20000,
) -> float:
    """Radial dipole integral for the 1s -> p continuum, in atomic units."""
    if photon_ev <= 0.0:
        raise ValueError("photon must be positive")
    state = bound_state(radius_m, depth_ev, grid=points)
    return _dipole_from_state(state, photon_ev, points)


def _oscillator_from_state(state: dict, photon_ev: float, grid: int) -> float:
    if photon_ev <= state["threshold_ev"]:
        return 0.0
    integral = _dipole_from_state(state, photon_ev, grid)
    omega_ha = photon_ev / HARTREE_EV
    return (2.0 / 3.0) * omega_ha * integral * integral


def oscillator_strength(
    radius_m: float,
    depth_ev: float,
    photon_ev: float,
    points: int = 20000,
) -> float:
    """Oscillator strength at a photon energy, in atomic units."""
    if photon_ev <= 0.0:
        raise ValueError("photon must be positive")
    state = bound_state(radius_m, depth_ev, grid=points)
    return _oscillator_from_state(state, photon_ev, points)


def oscillator_sum_rule(
    radius_m: float,
    depth_ev: float,
    grid: int = 20000,
    points: int = 600,
    max_ev: float = 136.0,
) -> float:
    """Integrate the continuum oscillator strength from threshold to max_ev."""
    if max_ev <= 0.0:
        raise ValueError("max_ev must be positive")
    if points < 8:
        raise ValueError("points must be at least 8")
    state = bound_state(radius_m, depth_ev, grid=grid)
    energies = np.linspace(state["threshold_ev"] + 0.01, max_ev, points)
    strengths = np.array(
        [_oscillator_from_state(state, photon, grid) for photon in energies]
    )
    return float(np.trapezoid(strengths, energies) / HARTREE_EV)


def peak_absorption(
    radius_m: float,
    depth_ev: float,
    grid: int = 20000,
    points: int = 81,
) -> dict:
    """Locate the continuum absorption peak for one well."""
    if points < 8:
        raise ValueError("points must be at least 8")
    state = bound_state(radius_m, depth_ev, grid=grid)
    photon_min = max(0.05, state["threshold_ev"] + 0.05)
    photon_max = max(4.0, 2.5 * state["threshold_ev"] + 1.0)
    energies = np.linspace(photon_min, photon_max, points)
    strengths = np.array(
        [_oscillator_from_state(state, photon, grid) for photon in energies]
    )
    index = int(np.argmax(strengths))
    if 0 < index < len(energies) - 1:
        left = strengths[index - 1]
        middle = strengths[index]
        right = strengths[index + 1]
        denominator = left - 2.0 * middle + right
        shift = 0.5 * (left - right) / denominator if denominator != 0.0 else 0.0
        step = energies[1] - energies[0]
        peak_energy = energies[index] + shift * step
        peak_strength = middle - 0.25 * (left - right) * shift
    else:
        peak_energy = energies[index]
        peak_strength = strengths[index]
    return {
        "threshold_ev": state["threshold_ev"],
        "photon_min_ev": photon_min,
        "photon_max_ev": photon_max,
        "peak_ev": float(peak_energy),
        "peak_strength": float(peak_strength),
        "points": points,
        "grid": grid,
    }


def required_extra_depth(
    radius_m: float,
    target_ev: float = 1.7,
    grid: int = 12000,
    points: int = 41,
) -> dict:
    """Depth beyond Born needed to put the continuum peak at target_ev."""
    if radius_m <= 0.0:
        raise ValueError("radius must be positive")
    if target_ev <= 0.0:
        raise ValueError("target must be positive")
    born = born_depth_ev(radius_m)
    lower = born
    upper = born + max(2.0, target_ev)
    while peak_absorption(radius_m, upper, grid=grid, points=points)[
        "peak_ev"
    ] <= target_ev:
        upper += max(1.0, target_ev)
        if upper > born + 20.0:
            raise ValueError("target peak is not reachable by this well")
    for _ in range(24):
        middle = 0.5 * (lower + upper)
        peak = peak_absorption(radius_m, middle, grid=grid, points=points)
        if peak["peak_ev"] < target_ev:
            lower = middle
        else:
            upper = middle
    depth = 0.5 * (lower + upper)
    final = peak_absorption(radius_m, depth, grid=20000, points=81)
    for _ in range(4):
        error = target_ev - final["peak_ev"]
        if abs(error) < 1.0e-4:
            break
        step = 0.05 if error > 0.0 else -0.05
        probe = peak_absorption(
            radius_m, depth + step, grid=20000, points=81
        )
        slope = (probe["peak_ev"] - final["peak_ev"]) / step
        if slope <= 1.0e-6:
            break
        depth = max(born, depth + error / slope)
        final = peak_absorption(radius_m, depth, grid=20000, points=81)
    return {
        "depth_ev": depth,
        "extra_ev": depth - born,
        "peak_ev": final["peak_ev"],
        "peak_strength": final["peak_strength"],
        "threshold_ev": final["threshold_ev"],
    }


def absorption_scales() -> dict:
    """Collect the bound-free scales used by the report and the tests."""
    radius = capillary_cavity_radius()
    born = born_depth_ev(radius)
    born_peak = peak_absorption(radius, born, grid=20000, points=81)
    sum_rule = oscillator_sum_rule(
        radius, born, grid=20000, points=600, max_ev=136.0
    )
    required = required_extra_depth(radius, 1.7, grid=12000, points=41)
    reorganization = (
        BORN_COEFFICIENT_EV_ANGSTROM
        / (2.0 * radius / _ANGSTROM)
        * (1.0 / EPSILON_OPTICAL - 1.0 / EPSILON_WATER)
    )
    scan = []
    for depth in (
        born,
        3.0,
        3.3,
        3.6,
        required["depth_ev"],
        born + reorganization,
    ):
        state = bound_state(radius, depth, grid=20000)
        peak = peak_absorption(radius, depth, grid=20000, points=81)
        scan.append(
            {
                "depth_ev": depth,
                "binding_ev": state["threshold_ev"],
                "peak_ev": peak["peak_ev"],
                "peak_strength": peak["peak_strength"],
            }
        )
    return {
        "model": {
            "epsilon_water": EPSILON_WATER,
            "epsilon_optical": EPSILON_OPTICAL,
            "hartree_ev": HARTREE_EV,
            "bohr_m": BOHR_M,
        },
        "capillary": {
            "radius_m": radius,
            "born_depth_ev": born,
            "binding_ev": born_peak["threshold_ev"],
            "peak_ev": born_peak["peak_ev"],
            "peak_strength": born_peak["peak_strength"],
            "sum_rule": sum_rule,
        },
        "required": required,
        "reorganization_ev": reorganization,
        "extra_to_reorganization": required["extra_ev"] / reorganization,
        "scan": scan,
    }
