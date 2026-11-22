//! Shallow-water acoustic horizon (fluid_universe/theory/water_analogue.py).

use serde_json::{json, Value};

use crate::error::{EngineError, Result};

pub const GRAVITY: f64 = 9.81;
const HBAR: f64 = 1.054571817e-34;
const BOLTZMANN: f64 = 1.380649e-23;

pub fn sound_speed(depth: f64, gravity: f64) -> Result<f64> {
    if depth <= 0.0 || gravity <= 0.0 {
        return Err(EngineError::new("depth and gravity must be positive",
            "a shallow-water sound speed needs positive inputs", "pass depth > 0 and gravity > 0"));
    }
    Ok((gravity * depth).sqrt())
}

pub fn flow_velocity(r: f64, flow_rate: f64, depth: f64, gravity: f64) -> Result<f64> {
    let _ = gravity;
    if r <= 0.0 || flow_rate <= 0.0 {
        return Err(EngineError::new("r and flow_rate must be positive",
            "the radial flow needs a positive radius and rate", "pass r > 0 and flow_rate > 0"));
    }
    Ok(flow_rate / (2.0 * std::f64::consts::PI * r * depth))
}

pub fn horizon_radius(flow_rate: f64, depth: f64, gravity: f64) -> Result<f64> {
    if flow_rate <= 0.0 {
        return Err(EngineError::new("flow_rate must be positive",
            "a horizon needs a positive drain rate", "pass flow_rate > 0"));
    }
    let speed = sound_speed(depth, gravity)?;
    Ok(flow_rate / (2.0 * std::f64::consts::PI * depth * speed))
}

pub fn surface_gravity(flow_rate: f64, depth: f64, gravity: f64) -> Result<f64> {
    let radius = horizon_radius(flow_rate, depth, gravity)?;
    let speed = sound_speed(depth, gravity)?;
    Ok(speed * speed / radius)
}

pub fn hawking_temperature(kappa: f64) -> Result<f64> {
    if kappa <= 0.0 {
        return Err(EngineError::new("kappa must be positive",
            "a temperature needs positive surface gravity", "pass kappa > 0"));
    }
    Ok(HBAR * kappa / (2.0 * std::f64::consts::PI * BOLTZMANN))
}

pub fn acoustic_metric(r: f64, flow_rate: f64, depth: f64, gravity: f64) -> Result<Value> {
    let speed = sound_speed(depth, gravity)?;
    let velocity = flow_velocity(r, flow_rate, depth, gravity)?;
    Ok(json!({
        "c": speed,
        "v_r": velocity,
        "g_tt": -(speed * speed - velocity * velocity),
        "g_tr": -velocity,
        "g_rr": 1.0,
        "g_phiphi": r * r,
    }))
}

pub fn lab_scales(depth: f64, flow_rate: f64, gravity: f64) -> Result<Value> {
    let speed = sound_speed(depth, gravity)?;
    let radius = horizon_radius(flow_rate, depth, gravity)?;
    let kappa = surface_gravity(flow_rate, depth, gravity)?;
    Ok(json!({
        "depth_m": depth,
        "flow_rate_m3_s": flow_rate,
        "gravity_m_s2": gravity,
        "sound_speed_m_s": speed,
        "horizon_radius_m": radius,
        "surface_gravity_m_s2": kappa,
        "hawking_temperature_k": hawking_temperature(kappa)?,
    }))
}

pub fn capillary_length(gamma: f64, density: f64, gravity: f64) -> Result<f64> {
    if gamma <= 0.0 || density <= 0.0 || gravity <= 0.0 {
        return Err(EngineError::new("gamma, density and gravity must be positive",
            "a capillary length needs positive inputs", "pass all three values > 0"));
    }
    Ok((gamma / (density * gravity)).sqrt())
}

pub fn capillary_ratio(radius: f64, length: f64) -> Result<f64> {
    if radius <= 0.0 || length <= 0.0 {
        return Err(EngineError::new("radii must be positive",
            "a ratio needs positive lengths", "pass radius > 0 and length > 0"));
    }
    Ok((length / radius).powi(2))
}

pub fn long_wavelength_min_flow(depth: f64, gravity: f64, gamma: f64,
                                density: f64, ratio: f64) -> Result<f64> {
    if ratio <= 0.0 {
        return Err(EngineError::new("ratio must be positive",
            "the long-wavelength condition needs a positive ratio", "pass ratio > 0"));
    }
    let speed = sound_speed(depth, gravity)?;
    let length = capillary_length(gamma, density, gravity)?;
    Ok(2.0 * std::f64::consts::PI * depth * speed * ratio * length)
}

pub fn validity(depth: f64, flow_rate: f64, gamma: f64, density: f64,
                gravity: f64, ratio: f64) -> Result<Value> {
    let radius = horizon_radius(flow_rate, depth, gravity)?;
    let length = capillary_length(gamma, density, gravity)?;
    Ok(json!({
        "depth_m": depth,
        "flow_rate_m3_s": flow_rate,
        "horizon_radius_m": radius,
        "capillary_length_m": length,
        "capillary_ratio": capillary_ratio(radius, length)?,
        "long_wavelength": radius >= ratio * length,
        "required_ratio": ratio,
        "minimum_flow_m3_s": long_wavelength_min_flow(depth, gravity, gamma, density, ratio)?,
    }))
}
