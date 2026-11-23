//! Hypothalamic circuit, PNN turnover and dosing dynamics (domains/pnn/pathway.rs).

use std::collections::BTreeSet;

use serde_json::{json, Value};

use crate::error::{EngineError, Result};

pub const SIMULATION_FIELDS: &[&str] = &["time_h", "brain_conc_ng_ml", "pnn_density_pct",
    "ir_accessibility_pct", "akt_signaling_pct", "food_intake_reduction_pct",
    "cumulative_weight_delta_pct", "plasticity_risk_tier"];
pub const REGIMEN_FIELDS: &[&str] = &["regimen_name", "compound_id", "dose_mg_kg",
    "duration_days", "mean_pnn_reduction_pct", "peak_pnn_reduction_pct",
    "mean_akt_restoration_pct", "projected_weight_loss_pct", "plasticity_safety_score",
    "recommendation"];

pub fn dosing_times(regimen: &str, duration_h: f64) -> Result<Vec<f64>> {
    let clean = regimen.trim().to_uppercase();
    let mut times = Vec::new();
    let mut t = 0.0;
    match clean.as_str() {
        "CONTINUOUS_DAILY" => {
            while t < duration_h { times.push(t); t += 24.0; }
        }
        "INTERMITTENT_PULSATILE" | "ALTERNATE_DAY" => {
            while t < duration_h { times.push(t); t += 48.0; }
        }
        "TWICE_WEEKLY" => {
            let mut week = 0.0;
            while week < duration_h {
                times.push(week);
                if week + 72.0 < duration_h { times.push(week + 72.0); }
                week += 168.0;
            }
        }
        "ONCE_WEEKLY" => {
            while t < duration_h { times.push(t); t += 168.0; }
        }
        "SINGLE_DOSE" => times.push(0.0),
        _ => return Err(EngineError::new(
            format!("Unknown dosing regimen '{regimen}'. Supported: CONTINUOUS_DAILY, INTERMITTENT_PULSATILE, TWICE_WEEKLY, ONCE_WEEKLY, SINGLE_DOSE"),
            "regimens are a closed vocabulary", "pass one of the listed regimens")),
    }
    Ok(times)
}

pub struct SimOptions<'a> {
    pub compound_id: &'a str,
    pub dose_mg_kg: f64,
    pub regimen: &'a str,
    pub duration_days: i64,
    pub dt_h: f64,
    pub half_life_h: f64,
    pub cmax_per_dose: f64,
    pub ec50_nm: f64,
    pub mw: f64,
}

pub fn simulate_circuit_dynamics(options: &SimOptions) -> Result<Value> {
    if options.dose_mg_kg <= 0.0 {
        return Err(EngineError::new(format!("Dose must be > 0 mg/kg, got {}", options.dose_mg_kg),
            "a dose must be positive", "pass dose_mg_kg > 0"));
    }
    if options.duration_days <= 0 || options.duration_days > 90 {
        return Err(EngineError::new(format!("Duration must be between 1 and 90 days, got {}", options.duration_days),
            "a duration must be in 1..90", "pass 1 <= days <= 90"));
    }
    if options.dt_h <= 0.0 || options.dt_h > 2.0 {
        return Err(EngineError::new(format!("Step dt must be between 0.01 and 2.0 hours, got {}", options.dt_h),
            "a time step must be in (0, 2]", "pass 0 < dt <= 2"));
    }
    if options.half_life_h <= 0.0 {
        return Err(EngineError::new(format!("Half-life must be > 0 h, got {}", options.half_life_h),
            "a half-life must be positive", "pass half_life_h > 0"));
    }
    if options.cmax_per_dose <= 0.0 || options.ec50_nm <= 0.0 || options.mw <= 0.0 {
        return Err(EngineError::new("cmax_per_dose, ec50_nm and mw must all be > 0",
            "all potency constants must be positive", "pass positive values"));
    }
    let duration_h = options.duration_days as f64 * 24.0;
    let dose_times: BTreeSet<u64> = dosing_times(options.regimen, duration_h)?
        .into_iter().map(|v| v.to_bits()).collect();
    let ke = 2.0_f64.ln() / options.half_life_h;
    let ka = 1.2;
    let ec50_ng_ml = (options.ec50_nm * options.mw / 1000.0).max(1.0);
    let k_synth = 0.012;
    let k_deg_max = 0.085;
    let k_akt = 0.15;
    let k_akt_decay = 0.12;
    let akt_baseline = 0.25;
    let ir_baseline = (1.0_f64 - 0.75_f64).max(0.1_f64);
    let mut c_depot = 0.0;
    let mut c_brain = 0.0;
    let mut pnn = 1.0;
    let mut akt = akt_baseline;
    let mut weight_delta = 0.0;
    let mut points = Vec::new();
    let mut severe_plasticity_hours = 0.0;
    let mut pnn_values = Vec::new();
    let mut akt_values = Vec::new();
    let steps = (duration_h / options.dt_h) as i64;
    for step in 0..=steps {
        let t = step as f64 * options.dt_h;
        for dose_bits in &dose_times {
            let dose_time = f64::from_bits(*dose_bits);
            if (t - dose_time).abs() < options.dt_h / 2.0 {
                c_depot += options.dose_mg_kg * options.cmax_per_dose * 1.5;
            }
        }
        let d_depot = -ka * c_depot;
        let d_brain = ka * c_depot - ke * c_brain;
        let drug_effect = c_brain / (c_brain + ec50_ng_ml);
        let d_pnn = k_synth * (1.0 - pnn) - (k_deg_max * drug_effect * pnn);
        let ir_access = (1.0 - (0.75 * pnn)).max(0.1);
        let d_akt = k_akt * (ir_access - ir_baseline) - k_akt_decay * (akt - akt_baseline);
        c_depot = (c_depot + d_depot * options.dt_h).max(0.0);
        c_brain = (c_brain + d_brain * options.dt_h).max(0.0);
        pnn = (pnn + d_pnn * options.dt_h).max(0.05).min(1.0);
        akt = (akt + d_akt * options.dt_h).max(0.1).min(1.0);
        let pnn_pct = pnn * 100.0;
        let ir_access_pct = ir_access * 100.0;
        let akt_pct = akt * 100.0;
        let food_red_pct = ((akt - akt_baseline) * 50.0).max(0.0).min(40.0);
        let d_weight_day = -(food_red_pct / 25.0) * (1.0 / 3.0);
        weight_delta += d_weight_day * (options.dt_h / 24.0);
        let risk = if pnn_pct < 20.0 {
            severe_plasticity_hours += options.dt_h;
            "HIGH_PLASTICITY_RISK"
        } else if pnn_pct < 40.0 {
            "MODERATE_PLASTICITY_WINDOW"
        } else {
            "SAFE_PHYSIOLOGICAL_RANGE"
        };
        pnn_values.push(pnn_pct);
        akt_values.push(akt_pct);
        let sample_every = (1.0 / options.dt_h) as i64;
        if step % sample_every.max(1) == 0 || step == steps {
            points.push(json!({
                "time_h": t, "brain_conc_ng_ml": c_brain, "pnn_density_pct": pnn_pct,
                "ir_accessibility_pct": ir_access_pct, "akt_signaling_pct": akt_pct,
                "food_intake_reduction_pct": food_red_pct,
                "cumulative_weight_delta_pct": weight_delta, "plasticity_risk_tier": risk,
            }));
        }
    }
    let mean_pnn = pnn_values.iter().sum::<f64>() / pnn_values.len() as f64;
    let mean_pnn_red = (100.0 - mean_pnn).max(0.0);
    let peak_pnn_red = (100.0 - pnn_values.iter().copied().fold(f64::INFINITY, f64::min)).max(0.0);
    let mean_akt_level = akt_values.iter().sum::<f64>() / akt_values.len() as f64;
    let mean_akt_restoration = (((mean_akt_level / 100.0 - akt_baseline) / (1.0 - akt_baseline)) * 100.0)
        .max(0.0).min(100.0);
    let plasticity_penalty = (severe_plasticity_hours / 24.0 * 15.0).min(80.0);
    let safety_score = (100.0 - plasticity_penalty).max(10.0);
    let verdict = if mean_pnn_red < 15.0 {
        "SUB-THERAPEUTIC: Insufficient PNN digestion; consider increasing dose or frequency."
    } else if safety_score < 80.0 || mean_pnn_red < 20.0 {
        "CAUTION: Prolonged deep PNN depletion; reduce exposure or extend the dosing interval."
    } else if mean_akt_restoration < 40.0 {
        "CAUTION: PNN reduction outweighs insulin signaling recovery; verify the downstream coupling."
    } else {
        "RECOMMENDED: Balanced metabolic reversal with physiological plasticity preservation."
    };
    Ok(json!({
        "points": points,
        "summary": {
            "regimen_name": options.regimen, "compound_id": options.compound_id,
            "dose_mg_kg": options.dose_mg_kg, "duration_days": options.duration_days,
            "mean_pnn_reduction_pct": mean_pnn_red, "peak_pnn_reduction_pct": peak_pnn_red,
            "mean_akt_restoration_pct": mean_akt_restoration,
            "projected_weight_loss_pct": weight_delta.abs(),
            "plasticity_safety_score": safety_score, "recommendation": verdict,
        },
    }))
}

fn num(value: &Value, key: &str) -> f64 {
    value.get(key).and_then(Value::as_f64).unwrap_or(0.0)
}

fn text(value: &Value, key: &str) -> String {
    value.get(key).and_then(Value::as_str).unwrap_or("").to_string()
}

/// Python str(float) keeps a decimal point for integral values.
fn py_float(value: f64) -> String {
    let text = value.to_string();
    if text.contains('.') || text.contains('e') || text.contains('E') {
        text
    } else {
        format!("{text}.0")
    }
}

pub fn render_pathway_report(result: &Value) -> String {
    let s = result.get("summary").unwrap_or(&Value::Null);
    let points = result.get("points").and_then(Value::as_array).unwrap();
    let mut lines = vec![
        format!("# PNN Hypothalamic Circuit & Dosing Dynamics Report: {}", text(s, "compound_id")),
        String::new(),
        "## Executive Summary".to_string(),
        String::new(),
        format!("- **Compound ID**: `{}`", text(s, "compound_id")),
        format!("- **Simulated Regimen**: **{}** ({} mg/kg PO for {} days)",
            text(s, "regimen_name"), py_float(num(s, "dose_mg_kg")),
            s.get("duration_days").and_then(Value::as_i64).unwrap_or(0)),
        format!("- **Mean Hypothalamic PNN Reduction**: **{:.1}%** (Peak: {:.1}%)",
            num(s, "mean_pnn_reduction_pct"), num(s, "peak_pnn_reduction_pct")),
        format!("- **Insulin Signaling (pAKT) Restoration**: **{:.1}%** of the recoverable gap above the DIO baseline",
            num(s, "mean_akt_restoration_pct")),
        format!("- **Projected Cumulative Weight Loss**: **{:.1}%**", num(s, "projected_weight_loss_pct")),
        format!("- **Plasticity Safety Score**: **{:.1} / 100**", num(s, "plasticity_safety_score")),
        format!("- **Clinical Recommendation**: *{}*", text(s, "recommendation")),
        String::new(),
        "## Scientific Rationale & Plasticity Risk Avoidance".to_string(),
        String::new(),
        "> [!IMPORTANT]".to_string(),
        "> **Plasticity Risk Mitigation (ADR-008)**: Hypothalamic perineuronal nets maintain structural synaptic stability. Continuous unremitting degradation (<20% baseline density) risks anomalous synaptic remodeling. Intermittent pulsatile dosing allows periodic net stabilization while sustaining POMC insulin receptor accessibility.".to_string(),
        "> This report models a single regimen. The recommendation is derived from that regimen's computed metrics, not from a cross-regimen comparison.".to_string(),
        String::new(),
        "## Simulated Circuit Trajectory (Sampled Windows)".to_string(),
        String::new(),
        "| Time (h) | Brain Conc (ng/mL) | PNN Density (%) | IR Access (%) | pAKT Signal (%) | Weight Delta (%) | Plasticity Risk |".to_string(),
        "|---|---|---|---|---|---|---|".to_string(),
    ];
    let last_time = points.last().and_then(|p| p.get("time_h")).and_then(Value::as_f64).unwrap_or(0.0);
    for point in points {
        let t = num(point, "time_h");
        if (t % 24.0).abs() < 0.3 || (t - last_time).abs() < 1e-12 {
            lines.push(format!("| {:.0}h | {:.1} | {:.1}% | {:.1}% | {:.1}% | {:.2}% | *{}* |",
                t, num(point, "brain_conc_ng_ml"), num(point, "pnn_density_pct"),
                num(point, "ir_accessibility_pct"), num(point, "akt_signaling_pct"),
                num(point, "cumulative_weight_delta_pct"), text(point, "plasticity_risk_tier")));
        }
    }
    lines.extend([
        String::new(), "## Interpretation".to_string(), String::new(),
        format!("- **PNN effect**: mean reduction of {:.1}% with a peak of {:.1}%.",
            num(s, "mean_pnn_reduction_pct"), num(s, "peak_pnn_reduction_pct")),
        format!("- **Signaling effect**: {:.1}% of the recoverable pAKT gap was restored above the untreated DIO baseline.",
            num(s, "mean_akt_restoration_pct")),
        format!("- **Plasticity margin**: {:.1}/100, penalised for hours spent below 20% PNN density.",
            num(s, "plasticity_safety_score")),
        "- **Model limits**: this is a deterministic ODE abstraction with literature-derived constants. It ranks dosing hypotheses; it does not predict efficacy, safety or human exposure, and it must not be reported as measured pharmacology (G-001).".to_string(),
        String::new(),
    ]);
    lines.join("\n")
}
