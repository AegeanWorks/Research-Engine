"""Dispersive shallow-water horizon (claim 29, ADR-020).

The full shallow-water dispersion is

    omega_f^2 = (g k + gamma k^3 / rho) tanh(k h).

The horizon for an outgoing wave of frequency omega in an inward flow V is
where the group velocity equals the flow:

    k c_g(k) + omega_f(k) = omega,   V = c_g(k),   r = Q / (2 pi h V).

At low frequency r -> r_H = Q/(2 pi h c).  Above the capillary frequency
omega_c = sqrt(2 g / ell_c) the horizon shifts substantially.
"""

from __future__ import annotations

import math

from domains.fluid_universe.theory.water_analogue import GRAVITY, capillary_length, sound_speed


def dispersion(
    k: float,
    depth: float,
    gamma: float = 0.0728,
    density: float = 998.0,
    gravity: float = GRAVITY,
) -> float:
    if k < 0.0 or depth <= 0.0:
        raise ValueError("k must be non-negative and depth positive")
    return math.sqrt(
        max(0.0, (gravity * k + gamma * k**3 / density) * math.tanh(k * depth))
    )


def group_velocity(
    k: float,
    depth: float,
    gamma: float = 0.0728,
    density: float = 998.0,
    gravity: float = GRAVITY,
) -> float:
    if k < 0.0 or depth <= 0.0:
        raise ValueError("k must be non-negative and depth positive")
    if k == 0.0:
        return sound_speed(depth, gravity)
    omega = dispersion(k, depth, gamma, density, gravity)
    tangent = math.tanh(k * depth)
    sech_squared = 1.0 - tangent * tangent
    numerator = (
        (gravity + 3.0 * gamma * k * k / density) * tangent
        + (gravity * k + gamma * k**3 / density) * depth * sech_squared
    )
    return numerator / (2.0 * omega)


def horizon_wavenumber(
    omega: float,
    depth: float,
    gamma: float = 0.0728,
    density: float = 998.0,
    gravity: float = GRAVITY,
    maximum: float = 1e5,
) -> float:
    if omega <= 0.0 or depth <= 0.0 or maximum <= 0.0:
        raise ValueError("omega, depth and maximum must be positive")

    def residual(k: float) -> float:
        return k * group_velocity(k, depth, gamma, density, gravity) + dispersion(
            k, depth, gamma, density, gravity
        ) - omega

    lower = 1e-12
    upper = maximum
    if residual(lower) > 0.0 or residual(upper) < 0.0:
        raise ValueError("no bracket for the horizon wavenumber")
    for _ in range(200):
        middle = 0.5 * (lower + upper)
        if residual(middle) < 0.0:
            lower = middle
        else:
            upper = middle
    return 0.5 * (lower + upper)


def dispersive_horizon(
    omega: float,
    flow_rate: float,
    depth: float,
    gamma: float = 0.0728,
    density: float = 998.0,
    gravity: float = GRAVITY,
) -> dict:
    if flow_rate <= 0.0:
        raise ValueError("flow_rate must be positive")
    k = horizon_wavenumber(omega, depth, gamma, density, gravity)
    velocity = group_velocity(k, depth, gamma, density, gravity)
    radius = flow_rate / (2.0 * math.pi * depth * velocity)
    long_radius = flow_rate / (2.0 * math.pi * depth * sound_speed(depth, gravity))
    return {
        "omega_rad_s": omega,
        "k_per_m": k,
        "group_velocity_m_s": velocity,
        "horizon_radius_m": radius,
        "long_wavelength_radius_m": long_radius,
        "ratio": radius / long_radius,
    }


def capillary_frequency(
    depth: float,
    gamma: float = 0.0728,
    density: float = 998.0,
    gravity: float = GRAVITY,
) -> float:
    length = capillary_length(gamma, density, gravity)
    return math.sqrt(2.0 * gravity / length)
