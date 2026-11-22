//! HO-1 finite-core node probe (fluid_universe/theory/vortex_core.py).
//!
//! The regularized complex shift psi = (x + i*eps) exp(-x^2 / 2 sigma^2)
//! keeps the density non-zero and the phase/velocity finite at the node.

use serde_json::Value;

use crate::error::{EngineError, Result};

pub const GRID_LENGTH: f64 = 20.0;
const EPS0_FACTOR: f64 = 0.1;

fn bohr_radius(hbar: f64, mass: f64, coupling: f64) -> Result<f64> {
    if hbar <= 0.0 || mass <= 0.0 || coupling <= 0.0 {
        return Err(EngineError::new("hbar, mass and coupling must be positive",
            "the Bohr radius needs positive inputs", "pass positive values"));
    }
    Ok(hbar * hbar / (mass * coupling))
}

/// Pre-registered core radius eps0 = 0.1 * a0 (predicted, not fit).
pub fn core_radius() -> Result<f64> {
    Ok(EPS0_FACTOR * bohr_radius(1.0, 1.0, 1.0)?)
}

pub fn ho_sigma(omega: f64, hbar: f64, mass: f64) -> Result<f64> {
    if omega <= 0.0 || hbar <= 0.0 || mass <= 0.0 {
        return Err(EngineError::new("omega, hbar and mass must be positive",
            "the oscillator width needs positive inputs", "pass positive values"));
    }
    Ok((hbar / (mass * omega)).sqrt())
}

/// Exact L2 norm squared of the core wavefunction.
pub fn core_norm(eps: f64, sigma: f64) -> Result<f64> {
    if eps < 0.0 || sigma <= 0.0 {
        return Err(EngineError::new("eps >= 0 and sigma > 0 required",
            "the core norm requires a non-negative shift and positive width",
            "pass eps >= 0 and sigma > 0"));
    }
    Ok(sigma * std::f64::consts::PI.sqrt() * (sigma * sigma / 2.0 + eps * eps))
}

fn xs_from_json(raw: &str) -> Result<Vec<f64>> {
    serde_json::from_str(raw).map_err(|e| EngineError::new(
        format!("invalid xs JSON: {e}"), "xs must be a JSON array of numbers",
        "pass a JSON array such as [-2,-1,0,1,2]"))
}

/// Normalized core density sampled on a grid.
pub fn core_density(x: &[f64], eps: f64, sigma: f64) -> Result<Vec<f64>> {
    if sigma <= 0.0 {
        return Err(EngineError::new("sigma must be positive",
            "the Gaussian width must be positive", "pass sigma > 0"));
    }
    let raw: Vec<f64> = x.iter().map(|v| {
        let v2 = v * v;
        (v2 + eps * eps) * (-v2 / (sigma * sigma)).exp()
    }).collect();
    if x.len() <= 1 {
        return Ok(raw);
    }
    let sum: f64 = raw.iter().sum();
    let dx = x[1] - x[0];
    let scale = sum * dx;
    if scale == 0.0 {
        return Err(EngineError::new("density normalization is zero",
            "the grid cannot normalize a zero integral", "pass a wider grid"));
    }
    Ok(raw.into_iter().map(|v| v / scale).collect())
}

/// Phase arg(x + i*eps); singular arg(x) at eps = 0.
pub fn core_phase(x: &[f64], eps: f64) -> Result<Vec<f64>> {
    if eps < 0.0 {
        return Err(EngineError::new("eps must be non-negative",
            "a negative core shift is undefined", "pass eps >= 0"));
    }
    Ok(x.iter().map(|v| eps.atan2(*v)).collect())
}

/// v = (hbar/m) dS/dx = -(hbar/m) eps / (x^2 + eps^2).
pub fn core_velocity(x: &[f64], eps: f64, hbar: f64, mass: f64) -> Result<Vec<f64>> {
    if eps < 0.0 || hbar <= 0.0 || mass <= 0.0 {
        return Err(EngineError::new("eps >= 0 and hbar, mass > 0 required",
            "the core velocity needs a non-negative shift and positive constants",
            "pass eps >= 0, hbar > 0 and mass > 0"));
    }
    Ok(x.iter().map(|v| {
        if eps == 0.0 && *v == 0.0 { return f64::NEG_INFINITY; }
        -(hbar / mass) * eps / (v * v + eps * eps)
    }).collect())
}

/// Analytic Q at x = 0.
pub fn core_q_zero(eps: f64, sigma: f64, hbar: f64, mass: f64) -> Result<f64> {
    if eps <= 0.0 || sigma <= 0.0 || hbar <= 0.0 || mass <= 0.0 {
        return Err(EngineError::new("eps, sigma, hbar, mass must be positive",
            "the analytic core Q needs positive inputs", "pass positive values"));
    }
    Ok(-(hbar * hbar) / (2.0 * mass) * (1.0 / (eps * eps) - 1.0 / (sigma * sigma)))
}

/// Second-order central finite-difference Q at x = 0 from sqrt(rho).
pub fn fd_q_zero(eps: f64, n: usize, length: f64, sigma: f64) -> Result<f64> {
    if eps <= 0.0 {
        return Err(EngineError::new("eps must be positive for the FD core probe",
            "a zero shift makes the analytic core singular", "pass eps > 0"));
    }
    if n < 3 {
        return Err(EngineError::new("n must be at least 3",
            "the central difference needs two neighbours", "pass n >= 3"));
    }
    let dx = length / n as f64;
    let half = (n / 2) as i64;
    let x: Vec<f64> = (0..n).map(|i| (i as i64 - half) as f64 * dx).collect();
    let rho = core_density(&x, eps, sigma)?;
    let s: Vec<f64> = rho.into_iter().map(|v| v.max(1e-300).sqrt()).collect();
    let i0 = half as usize;
    let lap = (s[i0 + 1] - 2.0 * s[i0] + s[i0 - 1]) / (dx * dx);
    Ok(-0.5 * lap / s[i0])
}

pub fn json_array(values: Vec<f64>) -> Value {
    Value::Array(values.into_iter().map(Value::from).collect())
}

pub fn parse_xs(raw: &str) -> Result<Vec<f64>> {
    xs_from_json(raw)
}
