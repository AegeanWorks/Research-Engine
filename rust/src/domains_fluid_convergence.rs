//! Resolution/temporal convergence diagnostics for the claim-15 scan
//! (fluid_universe/sims/convergence.py).

use serde_json::{json, Value};

use crate::error::{EngineError, Result};

const H_RESOLUTION_TOL: f64 = 1.0e-2;
const H_TEMPORAL_TOL: f64 = 5.0e-3;
const Z3_RESOLUTION_TOL: f64 = 2.0e-2;
const Z3_TEMPORAL_TOL: f64 = 2.0e-2;
const SAME_PROBLEM_KEYS: &[&str] = &["length", "mu", "steps", "dt"];

/// Python repr for the scalar keys used in diagnostic messages.
fn py_repr(value: &Value) -> String {
    match value {
        Value::String(text) => format!("'{text}'"),
        Value::Bool(flag) => if *flag { "True".into() } else { "False".into() },
        Value::Null => "None".into(),
        other => other.to_string(),
    }
}

fn field<'a>(value: &'a Value, key: &str) -> Result<&'a Value> {
    value.get(key).ok_or_else(|| EngineError::new(
        format!("payload is missing '{key}'"),
        "the convergence payload needs all pre-registered fields",
        &format!("add '{key}' to the payload")),
    )
}

fn number(value: &Value, key: &str) -> Result<f64> {
    field(value, key)?.as_f64().ok_or_else(|| EngineError::new(
        format!("field '{key}' must be numeric"),
        "the convergence metric must be a number", &format!("pass a number for '{key}'")))
}

fn integer(value: &Value, key: &str) -> Result<i64> {
    field(value, key)?.as_i64().ok_or_else(|| EngineError::new(
        format!("field '{key}' must be an integer"),
        "grid sizes and step counts are integers", &format!("pass an integer for '{key}'")))
}

fn same_problem(low: &Value, high: &Value) -> Result<()> {
    if integer(low, "n")? >= integer(high, "n")? {
        return Err(EngineError::new("low resolution must have the smaller n",
            "the comparison needs a strictly coarser grid", "pass a smaller n for the low payload"));
    }
    for key in SAME_PROBLEM_KEYS {
        let a = field(low, key)?;
        let b = field(high, key)?;
        if a != b {
            return Err(EngineError::new(
                format!("scans must solve the same physical problem: {key} differs ({} != {})",
                    py_repr(a), py_repr(b)),
                "both scans must share the physical setup", &format!("make '{key}' equal in both payloads")));
        }
    }
    Ok(())
}

fn final_metrics(payload: &Value) -> Result<[f64; 5]> {
    let final_state = field(payload, "final")?;
    Ok([
        number(final_state, "H")?,
        number(final_state, "H_upsampled")?,
        number(final_state, "Z3")?,
        number(final_state, "force_rms")?,
        number(final_state, "max_bond")?,
    ])
}

pub fn compare_scans(low: &Value, high: &Value) -> Result<Value> {
    same_problem(low, high)?;
    let coarse = final_metrics(low)?;
    let fine = final_metrics(high)?;
    let deltas = [fine[0] - coarse[0], fine[1] - coarse[1], fine[2] - coarse[2],
        fine[3] - coarse[3], fine[4] - coarse[4]];
    let criteria = json!({
        "H_agrees": deltas[0].abs() <= H_RESOLUTION_TOL,
        "H_upsampled_agrees": deltas[1].abs() <= H_RESOLUTION_TOL,
        "Z3_agrees": deltas[2].abs() <= Z3_RESOLUTION_TOL,
        "force_not_worse": deltas[3] <= 0.0,
        "max_bond_not_worse": deltas[4] <= 0.0,
        "H_toward_one": (fine[0] - 1.0).abs() <= (coarse[0] - 1.0).abs(),
        "H_upsampled_toward_one": (fine[1] - 1.0).abs() <= (coarse[1] - 1.0).abs(),
    });
    let converged = ["H_agrees", "H_upsampled_agrees", "Z3_agrees", "force_not_worse",
        "max_bond_not_worse"].iter().all(|key| criteria[*key].as_bool().unwrap_or(false));
    let verdict = field(high, "verdict")?;
    Ok(json!({
        "n_low": integer(low, "n")?,
        "n_high": integer(high, "n")?,
        "steps": integer(high, "steps")?,
        "dt": number(high, "dt")?,
        "deltas": {
            "H": deltas[0], "H_upsampled": deltas[1], "Z3": deltas[2],
            "force_rms": deltas[3], "max_bond": deltas[4],
        },
        "tolerances": {"H": H_RESOLUTION_TOL, "Z3": Z3_RESOLUTION_TOL},
        "criteria": criteria,
        "resolution_converged": converged,
        "claim_15_status": field(verdict, "claim_15_status")?.as_str().unwrap_or(""),
        "note": "Resolution convergence is a diagnostic, not claim verification: the fine run must still satisfy the unchanged production criteria.",
    }))
}

pub fn compare_temporal(coarse: &Value, fine: &Value) -> Result<Value> {
    if integer(coarse, "n")? != integer(fine, "n")? {
        return Err(EngineError::new(
            format!("same n required: a dt check holds the grid fixed ({} != {})",
                integer(coarse, "n")?, integer(fine, "n")?),
            "a temporal check holds the grid fixed", "pass the same n in both payloads"));
    }
    for key in ["length", "mu"] {
        let a = field(coarse, key)?;
        let b = field(fine, key)?;
        if a != b {
            return Err(EngineError::new(
                format!("scans must solve the same physical problem: {key} differs ({} != {})",
                    py_repr(a), py_repr(b)),
                "both scans must share the physical setup", &format!("make '{key}' equal in both payloads")));
        }
    }
    let coarse_time = integer(coarse, "steps")? as f64 * number(coarse, "dt")?;
    let fine_time = integer(fine, "steps")? as f64 * number(fine, "dt")?;
    if (coarse_time - fine_time).abs() > 1e-12 {
        return Err(EngineError::new(
            format!("scans must reach the same physical time: {coarse_time} != {fine_time}"),
            "a temporal comparison needs the same end time", "adjust steps or dt"));
    }
    if number(coarse, "dt")? <= number(fine, "dt")? {
        return Err(EngineError::new("coarse dt must be larger than fine dt",
            "the temporal check compares a smaller timestep", "pass a larger dt for the coarse payload"));
    }
    let coarse_final = final_metrics(coarse)?;
    let fine_final = final_metrics(fine)?;
    let deltas = [fine_final[0] - coarse_final[0], fine_final[1] - coarse_final[1],
        fine_final[2] - coarse_final[2], fine_final[3] - coarse_final[3],
        fine_final[4] - coarse_final[4]];
    let criteria = json!({
        "H_agrees": deltas[0].abs() <= H_TEMPORAL_TOL,
        "H_upsampled_agrees": deltas[1].abs() <= H_TEMPORAL_TOL,
        "Z3_agrees": deltas[2].abs() <= Z3_TEMPORAL_TOL,
        "force_not_worse": fine_final[3] <= coarse_final[3],
        "max_bond_not_worse": fine_final[4] <= coarse_final[4],
    });
    let converged = ["H_agrees", "H_upsampled_agrees", "Z3_agrees"]
        .iter().all(|key| criteria[*key].as_bool().unwrap_or(false));
    let verdict = field(fine, "verdict")?;
    Ok(json!({
        "n": integer(fine, "n")?,
        "physical_time": fine_time,
        "dt_coarse": number(coarse, "dt")?,
        "dt_fine": number(fine, "dt")?,
        "deltas": {
            "H": deltas[0], "H_upsampled": deltas[1], "Z3": deltas[2],
            "force_rms": deltas[3], "max_bond": deltas[4],
        },
        "tolerances": {"H": H_TEMPORAL_TOL, "Z3": Z3_TEMPORAL_TOL},
        "criteria": criteria,
        "temporal_converged": converged,
        "claim_15_status": field(verdict, "claim_15_status")?.as_str().unwrap_or(""),
        "note": "Temporal convergence is a diagnostic, not claim verification: if it fails, the spatial resolution comparison is confounded.",
    }))
}

fn projection(current: f64, target: f64, slope: f64, rising: bool) -> Option<f64> {
    if rising && current >= target { return Some(0.0); }
    if !rising && current <= target { return Some(0.0); }
    if (rising && slope <= 0.0) || (!rising && slope >= 0.0) { return None; }
    Some((target - current) / slope)
}

fn nullable(value: Option<f64>) -> Value {
    value.map(Value::from).unwrap_or(Value::Null)
}

pub fn summarize_trend(rows: &[Value], z3_target: f64, force_tol: f64) -> Result<Value> {
    if rows.len() < 2 {
        return Err(EngineError::new("at least two rows are required for a trend",
            "a trend needs a start and an end", "pass at least two rows"));
    }
    let mut steps = Vec::new();
    let mut times = Vec::new();
    let mut z3_values = Vec::new();
    let mut force_values = Vec::new();
    for row in rows {
        steps.push(integer(row, "steps")?);
        times.push(number(row, "t")?);
        z3_values.push(number(row, "Z3")?);
        force_values.push(number(row, "force_rms")?);
    }
    let delta_steps = steps[steps.len() - 1] - steps[0];
    if delta_steps <= 0 {
        return Err(EngineError::new("steps must increase between rows",
            "a trend needs increasing step counts", "pass rows with increasing steps"));
    }
    let delta = delta_steps as f64;
    let z3_slope = (z3_values[z3_values.len() - 1] - z3_values[0]) / delta;
    let force_slope = (force_values[force_values.len() - 1] - force_values[0]) / delta;
    let dt_effective = (times[times.len() - 1] - times[0]) / delta;
    let last_time = times[times.len() - 1];
    let z3_steps = projection(z3_values[z3_values.len() - 1], z3_target, z3_slope, true);
    let force_steps = projection(force_values[force_values.len() - 1], force_tol, force_slope, false);
    let z3_monotone = z3_values.windows(2).all(|w| w[1] >= w[0]);
    let force_monotone = force_values.windows(2).all(|w| w[1] <= w[0]);
    let status = rows[rows.len() - 1].get("claim_15_status").and_then(Value::as_str).unwrap_or("");
    Ok(json!({
        "rows": rows.len(),
        "steps_total": steps[steps.len() - 1],
        "physical_time": last_time,
        "dt_effective": dt_effective,
        "z3_slope_per_step": z3_slope,
        "force_slope_per_step": force_slope,
        "z3_monotone": z3_monotone,
        "force_monotone": force_monotone,
        "projected_steps_to_z3_target": nullable(z3_steps),
        "projected_time_to_z3_target": nullable(z3_steps.map(|s| last_time + s * dt_effective)),
        "projected_steps_to_force_tol": nullable(force_steps),
        "projected_time_to_force_tol": nullable(force_steps.map(|s| last_time + s * dt_effective)),
        "claim_15_status": status,
        "note": "Linear projections are diagnostics, not claims; claim 15 is verified only when the final state satisfies the production rule.",
    }))
}
