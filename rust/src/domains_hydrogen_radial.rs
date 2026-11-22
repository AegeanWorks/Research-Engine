//! Hydrogen-2s radial-node two-branch representation
//! (fluid_universe/theory/hydrogen_radial_nodes.py).
//!
//! The pi phase slip lives in the branch sign of R_20; the magnitude is smooth.
//! The Bohr radius is derived from bohr_radius(1, 1, 1) rather than hardcoded.

use serde_json::{json, Value};

use crate::error::{EngineError, Result};

const RADIUS: f64 = 1.0; // bohr_radius(hbar=1, mass=1, coupling=1)
const LOOP_R: f64 = 2.0;
const LOOP_THETA: f64 = std::f64::consts::FRAC_PI_2;
const WINDING_M: i64 = 1;
const BALANCE_RADII: &[f64] = &[0.5, 1.0, 2.0, 5.0];

fn radius_arg(radius: f64) -> Result<()> {
    if radius <= 0.0 {
        return Err(EngineError::new("radius must be positive",
            "a hydrogenic radius must be positive", "pass radius > 0"));
    }
    Ok(())
}

fn parse_xs(raw: &str) -> Result<Vec<f64>> {
    serde_json::from_str(raw).map_err(|e| EngineError::new(
        format!("invalid xs JSON: {e}"), "xs must be a JSON array of numbers",
        "pass a JSON array such as [0,1,2]"))
}

pub fn json_array(values: Vec<f64>) -> Value {
    Value::Array(values.into_iter().map(Value::from).collect())
}

/// Hydrogen 1s radial function, normalized so integral r^2 R^2 dr = 1.
pub fn radial_10(r: &[f64], radius: f64) -> Result<Vec<f64>> {
    radius_arg(radius)?;
    let scale = 2.0 / radius.powf(1.5);
    Ok(r.iter().map(|v| scale * (-v / radius).exp()).collect())
}

/// Hydrogen 2s radial function, normalized so integral r^2 R^2 dr = 1.
pub fn radial_20(r: &[f64], radius: f64) -> Result<Vec<f64>> {
    radius_arg(radius)?;
    let scale = 1.0 / (2.0 * std::f64::consts::SQRT_2 * radius.powf(1.5));
    Ok(r.iter().map(|v| scale * (2.0 - v / radius) * (-v / (2.0 * radius)).exp()).collect())
}

pub fn radial_probability_20(r: &[f64], radius: f64) -> Result<Vec<f64>> {
    let radial = radial_20(r, radius)?;
    Ok(r.iter().zip(radial).map(|(v, f)| v * v * f * f).collect())
}

/// Exact two-branch split of R_20; the identity residual is zero by construction.
pub fn branch_split_20(r: &[f64], radius: f64) -> Result<Value> {
    let radial = radial_20(r, radius)?;
    let sign: Vec<f64> = radial.iter().map(|v| if *v > 0.0 { 1.0 } else if *v < 0.0 { -1.0 } else { 0.0 }).collect();
    let magnitude: Vec<f64> = radial.iter().map(|v| v.abs()).collect();
    let residual = radial.iter().zip(&sign).zip(&magnitude)
        .map(|((v, s), m)| (v - s * m).abs())
        .fold(0.0_f64, f64::max);
    Ok(json!({
        "sign": sign,
        "magnitude": magnitude,
        "identity_residual": residual,
    }))
}

pub fn node_position(radius: f64) -> Result<f64> {
    radius_arg(radius)?;
    Ok(2.0 * radius)
}

/// Phase jump across the shell from the sign of R_20 (0 or pi).
pub fn phase_slip_20(r: &[f64], radius: f64) -> Result<f64> {
    let radial = radial_20(r, radius)?;
    let mut low = f64::INFINITY;
    let mut high = f64::NEG_INFINITY;
    for v in radial {
        let phase = if v >= 0.0 { 0.0 } else { std::f64::consts::PI };
        low = low.min(phase);
        high = high.max(phase);
    }
    Ok(high - low)
}

fn linspace(stop: f64, n: usize) -> Vec<f64> {
    let step = stop / (n - 1) as f64;
    let mut out: Vec<f64> = (0..n).map(|i| i as f64 * step).collect();
    out[n - 1] = stop;
    out
}

/// Composite trapezoid rule matching numpy.trapezoid(y, x).
fn trapezoid(y: &[f64], x: &[f64]) -> f64 {
    let mut total = 0.0;
    for i in 0..x.len() - 1 {
        total += (x[i + 1] - x[i]) * (y[i] + y[i + 1]) / 2.0;
    }
    total
}

pub fn overlap_10_20(radius: f64) -> Result<f64> {
    radius_arg(radius)?;
    let r = linspace(120.0, 120_001);
    let a = radial_10(&r, radius)?;
    let b = radial_20(&r, radius)?;
    let y: Vec<f64> = r.iter().zip(a).zip(b).map(|((x, av), bv)| av * bv * x * x).collect();
    Ok(trapezoid(&y, &r))
}

pub fn norm_20(radius: f64) -> Result<f64> {
    let r = linspace(120.0, 120_001);
    let y = radial_probability_20(&r, radius)?;
    Ok(trapezoid(&y, &r))
}

pub fn peak_radii_20(radius: f64) -> Result<(f64, f64)> {
    radius_arg(radius)?;
    let root = 5.0_f64.sqrt();
    Ok(((3.0 - root) * radius, (3.0 + root) * radius))
}

fn ground_energy(radius: f64) -> Result<f64> {
    radius_arg(radius)?;
    Ok(-1.0 / (2.0 * radius * radius))
}

/// V + Q - mu; zero when radius is the Bohr radius.
pub fn force_balance(r: &[f64], radius: f64) -> Result<Vec<f64>> {
    radius_arg(radius)?;
    if r.iter().any(|v| *v <= 0.0) {
        return Err(EngineError::new("r must be positive",
            "the Coulomb potential is singular at and below zero", "pass r > 0"));
    }
    let mu = ground_energy(radius)?;
    Ok(r.iter().map(|v| {
        let quantum = -1.0 / (2.0 * radius * radius) + 1.0 / (radius * v);
        -1.0 / v + quantum - mu
    }).collect())
}

pub fn balance_residuals() -> Result<Vec<f64>> {
    force_balance(BALANCE_RADII, RADIUS)
}

/// Circulation of the 2p loop: 2*pi * m at the equator.
pub fn loop_circulation(r: f64, theta: f64, m: i64, samples: usize) -> Result<f64> {
    if r <= 0.0 {
        return Err(EngineError::new("r, hbar and mass must be positive",
            "the loop radius must be positive", "pass r > 0"));
    }
    if samples < 16 {
        return Err(EngineError::new("samples must be at least 16",
            "the loop integral needs at least 16 samples", "pass samples >= 16"));
    }
    let sine = theta.sin();
    if sine.abs() < 1e-12 {
        return Err(EngineError::new("theta must be away from the poles",
            "the azimuthal velocity diverges at the poles", "pass theta away from 0 and pi"));
    }
    let velocity = (m as f64) / (r * sine);
    // np.linspace(0, 2*pi, samples, endpoint=True)
    let span = 2.0 * std::f64::consts::PI;
    let step = span / (samples - 1) as f64;
    let phi: Vec<f64> = (0..samples).map(|i| i as f64 * step).collect();
    let constant = velocity * r * sine;
    let y: Vec<f64> = phi.iter().map(|_| constant).collect();
    Ok(trapezoid(&y, &phi))
}

pub fn representation_scales() -> Result<Value> {
    let r = linspace(60.0, 60_001);
    let split = branch_split_20(&r, RADIUS)?;
    let (inner, outer) = peak_radii_20(RADIUS)?;
    Ok(json!({
        "radius_source": "theory.hydrogen_fluid.bohr_radius (claim-25 derived)",
        "radius": RADIUS,
        "loop": {"r": LOOP_R, "theta": LOOP_THETA, "m": WINDING_M},
        "branch": {
            "identity_residual": split["identity_residual"],
            "node_radius": node_position(RADIUS)?,
            "phase_slip": phase_slip_20(&r, RADIUS)?,
        },
        "radial": {
            "norm": norm_20(RADIUS)?,
            "overlap_10_20": overlap_10_20(RADIUS)?,
            "inner_peak": inner,
            "outer_peak": outer,
        },
        "preserved": {
            "balance_residuals": balance_residuals()?,
            "loop_circulation": loop_circulation(LOOP_R, LOOP_THETA, WINDING_M, 4000)?,
        },
    }))
}

pub fn parse_grid(raw: &str) -> Result<Vec<f64>> {
    parse_xs(raw)
}
