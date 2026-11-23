//! Fixed-lambda cavity-Marcus line-shape prediction
//! (fluid_universe/theory/water_lineshape.py).

use serde_json::{json, Value};

use crate::domains_fluid_water_born_cavity as bc;
use crate::domains_fluid_water_marcus as wm;
use crate::domains_fluid_water_temperature as wt;
use crate::error::Result;

pub const KB_EV: f64 = 8.617333262e-5;
pub const LAMBDA_EV: f64 = 1.6171325440878093;
pub const WIDTH_RATIO_TOL: f64 = 0.05;
pub const SHAPE_RATIO_TOL: f64 = 0.15;
pub const SKEW_TOL: f64 = 0.3;

/// Exact symmetry facts for a Gaussian band (no inputs, no fit).
pub fn gaussian_moments() -> Value {
    json!({
        "skewness": 0.0,
        "half_width_ratio": 1.0,
        "third_central_moment": 0.0,
        "symmetric": true,
    })
}

pub fn predicted_widths() -> Result<Value> {
    let scales = wt::temperature_scales()?;
    let scan = scales.get("scan").and_then(Value::as_array).unwrap();
    let cold = &scan[0];
    let warm = &scan[scan.len() - 1];
    let cold_lambda = cold["lambda_ev"].as_f64().unwrap();
    let warm_lambda = warm["lambda_ev"].as_f64().unwrap();
    let width_0c = wm::marcus_width_ev(cold_lambda, 273.15)?;
    let width_45c = wm::marcus_width_ev(warm_lambda, 318.15)?;
    Ok(json!({
        "lambda_0c_ev": cold_lambda,
        "lambda_45c_ev": warm_lambda,
        "width_0c_ev": width_0c,
        "width_45c_ev": width_45c,
        "width_change_ev": width_45c - width_0c,
        "width_ratio_45_over_0": width_45c / width_0c,
    }))
}

pub fn kill_thresholds() -> Value {
    json!({
        "width_ratio_tol": WIDTH_RATIO_TOL,
        "shape_ratio_tol": SHAPE_RATIO_TOL,
        "skew_tol": SKEW_TOL,
    })
}

pub fn lineshape_scales() -> Result<Value> {
    let scales = bc::born_cavity_scales()?;
    let fixed_lambda = scales["synthesis"]["lambda_ev"].as_f64().unwrap();
    Ok(json!({
        "lambda_ev": fixed_lambda,
        "moments": gaussian_moments(),
        "prediction": predicted_widths()?,
        "thresholds": kill_thresholds(),
    }))
}
