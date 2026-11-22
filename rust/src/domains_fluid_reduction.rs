//! Dimensional reduction and the effective moment of inertia
//! (fluid_universe/theory/reduction.py).

use serde_json::{json, Value};

use crate::error::{EngineError, Result};

fn py_bool(value: bool) -> &'static str {
    if value { "True" } else { "False" }
}

pub fn wall_tension(mu: f64) -> Result<f64> {
    if mu < 0.0 {
        return Err(EngineError::new("mu must be non-negative",
            "the wall tension is defined for non-negative mu", "pass mu >= 0"));
    }
    Ok((8.0 / 3.0) * mu.sqrt())
}

pub fn wall_lower_bound_2d(mu: f64, length_y: f64) -> Result<f64> {
    if length_y < 0.0 {
        return Err(EngineError::new("length must be non-negative",
            "a 2D domain cannot have negative length", "pass length_y >= 0"));
    }
    Ok(wall_tension(mu)? * length_y)
}

pub fn moment_power(alpha: f64) -> f64 {
    3.0 - alpha
}

pub fn moment_finite(alpha: f64) -> bool {
    alpha > 4.0
}

pub fn moment_log_divergent(alpha: f64) -> bool {
    alpha == 4.0
}

pub fn moment_numeric(alpha: f64, r_min: f64, r_max: f64) -> Result<f64> {
    if r_min <= 0.0 || r_max <= r_min {
        return Err(EngineError::new("need 0 < r_min < r_max",
            "the moment integral needs a positive ordered interval", "pass 0 < r_min < r_max"));
    }
    if alpha == 4.0 {
        return Ok(2.0 * std::f64::consts::PI * (r_max / r_min).ln());
    }
    let exponent = 4.0 - alpha;
    Ok(2.0 * std::f64::consts::PI
        * (r_max.powf(exponent) - r_min.powf(exponent)) / exponent)
}

pub fn verdict(stated_alpha: f64) -> Value {
    let status = if moment_log_divergent(stated_alpha) {
        "log-divergent"
    } else if moment_finite(stated_alpha) {
        "finite"
    } else {
        "power-divergent"
    };
    json!({
        "6b_i_trivial_lower_bound": true,
        "6b_ii_exact_dimensional_reduction": false,
        "6b_iii_moment_finite_for_stated_profile": moment_finite(stated_alpha),
        "stated_tail_alpha": stated_alpha,
        "stated_tail_status": status,
        "note": "E_2D >= T L_y is a trivial positive-gradient bound, not an exact reduction. The stated 1/r^4 profile makes I_eff logarithmically divergent; a finite I_eff requires a tail steeper than r^-4.",
    })
}

pub fn render_markdown(payload: &Value) -> Result<String> {
    let v = payload.get("verdict").ok_or_else(|| EngineError::new(
        "payload must contain a 'verdict' object", "the report needs the reduction verdict",
        "pass a payload object with verdict, wall_tension and meta"))?;
    let get_number = |key: &str| -> Result<f64> {
        payload.get(key).and_then(Value::as_f64).ok_or_else(|| EngineError::new(
            format!("payload must contain numeric '{key}'"), "the report needs both numeric examples",
            "pass wall_tension and lower_bound_example numbers"))
    };
    let tension = get_number("wall_tension")?;
    let lower = get_number("lower_bound_example")?;
    let meta = payload.get("meta").ok_or_else(|| EngineError::new(
        "payload must contain a 'meta' object", "the report needs provenance metadata",
        "pass a payload object with verdict and meta"))?;
    let sha = meta.get("config_sha256").and_then(Value::as_str).unwrap_or("");
    let git = meta.get("git").unwrap_or(&Value::Null);
    let commit = git.get("commit").and_then(Value::as_str).unwrap_or("");
    let dirty = git.get("dirty").and_then(Value::as_bool).unwrap_or(false);
    let flag = |key: &str| py_bool(v.get(key).and_then(Value::as_bool).unwrap_or(false));
    let status = v.get("stated_tail_status").and_then(Value::as_str).unwrap_or("");
    let note = v.get("note").and_then(Value::as_str).unwrap_or("");
    Ok([
        "# Dimensional reduction and moment of inertia (claim 6b)".to_string(),
        String::new(),
        format!("1D wall tension at mu=1: T = {tension:.12}."),
        format!("Lower-bound example: T * L_y (L_y=2) = {lower:.12}."),
        String::new(),
        "| tail rho ~ r^-alpha | I_eff status |".to_string(),
        "|---:|---|".to_string(),
        "| 2 | power-divergent (integrand ~ r^1) |".to_string(),
        "| 4 | log-divergent (integrand ~ r^-1) |".to_string(),
        "| 5 | finite (integrand ~ r^-2) |".to_string(),
        String::new(),
        "I_eff = 2*pi int rho(r) r^3 dr; a tail steeper than r^-4 is required for convergence.".to_string(),
        String::new(),
        format!("**Verdict:** trivial lower bound: **{}**; exact dimensional reduction: **{}**; finite I_eff for the stated profile: **{}** ({status}).",
            flag("6b_i_trivial_lower_bound"), flag("6b_ii_exact_dimensional_reduction"),
            flag("6b_iii_moment_finite_for_stated_profile")),
        String::new(),
        note.to_string(),
        String::new(),
        format!("- Config SHA-256: `{sha}`"),
        format!("- Git: `{commit}` (dirty={})", py_bool(dirty)),
        String::new(),
    ].join("\n"))
}
