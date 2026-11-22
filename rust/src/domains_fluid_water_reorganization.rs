//! Water reorganization and the VDE–optical difference
//! (fluid_universe/theory/water_reorganization.py).

use serde_json::{json, Value};

use crate::domains_fluid_water_electron as we;
use crate::domains_fluid_water_pressure as wp;
use crate::domains_fluid_water_well as well;
use crate::error::{EngineError, Result};

const VDE_EV: f64 = 3.27;
const VDE_UNCERTAINTY_EV: f64 = 0.10;
const OPTICAL_EV: f64 = 1.70;
const ANGSTROM: f64 = 1.0e-10;

pub fn dielectric_contrast(epsilon_s: f64, epsilon_opt: f64) -> Result<f64> {
    if epsilon_s <= 1.0 {
        return Err(EngineError::new("epsilon_s must exceed 1",
            "the static dielectric must exceed unity", "pass epsilon_s > 1"));
    }
    if epsilon_opt <= 0.0 || epsilon_opt >= epsilon_s {
        return Err(EngineError::new("epsilon_opt must lie between 0 and epsilon_s",
            "the optical dielectric must be between 0 and the static value",
            "pass 0 < epsilon_opt < epsilon_s"));
    }
    Ok(1.0 / epsilon_opt - 1.0 / epsilon_s)
}

pub fn reorganization_energy_ev(radius_m: f64, epsilon_s: f64,
                                epsilon_opt: f64) -> Result<f64> {
    if radius_m <= 0.0 {
        return Err(EngineError::new("radius must be positive",
            "a cavity needs a positive radius", "pass radius > 0"));
    }
    let contrast = dielectric_contrast(epsilon_s, epsilon_opt)?;
    Ok(well::BORN_COEFFICIENT_EV_ANGSTROM * contrast / (2.0 * (radius_m / ANGSTROM)))
}

pub fn radius_for_difference(difference_ev: f64, epsilon_s: f64,
                             epsilon_opt: f64) -> Result<f64> {
    if difference_ev <= 0.0 {
        return Err(EngineError::new("difference must be positive",
            "a reorganization difference must be positive", "pass difference_ev > 0"));
    }
    let contrast = dielectric_contrast(epsilon_s, epsilon_opt)?;
    let radius_angstrom = well::BORN_COEFFICIENT_EV_ANGSTROM * contrast / (2.0 * difference_ev);
    Ok(radius_angstrom * ANGSTROM)
}

pub fn reorganization_scales() -> Result<Value> {
    let radius = we::capillary_cavity_radius(we::GAMMA_WATER, we::MASS, we::HBAR)?;
    let lambda_capillary = reorganization_energy_ev(radius, well::EPSILON_WATER, well::EPSILON_OPTICAL)?;
    let observed_difference = VDE_EV - OPTICAL_EV;
    let predicted_vde = OPTICAL_EV + lambda_capillary;
    let residual = predicted_vde - VDE_EV;
    let required_radius = radius_for_difference(observed_difference,
        well::EPSILON_WATER, well::EPSILON_OPTICAL)?;
    let born = well::born_depth_ev(radius, well::EPSILON_WATER)?;
    let pressure_radius = wp::equilibrium_radius(born, 1.5e-10, 6.0e-10)?["radius_m"]
        .as_f64().unwrap();
    let lambda_pressure = reorganization_energy_ev(pressure_radius,
        well::EPSILON_WATER, well::EPSILON_OPTICAL)?;
    Ok(json!({
        "epsilon_s": well::EPSILON_WATER,
        "epsilon_opt": well::EPSILON_OPTICAL,
        "vde_ev": VDE_EV,
        "vde_uncertainty_ev": VDE_UNCERTAINTY_EV,
        "optical_ev": OPTICAL_EV,
        "observed_difference_ev": observed_difference,
        "capillary": {
            "radius_m": radius,
            "lambda_ev": lambda_capillary,
            "predicted_vde_ev": predicted_vde,
            "residual_ev": residual,
            "relative_residual": -residual / observed_difference,
            "sigma": -residual / VDE_UNCERTAINTY_EV,
        },
        "required": {
            "radius_m": required_radius,
            "radius_ratio": required_radius / radius,
        },
        "pressure": {
            "radius_m": pressure_radius,
            "lambda_ev": lambda_pressure,
            "lambda_ratio": lambda_pressure / observed_difference,
            "residual_ev": observed_difference - lambda_pressure,
        },
    }))
}
