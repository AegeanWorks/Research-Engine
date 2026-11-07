"""Fixed-lambda cavity-Marcus line-shape prediction (claim 43, ADR-034).

The self-consistent Born cavity fixes the water reorganization energy at
``lambda = 1.617132544`` eV (claim 39). The classical Marcus model then
predicts a Gaussian absorption band

    FWHM = 2 sqrt(2 ln 2) sqrt(2 lambda k_B T),

which is symmetric by construction: the third central moment vanishes by
odd symmetry, so the skewness is exactly 0 and the high/low half-width
ratio is exactly 1. With ``lambda(T)`` from the temperature-dependent Born
cavity (claim 41), the model predicts absolute widths at 0 C and 45 C and
their ratio with no free parameters.

No observed width-vs-temperature or band-shape comparator exists in this
repository (the 2.4-2.8 meV/K band is the peak shift, not a width change;
the only shape references are the FWHM values 0.706/0.773 eV). The numbers
below are therefore a pre-registered quantitative prediction with dated
kill thresholds, not a comparison. Any effective vibrational frequency
would be a fit and is excluded here.
"""

from __future__ import annotations

import math

from domains.fluid_universe.theory.water_born_cavity import born_cavity_scales
from domains.fluid_universe.theory.water_marcus import marcus_width_ev
from domains.fluid_universe.theory.water_temperature import temperature_scales

KB_EV = 8.617333262e-5
LAMBDA_EV = 1.6171325440878093
WIDTH_RATIO_TOL = 0.05
SHAPE_RATIO_TOL = 0.15
SKEW_TOL = 0.3


def gaussian_moments() -> dict:
    """Exact symmetry facts for a Gaussian band (no inputs, no fit).

    A centered Gaussian is an even function, so every odd central moment
    vanishes: the third central moment is 0, the skewness is 0, and the
    half-maximum points are symmetric about the center, giving a
    high/low half-width ratio of exactly 1.
    """
    half_ratio = 1.0
    skewness = 0.0
    third_moment = 0.0
    return {
        "skewness": skewness,
        "half_width_ratio": half_ratio,
        "third_central_moment": third_moment,
        "symmetric": half_ratio == 1.0 and skewness == 0.0,
    }


def predicted_widths() -> dict:
    """Absolute Marcus widths at 0 C and 45 C from fixed inputs only."""
    scales = temperature_scales()
    scan = {row["temperature_c"]: row for row in scales["scan"]}
    cold = scan[0.0]
    warm = scan[45.0]
    width_0c = marcus_width_ev(cold["lambda_ev"], 0.0 + 273.15)
    width_45c = marcus_width_ev(warm["lambda_ev"], 45.0 + 273.15)
    return {
        "lambda_0c_ev": cold["lambda_ev"],
        "lambda_45c_ev": warm["lambda_ev"],
        "width_0c_ev": width_0c,
        "width_45c_ev": width_45c,
        "width_change_ev": width_45c - width_0c,
        "width_ratio_45_over_0": width_45c / width_0c,
    }


def kill_thresholds() -> dict:
    """Pre-registered kill thresholds for a future comparator (data only)."""
    return {
        "width_ratio_tol": WIDTH_RATIO_TOL,
        "shape_ratio_tol": SHAPE_RATIO_TOL,
        "skew_tol": SKEW_TOL,
    }


def lineshape_scales() -> dict:
    """Collect the fixed-lambda prediction and its kill thresholds."""
    fixed_lambda = born_cavity_scales()["synthesis"]["lambda_ev"]
    return {
        "lambda_ev": fixed_lambda,
        "moments": gaussian_moments(),
        "prediction": predicted_widths(),
        "thresholds": kill_thresholds(),
    }
