//! Self-consistent Born cavity synthesis
//! (fluid_universe/theory/water_born_cavity.py).

use serde_json::{json, Value};

use crate::domains_fluid_water_electron as we;
use crate::domains_fluid_water_pressure as wp;
use crate::domains_fluid_water_reorganization as wr;
use crate::domains_fluid_water_well as well;
use crate::error::{EngineError, Result};

const VDE_EV: f64 = 3.27;
const VDE_UNCERTAINTY_EV: f64 = 0.10;
const OPTICAL_EV: f64 = 1.70;

pub fn born_cavity_energy(radius_m: f64) -> Result<Option<f64>> {
    if radius_m <= 0.0 {
        return Err(EngineError::new("radius must be positive",
            "a cavity needs a positive radius", "pass radius > 0"));
    }
    let depth = well::born_depth_ev(radius_m, well::EPSILON_WATER)?;
    let roots = well::well_roots(radius_m, depth)?;
    match roots["energy_1s_ev"].as_f64() {
        None => Ok(None),
        Some(energy) => Ok(Some(energy + wp::surface_energy_ev(radius_m)?)),
    }
}

pub fn born_cavity_equilibrium(lower_m: f64, upper_m: f64) -> Result<Value> {
    if lower_m <= 0.0 || upper_m <= lower_m {
        return Err(EngineError::new("invalid radius bounds",
            "the search interval must be ordered and positive", "pass 0 < lower < upper"));
    }
    let objective = |radius: f64| -> Result<f64> {
        Ok(born_cavity_energy(radius)?.unwrap_or(1.0e6))
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
    let depth = well::born_depth_ev(radius_m, well::EPSILON_WATER)?;
    let roots = well::well_roots(radius_m, depth)?;
    let binding = -roots["energy_1s_ev"].as_f64().unwrap();
    Ok(json!({
        "radius_m": radius_m,
        "depth_ev": depth,
        "energy_1s_ev": roots["energy_1s_ev"],
        "energy_1p_ev": roots["energy_1p_ev"],
        "binding_ev": binding,
        "gap_ev": roots["transition_ev"],
        "u_1s": roots["u_1s"],
        "u_1p": roots["u_1p"],
        "surface_energy_ev": wp::surface_energy_ev(radius_m)?,
        "total_energy_ev": objective(radius_m)?,
    }))
}

pub fn born_cavity_scales() -> Result<Value> {
    let equilibrium = born_cavity_equilibrium(1.8e-10, 4.0e-10)?;
    let radius = equilibrium["radius_m"].as_f64().unwrap();
    let lam = wr::reorganization_energy_ev(radius, well::EPSILON_WATER, well::EPSILON_OPTICAL)?;
    let observed_difference = VDE_EV - OPTICAL_EV;
    let predicted_vde = OPTICAL_EV + lam;
    let residual = predicted_vde - VDE_EV;
    let required_radius = wr::radius_for_difference(observed_difference,
        well::EPSILON_WATER, well::EPSILON_OPTICAL)?;
    let capillary_radius = we::capillary_cavity_radius(we::GAMMA_WATER, we::MASS, we::HBAR)?;
    let born = well::born_depth_ev(capillary_radius, well::EPSILON_WATER)?;
    let pressure_radius = wp::equilibrium_radius(born, 1.5e-10, 6.0e-10)?["radius_m"]
        .as_f64().unwrap();
    Ok(json!({
        "vde_ev": VDE_EV,
        "vde_uncertainty_ev": VDE_UNCERTAINTY_EV,
        "optical_ev": OPTICAL_EV,
        "observed_difference_ev": observed_difference,
        "equilibrium": equilibrium,
        "synthesis": {
            "lambda_ev": lam,
            "predicted_vde_ev": predicted_vde,
            "residual_ev": residual,
            "sigma": residual / VDE_UNCERTAINTY_EV,
            "required_radius_m": required_radius,
            "required_ratio": required_radius / radius,
            "capillary_ratio": capillary_radius / radius,
            "pressure_ratio": pressure_radius / radius,
        },
    }))
}
