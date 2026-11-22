//! First excited state in the Madelung fluid
//! (fluid_universe/theory/excited_fluid.py).

use serde_json::Value;

use crate::domains_fluid_nelson_closure as nc;
use crate::error::{EngineError, Result};

pub fn oscillator_width(omega: f64, hbar: f64, mass: f64) -> Result<f64> {
    if omega <= 0.0 || hbar <= 0.0 || mass <= 0.0 {
        return Err(EngineError::new("omega, hbar and mass must be positive",
            "the oscillator width needs positive inputs", "pass omega, hbar and mass > 0"));
    }
    Ok((hbar / (mass * omega)).sqrt())
}

pub fn excited_density(x: &[f64], omega: f64, hbar: f64, mass: f64) -> Result<Vec<f64>> {
    let sigma = oscillator_width(omega, hbar, mass)?;
    let scale = 2.0 / (std::f64::consts::PI.sqrt() * sigma.powi(3));
    Ok(x.iter().map(|v| scale * v * v * (-v * v / (sigma * sigma)).exp()).collect())
}

pub fn excited_wavefunction(x: &[f64], omega: f64, hbar: f64, mass: f64) -> Result<Vec<f64>> {
    let sigma = oscillator_width(omega, hbar, mass)?;
    let scale = 2.0_f64.sqrt() / (std::f64::consts::PI.powf(0.25) * sigma.sqrt());
    Ok(x.iter().map(|v| scale * (v / sigma) * (-v * v / (2.0 * sigma * sigma)).exp()).collect())
}

pub fn excited_quantum_pressure_regular(x: &[f64], omega: f64, hbar: f64,
                                        mass: f64) -> Result<Vec<f64>> {
    let sigma = oscillator_width(omega, hbar, mass)?;
    let scale = hbar * hbar / (2.0 * mass * sigma * sigma);
    Ok(x.iter().map(|v| scale * (3.0 - v * v / (sigma * sigma))).collect())
}

/// np.angle of a real-valued array: 0 for non-negative, pi for negative.
fn phases(psi: &[f64]) -> Vec<f64> {
    psi.iter().map(|v| if *v < 0.0 { std::f64::consts::PI } else { 0.0 }).collect()
}

pub fn phase_slip(psi: &[f64]) -> f64 {
    let phase = phases(psi);
    let low = phase.iter().copied().fold(f64::INFINITY, f64::min);
    let high = phase.iter().copied().fold(f64::NEG_INFINITY, f64::max);
    if low.is_infinite() || high.is_infinite() { 0.0 } else { high - low }
}

pub fn phase_gradient_max(psi: &[f64], dx: f64) -> Result<f64> {
    if dx <= 0.0 {
        return Err(EngineError::new("dx must be positive",
            "a phase gradient needs a positive step", "pass dx > 0"));
    }
    let phase = phases(psi);
    let grad = nc::gradient(&phase, dx)?;
    Ok(grad.iter().map(|v| v.abs()).fold(0.0_f64, f64::max))
}

pub fn scaling_slope(dx: &[f64], maxima: &[f64]) -> Result<f64> {
    if dx.len() != maxima.len() || dx.len() < 2 {
        return Err(EngineError::new("dx_values and maxima must have the same length >= 2",
            "a log-log fit needs matching arrays of at least two points",
            "pass equal-length arrays of length >= 2"));
    }
    let log_dx: Vec<f64> = dx.iter().map(|v| v.ln()).collect();
    let log_max: Vec<f64> = maxima.iter().map(|v| v.ln()).collect();
    nc::polyfit_slope(&log_dx, &log_max)
}

pub fn json_array(values: Vec<f64>) -> Value {
    Value::Array(values.into_iter().map(Value::from).collect())
}

pub fn parse_xs(raw: &str) -> Result<Vec<f64>> {
    serde_json::from_str(raw).map_err(|e| EngineError::new(
        format!("invalid xs JSON: {e}"), "xs must be a JSON array of numbers",
        "pass a JSON array of numbers"))
}
