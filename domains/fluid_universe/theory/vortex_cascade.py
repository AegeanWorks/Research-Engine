"""One-parameter vortex/eddy hierarchy test (claim 18, ADR-009).

Two natural one-parameter spectra are tested against the charged-lepton masses:

* geometric cascade: m_n = A lambda^n, so m_tau/m_e = (m_mu/m_e)^2;
* power law: m_n = A (n+1)^p, so one p fixes both ratios and Koide Q.

Each has one shape parameter; fitting it to m_mu/m_e leaves the tau ratio and Q
as predictions.  A two-parameter offset can fit the masses but is not a
prediction and is not used here.
"""

from __future__ import annotations

import math

import numpy as np

from domains.fluid_universe.theory.vortex_particles import koide_q

KOIDE_TARGET = 2.0 / 3.0
RELATIVE_TOLERANCE = 0.1
KOIDE_TOLERANCE = 0.01


def geometric_spectrum(ratio: float, generations: int = 3) -> np.ndarray:
    if ratio <= 0.0:
        raise ValueError("ratio must be positive")
    return float(ratio) ** np.arange(generations, dtype=float)


def power_law_spectrum(exponent: float, generations: int = 3) -> np.ndarray:
    return np.arange(1, generations + 1, dtype=float) ** float(exponent)


def solve_power_for_koide(
    target: float = KOIDE_TARGET, lower: float = 0.0, upper: float = 50.0
) -> float:
    """Bisection for the power p with Koide Q = target."""
    if not 1.0 / 3.0 < target < 1.0:
        raise ValueError("target must lie between 1/3 and 1")
    if koide_q(power_law_spectrum(lower)) > target:
        raise ValueError("lower bound already above target")
    if koide_q(power_law_spectrum(upper)) < target:
        raise ValueError("upper bound below target")
    for _ in range(200):
        middle = 0.5 * (lower + upper)
        if koide_q(power_law_spectrum(middle)) < target:
            lower = middle
        else:
            upper = middle
    return 0.5 * (lower + upper)


def _summary(name: str, observed: np.ndarray, predicted: np.ndarray, parameter: float) -> dict:
    observed_ratio = float(observed[2] / observed[0])
    predicted_ratio = float(predicted[2] / predicted[0])
    ratio_error = (predicted_ratio - observed_ratio) / observed_ratio
    q_predicted = koide_q(predicted)
    q_observed = koide_q(observed)
    falsified = bool(
        abs(ratio_error) > RELATIVE_TOLERANCE
        or abs(q_predicted - KOIDE_TARGET) > KOIDE_TOLERANCE
    )
    return {
        "model": name,
        "parameter": float(parameter),
        "predicted_ratios": [float(value) for value in predicted / predicted[0]],
        "predicted_tau_ratio": predicted_ratio,
        "observed_tau_ratio": observed_ratio,
        "tau_relative_error": ratio_error,
        "koide_q_predicted": q_predicted,
        "koide_q_observed": q_observed,
        "falsified": falsified,
    }


def run_hypotheses(
    observed: np.ndarray | tuple[float, float, float],
) -> dict:
    observed = np.asarray(observed, dtype=float)
    if observed.shape != (3,) or np.any(observed <= 0.0):
        raise ValueError("observed must be three positive masses")
    muon_ratio = float(observed[1] / observed[0])
    geometric = _summary(
        "geometric",
        observed,
        observed[0] * geometric_spectrum(muon_ratio),
        muon_ratio,
    )
    power_muon = _summary(
        "power_law_muon_fit",
        observed,
        observed[0] * power_law_spectrum(math.log(muon_ratio) / math.log(2.0)),
        math.log(muon_ratio) / math.log(2.0),
    )
    power_koide_p = solve_power_for_koide()
    power_koide = _summary(
        "power_law_koide_fit",
        observed,
        observed[0] * power_law_spectrum(power_koide_p),
        power_koide_p,
    )
    models = {
        "geometric": geometric,
        "power_law_muon_fit": power_muon,
        "power_law_koide_fit": power_koide,
    }
    falsified = all(model["falsified"] for model in models.values())
    return {
        "models": models,
        "koide_target": KOIDE_TARGET,
        "relative_tolerance": RELATIVE_TOLERANCE,
        "koide_tolerance": KOIDE_TOLERANCE,
        "falsified": bool(falsified),
        "status": (
            "FALSIFIED (no one-parameter hierarchy matches both ratios and Q)"
            if falsified
            else "UNVERIFIED (one model matches at this tolerance; not a derivation)"
        ),
        "note": (
            "A one-parameter fluid hierarchy has no freedom left after the "
            "muon ratio or Q is fixed. A two-parameter offset can fit the "
            "masses, but then Q is reproduced rather than predicted."
        ),
    }
