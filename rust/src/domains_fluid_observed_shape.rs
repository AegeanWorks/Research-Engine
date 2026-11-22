//! Observed hydrated-electron band-shape comparator data
//! (fluid_universe/theory/water_observed_shape.py).

use serde_json::{json, Value};

use crate::error::{EngineError, Result};

pub const CHRISTENSEN_DWIDTH_DT: f64 = 2.0e-4;
pub const CHRISTENSEN_DEMAX_DT: f64 = -2.8e-3;
pub const CHRISTENSEN_T_RANGE_C: [f64; 2] = [5.0, 300.0];
pub const CHRISTENSEN_VALID_TO_C: f64 = 150.0;
pub const JF_G1_WIDTH: f64 = 0.71;
pub const JF_G1_SIGMA: f64 = 0.07;
pub const JF_G2_WIDTH: f64 = 0.37;
pub const JF_G2_SIGMA: f64 = 0.08;
pub const JF_TAIL_WIDTH: f64 = 1.0;
pub const JF_TAIL_SIGMA: f64 = 0.2;
pub const JF_TAIL_POWER_WATER_N: f64 = 4.4;
pub const OBSERVED_EMAX_EV: f64 = 1.72;
pub const JF_EMAX_INTERCEPT: f64 = 2.4506;
pub const JF_EMAX_SLOPE: f64 = -0.0024;
pub const JF_G_INTERCEPT: f64 = 0.1517;
pub const JF_G_SLOPE: f64 = 0.00051;
pub const JF_L_INTERCEPT: f64 = 0.5124;
pub const JF_L_SLOPE: f64 = -0.00010;

pub fn observed_width_change_ev(span_k: f64) -> Result<Value> {
    if span_k <= 0.0 {
        return Err(EngineError::new("span must be positive",
            "a temperature span must be positive", "pass span_k > 0"));
    }
    let as_stated = CHRISTENSEN_DWIDTH_DT * span_k;
    Ok(json!({
        "slope_ev_per_k": CHRISTENSEN_DWIDTH_DT,
        "span_k": span_k,
        "change_as_stated_ev": as_stated,
        "change_if_hwhm_ev": 2.0 * as_stated,
        "source": "Christensen & Sehested 1986, d(delta E_1/2)/dT = 2e-4 eV/K",
        "ambiguity": "delta E_1/2 stated as half-width; FWHM vs HWHM unclear",
    }))
}

pub fn shape_evidence() -> Value {
    json!({
        "two_gaussians_plus_tail": true,
        "g1_width_ev": JF_G1_WIDTH,
        "g2_width_ev": JF_G2_WIDTH,
        "component_width_ratio": JF_G1_WIDTH / JF_G2_WIDTH,
        "component_width_difference_ev": JF_G1_WIDTH - JF_G2_WIDTH,
        "tail_width_ev": JF_TAIL_WIDTH,
        "tail_power_n_water": JF_TAIL_POWER_WATER_N,
        "tail_is_gaussian": false,
        "band_described_as": "broad and highly asymmetric",
        "single_gaussian_compatible": false,
        "sources": [
            "Jou & Freeman, Can. J. Chem. 57, 591 (1979)",
            "Bartels et al., J. Phys. Chem. A (2005)",
            "Turi et al., JCTC 20, 4265 (2024)",
        ],
    })
}

pub fn observed_scales() -> Result<Value> {
    Ok(json!({
        "emax_ev": OBSERVED_EMAX_EV,
        "width": observed_width_change_ev(45.0)?,
        "shape": shape_evidence(),
    }))
}

pub fn jou_freeman_side_widths(temperature_k: f64) -> Result<Value> {
    if temperature_k <= 0.0 {
        return Err(EngineError::new("temperature must be positive",
            "a temperature must be positive", "pass temperature_k > 0"));
    }
    let g = JF_G_INTERCEPT + JF_G_SLOPE * temperature_k;
    let l = JF_L_INTERCEPT + JF_L_SLOPE * temperature_k;
    let emax = JF_EMAX_INTERCEPT + JF_EMAX_SLOPE * temperature_k;
    Ok(json!({
        "temperature_k": temperature_k,
        "red_gaussian_hwhm_ev": g,
        "blue_lorentzian_hwhm_ev": l,
        "emax_ev": emax,
        "side_ratio_blue_over_red": l / g,
        "fwhm_ev": g + l,
        "source": "Jou & Freeman fits via Coe et al. review; Wb/Wr per Bartels",
    }))
}
