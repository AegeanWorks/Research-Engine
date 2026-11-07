"""Finite spherical well for the hydrated electron (claim 33, ADR-024).

The minimal closure of the cavity scale is a spherical well

    V(r) = -V0  for r < R,    V(r) = 0  outside,

with the Born solvation depth

    V0(R) = e^2/(8 pi eps0 R) (1 - 1/eps_r).

The l=0 and l=1 matching conditions give the 1s and 1p roots.  At the
capillary radius R = 2.858 Angstrom the Born well supports only the 1s state.
The 1p appears only for R > 5.290 Angstrom, and the maximum Born-depth s->p
gap is 0.615 eV -- far below the observed 1.7 eV absorption.  A 1.7 eV gap
requires a well at least 3.715 eV deep at R = 3.181 Angstrom, about 1.48 eV
deeper than Born.  This is a negative result for the minimal model, not a
derivation of the absorption.
"""

from __future__ import annotations

import math

from domains.fluid_universe.theory.water_electron import EPSILON_WATER, capillary_cavity_radius

HBAR = 1.054571817e-34
MASS = 9.1093837015e-31
EV_JOULE = 1.602176634e-19
BORN_COEFFICIENT_EV_ANGSTROM = 14.399645
EPSILON_OPTICAL = 1.78
J1_FIRST_ZERO = 4.493409457909064

# hbar^2/(2 m) in eV Angstrom^2.
KINETIC_EV_ANGSTROM2 = HBAR * HBAR / (2.0 * MASS * EV_JOULE) * 1.0e20
_ANGSTROM = 1.0e-10
_BORN_DEPTH_COEFFICIENT = (
    BORN_COEFFICIENT_EV_ANGSTROM * (1.0 - 1.0 / EPSILON_WATER) / 2.0
)


def born_depth_ev(
    radius_m: float, epsilon_r: float = EPSILON_WATER
) -> float:
    """Born solvation depth of a spherical cavity, in eV."""
    if radius_m <= 0.0:
        raise ValueError("radius must be positive")
    if epsilon_r <= 0.0:
        raise ValueError("epsilon_r must be positive")
    radius_angstrom = radius_m / _ANGSTROM
    return (
        BORN_COEFFICIENT_EV_ANGSTROM
        / (2.0 * radius_angstrom)
        * (1.0 - 1.0 / epsilon_r)
    )


def threshold_depth_ev(radius_m: float) -> float:
    """Well depth at which the 1p state reaches the continuum (kappa = pi)."""
    if radius_m <= 0.0:
        raise ValueError("radius must be positive")
    radius_angstrom = radius_m / _ANGSTROM
    return math.pi**2 * KINETIC_EV_ANGSTROM2 / (radius_angstrom * radius_angstrom)


def infinite_well_transition_ev(radius_m: float) -> float:
    """Infinite-well 1s -> 1p level spacing, in eV."""
    if radius_m <= 0.0:
        raise ValueError("radius must be positive")
    radius_angstrom = radius_m / _ANGSTROM
    spacing = (J1_FIRST_ZERO**2 - math.pi**2) * KINETIC_EV_ANGSTROM2
    return spacing / (radius_angstrom * radius_angstrom)


def _dimensionless_depth(radius_m: float, depth_ev: float) -> float:
    radius_angstrom = radius_m / _ANGSTROM
    return radius_angstrom * math.sqrt(depth_ev / KINETIC_EV_ANGSTROM2)


def _state_energy_ev(u: float, radius_m: float, depth_ev: float) -> float:
    radius_angstrom = radius_m / _ANGSTROM
    kinetic = KINETIC_EV_ANGSTROM2 * u * u / (radius_angstrom * radius_angstrom)
    return kinetic - depth_ev


def _f0(u: float, kappa: float) -> float:
    decay = math.sqrt(max(0.0, kappa * kappa - u * u))
    return u * math.cos(u) / math.sin(u) + decay


def _f1(u: float, kappa: float) -> float:
    decay = math.sqrt(max(0.0, kappa * kappa - u * u))
    sine = math.sin(u)
    cosine = math.cos(u)
    numerator = (u * u - 2.0) * sine + 2.0 * u * cosine
    denominator = sine - u * cosine
    return numerator / denominator + (decay * decay + 2.0 * decay + 2.0) / (
        decay + 1.0
    )


def _bisect(function, lower: float, upper: float, kappa: float) -> float:
    value_lower = function(lower, kappa)
    if abs(value_lower) < 1.0e-15:
        return lower
    for _ in range(120):
        middle = 0.5 * (lower + upper)
        value_middle = function(middle, kappa)
        if value_lower * value_middle <= 0.0:
            upper = middle
        else:
            lower = middle
            value_lower = value_middle
    return 0.5 * (lower + upper)


def _well_1s_root(kappa: float) -> float | None:
    if kappa <= 0.5 * math.pi + 1.0e-12:
        return None
    lower = 0.5 * math.pi + 1.0e-12
    upper = min(kappa, math.pi) - 1.0e-12
    if upper <= lower:
        return None
    return _bisect(_f0, lower, upper, kappa)


def _well_1p_root(kappa: float) -> float | None:
    if kappa <= math.pi + 1.0e-12:
        return None
    lower = math.pi + 1.0e-12
    upper = min(kappa, J1_FIRST_ZERO) - 1.0e-12
    if upper <= lower:
        return math.pi
    return _bisect(_f1, lower, upper, kappa)


_U1S_AT_PI = _well_1s_root(math.pi)


def well_roots(radius_m: float, depth_ev: float) -> dict:
    """Return the 1s/1p roots and energies for a finite spherical well."""
    if radius_m <= 0.0:
        raise ValueError("radius must be positive")
    if depth_ev <= 0.0:
        raise ValueError("depth must be positive")
    kappa = _dimensionless_depth(radius_m, depth_ev)
    u_1s = _well_1s_root(kappa)
    u_1p = _well_1p_root(kappa)
    energy_1s = (
        _state_energy_ev(u_1s, radius_m, depth_ev) if u_1s is not None else None
    )
    energy_1p = (
        _state_energy_ev(u_1p, radius_m, depth_ev) if u_1p is not None else None
    )
    transition = (
        energy_1p - energy_1s
        if energy_1s is not None and energy_1p is not None
        else None
    )
    return {
        "kappa": kappa,
        "u_1s": u_1s,
        "u_1p": u_1p,
        "energy_1s_ev": energy_1s,
        "energy_1p_ev": energy_1p,
        "transition_ev": transition,
    }


def _threshold_radius_m() -> float:
    """Radius where the Born depth equals the 1p threshold depth."""
    radius_angstrom = (
        math.pi**2 * KINETIC_EV_ANGSTROM2 / _BORN_DEPTH_COEFFICIENT
    )
    return radius_angstrom * _ANGSTROM


def _threshold_gap_ev(radius_m: float) -> float:
    depth = threshold_depth_ev(radius_m)
    return -_state_energy_ev(_U1S_AT_PI, radius_m, depth)


def _max_born_gap_ev() -> float:
    radius = _threshold_radius_m()
    return -_state_energy_ev(
        _U1S_AT_PI, radius, born_depth_ev(radius)
    )


def _infinite_radius_for_transition(energy_ev: float) -> float:
    if energy_ev <= 0.0:
        raise ValueError("energy must be positive")
    spacing = (J1_FIRST_ZERO**2 - math.pi**2) * KINETIC_EV_ANGSTROM2
    return math.sqrt(spacing / energy_ev) * _ANGSTROM


def required_depth_ev(radius_m: float, target_ev: float = 1.7) -> float | None:
    """Depth needed for an s->p gap of target_ev, or None if unreachable."""
    if radius_m <= 0.0:
        raise ValueError("radius must be positive")
    if target_ev <= 0.0:
        raise ValueError("target must be positive")
    threshold = threshold_depth_ev(radius_m)
    if _threshold_gap_ev(radius_m) > target_ev + 1.0e-12:
        return None
    if target_ev >= infinite_well_transition_ev(radius_m) - 1.0e-12:
        return None
    if abs(_threshold_gap_ev(radius_m) - target_ev) <= 1.0e-9:
        return threshold
    lower = threshold
    upper = max(10.0 * threshold, 10.0 * target_ev)
    while True:
        gap = well_roots(radius_m, upper)["transition_ev"]
        if gap is not None and gap >= target_ev:
            break
        upper *= 2.0
        if upper > 1.0e6:
            return None
    for _ in range(120):
        middle = 0.5 * (lower + upper)
        gap = well_roots(radius_m, middle)["transition_ev"]
        if gap is None or gap < target_ev:
            lower = middle
        else:
            upper = middle
    return 0.5 * (lower + upper)


def minimum_required_depth(target_ev: float = 1.7) -> dict:
    """Minimum depth over radii that yields an s->p gap of target_ev."""
    if target_ev <= 0.0:
        raise ValueError("target must be positive")
    radius_max = _infinite_radius_for_transition(target_ev)
    radius_min = 1.0e-10
    if _threshold_gap_ev(radius_min) < target_ev:
        raise ValueError("target is below the reachable threshold gap")
    lower = radius_min
    upper = radius_max
    for _ in range(120):
        middle = 0.5 * (lower + upper)
        if _threshold_gap_ev(middle) > target_ev:
            lower = middle
        else:
            upper = middle
    radius = 0.5 * (lower + upper)
    required = threshold_depth_ev(radius)
    born = born_depth_ev(radius)
    return {
        "radius_m": radius,
        "required_depth_ev": required,
        "born_depth_ev": born,
        "excess_ev": required - born,
        "threshold_gap_ev": _threshold_gap_ev(radius),
    }


def well_scales() -> dict:
    """Collect the finite-well scales used by the report and the tests."""
    radius = capillary_cavity_radius()
    born = born_depth_ev(radius)
    capillary = well_roots(radius, born)
    threshold_depth = threshold_depth_ev(radius)
    threshold_roots = well_roots(radius, threshold_depth)
    threshold_gap = -threshold_roots["energy_1s_ev"]
    radius_3p2 = 3.2e-10
    required_3p2 = required_depth_ev(radius_3p2, 1.7)
    born_3p2 = born_depth_ev(radius_3p2)
    minimum = minimum_required_depth(1.7)
    optical = (
        BORN_COEFFICIENT_EV_ANGSTROM
        / (2.0 * minimum["radius_m"] / _ANGSTROM)
        * (1.0 / EPSILON_OPTICAL - 1.0 / EPSILON_WATER)
    )
    depth_scan = []
    for depth in (born, 5.0, 10.0, 30.0):
        roots = well_roots(radius, depth)
        depth_scan.append(
            {
                "depth_ev": depth,
                "kappa": roots["kappa"],
                "u_1s": roots["u_1s"],
                "u_1p": roots["u_1p"],
                "transition_ev": roots["transition_ev"],
            }
        )
    return {
        "model": {
            "epsilon_water": EPSILON_WATER,
            "epsilon_optical": EPSILON_OPTICAL,
            "born_coefficient_ev_angstrom": BORN_COEFFICIENT_EV_ANGSTROM,
            "j1_first_zero": J1_FIRST_ZERO,
        },
        "capillary": {
            "radius_m": radius,
            "born_depth_ev": born,
            "kappa": capillary["kappa"],
            "u_1s": capillary["u_1s"],
            "u_1p": capillary["u_1p"],
            "energy_1s_ev": capillary["energy_1s_ev"],
            "energy_1p_ev": capillary["energy_1p_ev"],
            "transition_ev": capillary["transition_ev"],
            "binding_ev": -capillary["energy_1s_ev"],
        },
        "threshold": {
            "depth_at_capillary_ev": threshold_depth,
            "gap_at_capillary_ev": threshold_gap,
            "radius_m": _threshold_radius_m(),
            "max_born_gap_ev": _max_born_gap_ev(),
        },
        "depth_scan": depth_scan,
        "inverse": {
            "radius_3p2_m": radius_3p2,
            "required_depth_3p2_ev": required_3p2,
            "born_depth_3p2_ev": born_3p2,
            "excess_3p2_ev": required_3p2 - born_3p2,
            "minimum": minimum,
            "optical_polarization_ev": optical,
            "optical_polarization_ratio": minimum["excess_ev"] / optical,
        },
        "infinite_well": {
            "transition_at_4p703_ev": infinite_well_transition_ev(
                4.703128884e-10
            ),
            "radius_for_1p7_m": _infinite_radius_for_transition(1.7),
        },
    }
