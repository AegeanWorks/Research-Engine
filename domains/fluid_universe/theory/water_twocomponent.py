"""Zero-free-parameter two-component band model (claim 45, ADR-037).

The claim-43 cycle falsified the single symmetric Gaussian but left the
sqrt(lambda T) width scaling alive. The minimal asymmetric repair joins,
at the observed maximum, a Gaussian low-energy side fixed by the Marcus
scale to a power-law blue tail fixed by Jou & Freeman:

    A(E) = exp(-4 ln2 ((E - Emax)/FWHM)^2)   for E <= Emax   (red side),
    A(E) = (E/Emax)^(-n)                     for E >= Emax   (blue tail),

with FWHM = Marcus FWHM(lambda, T) from claim 40 (lambda fixed from
claim 39), Emax = 1.72 eV observed, n = 4.4 observed (Jou & Freeman
1979, water). Continuity at Emax (A = 1 both sides) is definitional to
the claim: it is the join the claim asserts, not a fitted parameter.
There are zero free parameters.

Predictions at T_REF_K = 299.15 K (26 C, Jou & Freeman Table 1 conditions):
    red HWHM   = FWHM/2,
    blue HWHM  = Emax * (2^(1/n) - 1),
    R_pred     = blue/red,
    FWHM_model = blue + red.
With FWHM(299.15 K) = 0.679949 eV: red = 0.339975, blue = 0.293466,
R_pred = 0.863201, FWHM_model = 0.633441 eV.

Kill thresholds are the frozen ADR-034 shape/width values: |R_pred - R_obs| > 0.15
(shape leg, cf. water_lineshape SHAPE_RATIO_TOL; named width_ratio_tol here
for payload compatibility) kills the join (R_obs = L/G from the Jou-Freeman
side-width fits via Coe review, Wb/Wr per Bartels);
|FWHM_model - 0.706|/0.706 > 0.05 (classical) or the 0.15 quantized
bound vs 0.773 kills the width scale. The Emax value itself carries no
kill threshold and is reported for consistency only.
"""

from __future__ import annotations

import math

from domains.fluid_universe.theory.water_born_cavity import born_cavity_scales
from domains.fluid_universe.theory.water_marcus import marcus_width_ev
from domains.fluid_universe.theory.water_observed_shape import (
    JOU_FREEMAN_TAIL_POWER_WATER_N,
    jou_freeman_side_widths,
)

T_REF_K = 299.15
EMAX_EV = 1.72
WIDTH_RATIO_TOL = 0.15
FWHM_CLASSICAL_TOL = 0.05
FWHM_QUANTIZED_TOL = 0.15
REFERENCE_CLASSICAL_EV = 0.706
REFERENCE_QUANTIZED_EV = 0.773


def twocomponent_scales(
    temperature_k: float = T_REF_K,
) -> dict:
    """Fixed-input two-component prediction plus observed side widths."""
    lambda_ev = born_cavity_scales()["synthesis"]["lambda_ev"]
    fwhm = marcus_width_ev(lambda_ev, temperature_k)
    n = JOU_FREEMAN_TAIL_POWER_WATER_N
    red = fwhm / 2.0
    blue = EMAX_EV * (2.0 ** (1.0 / n) - 1.0)
    observed = jou_freeman_side_widths(temperature_k)
    r_pred = blue / red
    r_obs = observed["side_ratio_blue_over_red"]
    fwhm_model = blue + red
    classical_rel = abs(fwhm_model - REFERENCE_CLASSICAL_EV) / REFERENCE_CLASSICAL_EV
    quantized_rel = abs(fwhm_model - REFERENCE_QUANTIZED_EV) / REFERENCE_QUANTIZED_EV
    return {
        "temperature_k": temperature_k,
        "lambda_ev": lambda_ev,
        "n_tail": n,
        "emax_ev": EMAX_EV,
        "marcus_fwhm_ev": fwhm,
        "red_hwhm_ev": red,
        "blue_hwhm_ev": blue,
        "r_pred": r_pred,
        "fwhm_model_ev": fwhm_model,
        "observed": observed,
        "r_obs": r_obs,
        "ratio_diff": abs(r_pred - r_obs),
        "ratio_kill": abs(r_pred - r_obs) > WIDTH_RATIO_TOL,
        "classical_rel_diff": classical_rel,
        "quantized_rel_diff": quantized_rel,
        "width_kill": classical_rel > FWHM_CLASSICAL_TOL
        or quantized_rel > FWHM_QUANTIZED_TOL,
        "thresholds": {
            "width_ratio_tol": WIDTH_RATIO_TOL,
            "fwhm_classical_tol": FWHM_CLASSICAL_TOL,
            "fwhm_quantized_tol": FWHM_QUANTIZED_TOL,
        },
    }
