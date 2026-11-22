//! Hydrogen 2p vortex identification
//! (fluid_universe/theory/hydrogen_vortex.py).

use serde_json::Value;

use crate::domains_fluid_nelson_closure as nc;
use crate::error::{EngineError, Result};

pub fn radial_2p(r: &[f64], radius: f64) -> Result<Vec<f64>> {
    if radius <= 0.0 {
        return Err(EngineError::new("radius must be positive",
            "a hydrogenic radius must be positive", "pass radius > 0"));
    }
    let scale = 1.0 / (2.0 * 6.0_f64.sqrt() * radius.powf(1.5));
    Ok(r.iter().map(|v| scale * (v / radius) * (-v / (2.0 * radius)).exp()).collect())
}

pub fn radial_probability(r: &[f64], radius: f64) -> Result<Vec<f64>> {
    let values = radial_2p(r, radius)?;
    Ok(r.iter().zip(values).map(|(v, f)| v * v * f * f).collect())
}

pub fn most_probable_radius(radius: f64) -> Result<f64> {
    if radius <= 0.0 {
        return Err(EngineError::new("radius must be positive",
            "a hydrogenic radius must be positive", "pass radius > 0"));
    }
    Ok(4.0 * radius)
}

pub fn azimuthal_velocity(r: f64, theta: f64, m: i64, hbar: f64, mass: f64) -> Result<f64> {
    if r <= 0.0 || hbar <= 0.0 || mass <= 0.0 {
        return Err(EngineError::new("r, hbar and mass must be positive",
            "the azimuthal flow needs positive inputs", "pass r, hbar and mass > 0"));
    }
    let sine = theta.sin();
    if sine.abs() < 1e-12 {
        return Err(EngineError::new("theta must be away from the poles",
            "the azimuthal velocity diverges at the poles", "pass theta away from 0 and pi"));
    }
    Ok(hbar * m as f64 / (mass * r * sine))
}

pub fn circulation(m: i64, hbar: f64, mass: f64) -> Result<f64> {
    if hbar <= 0.0 || mass <= 0.0 {
        return Err(EngineError::new("hbar and mass must be positive",
            "a circulation needs positive constants", "pass hbar > 0 and mass > 0"));
    }
    Ok(2.0 * std::f64::consts::PI * hbar * m as f64 / mass)
}

pub fn loop_circulation(r: f64, theta: f64, m: i64, hbar: f64, mass: f64,
                        samples: usize) -> Result<f64> {
    if samples < 16 {
        return Err(EngineError::new("samples must be at least 16",
            "a loop integral needs at least 16 samples", "pass samples >= 16"));
    }
    let velocity = azimuthal_velocity(r, theta, m, hbar, mass)?;
    let span = 2.0 * std::f64::consts::PI;
    let step = span / (samples - 1) as f64;
    let phi: Vec<f64> = (0..samples).map(|i| i as f64 * step).collect();
    let constant = velocity * r * theta.sin();
    let values: Vec<f64> = phi.iter().map(|_| constant).collect();
    Ok(nc::trapezoid(&values, &phi))
}

pub fn angular_momentum(m: i64, hbar: f64) -> Result<f64> {
    if hbar <= 0.0 {
        return Err(EngineError::new("hbar must be positive",
            "an angular momentum needs positive hbar", "pass hbar > 0"));
    }
    Ok(hbar * m as f64)
}

pub fn json_array(values: Vec<f64>) -> Value {
    Value::Array(values.into_iter().map(Value::from).collect())
}

pub fn parse_xs(raw: &str) -> Result<Vec<f64>> {
    serde_json::from_str(raw).map_err(|e| EngineError::new(
        format!("invalid xs JSON: {e}"), "xs must be a JSON array of numbers",
        "pass a JSON array of numbers"))
}
