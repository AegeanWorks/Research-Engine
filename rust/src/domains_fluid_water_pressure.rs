//! Pressure-balanced cavities for the hydrated electron
//! (fluid_universe/theory/water_pressure.py).

use serde_json::{json, Value};

use crate::domains_fluid_water_electron as we;
use crate::domains_fluid_water_well as well;
use crate::error::{EngineError, Result};

pub const VDE_EV: f64 = 3.27;

pub fn surface_energy_ev(radius_m: f64) -> Result<f64> {
    if radius_m <= 0.0 {
        return Err(EngineError::new("radius must be positive",
            "a cavity needs a positive radius", "pass radius > 0"));
    }
    Ok(4.0 * std::f64::consts::PI * we::GAMMA_WATER * radius_m * radius_m / we::EV_JOULE)
}

pub fn total_energy_ev(radius_m: f64, depth_ev: f64) -> Result<Option<f64>> {
    if radius_m <= 0.0 {
        return Err(EngineError::new("radius must be positive",
            "a cavity needs a positive radius", "pass radius > 0"));
    }
    if depth_ev <= 0.0 {
        return Err(EngineError::new("depth must be positive",
            "a well needs a positive depth", "pass depth > 0"));
    }
    let roots = well::well_roots(radius_m, depth_ev)?;
    match roots["energy_1s_ev"].as_f64() {
        None => Ok(None),
        Some(energy) => Ok(Some(energy + surface_energy_ev(radius_m)?)),
    }
}

/// Golden-section minimization of the total energy over the radius interval.
pub fn equilibrium_radius(depth_ev: f64, lower_m: f64, upper_m: f64) -> Result<Value> {
    if depth_ev <= 0.0 {
        return Err(EngineError::new("depth must be positive",
            "a well needs a positive depth", "pass depth > 0"));
    }
    if lower_m <= 0.0 || upper_m <= lower_m {
        return Err(EngineError::new("invalid radius bounds",
            "the search interval must be ordered and positive", "pass 0 < lower < upper"));
    }
    let objective = |radius: f64| -> Result<f64> {
        Ok(total_energy_ev(radius, depth_ev)?.unwrap_or(1.0e6))
    };
    let golden = (5.0_f64.sqrt() - 1.0) / 2.0;
    let mut low = lower_m;
    let mut high = upper_m;
    let mut c = high - golden * (high - low);
    let mut d = low + golden * (high - low);
    let mut fc = objective(c)?;
    let mut fd = objective(d)?;
    for _ in 0..200 {
        if fc < fd {
            high = d;
            d = c;
            fd = fc;
            c = high - golden * (high - low);
            fc = objective(c)?;
        } else {
            low = c;
            c = d;
            fc = fd;
            d = low + golden * (high - low);
            fd = objective(d)?;
        }
    }
    let radius_m = 0.5 * (low + high);
    let roots = well::well_roots(radius_m, depth_ev)?;
    let total = objective(radius_m)?;
    let binding = -roots["energy_1s_ev"].as_f64().unwrap();
    Ok(json!({
        "radius_m": radius_m,
        "depth_ev": depth_ev,
        "energy_1s_ev": roots["energy_1s_ev"],
        "energy_1p_ev": roots["energy_1p_ev"],
        "binding_ev": binding,
        "gap_ev": roots["transition_ev"],
        "u_1s": roots["u_1s"],
        "u_1p": roots["u_1p"],
        "surface_energy_ev": surface_energy_ev(radius_m)?,
        "total_energy_ev": total,
    }))
}

pub fn vde_matched_depth(binding_ev: f64) -> Result<Value> {
    if binding_ev <= 0.0 {
        return Err(EngineError::new("binding must be positive",
            "a binding energy must be positive", "pass binding_ev > 0"));
    }
    let mut lower = binding_ev;
    let mut upper = binding_ev + 5.0;
    for _ in 0..60 {
        let middle = 0.5 * (lower + upper);
        let binding = equilibrium_radius(middle, 1.5e-10, 6.0e-10)?["binding_ev"]
            .as_f64().unwrap();
        if binding < binding_ev { lower = middle; } else { upper = middle; }
    }
    equilibrium_radius(0.5 * (lower + upper), 1.5e-10, 6.0e-10)
}

pub fn pressure_scales() -> Result<Value> {
    let radius = we::capillary_cavity_radius(we::GAMMA_WATER, we::MASS, we::HBAR)?;
    let born = well::born_depth_ev(radius, well::EPSILON_WATER)?;
    let mut scans = Vec::new();
    for depth in [born, 3.27, 4.0, 4.5, 5.0, 5.5, 6.0] {
        scans.push(equilibrium_radius(depth, 1.5e-10, 6.0e-10)?);
    }
    Ok(json!({
        "gamma_water_n_m": we::GAMMA_WATER,
        "born_depth_ev": born,
        "scans": scans,
        "vde_matched": vde_matched_depth(VDE_EV)?,
        "crude_capillary": {
            "radius_m": radius,
            "total_energy_ev": total_energy_ev(radius, born)?,
        },
    }))
}
