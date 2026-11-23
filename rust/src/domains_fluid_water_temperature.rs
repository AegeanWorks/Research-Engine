//! Temperature-dependent Born cavity
//! (fluid_universe/theory/water_temperature.py).

use serde_json::{json, Value};

use crate::domains_fluid_water_marcus as wm;
use crate::domains_fluid_water_well as well;
use crate::error::{EngineError, Result};

const EV_JOULE: f64 = 1.602176634e-19;
const EPSILON_OPTICAL: f64 = 1.78;
const OPTICAL_EV: f64 = 1.70;
const OBSERVED_LOWER_MEV_PER_K: f64 = 2.4;
const OBSERVED_UPPER_MEV_PER_K: f64 = 2.8;
const ANGSTROM: f64 = 1.0e-10;

fn validate_celsius(temperature_c: f64) -> Result<()> {
    if !(0.0..=100.0).contains(&temperature_c) {
        return Err(EngineError::new("temperature must lie between 0 and 100 C",
            "the water property fits are valid from 0 to 100 C", "pass a temperature in [0, 100]"));
    }
    Ok(())
}

pub fn water_dielectric_constant(temperature_c: f64) -> Result<f64> {
    validate_celsius(temperature_c)?;
    Ok(87.740 - 0.40008 * temperature_c + 9.398e-4 * temperature_c * temperature_c
        - 1.410e-6 * temperature_c.powi(3))
}

pub fn water_surface_tension(temperature_c: f64) -> Result<f64> {
    validate_celsius(temperature_c)?;
    Ok(0.07564 - 1.4e-4 * temperature_c - 3.0e-7 * temperature_c * temperature_c)
}

fn born_depth_ev(radius_m: f64, epsilon_s: f64) -> f64 {
    well::BORN_COEFFICIENT_EV_ANGSTROM / (2.0 * (radius_m / ANGSTROM)) * (1.0 - 1.0 / epsilon_s)
}

fn surface_energy_ev(radius_m: f64, gamma: f64) -> f64 {
    4.0 * std::f64::consts::PI * gamma * radius_m * radius_m / EV_JOULE
}

fn reorganization_ev(radius_m: f64, epsilon_s: f64) -> f64 {
    well::BORN_COEFFICIENT_EV_ANGSTROM / (2.0 * (radius_m / ANGSTROM))
        * (1.0 / EPSILON_OPTICAL - 1.0 / epsilon_s)
}

pub fn born_cavity_at_temperature(temperature_c: f64) -> Result<Value> {
    let epsilon_s = water_dielectric_constant(temperature_c)?;
    let gamma = water_surface_tension(temperature_c)?;
    let objective = |radius: f64| -> Result<f64> {
        let roots = well::well_roots(radius, born_depth_ev(radius, epsilon_s))?;
        match roots["energy_1s_ev"].as_f64() {
            None => Ok(1.0e6),
            Some(energy) => Ok(energy + surface_energy_ev(radius, gamma)),
        }
    };
    let golden = (5.0_f64.sqrt() - 1.0) / 2.0;
    let mut low = 1.8e-10;
    let mut high = 4.0e-10;
    let mut c = high - golden * (high - low);
    let mut d = low + golden * (high - low);
    let mut fc = objective(c)?;
    let mut fd = objective(d)?;
    for _ in 0..200 {
        if fc < fd {
            high = d; d = c; fd = fc;
            c = high - golden * (high - low); fc = objective(c)?;
        } else {
            low = c; c = d; fc = fd;
            d = low + golden * (high - low); fd = objective(d)?;
        }
    }
    let radius_m = 0.5 * (low + high);
    let depth = born_depth_ev(radius_m, epsilon_s);
    let roots = well::well_roots(radius_m, depth)?;
    let lambda_ev = reorganization_ev(radius_m, epsilon_s);
    Ok(json!({
        "temperature_c": temperature_c,
        "epsilon_s": epsilon_s,
        "gamma_n_m": gamma,
        "radius_m": radius_m,
        "depth_ev": depth,
        "energy_1s_ev": roots["energy_1s_ev"],
        "binding_ev": -roots["energy_1s_ev"].as_f64().unwrap(),
        "u_1p": roots["u_1p"],
        "gap_ev": roots["transition_ev"],
        "lambda_ev": lambda_ev,
        "predicted_vde_ev": OPTICAL_EV + lambda_ev,
        "fwhm_ev": wm::marcus_width_ev(lambda_ev, temperature_c + 273.15)?,
    }))
}

pub fn temperature_scales() -> Result<Value> {
    let mut scan = Vec::new();
    for temperature in [0.0, 10.0, 20.0, 25.0, 30.0, 37.0, 45.0] {
        scan.push(born_cavity_at_temperature(temperature)?);
    }
    let cold = &scan[0];
    let warm = &scan[scan.len() - 1];
    let middle = &scan[3];
    let lambda_cold = cold["lambda_ev"].as_f64().unwrap();
    let lambda_warm = warm["lambda_ev"].as_f64().unwrap();
    let slope = (lambda_warm - lambda_cold) / 45.0 * 1000.0;
    let magnitude = slope.abs();
    let radius_cold = cold["radius_m"].as_f64().unwrap();
    let radius_warm = warm["radius_m"].as_f64().unwrap();
    let radius_slope = (radius_warm - radius_cold) / 45.0;
    let geometric_slope = OPTICAL_EV / middle["radius_m"].as_f64().unwrap() * radius_slope * 1000.0;
    let geometric_magnitude = geometric_slope.abs();
    let net_slope = slope + geometric_slope;
    let net_magnitude = net_slope.abs();
    let width_0c = cold["fwhm_ev"].as_f64().unwrap();
    let width_45c = warm["fwhm_ev"].as_f64().unwrap();
    Ok(json!({
        "scan": scan,
        "lambda_slope_mev_per_k": slope,
        "geometric_slope_mev_per_k": geometric_slope,
        "net_cavity_slope_mev_per_k": net_slope,
        "cavity_terms_oppose": slope * geometric_slope < 0.0,
        "observed_shift_mev_per_k": OBSERVED_LOWER_MEV_PER_K,
        "observed_shift_upper_mev_per_k": OBSERVED_UPPER_MEV_PER_K,
        "fraction_of_lower": magnitude / OBSERVED_LOWER_MEV_PER_K,
        "fraction_of_upper": magnitude / OBSERVED_UPPER_MEV_PER_K,
        "coverage_geometric_lower": geometric_magnitude / OBSERVED_LOWER_MEV_PER_K,
        "coverage_geometric_upper": geometric_magnitude / OBSERVED_UPPER_MEV_PER_K,
        "coverage_net_lower": net_magnitude / OBSERVED_LOWER_MEV_PER_K,
        "coverage_net_upper": net_magnitude / OBSERVED_UPPER_MEV_PER_K,
        "residual_after_lambda_lower": OBSERVED_LOWER_MEV_PER_K - magnitude,
        "residual_after_lambda_upper": OBSERVED_UPPER_MEV_PER_K - magnitude,
        "residual_after_geometric_lower": OBSERVED_LOWER_MEV_PER_K - geometric_magnitude,
        "residual_after_geometric_upper": OBSERVED_UPPER_MEV_PER_K - geometric_magnitude,
        "residual_after_net_lower": OBSERVED_LOWER_MEV_PER_K - net_slope,
        "residual_after_net_upper": OBSERVED_UPPER_MEV_PER_K - net_slope,
        "width_0c_ev": width_0c,
        "width_45c_ev": width_45c,
        "width_change_ev": width_45c - width_0c,
    }))
}
