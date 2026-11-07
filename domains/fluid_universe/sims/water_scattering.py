"""1D shallow-water wave scattering at an acoustic horizon (claim 31, ADR-022).

The linearized equations are solved in Riemann invariants

    R_pm = u +/- (c/h) eta,

with upwind advection at speeds v +/- c.  The horizon flow is
v = -c (1 + x/(2L)); a uniform v = -0.5 c is the transmitting control.
The flow is prescribed (kinematic analogue), not a consistent shallow-water
equilibrium.
"""

from __future__ import annotations

import math

import numpy as np

GRAVITY = 9.81


def horizon_flow(x: np.ndarray, c: float, length: float) -> np.ndarray:
    if length <= 0.0 or c <= 0.0:
        raise ValueError("length and c must be positive")
    return -c * (1.0 + np.asarray(x, dtype=float) / (2.0 * length))


def uniform_flow(x: np.ndarray, c: float, fraction: float = 0.5) -> np.ndarray:
    if not 0.0 < fraction < 1.0:
        raise ValueError("fraction must lie between 0 and 1")
    return np.full_like(np.asarray(x, dtype=float), -fraction * c)


def initial_packet(
    x: np.ndarray, center: float, width: float, c: float, depth: float
) -> tuple[np.ndarray, np.ndarray]:
    if width <= 0.0 or depth <= 0.0:
        raise ValueError("width and depth must be positive")
    eta = np.exp(-((x - center) ** 2) / (2.0 * width * width))
    u = (c / depth) * eta
    return eta, u


def sponge_profile(
    x: np.ndarray, length: float, fraction: float = 0.15
) -> np.ndarray:
    if not 0.0 < fraction < 0.5:
        raise ValueError("fraction must lie between 0 and 0.5")
    edge = fraction * length
    profile = np.zeros_like(x, dtype=float)
    left = x < -0.5 * length + edge
    right = x > 0.5 * length - edge
    profile[left] = ((-0.5 * length + edge - x[left]) / edge) ** 2
    profile[right] = ((x[right] - (0.5 * length - edge)) / edge) ** 2
    return profile


def energy_density(
    eta: np.ndarray, u: np.ndarray, depth: float, gravity: float = GRAVITY
) -> np.ndarray:
    return 0.5 * (gravity * eta * eta + depth * u * u)


def simulate(
    flow,
    n: int = 1200,
    length: float = 20.0,
    depth: float = 0.1,
    center: float = -3.0,
    width: float = 0.5,
    t_max: float = 30.0,
    dt: float = 2e-4,
    sponge_fraction: float = 0.15,
    sponge_strength: float = 3.0,
    gravity: float = GRAVITY,
) -> dict:
    if n < 32 or length <= 0.0 or depth <= 0.0 or t_max <= 0.0 or dt <= 0.0:
        raise ValueError("invalid grid or time parameters")
    dx = length / n
    x = (np.arange(n) - n // 2) * dx
    c = math.sqrt(gravity * depth)
    eta, u = initial_packet(x, center, width, c, depth)
    flow_array = np.asarray(flow(x), dtype=float)
    dvdx = np.gradient(flow_array, dx)
    sponge = sponge_profile(x, length, sponge_fraction)
    gamma = sponge_strength * sponge
    right_moving = u + (c / depth) * eta
    left_moving = u - (c / depth) * eta
    speed_right = flow_array + c
    speed_left = flow_array - c

    def advect(values: np.ndarray, speed: np.ndarray) -> np.ndarray:
        backward = (values - np.roll(values, 1)) / dx
        forward = (np.roll(values, -1) - values) / dx
        return np.where(speed > 0.0, backward * speed, forward * speed)

    def rhs(rp: np.ndarray, rm: np.ndarray):
        eta_now = depth / (2.0 * c) * (rp - rm)
        source = -(c / depth) * eta_now * dvdx
        drp = -advect(rp, speed_right) + source - gamma * rp
        drm = -advect(rm, speed_left) - source - gamma * rm
        return drp, drm

    steps = int(round(t_max / dt))
    for _ in range(steps):
        k1 = rhs(right_moving, left_moving)
        k2 = rhs(
            right_moving + 0.5 * dt * k1[0],
            left_moving + 0.5 * dt * k1[1],
        )
        k3 = rhs(
            right_moving + 0.5 * dt * k2[0],
            left_moving + 0.5 * dt * k2[1],
        )
        k4 = rhs(
            right_moving + dt * k3[0],
            left_moving + dt * k3[1],
        )
        right_moving += dt * (k1[0] + 2.0 * k2[0] + 2.0 * k3[0] + k4[0]) / 6.0
        left_moving += dt * (k1[1] + 2.0 * k2[1] + 2.0 * k3[1] + k4[1]) / 6.0
        if not np.isfinite(right_moving).all() or not np.isfinite(
            left_moving
        ).all():
            raise RuntimeError("scattering simulation became non-finite")

    eta = depth / (2.0 * c) * (right_moving - left_moving)
    u = 0.5 * (right_moving + left_moving)
    energy = energy_density(eta, u, depth, gravity)
    left_energy = float(np.sum(energy[x < 0.0]) * dx)
    right_energy = float(np.sum(energy[x > 0.0]) * dx)
    total = left_energy + right_energy
    return {
        "n": n,
        "length": length,
        "depth": depth,
        "center": center,
        "width": width,
        "t_max": t_max,
        "dt": dt,
        "energy_left": left_energy,
        "energy_right": right_energy,
        "energy_total": total,
        "transmitted_fraction": right_energy / total if total > 0.0 else 0.0,
        "final_center": float(x[np.argmax(np.abs(eta))]),
        "max_eta": float(np.max(np.abs(eta))),
    }
