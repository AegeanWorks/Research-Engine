//! Exact algebra of the Hermitian 3x3 circulant mass matrix
//! (fluid_universe/theory/circulant.py).

use serde_json::{json, Value};

use crate::error::{EngineError, Result};

const TAU: f64 = std::f64::consts::PI * 2.0;

fn cis(angle: f64) -> (f64, f64) {
    (angle.cos(), angle.sin())
}

/// M = circ(a, c exp(i delta), c exp(-i delta)) as (re, im) entries.
pub fn circulant_matrix(a: f64, c: f64, delta: f64) -> [[(f64, f64); 3]; 3] {
    let (cos, sin) = cis(delta);
    let b = (c * cos, c * sin);
    let bc = (c * cos, -c * sin);
    let real = (a, 0.0);
    [[real, b, bc], [bc, real, b], [b, bc, real]]
}

pub fn dft_vectors() -> [[(f64, f64); 3]; 3] {
    let norm = 3.0_f64.sqrt();
    let mut out = [[(0.0, 0.0); 3]; 3];
    for n in 0..3 {
        for k in 0..3 {
            let exponent = (k * n) % 3;
            let omega_power = if exponent == 0 {
                (1.0, 0.0)
            } else if exponent == 1 {
                cis(TAU / 3.0)
            } else {
                cis(2.0 * TAU / 3.0)
            };
            out[n][k] = (omega_power.0 / norm, omega_power.1 / norm);
        }
    }
    out
}

/// Signed eigenvalues in the k = 0, 1, 2 order.
pub fn eigenvalues(a: f64, c: f64, delta: f64) -> Vec<f64> {
    (0..3).map(|k| a + 2.0 * c * (delta + TAU * k as f64 / 3.0).cos()).collect()
}

fn sum(values: &[f64]) -> f64 {
    values.iter().sum()
}

pub fn q_signed(x: &[f64]) -> f64 {
    let total = sum(x);
    sum(&x.iter().map(|v| v * v).collect::<Vec<_>>()) / (total * total)
}

pub fn q_masses(m: &[f64]) -> f64 {
    let roots: Vec<f64> = m.iter().map(|v| v.sqrt()).collect();
    let root_sum = sum(&roots);
    sum(m) / (root_sum * root_sum)
}

pub fn q_physical_from_roots(x: &[f64]) -> f64 {
    let abs_sum: f64 = x.iter().map(|v| v.abs()).sum();
    sum(&x.iter().map(|v| v * v).collect::<Vec<_>>()) / (abs_sum * abs_sum)
}

pub fn q_from_ac(a: f64, c: f64) -> f64 {
    1.0 / 3.0 + 2.0 * c * c / (3.0 * a * a)
}

/// Inverse DFT: (a, c, delta) from three signed roots.
pub fn extract_ac_delta(x: &[f64]) -> Result<(f64, f64, f64)> {
    if x.len() != 3 {
        return Err(EngineError::new("expected exactly three roots",
            "the inverse DFT needs three signed roots", "pass an array of length 3"));
    }
    let a = sum(x) / 3.0;
    // conj(omega)^k = exp(-i * 2*pi*k/3)
    let mut re = 0.0;
    let mut im = 0.0;
    for k in 0..3 {
        let angle = -TAU * k as f64 / 3.0;
        let (cr, ci) = cis(angle);
        re += x[k] * cr;
        im += x[k] * ci;
    }
    re /= 3.0;
    im /= 3.0;
    let c = (re * re + im * im).sqrt();
    let mut delta = im.atan2(re);
    if delta < 0.0 { delta += TAU; }
    let delta = if c < 1e-14 { 0.0 } else { delta };
    Ok((a, c, delta))
}

pub fn fit_masses(m: &[f64]) -> Result<Value> {
    if m.is_empty() || m.iter().any(|v| *v <= 0.0) {
        return Err(EngineError::new("masses must be positive",
            "the physical Koide fit needs strictly positive masses", "pass positive masses"));
    }
    let roots: Vec<f64> = m.iter().map(|v| v.sqrt()).collect();
    let (a, c, delta) = extract_ac_delta(&roots)?;
    let fitted = eigenvalues(a, c, delta);
    let residual: Vec<f64> = fitted.iter().zip(&roots).map(|(f, r)| f - r).collect();
    let max_abs_residual = residual.iter().map(|v| v.abs()).fold(0.0_f64, f64::max);
    Ok(json!({
        "a": a,
        "c": c,
        "delta": delta,
        "r": c / a,
        "Q": q_masses(m),
        "Q_from_ac": q_from_ac(a, c),
        "max_abs_residual": max_abs_residual,
        "all_roots_positive": fitted.iter().all(|v| *v >= 0.0),
    }))
}

/// Solve Q = 2/3 for m_tau given m_e and m_mu (larger positive root).
pub fn koide_tau_prediction(m_e: f64, m_mu: f64) -> Result<f64> {
    if m_e < 0.0 || m_mu < 0.0 {
        return Err(EngineError::new("masses must be non-negative",
            "the Koide prediction takes non-negative input masses", "pass m_e >= 0 and m_mu >= 0"));
    }
    let s = m_e.sqrt() + m_mu.sqrt();
    let b = -4.0 * s;
    let c = 3.0 * (m_e + m_mu) - 2.0 * s * s;
    let disc = b * b - 4.0 * c;
    if disc < 0.0 {
        return Err(EngineError::new("no positive tau root",
            "the Koide discriminant is negative for these inputs", "pass different masses"));
    }
    let root = disc.sqrt();
    let r1 = (-b - root) / 2.0;
    let r2 = (-b + root) / 2.0;
    let mut positive: Vec<f64> = Vec::new();
    for value in [r1, r2] {
        if value > 0.0 { positive.push(value); }
    }
    if positive.is_empty() {
        return Err(EngineError::new("no positive tau root",
            "both quadratic roots are non-positive", "pass different masses"));
    }
    Ok(positive.into_iter().fold(f64::NEG_INFINITY, f64::max).powi(2))
}
