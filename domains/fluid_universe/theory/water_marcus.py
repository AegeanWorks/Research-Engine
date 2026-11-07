"""Marcus band width from the water reorganization energy (claim 40, ADR-031).

The same reorganization energy that predicts the VDE also sets the optical
band width in the classical Marcus model:

    FWHM = 2 sqrt(2 ln 2) sqrt(2 lambda k_B T).

At lambda = 1.617132544 eV and T = 300 K, FWHM = 0.680915 eV, close to the
reference bulk hydrated-electron widths 0.706 eV (classical) and 0.773 eV
(quantized) from Turi et al., JCTC 20, 4265 (2024).  The width scales as
sqrt(T): 0.555964 eV at 200 K and 0.735472 eV at 350 K.
"""

from __future__ import annotations

import math

from domains.fluid_universe.theory.water_born_cavity import born_cavity_scales

KB_EV = 8.617333262e-5
REFERENCE_CLASSICAL_EV = 0.706
REFERENCE_QUANTIZED_EV = 0.773
CENTER_EV = 1.70


def marcus_width_ev(lambda_ev: float, temperature_k: float = 300.0) -> float:
    """Classical Marcus Gaussian FWHM in eV."""
    if lambda_ev <= 0.0:
        raise ValueError("lambda must be positive")
    if temperature_k <= 0.0:
        raise ValueError("temperature must be positive")
    sigma = math.sqrt(2.0 * lambda_ev * KB_EV * temperature_k)
    return 2.0 * math.sqrt(2.0 * math.log(2.0)) * sigma


def gaussian_line_shape(
    energy_ev: float, center_ev: float, fwhm_ev: float
) -> float:
    """Normalized Gaussian value at energy_ev."""
    if fwhm_ev <= 0.0:
        raise ValueError("fwhm must be positive")
    offset = (energy_ev - center_ev) / fwhm_ev
    return math.exp(-4.0 * math.log(2.0) * offset * offset)


def marcus_scales() -> dict:
    """Collect the Marcus widths and the reference comparison."""
    lambda_ev = born_cavity_scales()["synthesis"]["lambda_ev"]
    widths = {
        str(temperature): marcus_width_ev(lambda_ev, temperature)
        for temperature in (200, 250, 298, 300, 350)
    }
    width_300 = widths["300"]
    return {
        "lambda_ev": lambda_ev,
        "center_ev": CENTER_EV,
        "widths_ev": widths,
        "reference_classical_ev": REFERENCE_CLASSICAL_EV,
        "reference_quantized_ev": REFERENCE_QUANTIZED_EV,
        "ratio_classical": width_300 / REFERENCE_CLASSICAL_EV,
        "ratio_quantized": width_300 / REFERENCE_QUANTIZED_EV,
        "sqrt_ratio_350_300": math.sqrt(350.0 / 300.0),
    }
