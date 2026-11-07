"""Observed hydrated-electron band-shape comparator data (claim 43, ADR-035).

Citable observed numbers only. No fit, no model parameter, no effective
frequency. The comparison logic lives in
``phenomenology/water_lineshape_report.py``; the kill thresholds stay frozen
in ``theory/water_lineshape.py`` (ADR-034).

Sources
-------
- Christensen & Sehested, J. Phys. Chem. 90:1 (1986), DOI
  10.1021/j100273a042 (OSTI ID 5827886): spectrum measured 5-300 C;
  up to ~150 C, dE_max/dT = -2.8e-3 eV/K and d(delta E_1/2)/dT = 2e-4
  eV/K, where delta E_1/2 is stated as "the half-width of the spectrum".
  Whether delta E_1/2 means FWHM or HWHM is ambiguous in the abstract;
  both interpretations are carried below and both are far below the
  predicted width slope (see compare_width_slope).
- Jou & Freeman, Can. J. Chem. 57, 591 (1979): optical spectra resolved
  into two Gaussian bands plus a continuum tail. In water and alcohols
  the first Gaussian half-width is 0.71 +/- 0.07 eV, the second
  0.37 +/- 0.08 eV, the tail ~1.0 +/- 0.2 eV. High-energy side follows
  A/Amax ~ E^-n with n = 4.4 in water (not Gaussian). The band is
  broad and asymmetric; a single Gaussian cannot reproduce two
  different component widths plus a power-law tail.
- Bartels et al., J. Phys. Chem. A (2005, supercritical water):
  subcritical spectra are approximately Gaussian on the low-energy
  side and Lorentzian on the high-energy side; the Gaussian-Lorentzian
  form fails above ~200 C. Gaussian-only shape is an approximation,
  not the observed shape.
- Turi et al., JCTC 20, 4265 (2024) and supporting review: observed
  bulk band is "broad and highly asymmetric" with maximum at
  1.72 eV (Jou & Freeman); the high-energy blue tail is the stubborn
  part for one-electron models.

Use
--
``observed_width_change_ev(span_k)`` gives the Christensen half-width
change over a temperature span. ``shape_evidence()`` returns the
Jou-Freeman component widths and the tail index that falsify a single
symmetric Gaussian. No observed half-width ratio or skew number is
invented: the kill follows because two different component widths
(0.71 vs 0.37 eV, ratio 1.92, difference 0.34 eV) plus a power-law
tail cannot come from one symmetric Gaussian (ratio 1, skew 0).
"""

from __future__ import annotations

# Christensen & Sehested (1986), valid to ~150 C.
CHRISTENSEN_DWIDTH_DT_EV_PER_K = 2.0e-4
CHRISTENSEN_DEMAX_DT_EV_PER_K = -2.8e-3
CHRISTENSEN_T_RANGE_C = (5.0, 300.0)
CHRISTENSEN_VALID_TO_C = 150.0

# Jou & Freeman (1979), Can. J. Chem. 57, 591.
JOU_FREEMAN_G1_WIDTH_EV = 0.71
JOU_FREEMAN_G1_WIDTH_SIGMA_EV = 0.07
JOU_FREEMAN_G2_WIDTH_EV = 0.37
JOU_FREEMAN_G2_WIDTH_SIGMA_EV = 0.08
JOU_FREEMAN_TAIL_WIDTH_EV = 1.0
JOU_FREEMAN_TAIL_WIDTH_SIGMA_EV = 0.2
JOU_FREEMAN_TAIL_POWER_WATER_N = 4.4

# Observed band maximum (Jou & Freeman; cited by Turi et al. 2024).
OBSERVED_EMAX_EV = 1.72


def observed_width_change_ev(span_k: float = 45.0) -> dict:
    """Observed half-width change over a temperature span.

    Uses the Christensen & Sehested slope as stated ("half-width of the
    spectrum"). The abstract does not say FWHM vs HWHM, so both
    readings are returned: as-stated (slope x span) and doubled
    (in case delta E_1/2 meant HWHM and the comparator needs FWHM).
    """
    if span_k <= 0.0:
        raise ValueError("span must be positive")
    as_stated = CHRISTENSEN_DWIDTH_DT_EV_PER_K * span_k
    doubled = 2.0 * as_stated
    return {
        "slope_ev_per_k": CHRISTENSEN_DWIDTH_DT_EV_PER_K,
        "span_k": span_k,
        "change_as_stated_ev": as_stated,
        "change_if_hwhm_ev": doubled,
        "source": "Christensen & Sehested 1986, d(delta E_1/2)/dT = 2e-4 eV/K",
        "ambiguity": "delta E_1/2 stated as half-width; FWHM vs HWHM unclear",
    }


def shape_evidence() -> dict:
    """Observed shape facts that a single symmetric Gaussian must meet."""
    g1 = JOU_FREEMAN_G1_WIDTH_EV
    g2 = JOU_FREEMAN_G2_WIDTH_EV
    return {
        "two_gaussians_plus_tail": True,
        "g1_width_ev": g1,
        "g2_width_ev": g2,
        "component_width_ratio": g1 / g2,
        "component_width_difference_ev": g1 - g2,
        "tail_width_ev": JOU_FREEMAN_TAIL_WIDTH_EV,
        "tail_power_n_water": JOU_FREEMAN_TAIL_POWER_WATER_N,
        "tail_is_gaussian": False,
        "band_described_as": "broad and highly asymmetric",
        "single_gaussian_compatible": False,
        "sources": [
            "Jou & Freeman, Can. J. Chem. 57, 591 (1979)",
            "Bartels et al., J. Phys. Chem. A (2005)",
            "Turi et al., JCTC 20, 4265 (2024)",
        ],
    }


def observed_scales() -> dict:
    """Collect the observed comparator numbers in one payload."""
    return {
        "emax_ev": OBSERVED_EMAX_EV,
        "width": observed_width_change_ev(),
        "shape": shape_evidence(),
    }


# ---------------------------------------------------------------------------
# Side half-widths (claim 44 comparator; Jou & Freeman fits via Coe review).
# ---------------------------------------------------------------------------
# Jou & Freeman temperature-dependent lineshape fits for bulk H2O, as
# tabulated in the Coe et al. review (research.cbc.osu.edu IRPC proceedings,
# which reproduces both the Tuttle-Golden and the Jou-Freeman constraints):
#   Emax(T) = 2.4506 - 0.0024 * T          (eV, absorption maximum)
#   G(T)    = 0.1517 + 0.00051 * T        (eV, Gaussian HWHM, red side)
#   L(T)    = 0.5124 - 0.00010 * T        (eV, Lorentzian HWHM, blue side)
# with T in Kelvin. Cross-checks: G(210) = 0.2588 vs table 0.259;
# L(210) = 0.4914 vs table 0.491; Emax(210) = 1.9466 vs table 1.947;
# G(298) = 0.3037 with L(298) = 0.4826. Definitions (blue = Lorentzian
# HWHM, red = Gaussian HWHM) per Bartels et al. D2O work: Wb and Wr are
# the half-widths at half-maximum of the Lorentzian and Gaussian on the
# blue and red sides, respectively. Jou & Freeman Table 1 itself was
# measured at 26 C (299.15 K).

JF_EMAX_INTERCEPT_EV = 2.4506
JF_EMAX_SLOPE_EV_PER_K = -0.0024
JF_G_INTERCEPT_EV = 0.1517
JF_G_SLOPE_EV_PER_K = 0.00051
JF_L_INTERCEPT_EV = 0.5124
JF_L_SLOPE_EV_PER_K = -0.00010


def jou_freeman_side_widths(temperature_k: float = 299.15) -> dict:
    """Observed red/blue side half-widths from the Jou-Freeman fits."""
    if temperature_k <= 0.0:
        raise ValueError("temperature must be positive")
    g = JF_G_INTERCEPT_EV + JF_G_SLOPE_EV_PER_K * temperature_k
    l = JF_L_INTERCEPT_EV + JF_L_SLOPE_EV_PER_K * temperature_k
    emax = JF_EMAX_INTERCEPT_EV + JF_EMAX_SLOPE_EV_PER_K * temperature_k
    return {
        "temperature_k": temperature_k,
        "red_gaussian_hwhm_ev": g,
        "blue_lorentzian_hwhm_ev": l,
        "emax_ev": emax,
        "side_ratio_blue_over_red": l / g,
        "fwhm_ev": g + l,
        "source": "Jou & Freeman fits via Coe et al. review; Wb/Wr per Bartels",
    }
