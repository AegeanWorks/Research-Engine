//! VDE and 1.7 eV absorption constrain the finite well
//! (fluid_universe/theory/water_vde.py).

use serde_json::{json, Value};

use crate::domains_fluid_water_electron as we;
use crate::domains_fluid_water_well as well;
use crate::error::{EngineError, Result};

const VDE_EV: f64 = 3.27;
const VDE_UNCERTAINTY_EV: f64 = 0.10;
const OBSERVED_ABSORPTION_EV: f64 = 1.7;

fn energy_1s(roots: &Value) -> Option<f64> {
    roots.get("energy_1s_ev").and_then(Value::as_f64)
}

fn transition(roots: &Value) -> Option<f64> {
    roots.get("transition_ev").and_then(Value::as_f64)
}

/// Well depth that gives a 1s binding energy of binding_ev.
pub fn depth_for_binding(radius_m: f64, binding_ev: f64) -> Result<f64> {
    if radius_m <= 0.0 {
        return Err(EngineError::new("radius must be positive",
            "a cavity needs a positive radius", "pass radius > 0"));
    }
    if binding_ev <= 0.0 {
        return Err(EngineError::new("binding must be positive",
            "a binding energy must be positive", "pass binding_ev > 0"));
    }
    let mut lower = 0.0;
    let mut upper = (2.0 * binding_ev).max(binding_ev + 10.0);
    loop {
        let roots = well::well_roots(radius_m, upper)?;
        if energy_1s(&roots).map(|v| -v >= binding_ev).unwrap_or(false) { break; }
        upper *= 2.0;
        if upper > 1.0e6 {
            return Err(EngineError::new("binding energy is not reachable",
                "no finite well depth produces this binding", "pass a smaller binding"));
        }
    }
    for _ in 0..70 {
        let middle = 0.5 * (lower + upper);
        let roots = well::well_roots(radius_m, middle)?;
        match energy_1s(&roots) {
            Some(value) if -value >= binding_ev => upper = middle,
            _ => lower = middle,
        }
    }
    Ok(0.5 * (lower + upper))
}

fn gap_at_radius(radius_m: f64, binding_ev: f64) -> Result<Option<f64>> {
    let depth = depth_for_binding(radius_m, binding_ev)?;
    Ok(transition(&well::well_roots(radius_m, depth)?))
}

/// Finite well satisfying the VDE and the 1s->1p gap.
pub fn cavity_for_observables(binding_ev: f64, gap_ev: f64) -> Result<Value> {
    if binding_ev <= 0.0 {
        return Err(EngineError::new("binding must be positive",
            "a binding energy must be positive", "pass binding_ev > 0"));
    }
    if gap_ev <= 0.0 {
        return Err(EngineError::new("gap must be positive",
            "a transition gap must be positive", "pass gap_ev > 0"));
    }
    let mut lower = 2.5e-10;
    let mut upper = 6.0e-10;
    for _ in 0..40 {
        let middle = 0.5 * (lower + upper);
        match gap_at_radius(middle, binding_ev)? {
            None => lower = middle,
            Some(gap) if gap > gap_ev => lower = middle,
            Some(_) => upper = middle,
        }
    }
    let radius = 0.5 * (lower + upper);
    let depth = depth_for_binding(radius, binding_ev)?;
    let roots = well::well_roots(radius, depth)?;
    let born = well::born_depth_ev(radius, well::EPSILON_WATER)?;
    let binding = -energy_1s(&roots).unwrap();
    Ok(json!({
        "radius_m": radius,
        "depth_ev": depth,
        "binding_ev": binding,
        "gap_ev": transition(&roots),
        "u_1s": roots["u_1s"],
        "u_1p": roots["u_1p"],
        "energy_1s_ev": roots["energy_1s_ev"],
        "energy_1p_ev": roots["energy_1p_ev"],
        "born_depth_ev": born,
        "excess_ev": depth - born,
    }))
}

pub fn vde_scales() -> Result<Value> {
    let central = cavity_for_observables(VDE_EV, OBSERVED_ABSORPTION_EV)?;
    let lower = cavity_for_observables(VDE_EV - VDE_UNCERTAINTY_EV, OBSERVED_ABSORPTION_EV)?;
    let upper = cavity_for_observables(VDE_EV + VDE_UNCERTAINTY_EV, OBSERVED_ABSORPTION_EV)?;
    let radius = we::capillary_cavity_radius(we::GAMMA_WATER, we::MASS, we::HBAR)?;
    let born = well::born_depth_ev(radius, well::EPSILON_WATER)?;
    let roots = well::well_roots(radius, born)?;
    let central_radius = central["radius_m"].as_f64().unwrap();
    let central_depth = central["depth_ev"].as_f64().unwrap();
    let reorganization = well::BORN_COEFFICIENT_EV_ANGSTROM / (2.0 * central_radius / 1.0e-10)
        * (1.0 / well::EPSILON_OPTICAL - 1.0 / well::EPSILON_WATER);
    let capillary_binding = -energy_1s(&roots).unwrap();
    Ok(json!({
        "vde_ev": VDE_EV,
        "vde_uncertainty_ev": VDE_UNCERTAINTY_EV,
        "observed_absorption_ev": OBSERVED_ABSORPTION_EV,
        "central": central,
        "lower": lower,
        "upper": upper,
        "reorganization_ev": reorganization,
        "excess_to_reorganization": central["excess_ev"].as_f64().unwrap() / reorganization,
        "capillary": {
            "radius_m": radius,
            "born_depth_ev": born,
            "binding_ev": capillary_binding,
            "gap_ev": transition(&roots),
            "radius_ratio": central_radius / radius,
            "radius_excess_m": central_radius - radius,
            "depth_ratio": central_depth / born,
            "depth_excess_ev": central_depth - born,
        },
    }))
}
