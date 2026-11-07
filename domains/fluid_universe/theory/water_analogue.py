"""Shallow-water acoustic horizon (claim 27, ADR-018).

For long-wavelength shallow-water waves over a radial drain,

    c = sqrt(g h),   v_r = Q / (2 pi r h),

the effective acoustic metric has g_tt = -(c^2 - v_r^2).  The horizon is at

    r_H = Q / (2 pi h c),

with surface gravity kappa = c^2 / r_H and analogue temperature
T_H = hbar kappa / (2 pi k_B).  The metric is acoustic and long-wavelength
only; capillary dispersion breaks it at short scales.
"""

from __future__ import annotations

import math

GRAVITY = 9.81
HBAR = 1.054571817e-34
BOLTZMANN = 1.380649e-23


def sound_speed(depth: float, gravity: float = GRAVITY) -> float:
    if depth <= 0.0 or gravity <= 0.0:
        raise ValueError("depth and gravity must be positive")
    return math.sqrt(gravity * depth)


def flow_velocity(
    r: float, flow_rate: float, depth: float, gravity: float = GRAVITY
) -> float:
    if r <= 0.0 or flow_rate <= 0.0:
        raise ValueError("r and flow_rate must be positive")
    return flow_rate / (2.0 * math.pi * r * depth)


def horizon_radius(
    flow_rate: float, depth: float, gravity: float = GRAVITY
) -> float:
    if flow_rate <= 0.0:
        raise ValueError("flow_rate must be positive")
    speed = sound_speed(depth, gravity)
    return flow_rate / (2.0 * math.pi * depth * speed)


def surface_gravity(
    flow_rate: float, depth: float, gravity: float = GRAVITY
) -> float:
    radius = horizon_radius(flow_rate, depth, gravity)
    speed = sound_speed(depth, gravity)
    return speed * speed / radius


def hawking_temperature(kappa: float) -> float:
    if kappa <= 0.0:
        raise ValueError("kappa must be positive")
    return HBAR * kappa / (2.0 * math.pi * BOLTZMANN)


def acoustic_metric(
    r: float, flow_rate: float, depth: float, gravity: float = GRAVITY
) -> dict:
    speed = sound_speed(depth, gravity)
    velocity = flow_velocity(r, flow_rate, depth, gravity)
    return {
        "c": speed,
        "v_r": velocity,
        "g_tt": -(speed * speed - velocity * velocity),
        "g_tr": -velocity,
        "g_rr": 1.0,
        "g_phiphi": r * r,
    }


def lab_scales(
    depth: float = 0.1, flow_rate: float = 1e-3, gravity: float = GRAVITY
) -> dict:
    speed = sound_speed(depth, gravity)
    radius = horizon_radius(flow_rate, depth, gravity)
    kappa = surface_gravity(flow_rate, depth, gravity)
    return {
        "depth_m": depth,
        "flow_rate_m3_s": flow_rate,
        "gravity_m_s2": gravity,
        "sound_speed_m_s": speed,
        "horizon_radius_m": radius,
        "surface_gravity_m_s2": kappa,
        "hawking_temperature_k": hawking_temperature(kappa),
    }


def capillary_length(
    gamma: float = 0.0728,
    density: float = 998.0,
    gravity: float = GRAVITY,
) -> float:
    if gamma <= 0.0 or density <= 0.0 or gravity <= 0.0:
        raise ValueError("gamma, density and gravity must be positive")
    return math.sqrt(gamma / (density * gravity))


def capillary_ratio(horizon_radius_value: float, length: float) -> float:
    if horizon_radius_value <= 0.0 or length <= 0.0:
        raise ValueError("radii must be positive")
    return (length / horizon_radius_value) ** 2


def long_wavelength_min_flow(
    depth: float,
    gravity: float = GRAVITY,
    gamma: float = 0.0728,
    density: float = 998.0,
    ratio: float = 10.0,
) -> float:
    if ratio <= 0.0:
        raise ValueError("ratio must be positive")
    speed = sound_speed(depth, gravity)
    length = capillary_length(gamma, density, gravity)
    return 2.0 * math.pi * depth * speed * ratio * length


def validity(
    depth: float = 0.1,
    flow_rate: float = 1e-3,
    gamma: float = 0.0728,
    density: float = 998.0,
    gravity: float = GRAVITY,
    ratio: float = 10.0,
) -> dict:
    radius = horizon_radius(flow_rate, depth, gravity)
    length = capillary_length(gamma, density, gravity)
    return {
        "depth_m": depth,
        "flow_rate_m3_s": flow_rate,
        "horizon_radius_m": radius,
        "capillary_length_m": length,
        "capillary_ratio": capillary_ratio(radius, length),
        "long_wavelength": bool(radius >= ratio * length),
        "required_ratio": ratio,
        "minimum_flow_m3_s": long_wavelength_min_flow(
            depth, gravity, gamma, density, ratio
        ),
    }
