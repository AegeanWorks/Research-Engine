"""Thin-filament vortex-knot mass hypothesis (claim 17, ADR-008).

The simplest fluid-vortex assignment gives the three charged leptons the lowest
torus knots T(2,3), T(2,5), T(2,7) and sets the rest mass proportional to the
regularized Biot-Savart energy of the filament at a fixed core radius.

The energy proxy is

    E = sum_{i != j} (dr_i . dr_j) / |r_i - r_j| + L / a,

which is the thin-filament self-energy plus a core cutoff.  It is a scaling
proxy, not a calibrated vortex dynamics; the ratios and the required power are
the test.

A thin filament has E ~ L log(L/a), so its energy ratios are compressed.  The
observed charged-lepton hierarchy spans a factor 3477; a simple knot spectrum
cannot reach it without an exponentially small core or a different mechanism.
"""

from __future__ import annotations

import math

import numpy as np


def torus_knot(
    n: int, radius: float = 2.0, tube: float = 1.0, samples: int = 400
) -> tuple[np.ndarray, np.ndarray]:
    """Closed T(2,n) curve and its chord vectors."""
    if n < 1:
        raise ValueError("n must be at least 1")
    if samples < 16:
        raise ValueError("samples must be at least 16")
    t = np.linspace(0.0, 2.0 * math.pi, samples, endpoint=False)
    points = np.stack(
        [
            (radius + tube * np.cos(n * t)) * np.cos(t),
            (radius + tube * np.cos(n * t)) * np.sin(t),
            tube * np.sin(n * t),
        ],
        axis=1,
    )
    tangents = np.diff(np.vstack([points, points[:1]]), axis=0)
    return points, tangents


def knot_length(points: np.ndarray) -> float:
    points = np.asarray(points, dtype=float)
    closed = np.vstack([points, points[:1]])
    return float(np.sum(np.linalg.norm(np.diff(closed, axis=0), axis=1)))


def biot_savart_energy(points: np.ndarray, core: float = 0.1) -> float:
    """Regularized thin-filament energy proxy at a fixed core radius."""
    if core <= 0.0:
        raise ValueError("core must be positive")
    points = np.asarray(points, dtype=float)
    tangents = np.diff(np.vstack([points, points[:1]]), axis=0)
    differences = points[:, None, :] - points[None, :, :]
    distances = np.linalg.norm(differences, axis=-1)
    np.fill_diagonal(distances, core)
    mutual = float(np.sum((tangents @ tangents.T) / distances))
    self_term = knot_length(points) / core
    return mutual + self_term


def koide_q(values: np.ndarray) -> float:
    values = np.asarray(values, dtype=float)
    if np.any(values <= 0.0):
        raise ValueError("values must be positive")
    denominator = float(np.sum(np.sqrt(values))) ** 2
    if denominator == 0.0:
        raise ValueError("degenerate values")
    return float(np.sum(values) / denominator)


def mass_hypothesis(
    observed: np.ndarray | tuple[float, float, float],
    knots: tuple[int, int, int] = (3, 5, 7),
    core: float = 0.1,
    relative_tolerance: float = 0.1,
    koide_tolerance: float = 0.01,
) -> dict:
    """Test m proportional to the knot energy against the observed masses."""
    observed = np.asarray(observed, dtype=float)
    if observed.shape != (3,) or np.any(observed <= 0.0):
        raise ValueError("observed must be three positive masses")
    energies = []
    lengths = []
    for n in knots:
        points, _tangents = torus_knot(n)
        energies.append(biot_savart_energy(points, core))
        lengths.append(knot_length(points))
    energies = np.asarray(energies)
    lengths = np.asarray(lengths)
    energy_ratios = energies / energies[0]
    length_ratios = lengths / lengths[0]
    observed_ratios = observed / observed[0]
    relative_error = float(np.max(np.abs(energy_ratios - observed_ratios) / observed_ratios))
    q_energy = koide_q(energies)
    q_length = koide_q(lengths)
    q_observed = koide_q(observed)
    required_power = float(
        math.log(observed_ratios[-1]) / math.log(energy_ratios[-1])
    )
    falsified = bool(
        relative_error > relative_tolerance
        or abs(q_energy - 2.0 / 3.0) > koide_tolerance
    )
    return {
        "knots": list(knots),
        "core": core,
        "energies": [float(value) for value in energies],
        "lengths": [float(value) for value in lengths],
        "energy_ratios": [float(value) for value in energy_ratios],
        "length_ratios": [float(value) for value in length_ratios],
        "observed_ratios": [float(value) for value in observed_ratios],
        "relative_error": relative_error,
        "koide_q_energy": q_energy,
        "koide_q_length": q_length,
        "koide_q_observed": q_observed,
        "required_power": required_power,
        "falsified": falsified,
        "status": (
            "FALSIFIED (thin-filament spectrum too compressed)"
            if falsified
            else "UNVERIFIED (ratios agree at this core; not a derivation)"
        ),
        "note": (
            "A thin filament has E ~ L log(L/a); its ratios are O(1). Matching "
            "the charged-lepton hierarchy would need m ~ E^p with p about "
            f"{required_power:.1f}, or an exponentially small core. This test "
            "falsifies only the simple assignment, not the general vortex idea."
        ),
    }
