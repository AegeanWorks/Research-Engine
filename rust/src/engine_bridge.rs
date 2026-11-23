//! Fluid-universe Gaussian bridge primitives (domains/fluid_universe/theory/gaussian_bridge.py).

use serde_json::{json, Value};

use crate::error::{EngineError, Result};

pub fn diffusivity(hbar: f64, mass: f64) -> Result<f64> {
    if hbar <= 0.0 || mass <= 0.0 {
        return Err(EngineError::new("hbar and mass must be positive",
            "diffusivity is defined only for positive parameters", "pass positive hbar and mass"));
    }
    Ok(hbar / (2.0 * mass))
}

pub fn horizon(omega: f64) -> Result<f64> {
    if omega <= 0.0 {
        return Err(EngineError::new("omega must be positive",
            "the horizon is defined only for positive omega", "pass a positive omega"));
    }
    Ok(std::f64::consts::PI / (4.0 * omega))
}

pub fn pinney_coeffs(s0: f64, st: f64, horizon_t: f64, omega: f64,
                     hbar: f64, mass: f64) -> Result<Vec<Value>> {
    let nu = diffusivity(hbar, mass)?;
    let u_t = (omega * horizon_t).cos();
    let v_t = (omega * horizon_t).sin() / omega;
    let a = s0 * s0;
    let a2 = u_t * u_t;
    let b2 = 2.0 * u_t * v_t;
    let c2 = v_t * v_t;
    if c2.abs() < 1e-15 {
        return Err(EngineError::new("degenerate endpoint basis (vT == 0)",
            "the quadratic cannot be solved", "choose an omega/horizon with non-zero vT"));
    }
    let qb = a * b2 / c2;
    let qc = nu * nu - a * st * st / c2 + a * a * a2 / c2;
    let disc = qb * qb - 4.0 * qc;
    if disc < 0.0 { return Ok(Vec::new()); }
    let mut out = Vec::new();
    for sign in [1.0f64, -1.0f64] {
        let b = (-qb + sign * disc.sqrt()) / 2.0;
        let c = (st * st - a * a2 - b * b2) / c2;
        out.push(json!({"A": a, "B": b, "C": c}));
    }
    out.sort_by(|left, right| {
        let lb = left.get("B").and_then(Value::as_f64).unwrap_or(0.0).abs();
        let rb = right.get("B").and_then(Value::as_f64).unwrap_or(0.0).abs();
        lb.partial_cmp(&rb).unwrap_or(std::cmp::Ordering::Equal)
    });
    Ok(out)
}

pub fn pinney_path(coeffs: &Value, times: &[f64], omega: f64) -> Vec<f64> {
    let a = coeffs.get("A").and_then(Value::as_f64).unwrap_or(0.0);
    let b = coeffs.get("B").and_then(Value::as_f64).unwrap_or(0.0);
    let c = coeffs.get("C").and_then(Value::as_f64).unwrap_or(0.0);
    times.iter().map(|t| {
        let u = (omega * t).cos();
        let v = (omega * t).sin() / omega;
        (a * u * u + 2.0 * b * u * v + c * v * v).max(0.0).sqrt()
    }).collect()
}
