//! Finite spherical well for the hydrated electron
//! (fluid_universe/theory/water_well.py).

use std::sync::OnceLock;

use serde_json::{json, Value};

use crate::error::{EngineError, Result};

const HBAR: f64 = 1.054571817e-34;
const MASS: f64 = 9.1093837015e-31;
const EV_JOULE: f64 = 1.602176634e-19;
const BORN_COEFFICIENT_EV_ANGSTROM: f64 = 14.399645;
const EPSILON_WATER: f64 = 78.4;
const GAMMA_WATER: f64 = 0.0728;
const EPSILON_OPTICAL: f64 = 1.78;
const J1_FIRST_ZERO: f64 = 4.493409457909064;
const ANGSTROM: f64 = 1.0e-10;
const KINETIC: f64 = HBAR * HBAR / (2.0 * MASS * EV_JOULE) * 1.0e20;
const BORN_DEPTH_COEFFICIENT: f64 =
    BORN_COEFFICIENT_EV_ANGSTROM * (1.0 - 1.0 / EPSILON_WATER) / 2.0;

pub fn capillary_cavity_radius() -> f64 {
    (HBAR * HBAR / (8.0 * std::f64::consts::PI * MASS * GAMMA_WATER)).powf(0.25)
}

pub fn born_depth_ev(radius_m: f64, epsilon_r: f64) -> Result<f64> {
    if radius_m <= 0.0 { return Err(EngineError::new("radius must be positive",
        "a cavity needs a positive radius", "pass radius > 0")); }
    if epsilon_r <= 0.0 { return Err(EngineError::new("epsilon_r must be positive",
        "a dielectric constant must be positive", "pass epsilon_r > 0")); }
    let radius_angstrom = radius_m / ANGSTROM;
    Ok(BORN_COEFFICIENT_EV_ANGSTROM / (2.0 * radius_angstrom) * (1.0 - 1.0 / epsilon_r))
}

pub fn threshold_depth_ev(radius_m: f64) -> Result<f64> {
    if radius_m <= 0.0 { return Err(EngineError::new("radius must be positive",
        "a cavity needs a positive radius", "pass radius > 0")); }
    let radius_angstrom = radius_m / ANGSTROM;
    Ok(std::f64::consts::PI.powi(2) * KINETIC / (radius_angstrom * radius_angstrom))
}

pub fn infinite_well_transition_ev(radius_m: f64) -> Result<f64> {
    if radius_m <= 0.0 { return Err(EngineError::new("radius must be positive",
        "a cavity needs a positive radius", "pass radius > 0")); }
    let radius_angstrom = radius_m / ANGSTROM;
    let spacing = (J1_FIRST_ZERO.powi(2) - std::f64::consts::PI.powi(2)) * KINETIC;
    Ok(spacing / (radius_angstrom * radius_angstrom))
}

fn dimensionless_depth(radius_m: f64, depth_ev: f64) -> f64 {
    (radius_m / ANGSTROM) * (depth_ev / KINETIC).sqrt()
}

fn state_energy_ev(u: f64, radius_m: f64, depth_ev: f64) -> f64 {
    let radius_angstrom = radius_m / ANGSTROM;
    KINETIC * u * u / (radius_angstrom * radius_angstrom) - depth_ev
}

fn f0(u: f64, kappa: f64) -> f64 {
    let decay = (kappa * kappa - u * u).max(0.0).sqrt();
    u * u.cos() / u.sin() + decay
}

fn f1(u: f64, kappa: f64) -> f64 {
    let decay = (kappa * kappa - u * u).max(0.0).sqrt();
    let sine = u.sin();
    let cosine = u.cos();
    let numerator = (u * u - 2.0) * sine + 2.0 * u * cosine;
    let denominator = sine - u * cosine;
    numerator / denominator + (decay * decay + 2.0 * decay + 2.0) / (decay + 1.0)
}

fn bisect(function: fn(f64, f64) -> f64, mut lower: f64, mut upper: f64, kappa: f64) -> f64 {
    let mut value_lower = function(lower, kappa);
    if value_lower.abs() < 1.0e-15 { return lower; }
    for _ in 0..120 {
        let middle = 0.5 * (lower + upper);
        let value_middle = function(middle, kappa);
        if value_lower * value_middle <= 0.0 {
            upper = middle;
        } else {
            lower = middle;
            value_lower = value_middle;
        }
    }
    0.5 * (lower + upper)
}

fn well_1s_root(kappa: f64) -> Option<f64> {
    let epsilon = 1.0e-12;
    if kappa <= 0.5 * std::f64::consts::PI + epsilon { return None; }
    let lower = 0.5 * std::f64::consts::PI + epsilon;
    let upper = kappa.min(std::f64::consts::PI) - epsilon;
    if upper <= lower { return None; }
    Some(bisect(f0, lower, upper, kappa))
}

fn well_1p_root(kappa: f64) -> Option<f64> {
    let epsilon = 1.0e-12;
    if kappa <= std::f64::consts::PI + epsilon { return None; }
    let lower = std::f64::consts::PI + epsilon;
    let upper = kappa.min(J1_FIRST_ZERO) - epsilon;
    if upper <= lower { return Some(std::f64::consts::PI); }
    Some(bisect(f1, lower, upper, kappa))
}

fn u1s_at_pi() -> f64 {
    static VALUE: OnceLock<f64> = OnceLock::new();
    *VALUE.get_or_init(|| well_1s_root(std::f64::consts::PI).unwrap())
}

pub fn well_roots(radius_m: f64, depth_ev: f64) -> Result<Value> {
    if radius_m <= 0.0 { return Err(EngineError::new("radius must be positive",
        "a cavity needs a positive radius", "pass radius > 0")); }
    if depth_ev <= 0.0 { return Err(EngineError::new("depth must be positive",
        "a well needs a positive depth", "pass depth > 0")); }
    let kappa = dimensionless_depth(radius_m, depth_ev);
    let u_1s = well_1s_root(kappa);
    let u_1p = well_1p_root(kappa);
    let energy_1s = u_1s.map(|u| state_energy_ev(u, radius_m, depth_ev));
    let energy_1p = u_1p.map(|u| state_energy_ev(u, radius_m, depth_ev));
    let transition = match (energy_1s, energy_1p) {
        (Some(a), Some(b)) => Some(b - a),
        _ => None,
    };
    Ok(json!({
        "kappa": kappa, "u_1s": u_1s, "u_1p": u_1p,
        "energy_1s_ev": energy_1s, "energy_1p_ev": energy_1p,
        "transition_ev": transition,
    }))
}

fn threshold_radius_m() -> f64 {
    (std::f64::consts::PI.powi(2) * KINETIC / BORN_DEPTH_COEFFICIENT) * ANGSTROM
}

fn threshold_gap_ev(radius_m: f64) -> f64 {
    let depth = threshold_depth_ev(radius_m).unwrap();
    -state_energy_ev(u1s_at_pi(), radius_m, depth)
}

fn max_born_gap_ev() -> f64 {
    let radius = threshold_radius_m();
    -state_energy_ev(u1s_at_pi(), radius, born_depth_ev(radius, EPSILON_WATER).unwrap())
}

fn infinite_radius_for_transition(energy_ev: f64) -> Result<f64> {
    if energy_ev <= 0.0 { return Err(EngineError::new("energy must be positive",
        "a radius needs a positive transition energy", "pass energy > 0")); }
    let spacing = (J1_FIRST_ZERO.powi(2) - std::f64::consts::PI.powi(2)) * KINETIC;
    Ok((spacing / energy_ev).sqrt() * ANGSTROM)
}

pub fn required_depth_ev(radius_m: f64, target_ev: f64) -> Result<Option<f64>> {
    if radius_m <= 0.0 { return Err(EngineError::new("radius must be positive",
        "a cavity needs a positive radius", "pass radius > 0")); }
    if target_ev <= 0.0 { return Err(EngineError::new("target must be positive",
        "a transition target must be positive", "pass target > 0")); }
    let threshold = threshold_depth_ev(radius_m)?;
    if threshold_gap_ev(radius_m) > target_ev + 1.0e-12 { return Ok(None); }
    if target_ev >= infinite_well_transition_ev(radius_m)? - 1.0e-12 { return Ok(None); }
    if (threshold_gap_ev(radius_m) - target_ev).abs() <= 1.0e-9 { return Ok(Some(threshold)); }
    let mut lower = threshold;
    let mut upper = (10.0 * threshold).max(10.0 * target_ev);
    loop {
        let gap = well_roots(radius_m, upper)?["transition_ev"].as_f64();
        if gap.is_some() && gap.unwrap() >= target_ev { break; }
        upper *= 2.0;
        if upper > 1.0e6 { return Ok(None); }
    }
    for _ in 0..120 {
        let middle = 0.5 * (lower + upper);
        let gap = well_roots(radius_m, middle)?["transition_ev"].as_f64();
        if gap.is_none() || gap.unwrap() < target_ev { lower = middle; } else { upper = middle; }
    }
    Ok(Some(0.5 * (lower + upper)))
}

pub fn minimum_required_depth(target_ev: f64) -> Result<Value> {
    if target_ev <= 0.0 { return Err(EngineError::new("target must be positive",
        "a transition target must be positive", "pass target > 0")); }
    let radius_max = infinite_radius_for_transition(target_ev)?;
    let radius_min = 1.0e-10;
    if threshold_gap_ev(radius_min) < target_ev {
        return Err(EngineError::new("target is below the reachable threshold gap",
            "no cavity can produce this small a transition", "pass a larger target"));
    }
    let mut lower = radius_min;
    let mut upper = radius_max;
    for _ in 0..120 {
        let middle = 0.5 * (lower + upper);
        if threshold_gap_ev(middle) > target_ev { lower = middle; } else { upper = middle; }
    }
    let radius = 0.5 * (lower + upper);
    let required = threshold_depth_ev(radius)?;
    let born = born_depth_ev(radius, EPSILON_WATER)?;
    Ok(json!({
        "radius_m": radius, "required_depth_ev": required, "born_depth_ev": born,
        "excess_ev": required - born, "threshold_gap_ev": threshold_gap_ev(radius),
    }))
}

pub fn well_scales() -> Result<Value> {
    let radius = capillary_cavity_radius();
    let born = born_depth_ev(radius, EPSILON_WATER)?;
    let capillary = well_roots(radius, born)?;
    let threshold_depth = threshold_depth_ev(radius)?;
    let threshold_roots = well_roots(radius, threshold_depth)?;
    let threshold_gap = -threshold_roots["energy_1s_ev"].as_f64().unwrap();
    let radius_3p2 = 3.2e-10;
    let required_3p2 = required_depth_ev(radius_3p2, 1.7)?;
    let born_3p2 = born_depth_ev(radius_3p2, EPSILON_WATER)?;
    let minimum = minimum_required_depth(1.7)?;
    let min_radius = minimum["radius_m"].as_f64().unwrap();
    let optical = BORN_COEFFICIENT_EV_ANGSTROM / (2.0 * min_radius / ANGSTROM)
        * (1.0 / EPSILON_OPTICAL - 1.0 / EPSILON_WATER);
    let mut depth_scan = Vec::new();
    for depth in [born, 5.0, 10.0, 30.0] {
        let roots = well_roots(radius, depth)?;
        depth_scan.push(json!({
            "depth_ev": depth, "kappa": roots["kappa"], "u_1s": roots["u_1s"],
            "u_1p": roots["u_1p"], "transition_ev": roots["transition_ev"],
        }));
    }
    let excess = minimum["excess_ev"].as_f64().unwrap();
    Ok(json!({
        "model": {
            "epsilon_water": EPSILON_WATER, "epsilon_optical": EPSILON_OPTICAL,
            "born_coefficient_ev_angstrom": BORN_COEFFICIENT_EV_ANGSTROM,
            "j1_first_zero": J1_FIRST_ZERO,
        },
        "capillary": {
            "radius_m": radius, "born_depth_ev": born, "kappa": capillary["kappa"],
            "u_1s": capillary["u_1s"], "u_1p": capillary["u_1p"],
            "energy_1s_ev": capillary["energy_1s_ev"],
            "energy_1p_ev": capillary["energy_1p_ev"],
            "transition_ev": capillary["transition_ev"],
            "binding_ev": -capillary["energy_1s_ev"].as_f64().unwrap(),
        },
        "threshold": {
            "depth_at_capillary_ev": threshold_depth, "gap_at_capillary_ev": threshold_gap,
            "radius_m": threshold_radius_m(), "max_born_gap_ev": max_born_gap_ev(),
        },
        "depth_scan": depth_scan,
        "inverse": {
            "radius_3p2_m": radius_3p2, "required_depth_3p2_ev": required_3p2,
            "born_depth_3p2_ev": born_3p2,
            "excess_3p2_ev": required_3p2.map(|v| v - born_3p2),
            "minimum": minimum,
            "optical_polarization_ev": optical,
            "optical_polarization_ratio": excess / optical,
        },
        "infinite_well": {
            "transition_at_4p703_ev": infinite_well_transition_ev(4.703128884e-10)?,
            "radius_for_1p7_m": infinite_radius_for_transition(1.7)?,
        },
    }))
}
