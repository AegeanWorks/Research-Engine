//! Non-compartmental analysis and preclinical triage (domains/pnn/preclinical.rs).

use serde_json::{json, Value};

use crate::error::{EngineError, Result};

fn number(value: &Value, key: &str) -> f64 {
    value.get(key).and_then(Value::as_f64).unwrap_or(0.0)
}

fn optional(value: &Value, key: &str) -> Option<f64> {
    value.get(key).and_then(Value::as_f64)
}

fn field(value: &Value, key: &str) -> String {
    value.get(key).and_then(Value::as_str).unwrap_or("").to_string()
}

fn text(value: Option<f64>, decimals: usize, missing: &str) -> String {
    match value {
        Some(number) => format!("{number:.decimals$}"),
        None => missing.to_string(),
    }
}

fn py_number(value: f64) -> String {
    let text = value.to_string();
    if text.contains('.') || text.contains('e') || text.contains('E') { text } else { format!("{text}.0") }
}

/// Non-compartmental pharmacokinetic analysis for one concentration-time series.
pub fn calculate_nca(points: &[Value], dose_mg_kg: f64, compound_id: &str,
                     route: &str, tissue: &str) -> Result<Value> {
    let mut sorted = points.to_vec();
    sorted.sort_by(|a, b| number(a, "time_h").partial_cmp(&number(b, "time_h"))
        .unwrap_or(std::cmp::Ordering::Equal));
    if sorted.is_empty() {
        return Err(EngineError::new(format!("Compound '{compound_id}' ({route}/{tissue}): no time points provided"),
            "NCA needs at least one concentration point", "pass concentration-time points"));
    }
    let cmax_pt = sorted.iter().max_by(|a, b| number(a, "concentration")
        .partial_cmp(&number(b, "concentration"))
        .unwrap_or(std::cmp::Ordering::Equal)).unwrap();
    let cmax = number(cmax_pt, "concentration");
    let tmax = number(cmax_pt, "time_h");
    let mut auc_0_t = 0.0;
    for pair in sorted.windows(2) {
        let dt = number(&pair[1], "time_h") - number(&pair[0], "time_h");
        if dt < 0.0 { continue; }
        let mean = (number(&pair[0], "concentration") + number(&pair[1], "concentration")) / 2.0;
        auc_0_t += mean * dt;
    }
    let terminal: Vec<&Value> = sorted.iter()
        .filter(|p| number(p, "time_h") >= tmax && number(p, "concentration") > 0.0)
        .collect();
    let mut lambda_z: Option<f64> = None;
    if terminal.len() >= 3 {
        let n = terminal.len() as f64;
        let sum_t: f64 = terminal.iter().map(|p| number(p, "time_h")).sum();
        let sum_ln_c: f64 = terminal.iter().map(|p| number(p, "concentration").ln()).sum();
        let sum_t2: f64 = terminal.iter().map(|p| number(p, "time_h").powi(2)).sum();
        let sum_t_ln_c: f64 = terminal.iter()
            .map(|p| number(p, "time_h") * number(p, "concentration").ln()).sum();
        let denom = n * sum_t2 - sum_t.powi(2);
        if denom != 0.0 {
            let slope = (n * sum_t_ln_c - sum_t * sum_ln_c) / denom;
            if slope < 0.0 { lambda_z = Some(-slope); }
        }
    } else if terminal.len() == 2 {
        let dt = number(terminal[1], "time_h") - number(terminal[0], "time_h");
        let c1 = number(terminal[0], "concentration");
        let c2 = number(terminal[1], "concentration");
        if dt > 0.0 && c1 > c2 { lambda_z = Some((c1.ln() - c2.ln()) / dt); }
    }
    let half_life = lambda_z.map(|lz| 2.0_f64.ln() / lz);
    let last = sorted.last().unwrap();
    let mut auc_0_inf = None;
    let mut cl = None;
    let mut vd = None;
    if let Some(lz) = lambda_z {
        if lz > 0.0 && number(last, "concentration") > 0.0 {
            let extrap = number(last, "concentration") / lz;
            let total = auc_0_t + extrap;
            auc_0_inf = Some(total);
            if total > 0.0 {
                cl = Some(dose_mg_kg * 1000.0 / total);
                vd = Some(cl.unwrap() / lz);
            }
        }
    }
    Ok(json!({
        "compound_id": compound_id,
        "route": route.to_uppercase(),
        "tissue": tissue.to_lowercase(),
        "dose_mg_kg": dose_mg_kg,
        "cmax": cmax,
        "tmax_h": tmax,
        "auc_0_t": auc_0_t,
        "auc_0_inf": auc_0_inf,
        "half_life_h": half_life,
        "lambda_z": lambda_z,
        "cl_l_h_kg": cl,
        "vd_l_kg": vd,
    }))
}

pub struct PreclinicalCriteria {
    pub min_kp_brain: f64,
    pub min_oral_f_pct: f64,
    pub min_wfa_reduction_pct: f64,
    pub min_itt_improvement_pct: f64,
}

pub fn evaluate_candidates(pk_profiles: &Value, pd_outcomes: Option<&Value>,
                           criteria: &PreclinicalCriteria) -> Vec<Value> {
    let empty = Value::Object(serde_json::Map::new());
    let pd_map = pd_outcomes.unwrap_or(&empty);
    let mut ids: Vec<String> = pk_profiles.as_object().map(|m| m.keys().cloned().collect()).unwrap_or_default();
    if let Some(map) = pd_map.as_object() { ids.extend(map.keys().cloned()); }
    ids.sort();
    ids.dedup();
    let mut candidates = Vec::new();
    for cid in ids {
        let pk_sub = pk_profiles.get(&cid).cloned().unwrap_or(Value::Null);
        let pd = pd_map.get(&cid).cloned();
        let po_plasma = pk_sub.get("PO_plasma");
        let iv_plasma = pk_sub.get("IV_plasma");
        let po_brain = pk_sub.get("PO_brain");
        let oral_f = match (po_plasma, iv_plasma) {
            (Some(po), Some(iv)) if optional(iv, "auc_0_t").unwrap_or(0.0) > 0.0
                && optional(iv, "dose_mg_kg").unwrap_or(0.0) > 0.0 =>
                Some((optional(po, "auc_0_t").unwrap_or(0.0) / optional(po, "dose_mg_kg").unwrap_or(1.0))
                    / (optional(iv, "auc_0_t").unwrap_or(0.0) / optional(iv, "dose_mg_kg").unwrap_or(1.0)) * 100.0),
            _ => None,
        };
        let kp_brain = if let (Some(brain), Some(plasma)) = (po_brain, po_plasma) {
            if optional(plasma, "auc_0_t").unwrap_or(0.0) > 0.0 {
                Some(optional(brain, "auc_0_t").unwrap_or(0.0) / optional(plasma, "auc_0_t").unwrap_or(1.0))
            } else { None }
        } else if let (Some(brain), Some(iv)) = (po_brain, iv_plasma) {
            if optional(iv, "auc_0_t").unwrap_or(0.0) > 0.0 {
                Some(optional(brain, "auc_0_t").unwrap_or(0.0) / optional(iv, "auc_0_t").unwrap_or(1.0))
            } else { None }
        } else { None };
        let plasma_cmax = po_plasma.and_then(|p| optional(p, "cmax"))
            .or_else(|| iv_plasma.and_then(|p| optional(p, "cmax")));
        let plasma_auc = po_plasma.and_then(|p| optional(p, "auc_0_t"))
            .or_else(|| iv_plasma.and_then(|p| optional(p, "auc_0_t")));
        let brain_auc = po_brain.and_then(|p| optional(p, "auc_0_t"));
        let half_life = po_plasma.and_then(|p| optional(p, "half_life_h"))
            .or_else(|| iv_plasma.and_then(|p| optional(p, "half_life_h")));
        let wfa_red = pd.as_ref().and_then(|p| optional(p, "wfa_pnn_reduction_pct"));
        let itt_imp = pd.as_ref().and_then(|p| optional(p, "itt_glucose_auc_reduction_pct"));
        let mut findings = Vec::new();
        if let Some(kp) = kp_brain {
            if kp < 0.20 { findings.push(format!("Restricted brain exposure (Kp={kp:.2} < 0.20)")); }
            else if kp >= criteria.min_kp_brain { findings.push(format!("High brain exposure (Kp={kp:.2})")); }
            else { findings.push(format!("Moderate brain exposure (Kp={kp:.2})")); }
        } else { findings.push("Brain PK unmeasured".to_string()); }
        if let Some(f) = oral_f {
            if f < 15.0 { findings.push(format!("Low oral bioavailability (F={f:.1}% < 15%)")); }
            else if f >= criteria.min_oral_f_pct { findings.push(format!("Robust oral F ({f:.1}%)")); }
            else { findings.push(format!("Marginal oral F ({f:.1}%)")); }
        }
        if let (Some(wfa), Some(itt)) = (wfa_red, itt_imp) {
            if wfa < 10.0 || itt < 10.0 {
                findings.push(format!("Sub-therapeutic PD efficacy (WFA={wfa:.1}%, ITT={itt:.1}%)"));
            } else if wfa >= criteria.min_wfa_reduction_pct && itt >= criteria.min_itt_improvement_pct {
                findings.push(format!("Potent metabolic reversal (WFA={wfa:.1}%, ITT={itt:.1}%)"));
            } else {
                findings.push(format!("Moderate PD response (WFA={wfa:.1}%, ITT={itt:.1}%)"));
            }
        } else { findings.push("In vivo PD unmeasured".to_string()); }
        let status = if kp_brain.map(|k| k < 0.20).unwrap_or(false) {
            "INSUFFICIENT_BRAIN_PENETRATION"
        } else if oral_f.map(|f| f < 15.0).unwrap_or(false) {
            "POOR_BIOAVAILABILITY"
        } else if wfa_red.map(|w| w < 10.0 || itt_imp.map(|i| i < 10.0).unwrap_or(false)).unwrap_or(false) {
            "INSUFFICIENT_EFFICACY"
        } else if kp_brain.map(|k| k >= criteria.min_kp_brain).unwrap_or(false)
            && oral_f.map(|f| f >= criteria.min_oral_f_pct).unwrap_or(false)
            && wfa_red.map(|w| w >= criteria.min_wfa_reduction_pct).unwrap_or(false)
            && itt_imp.map(|i| i >= criteria.min_itt_improvement_pct).unwrap_or(false) {
            "CLINICAL_CANDIDATE"
        } else { "ADVANCED_LEAD" };
        candidates.push(json!({
            "compound_id": cid, "status": status,
            "oral_bioavailability_pct": oral_f, "brain_plasma_ratio": kp_brain,
            "plasma_cmax_ng_ml": plasma_cmax, "plasma_auc_h_ng_ml": plasma_auc,
            "brain_auc_h_ng_ml": brain_auc, "half_life_h": half_life,
            "wfa_pnn_reduction_pct": wfa_red, "itt_glucose_auc_reduction_pct": itt_imp,
            "findings": findings.join("; "),
        }));
    }
    let priority = |status: &str| match status {
        "CLINICAL_CANDIDATE" => 0, "ADVANCED_LEAD" => 1,
        "INSUFFICIENT_BRAIN_PENETRATION" => 2, "POOR_BIOAVAILABILITY" => 3,
        "INSUFFICIENT_EFFICACY" => 4, _ => 9,
    };
    candidates.sort_by(|a, b| {
        let ord = priority(&field(a, "status")).cmp(&priority(&field(b, "status")));
        if ord != std::cmp::Ordering::Equal { return ord; }
        let kp_a = optional(a, "brain_plasma_ratio").unwrap_or(0.0);
        let kp_b = optional(b, "brain_plasma_ratio").unwrap_or(0.0);
        let ord = kp_b.partial_cmp(&kp_a).unwrap_or(std::cmp::Ordering::Equal);
        if ord != std::cmp::Ordering::Equal { return ord; }
        let w_a = optional(a, "wfa_pnn_reduction_pct").unwrap_or(0.0);
        let w_b = optional(b, "wfa_pnn_reduction_pct").unwrap_or(0.0);
        w_b.partial_cmp(&w_a).unwrap_or(std::cmp::Ordering::Equal)
    });
    candidates
}

pub fn render_preclinical_report(candidates: &[Value], criteria: &PreclinicalCriteria) -> String {
    let clinical = candidates.iter().filter(|c| field(c, "status") == "CLINICAL_CANDIDATE").count();
    let advanced = candidates.iter().filter(|c| field(c, "status") == "ADVANCED_LEAD").count();
    let failed = candidates.len() - clinical - advanced;
    let mut lines = vec![
        "# PNN Phase 4 In Vivo Preclinical Candidate Selection Report".to_string(),
        String::new(),
        "## Scientific Context & Translation Invariants".to_string(),
        String::new(),
        "> [!IMPORTANT]".to_string(),
        "> **Preclinical Guidance (G-001)**: Preclinical efficacy demonstrated in mouse DIO models verifies target engagement, oral bioavailability, and metabolic phenotype rescue; human clinical translation requires formal GLP safety pharmacology (ICH S7A/S7B) and Phase 1 human PK dose-escalation trials.".to_string(),
        String::new(),
        "## Candidate Advancement Summary".to_string(),
        String::new(),
        format!("- **Evaluated Candidates**: {}", candidates.len()),
        format!("- **Clinical Candidates (Kp >= {}, F >= {}%, WFA >= {}%)**: {clinical}",
            py_number(criteria.min_kp_brain), py_number(criteria.min_oral_f_pct),
            py_number(criteria.min_wfa_reduction_pct)),
        format!("- **Advanced Leads (Sub-optimal exposure or pending complete PD)**: {advanced}"),
        format!("- **Failed Preclinical Thresholds (Low Kp / Poor F / Inactive)**: {failed}"),
        String::new(),
        "## Preclinical Decision Thresholds".to_string(),
        String::new(),
        format!("- **Brain Partitioning**: Kp,brain (AUC_brain / AUC_plasma) >= {}", py_number(criteria.min_kp_brain)),
        format!("- **Oral Bioavailability**: F >= {}%", py_number(criteria.min_oral_f_pct)),
        format!("- **PNN Remodeling Efficacy**: Hypothalamic WFA+ area reduction >= {}%", py_number(criteria.min_wfa_reduction_pct)),
        format!("- **Insulin Sensitivity**: ITT glucose clearance AUC improvement >= {}%", py_number(criteria.min_itt_improvement_pct)),
        String::new(),
        "## Preclinical Candidate Shortlist".to_string(),
        String::new(),
        "| Compound ID | Status | Brain Kp | Oral F (%) | Plasma Cmax (ng/mL) | Half-life (h) | WFA Red (%) | ITT Imp (%) | Findings |".to_string(),
        "|---|---|---|---|---|---|---|---|---|".to_string(),
    ];
    for c in candidates.iter().filter(|c| matches!(field(c, "status").as_str(), "CLINICAL_CANDIDATE" | "ADVANCED_LEAD")) {
        lines.push(format!("| `{}` | **{}** | {} | {} | {} | {} | {} | {} | {} |",
            field(c, "compound_id"), field(c, "status"),
            text(optional(c, "brain_plasma_ratio"), 2, "-"),
            text(optional(c, "oral_bioavailability_pct"), 1, "-") + if optional(c, "oral_bioavailability_pct").is_some() { "%" } else { "" },
            text(optional(c, "plasma_cmax_ng_ml"), 1, "-"),
            text(optional(c, "half_life_h"), 1, "-"),
            text(optional(c, "wfa_pnn_reduction_pct"), 1, "-") + if optional(c, "wfa_pnn_reduction_pct").is_some() { "%" } else { "" },
            text(optional(c, "itt_glucose_auc_reduction_pct"), 1, "-") + if optional(c, "itt_glucose_auc_reduction_pct").is_some() { "%" } else { "" },
            field(c, "findings")));
    }
    lines.extend([
        String::new(), "## Next Steps for Nominated Candidates".to_string(), String::new(),
        "1. **Formulation & Salt Selection**: Perform salt screening and crystal polymorph stability studies to optimize solid-state oral formulation.".to_string(),
        "2. **Dose-Ranging Repeat Toxicology**: Complete 14-day and 28-day repeated-dose toxicity in rodents and non-rodents to establish NOAEL.".to_string(),
        "3. **Regulatory IND-Enabling Package**: Prepare documentation for Investigational New Drug (IND) filing.".to_string(),
        String::new(),
    ]);
    lines.join("\n")
}

pub fn as_row(candidate: &Value) -> Value {
    json!({
        "compound_id": field(candidate, "compound_id"),
        "status": field(candidate, "status"),
        "oral_bioavailability_pct": text(optional(candidate, "oral_bioavailability_pct"), 1, ""),
        "brain_plasma_ratio": text(optional(candidate, "brain_plasma_ratio"), 2, ""),
        "plasma_cmax_ng_ml": text(optional(candidate, "plasma_cmax_ng_ml"), 1, ""),
        "plasma_auc_h_ng_ml": text(optional(candidate, "plasma_auc_h_ng_ml"), 1, ""),
        "brain_auc_h_ng_ml": text(optional(candidate, "brain_auc_h_ng_ml"), 1, ""),
        "half_life_h": text(optional(candidate, "half_life_h"), 1, ""),
        "wfa_pnn_reduction_pct": text(optional(candidate, "wfa_pnn_reduction_pct"), 1, ""),
        "itt_glucose_auc_reduction_pct": text(optional(candidate, "itt_glucose_auc_reduction_pct"), 1, ""),
        "findings": field(candidate, "findings"),
    })
}
