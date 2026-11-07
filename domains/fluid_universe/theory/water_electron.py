"""Hydrated-electron cavity scale from water properties (claim 32, ADR-023).

A simple screened hydrogen state in water has

    a0* = epsilon_r a0,   E* = -Ry / epsilon_r^2,

which is 41.5 Angstrom and -2.2 meV -- far from the hydrated electron.

Balancing electron quantum pressure against the water surface energy,

    E(R) = hbar^2/(2 m R^2) + 4 pi gamma R^2,

gives R^4 = hbar^2/(8 pi m gamma), i.e. R = 2.858 Angstrom and E = 0.933 eV at
20 C.  The observed absorption is about 1.7 eV, a factor 1.8 higher; this is a
scale test, not a derivation.
"""

from __future__ import annotations

import math

HBAR = 1.054571817e-34
MASS = 9.1093837015e-31
EV_JOULE = 1.602176634e-19
BOHR = 5.29177210903e-11
RYDBERG_EV = 13.605693
EPSILON_WATER = 78.4
GAMMA_WATER = 0.0728


def screened_bohr_radius(epsilon_r: float = EPSILON_WATER) -> float:
    if epsilon_r <= 0.0:
        raise ValueError("epsilon_r must be positive")
    return epsilon_r * BOHR


def screened_energy_ev(epsilon_r: float = EPSILON_WATER) -> float:
    if epsilon_r <= 0.0:
        raise ValueError("epsilon_r must be positive")
    return -RYDBERG_EV / (epsilon_r * epsilon_r)


def capillary_cavity_radius(
    gamma: float = GAMMA_WATER,
    mass: float = MASS,
    hbar: float = HBAR,
) -> float:
    if gamma <= 0.0 or mass <= 0.0 or hbar <= 0.0:
        raise ValueError("gamma, mass and hbar must be positive")
    return (hbar * hbar / (8.0 * math.pi * mass * gamma)) ** 0.25


def capillary_cavity_energy_ev(
    gamma: float = GAMMA_WATER,
    mass: float = MASS,
    hbar: float = HBAR,
) -> float:
    radius = capillary_cavity_radius(gamma, mass, hbar)
    kinetic = hbar * hbar / (2.0 * mass * radius * radius)
    return 2.0 * kinetic / EV_JOULE


def infinite_well_gap_ev(
    radius: float, mass: float = MASS, hbar: float = HBAR
) -> float:
    """Ground-state energy of an infinite spherical well, not the s->p gap."""
    if radius <= 0.0 or mass <= 0.0 or hbar <= 0.0:
        raise ValueError("radius, mass and hbar must be positive")
    return math.pi**2 * hbar * hbar / (2.0 * mass * radius * radius) / EV_JOULE


def well_radius_for_gap(
    energy_ev: float, mass: float = MASS, hbar: float = HBAR
) -> float:
    """Radius where the infinite-well ground-state energy equals energy_ev."""
    if energy_ev <= 0.0 or mass <= 0.0 or hbar <= 0.0:
        raise ValueError("energy, mass and hbar must be positive")
    return math.sqrt(
        math.pi**2 * hbar * hbar / (2.0 * mass * energy_ev * EV_JOULE)
    )


def hydrated_scales() -> dict:
    radius = capillary_cavity_radius()
    return {
        "epsilon_water": EPSILON_WATER,
        "gamma_water_n_m": GAMMA_WATER,
        "screened_bohr_radius_m": screened_bohr_radius(),
        "screened_energy_ev": screened_energy_ev(),
        "cavity_radius_m": radius,
        "cavity_energy_ev": capillary_cavity_energy_ev(),
        "well_gap_at_cavity_ev": infinite_well_gap_ev(radius),
        "well_gap_at_2p5_angstrom_ev": infinite_well_gap_ev(2.5e-10),
        "well_radius_for_1p7_ev_m": well_radius_for_gap(1.7),
    }
