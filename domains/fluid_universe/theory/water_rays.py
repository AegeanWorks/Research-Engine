"""Radial rays at the shallow-water acoustic horizon (claim 30, ADR-021).

The outgoing radial speed is

    dr/dt = c - Q/(2 pi r h) = c (1 - r_H/r),

so the horizon is a separatrix: outside it rays move outward, inside they move
inward, and near r_H they peel away with rate c/r_H = c^2/r_H, the surface
gravity.  The analytic ray time for r0 > r_H is

    t = (r - r0)/c + (r_H/c) ln((r - r_H)/(r0 - r_H)).
"""

from __future__ import annotations

import math

from domains.fluid_universe.theory.water_analogue import sound_speed, surface_gravity


def outgoing_speed(
    r: float, flow_rate: float, depth: float, gravity: float = 9.81
) -> float:
    if r <= 0.0 or flow_rate <= 0.0:
        raise ValueError("r and flow_rate must be positive")
    speed = sound_speed(depth, gravity)
    return speed - flow_rate / (2.0 * math.pi * r * depth)


def ingoing_speed(
    r: float, flow_rate: float, depth: float, gravity: float = 9.81
) -> float:
    if r <= 0.0 or flow_rate <= 0.0:
        raise ValueError("r and flow_rate must be positive")
    speed = sound_speed(depth, gravity)
    return -speed - flow_rate / (2.0 * math.pi * r * depth)


def peeling_rate(
    flow_rate: float, depth: float, gravity: float = 9.81
) -> float:
    return surface_gravity(flow_rate, depth, gravity)


def analytic_outgoing_time(
    r: float, r0: float, horizon: float, speed: float
) -> float:
    if r <= horizon or r0 <= horizon or speed <= 0.0:
        raise ValueError("r and r0 must exceed the horizon; speed must be positive")
    return (r - r0) / speed + (horizon / speed) * math.log(
        (r - horizon) / (r0 - horizon)
    )


def integrate_outgoing(
    r0: float,
    r_end: float,
    flow_rate: float,
    depth: float,
    gravity: float = 9.81,
    dt: float = 1e-5,
) -> dict:
    if r0 <= 0.0 or r_end <= r0 or dt <= 0.0:
        raise ValueError("require 0 < r0 < r_end and dt > 0")
    time = 0.0
    radius = r0
    steps = 0
    while radius < r_end:
        k1 = outgoing_speed(radius, flow_rate, depth, gravity)
        k2 = outgoing_speed(
            radius + 0.5 * dt * k1, flow_rate, depth, gravity
        )
        k3 = outgoing_speed(
            radius + 0.5 * dt * k2, flow_rate, depth, gravity
        )
        k4 = outgoing_speed(radius + dt * k3, flow_rate, depth, gravity)
        radius += dt * (k1 + 2.0 * k2 + 2.0 * k3 + k4) / 6.0
        time += dt
        steps += 1
        if steps > 10_000_000:
            raise RuntimeError("ray integration did not reach r_end")
    return {"time": time, "radius": radius, "steps": steps}
