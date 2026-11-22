//! One-parameter vortex/eddy hierarchy test
//! (fluid_universe/theory/vortex_cascade.py).

use serde_json::{json, Value};

use crate::error::{EngineError, Result};

pub const KOIDE_TARGET: f64 = 2.0 / 3.0;
pub const RELATIVE_TOLERANCE: f64 = 0.1;
pub const KOIDE_TOLERANCE: f64 = 0.01;

pub fn koide_q(values: &[f64]) -> Result<f64> {
    if values.is_empty() || values.iter().any(|v| *v <= 0.0) {
        return Err(EngineError::new("values must be positive",
            "Koide Q needs strictly positive masses", "pass positive values"));
    }
    let root_sum: f64 = values.iter().map(|v| v.sqrt()).sum();
    let denominator = root_sum * root_sum;
    if denominator == 0.0 {
        return Err(EngineError::new("degenerate values",
            "Koide Q needs a non-zero root sum", "pass non-degenerate values"));
    }
    Ok(values.iter().sum::<f64>() / denominator)
}

pub fn geometric_spectrum(ratio: f64, generations: usize) -> Result<Vec<f64>> {
    if ratio <= 0.0 {
        return Err(EngineError::new("ratio must be positive",
            "a geometric cascade needs a positive ratio", "pass ratio > 0"));
    }
    Ok((0..generations).map(|n| ratio.powf(n as f64)).collect())
}

pub fn power_law_spectrum(exponent: f64, generations: usize) -> Vec<f64> {
    (1..=generations).map(|n| (n as f64).powf(exponent)).collect()
}

pub fn solve_power_for_koide(target: f64, mut lower: f64, mut upper: f64) -> Result<f64> {
    if target <= 1.0 / 3.0 || target >= 1.0 {
        return Err(EngineError::new("target must lie between 1/3 and 1",
            "the Koide target must be in the admissible interval", "pass 1/3 < target < 1"));
    }
    if koide_q(&power_law_spectrum(lower, 3))? > target {
        return Err(EngineError::new("lower bound already above target",
            "the bracket lower bound must be below the target", "pass a smaller lower bound"));
    }
    if koide_q(&power_law_spectrum(upper, 3))? < target {
        return Err(EngineError::new("upper bound below target",
            "the bracket upper bound must be above the target", "pass a larger upper bound"));
    }
    for _ in 0..200 {
        let middle = 0.5 * (lower + upper);
        if koide_q(&power_law_spectrum(middle, 3))? < target {
            lower = middle;
        } else {
            upper = middle;
        }
    }
    Ok(0.5 * (lower + upper))
}

fn summary(name: &str, observed: &[f64], predicted: &[f64], parameter: f64) -> Result<Value> {
    let observed_ratio = observed[2] / observed[0];
    let predicted_ratio = predicted[2] / predicted[0];
    let ratio_error = (predicted_ratio - observed_ratio) / observed_ratio;
    let q_predicted = koide_q(predicted)?;
    let q_observed = koide_q(observed)?;
    let falsified = ratio_error.abs() > RELATIVE_TOLERANCE
        || (q_predicted - KOIDE_TARGET).abs() > KOIDE_TOLERANCE;
    Ok(json!({
        "model": name,
        "parameter": parameter,
        "predicted_ratios": predicted.iter().map(|v| Value::from(v / predicted[0])).collect::<Vec<_>>(),
        "predicted_tau_ratio": predicted_ratio,
        "observed_tau_ratio": observed_ratio,
        "tau_relative_error": ratio_error,
        "koide_q_predicted": q_predicted,
        "koide_q_observed": q_observed,
        "falsified": falsified,
    }))
}

pub fn run_hypotheses(observed: &[f64]) -> Result<Value> {
    if observed.len() != 3 || observed.iter().any(|v| *v <= 0.0) {
        return Err(EngineError::new("observed must be three positive masses",
            "a hierarchy test needs three positive charged-lepton masses",
            "pass three positive values"));
    }
    let muon_ratio = observed[1] / observed[0];
    let geometric = geometric_spectrum(muon_ratio, 3)?
        .iter().map(|v| observed[0] * v).collect::<Vec<_>>();
    let power_parameter = muon_ratio.ln() / 2.0_f64.ln();
    let power_muon = power_law_spectrum(power_parameter, 3)
        .iter().map(|v| observed[0] * v).collect::<Vec<_>>();
    let koide_p = solve_power_for_koide(KOIDE_TARGET, 0.0, 50.0)?;
    let power_koide = power_law_spectrum(koide_p, 3)
        .iter().map(|v| observed[0] * v).collect::<Vec<_>>();
    let models = json!({
        "geometric": summary("geometric", observed, &geometric, muon_ratio)?,
        "power_law_muon_fit": summary("power_law_muon_fit", observed, &power_muon, power_parameter)?,
        "power_law_koide_fit": summary("power_law_koide_fit", observed, &power_koide, koide_p)?,
    });
    let falsified = models.as_object().unwrap().values()
        .all(|m| m.get("falsified").and_then(Value::as_bool).unwrap_or(false));
    Ok(json!({
        "models": models,
        "koide_target": KOIDE_TARGET,
        "relative_tolerance": RELATIVE_TOLERANCE,
        "koide_tolerance": KOIDE_TOLERANCE,
        "falsified": falsified,
        "status": if falsified {
            "FALSIFIED (no one-parameter hierarchy matches both ratios and Q)"
        } else {
            "UNVERIFIED (one model matches at this tolerance; not a derivation)"
        },
        "note": "A one-parameter fluid hierarchy has no freedom left after the muon ratio or Q is fixed. A two-parameter offset can fit the masses, but then Q is reproduced rather than predicted.",
    }))
}
