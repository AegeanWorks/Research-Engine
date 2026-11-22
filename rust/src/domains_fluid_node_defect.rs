//! Two-branch defect representation of nodal states
//! (fluid_universe/theory/node_defect.py).

use serde_json::{json, Value};

use crate::domains_fluid_excited_fluid as ef;
use crate::domains_fluid_hydrogen_vortex as hv;
use crate::domains_fluid_nelson_closure as nc;
use crate::error::{EngineError, Result};

const GRID_NS: &[usize] = &[256, 512, 1024, 2048];
const GRID_LENGTH: f64 = 20.0;
const LOOP_R: f64 = 2.0;
const LOOP_THETA: f64 = std::f64::consts::FRAC_PI_2;
const WINDING_M: i64 = 1;

fn sign(value: f64) -> f64 {
    if value > 0.0 { 1.0 } else if value < 0.0 { -1.0 } else { 0.0 }
}

pub fn branch_split(x: &[f64], omega: f64, hbar: f64, mass: f64) -> Result<Value> {
    let psi = ef::excited_wavefunction(x, omega, hbar, mass)?;
    let signs: Vec<f64> = psi.iter().map(|v| sign(*v)).collect();
    let magnitudes: Vec<f64> = psi.iter().map(|v| v.abs()).collect();
    let residual = psi.iter().zip(&signs).zip(&magnitudes)
        .map(|((p, s), m)| (p - s * m).abs())
        .fold(0.0_f64, f64::max);
    let node_density = ef::excited_density(&[0.0], omega, hbar, mass)?[0];
    Ok(json!({
        "sign": signs,
        "magnitude": magnitudes,
        "identity_residual": residual,
        "node_density": node_density,
        "phase_slip": ef::phase_slip(&psi),
    }))
}

pub fn branch_regular_pressure_match(x: &[f64], omega: f64, hbar: f64,
                                     mass: f64) -> Result<Value> {
    let kept: Vec<f64> = x.iter().copied().filter(|v| *v != 0.0).collect();
    let pressure = ef::excited_quantum_pressure_regular(&kept, omega, hbar, mass)?;
    Ok(json!({
        "n_branch_points": kept.len(),
        "n_excluded": x.len() - kept.len(),
        "pressure finite": pressure.iter().all(|v| v.is_finite()),
    }))
}

pub fn node_scaling() -> Result<Value> {
    let mut dx_values = Vec::new();
    let mut maxima = Vec::new();
    for n in GRID_NS {
        let dx = GRID_LENGTH / *n as f64;
        let x: Vec<f64> = (0..*n).map(|i| (i as i64 - (*n / 2) as i64) as f64 * dx).collect();
        let wave = ef::excited_wavefunction(&x, 1.0, 1.0, 1.0)?;
        dx_values.push(dx);
        maxima.push(ef::phase_gradient_max(&wave, dx)?);
    }
    Ok(json!({
        "grid_ns": GRID_NS,
        "grid_length": GRID_LENGTH,
        "dx_values": dx_values,
        "maxima": maxima,
        "slope": ef::scaling_slope(&dx_values, &maxima)?,
    }))
}

pub fn vortex_gate() -> Result<Value> {
    let step = 80.0 / 160000.0;
    let mut r: Vec<f64> = (0..160001).map(|i| i as f64 * step).collect();
    r[160000] = 80.0;
    let probability = hv::radial_probability(&r, 1.0)?;
    Ok(json!({
        "circulation": hv::circulation(WINDING_M, 1.0, 1.0)?,
        "loop_circulation": hv::loop_circulation(LOOP_R, LOOP_THETA, WINDING_M, 1.0, 1.0, 4000)?,
        "azimuthal_velocity": hv::azimuthal_velocity(LOOP_R, LOOP_THETA, WINDING_M, 1.0, 1.0)?,
        "angular_momentum": hv::angular_momentum(WINDING_M, 1.0)?,
        "most_probable_radius": hv::most_probable_radius(1.0)?,
        "radial_norm": nc::trapezoid(&probability, &r),
    }))
}

pub fn representation_scales() -> Result<Value> {
    let x: Vec<f64> = (0..256).map(|i| (i as i64 - 128) as f64 * (GRID_LENGTH / 256.0)).collect();
    let split = branch_split(&x, 1.0, 1.0, 1.0)?;
    Ok(json!({
        "grids": {"ns": GRID_NS, "length": GRID_LENGTH},
        "loop": {"r": LOOP_R, "theta": LOOP_THETA, "m": WINDING_M},
        "units": {"omega": 1.0, "hbar": 1.0, "mass": 1.0},
        "branch": {
            "identity_residual": split["identity_residual"],
            "node_density": split["node_density"],
            "phase_slip": split["phase_slip"],
        },
        "scaling": node_scaling()?,
        "vortex": vortex_gate()?,
    }))
}

pub fn parse_xs(raw: &str) -> Result<Vec<f64>> {
    serde_json::from_str(raw).map_err(|e| EngineError::new(
        format!("invalid xs JSON: {e}"), "xs must be a JSON array of numbers",
        "pass a JSON array of numbers"))
}
