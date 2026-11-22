//! Marcus band width from water reorganization energy
//! (fluid_universe/theory/water_marcus.py).

use serde_json::{json, Value};

use crate::domains_fluid_water_born_cavity as bc;
use crate::error::{EngineError, Result};

pub const KB_EV: f64 = 8.617333262e-5;
pub const REFERENCE_CLASSICAL_EV: f64 = 0.706;
pub const REFERENCE_QUANTIZED_EV: f64 = 0.773;
pub const CENTER_EV: f64 = 1.70;

pub fn marcus_width_ev(lambda_ev: f64, temperature_k: f64) -> Result<f64> {
    if lambda_ev <= 0.0 {
        return Err(EngineError::new("lambda must be positive",
            "a reorganization energy must be positive", "pass lambda_ev > 0"));
    }
    if temperature_k <= 0.0 {
        return Err(EngineError::new("temperature must be positive",
            "a temperature must be positive", "pass temperature_k > 0"));
    }
    let sigma = (2.0 * lambda_ev * KB_EV * temperature_k).sqrt();
    Ok(2.0 * (2.0 * std::f64::consts::LN_2).sqrt() * sigma)
}

pub fn gaussian_line_shape(energy_ev: f64, center_ev: f64, fwhm_ev: f64) -> Result<f64> {
    if fwhm_ev <= 0.0 {
        return Err(EngineError::new("fwhm must be positive",
            "a Gaussian line shape needs a positive width", "pass fwhm_ev > 0"));
    }
    let offset = (energy_ev - center_ev) / fwhm_ev;
    Ok((-4.0 * std::f64::consts::LN_2 * offset * offset).exp())
}

pub fn marcus_scales() -> Result<Value> {
    let scales = bc::born_cavity_scales()?;
    let lambda_ev = scales["synthesis"]["lambda_ev"].as_f64().unwrap();
    let mut widths = serde_json::Map::new();
    for temperature in [200, 250, 298, 300, 350] {
        widths.insert(temperature.to_string(),
            Value::from(marcus_width_ev(lambda_ev, temperature as f64)?));
    }
    let width_300 = widths["300"].as_f64().unwrap();
    Ok(json!({
        "lambda_ev": lambda_ev,
        "center_ev": CENTER_EV,
        "widths_ev": Value::Object(widths),
        "reference_classical_ev": REFERENCE_CLASSICAL_EV,
        "reference_quantized_ev": REFERENCE_QUANTIZED_EV,
        "ratio_classical": width_300 / REFERENCE_CLASSICAL_EV,
        "ratio_quantized": width_300 / REFERENCE_QUANTIZED_EV,
        "sqrt_ratio_350_300": (350.0_f64 / 300.0_f64).sqrt(),
    }))
}
