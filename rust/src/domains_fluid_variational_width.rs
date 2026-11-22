//! Gaussian Ritz width selection: G-M vs Yasui
//! (fluid_universe/theory/variational_width.py).

use serde_json::{json, Value};

use crate::error::{EngineError, Result};

const NEWTON_STEPS: usize = 8;
const GRID_START: f64 = 0.125;
const GRID_STOP: f64 = 2.0;
const GRID_POINTS: usize = 2001;

fn positive(args: &[(&str, f64)]) -> Result<()> {
    for (name, value) in args {
        if *value <= 0.0 {
            return Err(EngineError::new(format!("{name} must be positive"),
                "the variational formulas need positive parameters",
                &format!("pass {name} > 0")));
        }
    }
    Ok(())
}

fn linspace(start: f64, stop: f64, n: usize) -> Vec<f64> {
    let step = (stop - start) / (n - 1) as f64;
    let mut out: Vec<f64> = (0..n).map(|i| start + i as f64 * step).collect();
    out[n - 1] = stop;
    out
}

pub fn grid_s2() -> Vec<f64> {
    linspace(GRID_START, GRID_STOP, GRID_POINTS)
}

pub fn diffusivity(hbar: f64, mass: f64) -> Result<f64> {
    positive(&[("hbar", hbar), ("mass", mass)])?;
    Ok(hbar / (2.0 * mass))
}

pub fn quantum_width(omega: f64, hbar: f64, mass: f64) -> Result<f64> {
    positive(&[("omega", omega), ("hbar", hbar), ("mass", mass)])?;
    Ok((hbar / (2.0 * mass * omega)).sqrt())
}

pub fn effective_potential(sigma: f64, omega: f64, hbar: f64, mass: f64) -> Result<f64> {
    positive(&[("sigma", sigma)])?;
    Ok(0.5 * omega * omega * sigma * sigma
        + hbar * hbar / (8.0 * mass * mass * sigma * sigma))
}

pub fn action_gm(s2: f64, omega: f64, hbar: f64, mass: f64) -> Result<f64> {
    positive(&[("s2", s2), ("omega", omega)])?;
    let nu = diffusivity(hbar, mass)?;
    Ok(-mass * nu * nu / (2.0 * s2) - 0.5 * mass * omega * omega * s2)
}

pub fn action_yasui(s2: f64, omega: f64, hbar: f64, mass: f64) -> Result<f64> {
    positive(&[("s2", s2), ("omega", omega)])?;
    let nu = diffusivity(hbar, mass)?;
    Ok(mass * nu * nu / (2.0 * s2) - 0.5 * mass * omega * omega * s2)
}

pub fn d_action_gm(s2: f64, omega: f64, hbar: f64, mass: f64) -> Result<f64> {
    positive(&[("s2", s2), ("omega", omega)])?;
    let nu = diffusivity(hbar, mass)?;
    Ok(mass * nu * nu / (2.0 * s2 * s2) - 0.5 * mass * omega * omega)
}

pub fn d_action_yasui(s2: f64, omega: f64, hbar: f64, mass: f64) -> Result<f64> {
    positive(&[("s2", s2), ("omega", omega)])?;
    let nu = diffusivity(hbar, mass)?;
    Ok(-mass * nu * nu / (2.0 * s2 * s2) - 0.5 * mass * omega * omega)
}

pub fn d2_action_gm_s2(s2: f64, omega: f64, hbar: f64, mass: f64) -> Result<f64> {
    positive(&[("s2", s2), ("omega", omega)])?;
    let nu = diffusivity(hbar, mass)?;
    Ok(-mass * nu * nu / (s2 * s2 * s2))
}

pub fn d2_action_gm_sigma(sigma: f64, omega: f64, hbar: f64, mass: f64) -> Result<f64> {
    positive(&[("sigma", sigma), ("omega", omega)])?;
    let nu = diffusivity(hbar, mass)?;
    Ok(-3.0 * mass * nu * nu / sigma.powi(4) - mass * omega * omega)
}

pub fn extremum_s2(omega: f64, hbar: f64, mass: f64) -> Result<f64> {
    positive(&[("omega", omega), ("hbar", hbar), ("mass", mass)])?;
    Ok(diffusivity(hbar, mass)? / omega)
}

pub fn newton_refine(start: f64, omega: f64, hbar: f64, mass: f64, steps: usize) -> Result<f64> {
    let nu = diffusivity(hbar, mass)?;
    let mut s2 = start;
    for _ in 0..steps {
        let first = mass * nu * nu / (2.0 * s2 * s2) - 0.5 * mass * omega * omega;
        let second = -mass * nu * nu / (s2 * s2 * s2);
        s2 -= first / second;
    }
    Ok(s2)
}

pub fn grid_maximum(grid: &[f64], omega: f64, hbar: f64, mass: f64) -> Result<Value> {
    if grid.len() < 2 {
        return Err(EngineError::new("the scan grid needs at least two points",
            "a grid step requires two adjacent samples", "pass a longer grid"));
    }
    let values: Vec<f64> = grid.iter().map(|s| action_gm(*s, omega, hbar, mass)).collect::<Result<_>>()?;
    let mut peak = 0usize;
    for (i, value) in values.iter().enumerate().skip(1) {
        if *value > values[peak] { peak = i; }
    }
    Ok(json!({
        "grid_argmax": grid[peak],
        "grid_step": grid[1] - grid[0],
        "grid_max_value": values[peak],
        "refined": newton_refine(grid[peak], omega, hbar, mass, NEWTON_STEPS)?,
    }))
}

pub fn yasui_monotone(grid: &[f64], omega: f64, hbar: f64, mass: f64) -> Result<Value> {
    if grid.len() < 2 {
        return Err(EngineError::new("the scan grid needs at least two points",
            "a finite difference requires two adjacent samples", "pass a longer grid"));
    }
    let derivs: Vec<f64> = grid.iter().map(|s| d_action_yasui(*s, omega, hbar, mass)).collect::<Result<_>>()?;
    let actions: Vec<f64> = grid.iter().map(|s| action_yasui(*s, omega, hbar, mass)).collect::<Result<_>>()?;
    let diffs: Vec<f64> = actions.windows(2).map(|w| w[1] - w[0]).collect();
    Ok(json!({
        "max_derivative": derivs.iter().copied().fold(f64::NEG_INFINITY, f64::max),
        "min_derivative": derivs.iter().copied().fold(f64::INFINITY, f64::min),
        "all_negative": derivs.iter().all(|v| *v < 0.0),
        "max_diff": diffs.iter().copied().fold(f64::NEG_INFINITY, f64::max),
    }))
}

pub fn ermakov_cross_check() -> Result<Value> {
    let width = quantum_width(1.0, 1.0, 1.0)?;
    let grid = linspace(0.2, 1.4, 2401);
    let values: Vec<f64> = grid.iter().map(|s| effective_potential(*s, 1.0, 1.0, 1.0)).collect::<Result<_>>()?;
    let mut best = 0usize;
    for (i, value) in values.iter().enumerate().skip(1) {
        if *value < values[best] { best = i; }
    }
    Ok(json!({
        "quantum_width": width,
        "width_squared": width * width,
        "potential_argmin": grid[best],
        "potential_min_value": values[best],
    }))
}

pub fn selection_scales() -> Result<Value> {
    let grid = grid_s2();
    let (omega, hbar, mass) = (1.0, 1.0, 1.0);
    let star = extremum_s2(omega, hbar, mass)?;
    let peak = grid_maximum(&grid, omega, hbar, mass)?;
    let yasui = yasui_monotone(&grid, omega, hbar, mass)?;
    let scalings: Vec<(f64, f64, f64)> = vec![(2.0, 1.0, 1.0), (1.0, 1.0, 2.0)];
    let mut scaling_rows = Vec::new();
    for (w, h, m) in scalings {
        let predicted = extremum_s2(w, h, m)?;
        let peak_p = grid_maximum(&grid, w, h, m)?;
        scaling_rows.push(json!({
            "omega": w, "hbar": h, "mass": m,
            "predicted": predicted,
            "grid_argmax": peak_p["grid_argmax"],
            "refined": peak_p["refined"],
            "curvature_s2": d2_action_gm_s2(predicted, w, h, m)?,
        }));
    }
    Ok(json!({
        "grids": {"s2": grid},
        "base": {"omega": omega, "hbar": hbar, "mass": mass},
        "analytic": {
            "sigma_star_sq": star,
            "curvature_s2": d2_action_gm_s2(star, omega, hbar, mass)?,
            "curvature_sigma": d2_action_gm_sigma(star.sqrt(), omega, hbar, mass)?,
        },
        "grid": peak,
        "yasui": yasui,
        "scalings": scaling_rows,
        "ermakov": ermakov_cross_check()?,
    }))
}
