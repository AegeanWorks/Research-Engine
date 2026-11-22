//! Hydrated-electron cavity scale from water properties
//! (fluid_universe/theory/water_electron.py).

use serde_json::{json, Value};

use crate::error::{EngineError, Result};

pub const HBAR: f64 = 1.054571817e-34;
pub const MASS: f64 = 9.1093837015e-31;
pub const EV_JOULE: f64 = 1.602176634e-19;
pub const BOHR: f64 = 5.29177210903e-11;
pub const RYDBERG_EV: f64 = 13.605693;
pub const EPSILON_WATER: f64 = 78.4;
pub const GAMMA_WATER: f64 = 0.0728;

pub fn screened_bohr_radius(epsilon_r: f64) -> Result<f64> {
    if epsilon_r <= 0.0 {
        return Err(EngineError::new("epsilon_r must be positive",
            "a dielectric constant must be positive", "pass epsilon_r > 0"));
    }
    Ok(epsilon_r * BOHR)
}

pub fn screened_energy_ev(epsilon_r: f64) -> Result<f64> {
    if epsilon_r <= 0.0 {
        return Err(EngineError::new("epsilon_r must be positive",
            "a dielectric constant must be positive", "pass epsilon_r > 0"));
    }
    Ok(-RYDBERG_EV / (epsilon_r * epsilon_r))
}

pub fn capillary_cavity_radius(gamma: f64, mass: f64, hbar: f64) -> Result<f64> {
    if gamma <= 0.0 || mass <= 0.0 || hbar <= 0.0 {
        return Err(EngineError::new("gamma, mass and hbar must be positive",
            "the cavity balance needs positive constants", "pass gamma, mass and hbar > 0"));
    }
    Ok((hbar * hbar / (8.0 * std::f64::consts::PI * mass * gamma)).powf(0.25))
}

pub fn capillary_cavity_energy_ev(gamma: f64, mass: f64, hbar: f64) -> Result<f64> {
    let radius = capillary_cavity_radius(gamma, mass, hbar)?;
    let kinetic = hbar * hbar / (2.0 * mass * radius * radius);
    Ok(2.0 * kinetic / EV_JOULE)
}

pub fn infinite_well_gap_ev(radius: f64, mass: f64, hbar: f64) -> Result<f64> {
    if radius <= 0.0 || mass <= 0.0 || hbar <= 0.0 {
        return Err(EngineError::new("radius, mass and hbar must be positive",
            "the well ground state needs positive inputs", "pass radius, mass and hbar > 0"));
    }
    Ok(std::f64::consts::PI.powi(2) * hbar * hbar
        / (2.0 * mass * radius * radius) / EV_JOULE)
}

pub fn well_radius_for_gap(energy_ev: f64, mass: f64, hbar: f64) -> Result<f64> {
    if energy_ev <= 0.0 || mass <= 0.0 || hbar <= 0.0 {
        return Err(EngineError::new("energy, mass and hbar must be positive",
            "an inverse well radius needs positive inputs", "pass energy, mass and hbar > 0"));
    }
    Ok((std::f64::consts::PI.powi(2) * hbar * hbar
        / (2.0 * mass * energy_ev * EV_JOULE)).sqrt())
}

pub fn hydrated_scales() -> Result<Value> {
    let radius = capillary_cavity_radius(GAMMA_WATER, MASS, HBAR)?;
    Ok(json!({
        "epsilon_water": EPSILON_WATER,
        "gamma_water_n_m": GAMMA_WATER,
        "screened_bohr_radius_m": screened_bohr_radius(EPSILON_WATER)?,
        "screened_energy_ev": screened_energy_ev(EPSILON_WATER)?,
        "cavity_radius_m": radius,
        "cavity_energy_ev": capillary_cavity_energy_ev(GAMMA_WATER, MASS, HBAR)?,
        "well_gap_at_cavity_ev": infinite_well_gap_ev(radius, MASS, HBAR)?,
        "well_gap_at_2p5_angstrom_ev": infinite_well_gap_ev(2.5e-10, MASS, HBAR)?,
        "well_radius_for_1p7_ev_m": well_radius_for_gap(1.7, MASS, HBAR)?,
    }))
}
