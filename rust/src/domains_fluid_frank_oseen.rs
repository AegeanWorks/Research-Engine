//! Linearised Frank-Oseen director modes (fluid_universe/theory/frank_oseen.py).
//!
//! The elastic matrix is 2x2 symmetric, so its eigenvalues have a closed form
//! that matches `numpy.linalg.eigvalsh` without an LAPACK dependency.

use serde_json::{json, Value};

use crate::error::{EngineError, Result};

fn matrix(kx: f64, ky: f64, kz: f64, k1: f64, k2: f64, k3: f64) -> [[f64; 2]; 2] {
    let (kx2, ky2, kz2) = (kx * kx, ky * ky, kz * kz);
    let off = (k1 - k2) * kx * ky;
    [[k1 * kx2 + k2 * ky2 + k3 * kz2, off], [off, k1 * ky2 + k2 * kx2 + k3 * kz2]]
}

/// Ascending eigenvalues of the 2x2 symmetric elastic matrix, divided by rho.
pub fn dispersion(kx: f64, ky: f64, kz: f64, k1: f64, k2: f64, k3: f64, rho: f64) -> Result<Vec<f64>> {
    if rho <= 0.0 {
        return Err(EngineError::new("rho must be positive",
            "the effective inertia is a positive density", "pass rho > 0"));
    }
    let m = matrix(kx, ky, kz, k1, k2, k3);
    let half_trace = (m[0][0] + m[1][1]) / 2.0;
    let half_diff = (m[0][0] - m[1][1]) / 2.0;
    let radius = (half_diff * half_diff + m[0][1] * m[0][1]).sqrt();
    Ok(vec![(half_trace - radius) / rho, (half_trace + radius) / rho])
}

pub fn elastic_matrix(kx: f64, ky: f64, kz: f64, k1: f64, k2: f64, k3: f64) -> [[f64; 2]; 2] {
    matrix(kx, ky, kz, k1, k2, k3)
}

/// omega for K1=K2=K3=K: sqrt(K/rho) * |k|.
pub fn equal_constant_dispersion(k: f64, k_const: f64, rho: f64) -> Result<f64> {
    if k_const < 0.0 || rho <= 0.0 {
        return Err(EngineError::new("K must be non-negative and rho positive",
            "equal-constant dispersion needs K >= 0 and rho > 0", "pass K >= 0 and rho > 0"));
    }
    Ok((k_const / rho).sqrt() * k.abs())
}

/// Fractional split of the two omega^2 values at unit |k|.
pub fn anisotropy(direction: [f64; 3], k1: f64, k2: f64, k3: f64, rho: f64) -> Result<Value> {
    let norm = (direction[0] * direction[0] + direction[1] * direction[1] + direction[2] * direction[2]).sqrt();
    if norm == 0.0 {
        return Err(EngineError::new("direction must be nonzero",
            "a unit direction requires a nonzero vector", "pass a nonzero direction"));
    }
    let unit = [direction[0] / norm, direction[1] / norm, direction[2] / norm];
    let values = dispersion(unit[0], unit[1], unit[2], k1, k2, k3, rho)?;
    let mean = (values[0] + values[1]) / 2.0;
    let split = if mean > 0.0 { (values[1] - values[0]) / mean } else { 0.0 };
    Ok(json!({
        "direction": unit,
        "omega2": values,
        "fractional_split": split,
    }))
}

pub fn modes() -> Value {
    json!({
        "propagating_modes": 2,
        "polarisations": "two transverse director components (a,b); the longitudinal component is constrained by |n|=1",
        "gauge_field": false,
        "vector_potential": false,
        "electric_charge": 0,
        "can_be_photon": false,
        "reason": "Frank-Oseen describes neutral director fluctuations. A photon requires an independent U(1) gauge field and a coupling to it; neither is present.",
        "lorentz_invariance": "Not emergent: the background n0 selects a preferred frame even when K1=K2=K3. The equal-K dispersion is relativistic-looking only for the two transverse modes.",
    })
}
