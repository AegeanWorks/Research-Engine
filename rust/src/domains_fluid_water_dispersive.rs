//! Dispersive shallow-water horizon (fluid_universe/theory/water_dispersive.py).

use serde_json::{json, Value};

use crate::domains_fluid_water_analogue as analogue;
use crate::error::{EngineError, Result};

pub const GAMMA: f64 = 0.0728;
pub const DENSITY: f64 = 998.0;

fn validate(k: f64, depth: f64) -> Result<()> {
    if k < 0.0 || depth <= 0.0 {
        return Err(EngineError::new("k must be non-negative and depth positive",
            "a wavenumber needs a non-negative value and positive depth",
            "pass k >= 0 and depth > 0"));
    }
    Ok(())
}

pub fn dispersion(k: f64, depth: f64, gamma: f64, density: f64, gravity: f64) -> Result<f64> {
    validate(k, depth)?;
    let value = (gravity * k + gamma * k.powi(3) / density) * (k * depth).tanh();
    Ok(value.max(0.0).sqrt())
}

pub fn group_velocity(k: f64, depth: f64, gamma: f64, density: f64, gravity: f64) -> Result<f64> {
    validate(k, depth)?;
    if k == 0.0 { return analogue::sound_speed(depth, gravity); }
    let omega = dispersion(k, depth, gamma, density, gravity)?;
    let tangent = (k * depth).tanh();
    let sech_squared = 1.0 - tangent * tangent;
    let numerator = (gravity + 3.0 * gamma * k * k / density) * tangent
        + (gravity * k + gamma * k.powi(3) / density) * depth * sech_squared;
    Ok(numerator / (2.0 * omega))
}

pub fn horizon_wavenumber(omega: f64, depth: f64, gamma: f64, density: f64,
                          gravity: f64, maximum: f64) -> Result<f64> {
    if omega <= 0.0 || depth <= 0.0 || maximum <= 0.0 {
        return Err(EngineError::new("omega, depth and maximum must be positive",
            "a horizon search needs positive bounds", "pass omega, depth and maximum > 0"));
    }
    let residual = |k: f64| -> Result<f64> {
        Ok(k * group_velocity(k, depth, gamma, density, gravity)?
            + dispersion(k, depth, gamma, density, gravity)? - omega)
    };
    let mut lower = 1e-12;
    let mut upper = maximum;
    if residual(lower)? > 0.0 || residual(upper)? < 0.0 {
        return Err(EngineError::new("no bracket for the horizon wavenumber",
            "the frequency lies outside the dispersion range", "pass a different omega or maximum"));
    }
    for _ in 0..200 {
        let middle = 0.5 * (lower + upper);
        if residual(middle)? < 0.0 { lower = middle; } else { upper = middle; }
    }
    Ok(0.5 * (lower + upper))
}

pub fn dispersive_horizon(omega: f64, flow_rate: f64, depth: f64,
                          gamma: f64, density: f64, gravity: f64) -> Result<Value> {
    if flow_rate <= 0.0 {
        return Err(EngineError::new("flow_rate must be positive",
            "a horizon needs a positive drain", "pass flow_rate > 0"));
    }
    let k = horizon_wavenumber(omega, depth, gamma, density, gravity, 1e5)?;
    let velocity = group_velocity(k, depth, gamma, density, gravity)?;
    let radius = flow_rate / (2.0 * std::f64::consts::PI * depth * velocity);
    let long_radius = flow_rate / (2.0 * std::f64::consts::PI * depth
        * analogue::sound_speed(depth, gravity)?);
    Ok(json!({
        "omega_rad_s": omega,
        "k_per_m": k,
        "group_velocity_m_s": velocity,
        "horizon_radius_m": radius,
        "long_wavelength_radius_m": long_radius,
        "ratio": radius / long_radius,
    }))
}

pub fn capillary_frequency(depth: f64, gamma: f64, density: f64, gravity: f64) -> Result<f64> {
    let _ = depth; // retained for signature parity with the Python helper
    let length = analogue::capillary_length(gamma, density, gravity)?;
    Ok((2.0 * gravity / length).sqrt())
}
