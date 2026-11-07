"""Shared-lambda two-state Marcus assignment (claim 44, ADR-036).

Claim 43 falsified the single symmetric Gaussian on shape: the observed
hydrated-electron band needs two Gaussian components of widths 0.71 vs
0.37 eV (Jou & Freeman, Can. J. Chem. 57, 591, 1979) plus a power-law
tail. The natural rescue is two electronic states sharing one solvent
coordinate. This module tests the narrowest such rescue *conditionally*:

    IF the 0.71/0.37 eV components were two classical Marcus states
    sharing the frozen Born-cavity reorganization energy
    ``lambda = 1.617132544`` eV (claim 39) at one sample temperature,
    THEN both components have identical FWHM and their width ratio is
    exactly 1.

The Jou-Freeman decomposition is a fit, not a state assignment; nothing
here asserts two excited states exist. The threshold is inherited frozen
from ADR-034 (``SHAPE_RATIO_TOL = 0.15``), never tuned to this
comparison, so this falsification shares its shape fact with claim 43
and is not independent evidence. The tail evidence stays with claim 43;
claim 44 is killed or survives on the equal-width ratio leg alone.

The ratio prediction is independent of the temperature choice (T cancels
for two states in one sample) and of a common FWHM/HWHM convention
factor. With component uncertainties (0.07, 0.08 eV) the observed ratio
is 1.92 +/- ~0.47, and even the convention-confusion worst case of
exactly 2 still gives |2 - 1| = 1 > 0.15, so the kill is robust.
"""

from __future__ import annotations

from domains.fluid_universe.theory.water_lineshape import LAMBDA_EV, SHAPE_RATIO_TOL
from domains.fluid_universe.theory.water_marcus import marcus_width_ev
from domains.fluid_universe.theory.water_observed_shape import (
    JOU_FREEMAN_G1_WIDTH_EV,
    JOU_FREEMAN_G1_WIDTH_SIGMA_EV,
    JOU_FREEMAN_G2_WIDTH_EV,
    JOU_FREEMAN_G2_WIDTH_SIGMA_EV,
)

ROOM_TEMPERATURE_K = 300.0


def shared_lambda_widths(temperature_k: float = ROOM_TEMPERATURE_K) -> dict:
    """Predicted component widths for two Marcus states sharing lambda.

    Both states see the same solvent (same lambda) at the same sample
    temperature, so the classical Marcus FWHM is bit-identical for the
    two components and their ratio is exactly 1, independent of T.
    """
    if temperature_k <= 0.0:
        raise ValueError("temperature must be positive")
    width = marcus_width_ev(LAMBDA_EV, temperature_k)
    return {
        "lambda_ev": LAMBDA_EV,
        "temperature_k": temperature_k,
        "width_g1_ev": width,
        "width_g2_ev": width,
        "predicted_ratio": 1.0,
    }


def component_ratio() -> dict:
    """Observed Jou-Freeman component widths and their ratio."""
    g1 = JOU_FREEMAN_G1_WIDTH_EV
    g2 = JOU_FREEMAN_G2_WIDTH_EV
    ratio = g1 / g2
    ratio_sigma = ratio * (
        (JOU_FREEMAN_G1_WIDTH_SIGMA_EV / g1) ** 2
        + (JOU_FREEMAN_G2_WIDTH_SIGMA_EV / g2) ** 2
    ) ** 0.5
    return {
        "g1_width_ev": g1,
        "g2_width_ev": g2,
        "observed_ratio": ratio,
        "observed_ratio_sigma": ratio_sigma,
        "diff_vs_one": abs(ratio - 1.0),
        "worst_case_ratio": 2.0,
        "worst_case_diff_vs_one": 1.0,
    }


def kill_thresholds() -> dict:
    """Frozen kill threshold inherited from ADR-034 (never tuned here)."""
    return {"shape_ratio_tol": SHAPE_RATIO_TOL}


def two_state_scales(temperature_k: float = ROOM_TEMPERATURE_K) -> dict:
    """Collect the shared-lambda prediction and the observed ratio."""
    return {
        "lambda_ev": LAMBDA_EV,
        "prediction": shared_lambda_widths(temperature_k),
        "observed": component_ratio(),
        "thresholds": kill_thresholds(),
    }
