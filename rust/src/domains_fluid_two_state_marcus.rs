//! Shared-lambda two-state Marcus assignment
//! (fluid_universe/theory/two_state_marcus.py).

use serde_json::{json, Value};

use crate::error::{EngineError, Result};

pub const KB_EV: f64 = 8.617333262e-5;
pub const LAMBDA_EV: f64 = 1.6171325440878093;
pub const SHAPE_RATIO_TOL: f64 = 0.15;
pub const ROOM_TEMPERATURE_K: f64 = 300.0;
const G1_WIDTH: f64 = 0.71;
const G1_SIGMA: f64 = 0.07;
const G2_WIDTH: f64 = 0.37;
const G2_SIGMA: f64 = 0.08;

/// Classical Marcus Gaussian FWHM in eV.
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

pub fn shared_lambda_widths(temperature_k: f64) -> Result<Value> {
    if temperature_k <= 0.0 {
        return Err(EngineError::new("temperature must be positive",
            "a temperature must be positive", "pass temperature_k > 0"));
    }
    let width = marcus_width_ev(LAMBDA_EV, temperature_k)?;
    Ok(json!({
        "lambda_ev": LAMBDA_EV,
        "temperature_k": temperature_k,
        "width_g1_ev": width,
        "width_g2_ev": width,
        "predicted_ratio": 1.0,
    }))
}

pub fn component_ratio() -> Value {
    let ratio = G1_WIDTH / G2_WIDTH;
    let ratio_sigma = ratio * ((G1_SIGMA / G1_WIDTH).powi(2) + (G2_SIGMA / G2_WIDTH).powi(2)).sqrt();
    json!({
        "g1_width_ev": G1_WIDTH,
        "g2_width_ev": G2_WIDTH,
        "observed_ratio": ratio,
        "observed_ratio_sigma": ratio_sigma,
        "diff_vs_one": (ratio - 1.0).abs(),
        "worst_case_ratio": 2.0,
        "worst_case_diff_vs_one": 1.0,
    })
}

pub fn kill_thresholds() -> Value {
    json!({"shape_ratio_tol": SHAPE_RATIO_TOL})
}

pub fn two_state_scales(temperature_k: f64) -> Result<Value> {
    Ok(json!({
        "lambda_ev": LAMBDA_EV,
        "prediction": shared_lambda_widths(temperature_k)?,
        "observed": component_ratio(),
        "thresholds": kill_thresholds(),
    }))
}
