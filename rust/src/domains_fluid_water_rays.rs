//! Radial rays at the shallow-water acoustic horizon
//! (fluid_universe/theory/water_rays.py).

use serde_json::{json, Value};

use crate::domains_fluid_water_analogue as analogue;
use crate::error::{EngineError, Result};

pub const DEFAULT_GRAVITY: f64 = 9.81;

fn validate(r: f64, flow_rate: f64) -> Result<()> {
    if r <= 0.0 || flow_rate <= 0.0 {
        return Err(EngineError::new("r and flow_rate must be positive",
            "a radial ray needs a positive radius and drain", "pass r > 0 and flow_rate > 0"));
    }
    Ok(())
}

pub fn outgoing_speed(r: f64, flow_rate: f64, depth: f64, gravity: f64) -> Result<f64> {
    validate(r, flow_rate)?;
    let speed = analogue::sound_speed(depth, gravity)?;
    Ok(speed - flow_rate / (2.0 * std::f64::consts::PI * r * depth))
}

pub fn ingoing_speed(r: f64, flow_rate: f64, depth: f64, gravity: f64) -> Result<f64> {
    validate(r, flow_rate)?;
    let speed = analogue::sound_speed(depth, gravity)?;
    Ok(-speed - flow_rate / (2.0 * std::f64::consts::PI * r * depth))
}

pub fn peeling_rate(flow_rate: f64, depth: f64, gravity: f64) -> Result<f64> {
    analogue::surface_gravity(flow_rate, depth, gravity)
}

pub fn analytic_outgoing_time(r: f64, r0: f64, horizon: f64, speed: f64) -> Result<f64> {
    if r <= horizon || r0 <= horizon || speed <= 0.0 {
        return Err(EngineError::new("r and r0 must exceed the horizon; speed must be positive",
            "the analytic ray time needs an outside starting point", "pass r, r0 > horizon and speed > 0"));
    }
    Ok((r - r0) / speed + (horizon / speed) * ((r - horizon) / (r0 - horizon)).ln())
}

pub fn integrate_outgoing(r0: f64, r_end: f64, flow_rate: f64, depth: f64,
                          gravity: f64, dt: f64) -> Result<Value> {
    if r0 <= 0.0 || r_end <= r0 || dt <= 0.0 {
        return Err(EngineError::new("require 0 < r0 < r_end and dt > 0",
            "a ray needs an ordered radius interval and positive step", "pass 0 < r0 < r_end and dt > 0"));
    }
    let mut time = 0.0;
    let mut radius = r0;
    let mut steps = 0u64;
    while radius < r_end {
        let k1 = outgoing_speed(radius, flow_rate, depth, gravity)?;
        let k2 = outgoing_speed(radius + 0.5 * dt * k1, flow_rate, depth, gravity)?;
        let k3 = outgoing_speed(radius + 0.5 * dt * k2, flow_rate, depth, gravity)?;
        let k4 = outgoing_speed(radius + dt * k3, flow_rate, depth, gravity)?;
        radius += dt * (k1 + 2.0 * k2 + 2.0 * k3 + k4) / 6.0;
        time += dt;
        steps += 1;
        if steps > 10_000_000 {
            return Err(EngineError::new("ray integration did not reach r_end",
                "the ray did not escape within the step budget", "pass a larger dt"));
        }
    }
    Ok(json!({"time": time, "radius": radius, "steps": steps}))
}
