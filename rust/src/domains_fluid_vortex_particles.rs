//! Thin-filament vortex-knot mass hypothesis
//! (fluid_universe/theory/vortex_particles.py).

use serde_json::{json, Value};

use crate::error::{EngineError, Result};

const DEFAULT_RADIUS: f64 = 2.0;
const DEFAULT_TUBE: f64 = 1.0;
const DEFAULT_SAMPLES: usize = 400;

type Point = [f64; 3];

pub fn torus_knot(n: i64, radius: f64, tube: f64, samples: usize) -> Result<(Vec<Point>, Vec<Point>)> {
    if n < 1 {
        return Err(EngineError::new("n must be at least 1",
            "a torus knot needs a positive winding", "pass n >= 1"));
    }
    if samples < 16 {
        return Err(EngineError::new("samples must be at least 16",
            "a closed filament needs enough samples", "pass samples >= 16"));
    }
    let tau = 2.0 * std::f64::consts::PI;
    let step = tau / samples as f64;
    let mut points = Vec::with_capacity(samples);
    for i in 0..samples {
        let t = i as f64 * step;
        let ring = radius + tube * (n as f64 * t).cos();
        points.push([ring * t.cos(), ring * t.sin(), tube * (n as f64 * t).sin()]);
    }
    let mut tangents = Vec::with_capacity(samples);
    for i in 0..samples {
        let next = points[(i + 1) % samples];
        let current = points[i];
        tangents.push([next[0] - current[0], next[1] - current[1], next[2] - current[2]]);
    }
    Ok((points, tangents))
}

fn norm(v: Point) -> f64 {
    (v[0] * v[0] + v[1] * v[1] + v[2] * v[2]).sqrt()
}

pub fn knot_length(points: &[Point]) -> f64 {
    let mut total = 0.0;
    for i in 0..points.len() {
        let next = points[(i + 1) % points.len()];
        let current = points[i];
        total += norm([next[0] - current[0], next[1] - current[1], next[2] - current[2]]);
    }
    total
}

pub fn biot_savart_energy(points: &[Point], core: f64) -> Result<f64> {
    if core <= 0.0 {
        return Err(EngineError::new("core must be positive",
            "a filament energy needs a positive core", "pass core > 0"));
    }
    // Tangents are recomputed from the supplied points, as in the Python helper.
    let mut local = Vec::with_capacity(points.len());
    for i in 0..points.len() {
        let next = points[(i + 1) % points.len()];
        let current = points[i];
        local.push([next[0] - current[0], next[1] - current[1], next[2] - current[2]]);
    }
    let mut mutual = 0.0;
    for (i, a) in local.iter().enumerate() {
        for (j, b) in local.iter().enumerate() {
            let distance = if i == j { core } else {
                let p = points[i];
                let q = points[j];
                norm([p[0] - q[0], p[1] - q[1], p[2] - q[2]])
            };
            mutual += (a[0] * b[0] + a[1] * b[1] + a[2] * b[2]) / distance;
        }
    }
    Ok(mutual + knot_length(points) / core)
}

pub fn koide_q(values: &[f64]) -> Result<f64> {
    if values.is_empty() || values.iter().any(|v| *v <= 0.0) {
        return Err(EngineError::new("values must be positive",
            "Koide Q needs strictly positive values", "pass positive values"));
    }
    let root_sum: f64 = values.iter().map(|v| v.sqrt()).sum();
    let denominator = root_sum * root_sum;
    if denominator == 0.0 {
        return Err(EngineError::new("degenerate values",
            "Koide Q needs a non-zero root sum", "pass non-degenerate values"));
    }
    Ok(values.iter().sum::<f64>() / denominator)
}

pub fn mass_hypothesis(observed: &[f64], knots: &[i64], core: f64,
                       relative_tolerance: f64, koide_tolerance: f64) -> Result<Value> {
    if observed.len() != 3 || observed.iter().any(|v| *v <= 0.0) {
        return Err(EngineError::new("observed must be three positive masses",
            "a knot test needs three positive charged-lepton masses", "pass three positive values"));
    }
    let mut energies = Vec::new();
    let mut lengths = Vec::new();
    for n in knots {
        let (points, _) = torus_knot(*n, DEFAULT_RADIUS, DEFAULT_TUBE, DEFAULT_SAMPLES)?;
        energies.push(biot_savart_energy(&points, core)?);
        lengths.push(knot_length(&points));
    }
    let energy_ratios: Vec<f64> = energies.iter().map(|v| v / energies[0]).collect();
    let length_ratios: Vec<f64> = lengths.iter().map(|v| v / lengths[0]).collect();
    let observed_ratios: Vec<f64> = observed.iter().map(|v| v / observed[0]).collect();
    let relative_error = energy_ratios.iter().zip(&observed_ratios)
        .map(|(e, o)| ((e - o) / o).abs())
        .fold(0.0_f64, f64::max);
    let q_energy = koide_q(&energies)?;
    let q_length = koide_q(&lengths)?;
    let q_observed = koide_q(observed)?;
    let required_power = observed_ratios[2].ln() / energy_ratios[2].ln();
    let falsified = relative_error > relative_tolerance
        || (q_energy - 2.0 / 3.0).abs() > koide_tolerance;
    let status = if falsified {
        "FALSIFIED (thin-filament spectrum too compressed)"
    } else {
        "UNVERIFIED (ratios agree at this core; not a derivation)"
    };
    let powers = format!("{required_power:.1}");
    Ok(json!({
        "knots": knots,
        "core": core,
        "energies": energies,
        "lengths": lengths,
        "energy_ratios": energy_ratios,
        "length_ratios": length_ratios,
        "observed_ratios": observed_ratios,
        "relative_error": relative_error,
        "koide_q_energy": q_energy,
        "koide_q_length": q_length,
        "koide_q_observed": q_observed,
        "required_power": required_power,
        "falsified": falsified,
        "status": status,
        "note": format!("A thin filament has E ~ L log(L/a); its ratios are O(1). Matching the charged-lepton hierarchy would need m ~ E^p with p about {powers}, or an exponentially small core. This test falsifies only the simple assignment, not the general vortex idea."),
    }))
}
