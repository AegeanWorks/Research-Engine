//! Phase 5 multiparametric optimization and candidate profiling (domains/pnn/mpo.rs).

use serde_json::{json, Value};

pub const MPO_FIELDS: &[&str] = &["compound_id", "name", "cns_mpo_score",
    "composite_desirability", "mpo_tier", "potency_desirability", "brain_desirability",
    "oral_desirability", "safety_desirability", "primary_liability",
    "optimization_recommendation"];

pub fn ramp_desirability(val: f64, low: f64, high: f64, increasing: bool) -> f64 {
    if high <= low { return if val >= high { 1.0 } else { 0.0 }; }
    if val <= low { return if increasing { 0.0 } else { 1.0 }; }
    if val >= high { return if increasing { 1.0 } else { 0.0 }; }
    let frac = (val - low) / (high - low);
    if increasing { frac } else { 1.0 - frac }
}

pub fn calculate_cns_mpo(mw: f64, logp: f64, tpsa: f64, hbd: f64,
                         pka: Option<f64>, logd: Option<f64>) -> f64 {
    let d_mw = ramp_desirability(mw, 360.0, 500.0, false);
    let d_logp = ramp_desirability(logp, 3.0, 5.0, false);
    let eff_logd = logd.unwrap_or(logp - 0.5);
    let d_logd = ramp_desirability(eff_logd, 2.0, 4.0, false);
    let d_tpsa = if tpsa < 40.0 {
        ramp_desirability(tpsa, 20.0, 40.0, true)
    } else if tpsa <= 90.0 {
        1.0
    } else {
        ramp_desirability(tpsa, 90.0, 120.0, false)
    };
    let d_hbd = ramp_desirability(hbd, 0.5, 3.5, false);
    let eff_pka = pka.unwrap_or(7.4);
    let d_pka = ramp_desirability(eff_pka, 8.0, 10.0, false);
    d_mw + d_logp + d_logd + d_tpsa + d_hbd + d_pka
}

pub struct ProfileInput<'a> {
    pub compound_id: &'a str,
    pub name: &'a str,
    pub mw: f64,
    pub logp: f64,
    pub tpsa: f64,
    pub hbd: f64,
    pub pka: Option<f64>,
    pub ec50_nm: Option<f64>,
    pub brain_kp: Option<f64>,
    pub oral_f_pct: Option<f64>,
    pub selectivity_index: Option<f64>,
}

pub fn profile_candidate(input: &ProfileInput) -> Value {
    let cns_mpo = calculate_cns_mpo(input.mw, input.logp, input.tpsa, input.hbd,
        input.pka, None);
    let d_potency = ramp_desirability(input.ec50_nm.unwrap_or(250.0), 25.0, 500.0, false);
    let d_brain = ramp_desirability(input.brain_kp.unwrap_or(0.30), 0.15, 0.50, true);
    let d_oral = ramp_desirability(input.oral_f_pct.unwrap_or(20.0), 10.0, 30.0, true);
    let d_safety = ramp_desirability(input.selectivity_index.unwrap_or(25.0), 5.0, 50.0, true);
    let values = [d_potency.max(0.01), d_brain.max(0.01), d_oral.max(0.01), d_safety.max(0.01)];
    let composite = (values[0] * values[1] * values[2] * values[3]).powf(0.25);
    let mut liabilities: Vec<String> = Vec::new();
    let mut recommendations: Vec<String> = Vec::new();
    if cns_mpo < 4.5 {
        if input.mw > 380.0 {
            liabilities.push(format!("High molecular weight ({:.1} Da)", input.mw));
            recommendations.push("Truncate peripheral side-chains to improve ligand efficiency.".into());
        }
        if input.logp > 3.2 {
            liabilities.push(format!("Excessive lipophilicity (logP {:.2})", input.logp));
            recommendations.push("Incorporate polar heteroatoms or fluorinated motifs to control logD.".into());
        }
        if input.tpsa > 75.0 {
            liabilities.push(format!("High polar surface area ({:.1} Å²)", input.tpsa));
            recommendations.push("Cap hydrogen bond donors to enhance blood-brain barrier passive transport.".into());
        }
    }
    if let Some(pka) = input.pka {
        if pka > 8.5 {
            liabilities.push(format!("High basic center pKa ({pka:.1})"));
            recommendations.push("Modulate amine pKa to 7.5-8.2 with adjacent electron-withdrawing groups.".into());
        }
    }
    if let Some(kp) = input.brain_kp {
        if kp < 0.30 {
            liabilities.push(format!("Sub-optimal brain partition (Kp={kp:.2})"));
            recommendations.push("Reduce rotatable bonds and optimize TPSA to boost brain uptake.".into());
        }
    }
    if let Some(f) = input.oral_f_pct {
        if f < 20.0 {
            liabilities.push(format!("Marginal oral bioavailability (F={f:.1}%)"));
            recommendations.push("Screen oral salt forms (mesylate, besylate) or evaluate prodrug formulations.".into());
        }
    }
    let primary_liability = liabilities.first().cloned()
        .unwrap_or_else(|| "Balanced physicochemical and exposure profile".into());
    let recommendation = if recommendations.is_empty() {
        "Advance to dose-ranging toxicology and formulation development.".to_string()
    } else {
        recommendations.join(" ")
    };
    let tier = if composite >= 0.70 && cns_mpo >= 4.5 {
        "DEVELOPMENT_CANDIDATE"
    } else if composite >= 0.45 {
        "OPTIMIZATION_LEAD"
    } else {
        "DEPRIORITIZED"
    };
    json!({
        "compound_id": input.compound_id,
        "name": input.name,
        "cns_mpo_score": cns_mpo,
        "composite_desirability": composite,
        "mpo_tier": tier,
        "mw": input.mw, "logp": input.logp, "tpsa": input.tpsa, "hbd": input.hbd,
        "pka": input.pka, "ec50_nm": input.ec50_nm, "brain_kp": input.brain_kp,
        "oral_f_pct": input.oral_f_pct, "selectivity_index": input.selectivity_index,
        "potency_desirability": d_potency, "brain_desirability": d_brain,
        "oral_desirability": d_oral, "safety_desirability": d_safety,
        "primary_liability": primary_liability,
        "optimization_recommendation": recommendation,
    })
}

fn text(value: &Value, key: &str) -> String {
    value.get(key).and_then(Value::as_str).unwrap_or("").to_string()
}

fn number(value: &Value, key: &str) -> f64 {
    value.get(key).and_then(Value::as_f64).unwrap_or(0.0)
}

pub fn render_mpo_report(profiles: &[Value]) -> String {
    let dev = profiles.iter().filter(|p| text(p, "mpo_tier") == "DEVELOPMENT_CANDIDATE").count();
    let opt = profiles.iter().filter(|p| text(p, "mpo_tier") == "OPTIMIZATION_LEAD").count();
    let mut lines = vec![
        "# PNN Phase 5 Lead Optimization & Multiparametric Profiling (MPO) Report".to_string(),
        String::new(),
        "## Executive Summary".to_string(),
        String::new(),
        format!("- **Total Compounds Profiled**: {}", profiles.len()),
        format!("- **Development Candidates (Composite D >= 0.70, CNS MPO >= 4.5)**: {dev}"),
        format!("- **Optimization Leads (Composite D >= 0.45)**: {opt}"),
        format!("- **Deprioritized Compounds**: {}", profiles.len() - dev - opt),
        String::new(),
        "## Multiparametric Optimization Taxonomy".to_string(),
        String::new(),
        "> [!NOTE]".to_string(),
        "> **Pfizer CNS MPO & Derringer-Suich Desirability**: CNS MPO evaluates six central nervous system drug-likeness axes (MW, logP, logD, TPSA, HBD, pKa) on a 0.0 to 6.0 scale. Geometric composite desirability (D) weights target potency (DQ-CS EC50), brain partitioning (Kp,brain), oral bioavailability (F), and cytotoxicity safety margin (SI).".to_string(),
        String::new(),
        "## Profiled Candidates Shortlist".to_string(),
        String::new(),
        "| Compound ID | Chemotype Name | CNS MPO | Composite D | Status Tier | Primary Chemical Liability | Optimization Recommendation |".to_string(),
        "|---|---|---|---|---|---|---|".to_string(),
    ];
    for profile in profiles {
        lines.push(format!("| `{}` | **{}** | {:.2} / 6.0 | **{:.3}** | *{}* | {} | {} |",
            text(profile, "compound_id"), text(profile, "name"),
            number(profile, "cns_mpo_score"), number(profile, "composite_desirability"),
            text(profile, "mpo_tier"), text(profile, "primary_liability"),
            text(profile, "optimization_recommendation")));
    }
    lines.extend([
        String::new(),
        "## Key Medicinal Chemistry Action Items".to_string(),
        String::new(),
        "1. **Basic Nitrogen pKa Fine-Tuning**: Maintain pKa in the 7.5 - 8.2 window to maximize intracellular lysosomal penetration while avoiding systemic clearance.".to_string(),
        "2. **Polar Surface Area Shielding**: Target TPSA between 45 and 65 Å² with minimal HBD count (<= 1) for optimal blood-brain barrier passive transport.".to_string(),
        "3. **Solid-State Formulation & Polymorph Screen**: Advance nominated development candidates to crystalline salt screening for oral solid-dosage formulation stability.".to_string(),
        String::new(),
    ]);
    lines.join("\n")
}

pub fn as_row(profile: &Value) -> Value {
    json!({
        "compound_id": text(profile, "compound_id"),
        "name": text(profile, "name"),
        "cns_mpo_score": format!("{:.2}", number(profile, "cns_mpo_score")),
        "composite_desirability": format!("{:.3}", number(profile, "composite_desirability")),
        "mpo_tier": text(profile, "mpo_tier"),
        "potency_desirability": format!("{:.2}", number(profile, "potency_desirability")),
        "brain_desirability": format!("{:.2}", number(profile, "brain_desirability")),
        "oral_desirability": format!("{:.2}", number(profile, "oral_desirability")),
        "safety_desirability": format!("{:.2}", number(profile, "safety_desirability")),
        "primary_liability": text(profile, "primary_liability"),
        "optimization_recommendation": text(profile, "optimization_recommendation"),
    })
}
