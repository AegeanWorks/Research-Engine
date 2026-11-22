//! Osmotic-closure no-go at PDE level (fluid_universe/theory/nelson_closure.py).

use serde_json::{json, Value};

use crate::error::{EngineError, Result};

const GRID_NS: &[usize] = &[256, 512, 1024, 2048];
const GRID_LENGTH: f64 = 20.0;
const DIFFUSION: f64 = 0.5;
const TRIAL_SIGMA_SQ: &[f64] = &[0.125, 0.25, 0.5, 1.0, 2.0];
const FLOOR: f64 = 1e-300;

/// numpy.gradient with edge_order=1: central interior, one-sided boundaries.
pub fn gradient(values: &[f64], dx: f64) -> Result<Vec<f64>> {
    if dx <= 0.0 {
        return Err(EngineError::new("dx must be positive",
            "a finite difference needs a positive step", "pass dx > 0"));
    }
    if values.is_empty() { return Ok(Vec::new()); }
    if values.len() == 1 { return Ok(vec![0.0]); }
    let n = values.len();
    let mut out = Vec::with_capacity(n);
    out.push((values[1] - values[0]) / dx);
    for i in 1..n - 1 {
        out.push((values[i + 1] - values[i - 1]) / (2.0 * dx));
    }
    out.push((values[n - 1] - values[n - 2]) / dx);
    Ok(out)
}

pub fn trapezoid(values: &[f64], x: &[f64]) -> f64 {
    let mut total = 0.0;
    for i in 0..x.len() - 1 {
        total += (x[i + 1] - x[i]) * (values[i] + values[i + 1]) / 2.0;
    }
    total
}

/// Least-squares slope of a first-degree polyfit.
pub fn polyfit_slope(x: &[f64], y: &[f64]) -> Result<f64> {
    if x.len() != y.len() || x.len() < 2 {
        return Err(EngineError::new("polyfit needs matching arrays of at least two points",
            "a linear fit needs at least two samples", "pass equal-length arrays of length >= 2"));
    }
    let mean_x: f64 = x.iter().sum::<f64>() / x.len() as f64;
    let mean_y: f64 = y.iter().sum::<f64>() / y.len() as f64;
    let mut numerator = 0.0;
    let mut denominator = 0.0;
    for (xv, yv) in x.iter().zip(y) {
        let dx = xv - mean_x;
        numerator += dx * (yv - mean_y);
        denominator += dx * dx;
    }
    if denominator == 0.0 {
        return Err(EngineError::new("polyfit x values are constant",
            "a slope needs varying x values", "pass distinct x samples"));
    }
    Ok(numerator / denominator)
}

fn grid_x(n: usize, length: f64) -> Vec<f64> {
    let dx = length / n as f64;
    (0..n).map(|i| (i as i64 - (n / 2) as i64) as f64 * dx).collect()
}

pub fn trial_gaussian(x: &[f64], sigma_sq: f64) -> Result<Vec<f64>> {
    if sigma_sq <= 0.0 {
        return Err(EngineError::new("sigma_sq must be positive",
            "a Gaussian needs a positive variance", "pass sigma_sq > 0"));
    }
    let scale = 1.0 / (2.0 * std::f64::consts::PI * sigma_sq).sqrt();
    Ok(x.iter().map(|v| (-v * v / (2.0 * sigma_sq)).exp() * scale).collect())
}

pub fn trial_bimodal(x: &[f64]) -> Result<Vec<f64>> {
    let left = trial_gaussian(&x.iter().map(|v| v + 2.0).collect::<Vec<_>>(), 0.25)?;
    let right = trial_gaussian(&x.iter().map(|v| v - 2.0).collect::<Vec<_>>(), 0.25)?;
    let mix: Vec<f64> = left.iter().zip(right).map(|(l, r)| 0.5 * (l + r)).collect();
    let norm = trapezoid(&mix, x);
    Ok(mix.into_iter().map(|v| v / norm).collect())
}

pub fn osmotic_velocity(rho: &[f64], dx: f64) -> Result<Vec<f64>> {
    let safe: Vec<f64> = rho.iter().map(|v| v.max(FLOOR)).collect();
    let logs: Vec<f64> = safe.iter().map(|v| v.ln()).collect();
    let grad = gradient(&logs, dx)?;
    Ok(grad.into_iter().map(|v| 0.5 * v).collect())
}

pub fn fp_residual(rho: &[f64], dx: f64, diffusion: f64) -> Result<Vec<f64>> {
    let drift = osmotic_velocity(rho, dx)?;
    let safe: Vec<f64> = rho.iter().map(|v| v.max(FLOOR)).collect();
    let scaled: f64 = diffusion / 0.5;
    let flux: Vec<f64> = drift.iter().zip(&safe).map(|(d, r)| d * scaled * r).collect();
    let divergence = gradient(&flux, dx)?;
    let first = gradient(&safe, dx)?;
    let laplacian = gradient(&first, dx)?;
    Ok(divergence.iter().zip(laplacian).map(|(d, l)| -d + diffusion * l).collect())
}

pub fn interior_mask(x: &[f64], length: f64) -> Vec<bool> {
    x.iter().map(|v| v.abs() < length / 2.0 - 1.0).collect()
}

pub fn ground_state_density(x: &[f64], omega: f64) -> Vec<f64> {
    let width = (1.0 / (2.0 * omega)).sqrt();
    let scale = 1.0 / ((2.0 * std::f64::consts::PI).sqrt() * width);
    x.iter().map(|v| (-v * v / (2.0 * width * width)).exp() * scale).collect()
}

pub fn free_packet_drift(x: &[f64], t: f64, sigma: f64) -> Result<Vec<f64>> {
    if sigma <= 0.0 {
        return Err(EngineError::new("sigma must be positive",
            "a free packet needs a positive width", "pass sigma > 0"));
    }
    let tau = t / (2.0 * sigma * sigma);
    let width = sigma * (1.0 + tau * tau).sqrt();
    let velocity_scale = tau / (2.0 * sigma * sigma * (1.0 + tau * tau));
    let osmotic_scale = -0.5 / (width * width);
    Ok(x.iter().map(|v| velocity_scale * v + osmotic_scale * v).collect())
}

/// Python's str(float) always keeps a decimal point for integral values.
fn py_float(value: f64) -> String {
    let text = format!("{value}");
    if !text.contains('.') && !text.contains('e') && !text.contains('E') {
        format!("{text}.0")
    } else {
        text
    }
}

fn residual_row(kind: &str, sigma_sq: Option<f64>) -> Result<Value> {
    let mut dx_values = Vec::new();
    let mut full_values = Vec::new();
    let mut interior_values = Vec::new();
    for n in GRID_NS {
        let dx = GRID_LENGTH / *n as f64;
        let x = grid_x(*n, GRID_LENGTH);
        let rho = match kind {
            "gaussian" => trial_gaussian(&x, sigma_sq.unwrap())?,
            _ => trial_bimodal(&x)?,
        };
        let residual: Vec<f64> = fp_residual(&rho, dx, DIFFUSION)?.into_iter().map(|v| v.abs()).collect();
        let mask = interior_mask(&x, GRID_LENGTH);
        let full = residual.iter().copied().fold(0.0_f64, f64::max);
        let interior = residual.iter().zip(mask)
            .filter(|(_, inside)| *inside)
            .map(|(v, _)| *v)
            .fold(0.0_f64, f64::max);
        dx_values.push(dx);
        full_values.push(full);
        interior_values.push(interior);
    }
    let log_n: Vec<f64> = GRID_NS.iter().map(|n| (*n as f64).ln()).collect();
    let log_full: Vec<f64> = full_values.iter().map(|v| v.ln()).collect();
    let log_interior: Vec<f64> = interior_values.iter().map(|v| v.ln()).collect();
    Ok(json!({
        "dx": dx_values,
        "full": full_values,
        "interior": interior_values,
        "slope_full": polyfit_slope(&log_n, &log_full)?,
        "slope_interior": polyfit_slope(&log_n, &log_interior)?,
    }))
}

pub fn residual_scaling() -> Result<Value> {
    let mut rows = serde_json::Map::new();
    for sq in TRIAL_SIGMA_SQ {
        rows.insert(format!("gauss_{}", py_float(*sq)), residual_row("gaussian", Some(*sq))?);
    }
    rows.insert("bimodal".to_string(), residual_row("bimodal", None)?);
    Ok(json!({
        "grids": GRID_NS,
        "length": GRID_LENGTH,
        "rows": Value::Object(rows),
    }))
}

pub fn frozen_drift_sigma_map() -> Result<Value> {
    let mut entries = Vec::new();
    for sq in TRIAL_SIGMA_SQ {
        let mut sigma_values = Vec::new();
        for n in GRID_NS {
            let dx = GRID_LENGTH / *n as f64;
            let x = grid_x(*n, GRID_LENGTH);
            let rho0 = trial_gaussian(&x, *sq)?;
            let drift = osmotic_velocity(&rho0, dx)?;
            let mut increments = Vec::new();
            for pair in drift.windows(2) {
                increments.push(0.5 * (pair[1] + pair[0]) * dx / DIFFUSION);
            }
            let mut log_star = vec![0.0];
            let mut running = 0.0;
            for value in increments {
                running += value;
                log_star.push(running);
            }
            let peak = log_star.iter().copied().fold(f64::NEG_INFINITY, f64::max);
            let star: Vec<f64> = log_star.iter().map(|v| {
                let shifted = v - peak;
                shifted.max(-700.0).min(0.0).exp()
            }).collect();
            let norm = trapezoid(&star, &x);
            let normalized: Vec<f64> = star.iter().map(|v| v / norm).collect();
            let moment: Vec<f64> = x.iter().zip(&normalized).map(|(r, s)| r * r * s).collect();
            let sigma_sq = trapezoid(&moment, &x);
            sigma_values.push(sigma_sq.max(0.0).sqrt());
        }
        let sigma0 = sq.sqrt();
        let errors: Vec<f64> = sigma_values.iter().map(|v| (v - sigma0).abs()).collect();
        let max_error = errors.iter().copied().fold(0.0_f64, f64::max);
        let (slope, floor) = if max_error <= 1e-13 {
            (0.0, true)
        } else {
            let log_n: Vec<f64> = GRID_NS.iter().map(|n| (*n as f64).ln()).collect();
            let log_errors: Vec<f64> = errors.iter().map(|v| v.max(FLOOR).ln()).collect();
            (polyfit_slope(&log_n, &log_errors)?, false)
        };
        entries.push(json!({
            "sigma0_sq": sq,
            "sigma_star": sigma_values,
            "abs_errors": errors,
            "error_slope": slope,
            "error_floor": floor,
        }));
    }
    Ok(json!({"entries": entries}))
}

pub fn ou_free_packet_instances() -> Result<Value> {
    let step = 20.0 / 4096.0;
    let mut x: Vec<f64> = (0..4097).map(|i| -10.0 + i as f64 * step).collect();
    x[4096] = 10.0;
    let dx = x[1] - x[0];
    let rho_ou = ground_state_density(&x, 1.0);
    let residual = fp_residual(&rho_ou, dx, DIFFUSION)?;
    let mask = interior_mask(&x, GRID_LENGTH);
    let interior = residual.iter().zip(&mask).filter(|(_, m)| **m)
        .map(|(v, _)| v.abs()).fold(0.0_f64, f64::max);
    let full = residual.iter().map(|v| v.abs()).fold(0.0_f64, f64::max);
    Ok(json!({
        "ou_residual_interior": interior,
        "ou_residual_full": full,
        "free_drift_at_zero": free_packet_drift(&[0.0, 1.0, -1.0], 0.0, 1.0)?,
    }))
}

pub fn closure_scales() -> Result<Value> {
    Ok(json!({
        "grids": {"ns": GRID_NS, "length": GRID_LENGTH},
        "diffusion": DIFFUSION,
        "probes": {"gauss_sigma_sq": TRIAL_SIGMA_SQ, "bimodal": true},
        "units": {"hbar": 1.0, "mass": 1.0, "omega": 1.0},
        "stationary_map": residual_scaling()?,
        "sigma_map": frozen_drift_sigma_map()?,
        "instances": ou_free_packet_instances()?,
    }))
}
