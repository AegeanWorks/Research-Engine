//! FDA/ICH allometric scaling and IND dose projections (domains/pnn/ind.rs).

use serde_json::{json, Value};

use crate::error::{EngineError, Result};

pub const KM_MOUSE: f64 = 3.0;
pub const KM_HUMAN: f64 = 37.0;
pub const DEFAULT_SAFETY_FACTOR: f64 = 10.0;
pub const MOUSE_WEIGHT_KG: f64 = 0.020;
pub const HUMAN_WEIGHT_KG: f64 = 60.0;

fn opt(value: &Value, key: &str) -> Option<f64> {
    value.get(key).and_then(Value::as_f64)
}

fn text(value: &Value, key: &str) -> String {
    value.get(key).and_then(Value::as_str).unwrap_or("").to_string()
}

fn fmt(value: Option<f64>, spec: usize) -> String {
    match value {
        Some(number) => format!("{number:.spec$}"),
        None => String::new(),
    }
}

fn display(value: Option<f64>, spec: usize) -> String {
    match value {
        Some(number) => format!("{number:.spec$}"),
        None => "UNMEASURED".to_string(),
    }
}

pub fn calculate_allometric_scaling(animal_dose_mg_kg: f64, mouse_cl_l_h_kg: f64,
    mouse_vd_l_kg: f64, noael_mg_kg: f64, noael_km: f64, mouse_weight_kg: f64,
    human_weight_kg: f64, km_human: f64, safety_factor: f64) -> Result<Value> {
    if animal_dose_mg_kg <= 0.0 { return Err(EngineError::new("animal_dose_mg_kg must be > 0", "dose must be positive", "pass a positive dose")); }
    if mouse_cl_l_h_kg <= 0.0 { return Err(EngineError::new("mouse_cl_l_h_kg must be > 0", "clearance must be positive", "pass positive CL")); }
    if mouse_vd_l_kg <= 0.0 { return Err(EngineError::new("mouse_vd_l_kg must be > 0", "volume must be positive", "pass positive Vd")); }
    if noael_mg_kg <= 0.0 { return Err(EngineError::new("noael_mg_kg must be > 0", "NOAEL must be positive", "pass a positive NOAEL")); }
    if safety_factor <= 0.0 { return Err(EngineError::new("safety_factor must be > 0", "safety factor must be positive", "pass a positive safety factor")); }
    if mouse_weight_kg <= 0.0 || human_weight_kg <= 0.0 { return Err(EngineError::new("body weights must be > 0", "weights must be positive", "pass positive weights")); }
    let noael_factor = noael_km / km_human;
    let hed_mg_kg = animal_dose_mg_kg * (KM_MOUSE / km_human);
    let human_daily_mg = hed_mg_kg * human_weight_kg;
    let weight_ratio = human_weight_kg / mouse_weight_kg;
    let cl_human = mouse_cl_l_h_kg * mouse_weight_kg * weight_ratio.powf(0.75);
    let vd_human = mouse_vd_l_kg * mouse_weight_kg * weight_ratio;
    let t12_human = (2.0_f64.ln() * vd_human) / cl_human;
    let noael_hed = noael_mg_kg * noael_factor;
    let mrsd_mg = (noael_hed / safety_factor) * human_weight_kg;
    Ok(json!({
        "hed_mg_kg": hed_mg_kg, "human_daily_mg": human_daily_mg,
        "cl_human_l_h": cl_human, "vd_human_l": vd_human, "t12_human_h": t12_human,
        "noael_mg_kg": noael_mg_kg, "noael_hed": noael_hed, "mrsd_mg": mrsd_mg,
    }))
}

fn project_one(cid: &str, name: &str, info: &Value, safety_factor: f64,
               human_weight_kg: f64) -> Value {
    let dose = opt(info, "dose_mg_kg");
    let cl_mouse = opt(info, "cl_l_h_kg");
    let vd_mouse = opt(info, "vd_l_kg");
    let noael = opt(info, "noael_mg_kg");
    let noael_km = opt(info, "noael_km").unwrap_or(KM_MOUSE);
    let kp = opt(info, "brain_kp");
    let oral_f = opt(info, "oral_f");
    let mut findings: Vec<String> = Vec::new();
    let mut measured_fields = 0;
    let (mut hed, mut daily_mg) = (None, None);
    let mut dose_effective = dose;
    if let Some(d) = dose {
        if d > 0.0 {
            hed = Some(d * (KM_MOUSE / KM_HUMAN));
            daily_mg = Some(hed.unwrap() * human_weight_kg);
            measured_fields += 1;
        } else {
            dose_effective = None;
            findings.push("Efficacious animal dose unmeasured".to_string());
        }
    } else {
        findings.push("Efficacious animal dose unmeasured".to_string());
    }
    let (mut cl_h, mut vd_h, mut t12_h) = (None, None, None);
    if let (Some(cl), Some(vd)) = (cl_mouse, vd_mouse) {
        if cl > 0.0 && vd > 0.0 {
            let weight_ratio = human_weight_kg / MOUSE_WEIGHT_KG;
            cl_h = Some(cl * MOUSE_WEIGHT_KG * weight_ratio.powf(0.75));
            vd_h = Some(vd * MOUSE_WEIGHT_KG * weight_ratio);
            t12_h = Some((2.0_f64.ln() * vd_h.unwrap()) / cl_h.unwrap());
            measured_fields += 1;
        } else {
            findings.push("Mouse CL/Vd unmeasured; human half-life not projected".to_string());
        }
    } else {
        findings.push("Mouse CL/Vd unmeasured; human half-life not projected".to_string());
    }
    let (mut noael_hed, mut mrsd_mg, mut ti) = (None, None, None);
    if let Some(n) = noael {
        if n > 0.0 {
            noael_hed = Some(n * (noael_km / KM_HUMAN));
            mrsd_mg = Some((noael_hed.unwrap() / safety_factor) * human_weight_kg);
            measured_fields += 1;
            if let Some(d) = dose_effective { ti = Some(n / d); }
        } else {
            findings.push("NOAEL unmeasured; MRSD and therapeutic index not projected".to_string());
        }
    } else {
        findings.push("NOAEL unmeasured; MRSD and therapeutic index not projected".to_string());
    }
    if let Some(k) = kp {
        measured_fields += 1;
        if k >= 0.40 { findings.push(format!("Robust central brain exposure (Kp={k:.2})")); }
        else if k >= 0.30 { findings.push(format!("Acceptable central brain exposure (Kp={k:.2})")); }
        else { findings.push(format!("Restricted central brain exposure (Kp={k:.2})")); }
    } else { findings.push("Brain partitioning unmeasured".to_string()); }
    if let Some(f) = oral_f {
        measured_fields += 1;
        if f >= 20.0 { findings.push(format!("Oral bioavailability above the progression floor (F={f:.1}%)")); }
        else { findings.push(format!("Oral bioavailability below the progression floor (F={f:.1}%)")); }
    } else { findings.push("Oral bioavailability unmeasured".to_string()); }
    if let Some(t) = t12_h {
        if t >= 12.0 { findings.push(format!("Extended projected human t1/2 ({t:.1}h) supports once-daily dosing")); }
        else { findings.push(format!("Moderate projected human t1/2 ({t:.1}h) suggests pulsatile dosing")); }
    }
    if let Some(t) = ti {
        if t >= 5.0 { findings.push(format!("Broad therapeutic window (TI={t:.1}x)")); }
    }
    let status = if measured_fields >= 5 { "COMPLETE" }
        else if measured_fields > 0 { "PARTIAL" }
        else { "INSUFFICIENT_EVIDENCE" };
    json!({
        "compound_id": cid, "name": name, "animal_dose_mg_kg": dose_effective,
        "human_equivalent_dose_mg_kg": hed, "human_total_daily_dose_mg": daily_mg,
        "projected_human_cl_l_h": cl_h, "projected_human_vd_l": vd_h,
        "projected_human_half_life_h": t12_h, "noael_mg_kg": noael,
        "noael_hed_mg_kg": noael_hed, "phase1_mrsd_mg": mrsd_mg,
        "therapeutic_index": ti, "brain_kp": kp, "oral_f_pct": oral_f,
        "findings": findings.join("; "), "evidence_status": status,
    })
}

pub fn project_clinical_candidates(compounds: &[Value], preclinical_data: Option<&Value>,
    lead_id: Option<&str>, safety_factor: f64, human_weight_kg: f64) -> Vec<Value> {
    let empty = Value::Object(serde_json::Map::new());
    let pk_map = preclinical_data.unwrap_or(&empty);
    let mut projections = Vec::new();
    for row in compounds {
        let cid = text(row, "compound_id").trim().to_string();
        if cid.is_empty() { continue; }
        let name_raw = text(row, "name");
        let name = {
            let n = name_raw.trim();
            if n.is_empty() { cid.clone() } else { n.to_string() }
        };
        let info = pk_map.get(&cid).cloned().unwrap_or(Value::Null);
        projections.push(project_one(&cid, &name, &info, safety_factor, human_weight_kg));
    }
    let rank = |status: &str| match status {
        "COMPLETE" => 0, "PARTIAL" => 1, "INSUFFICIENT_EVIDENCE" => 2, _ => 3,
    };
    projections.sort_by(|a, b| {
        let lead_a = if lead_id.map(|id| id == text(a, "compound_id")).unwrap_or(false) { 0 } else { 1 };
        let lead_b = if lead_id.map(|id| id == text(b, "compound_id")).unwrap_or(false) { 0 } else { 1 };
        let ord = lead_a.cmp(&lead_b);
        if ord != std::cmp::Ordering::Equal { return ord; }
        let ord = rank(&text(a, "evidence_status")).cmp(&rank(&text(b, "evidence_status")));
        if ord != std::cmp::Ordering::Equal { return ord; }
        let ka = -opt(a, "brain_kp").unwrap_or(0.0);
        let kb = -opt(b, "brain_kp").unwrap_or(0.0);
        let ord = ka.partial_cmp(&kb).unwrap_or(std::cmp::Ordering::Equal);
        if ord != std::cmp::Ordering::Equal { return ord; }
        text(a, "compound_id").cmp(&text(b, "compound_id"))
    });
    projections
}

pub fn as_row(p: &Value) -> Value {
    json!({
        "compound_id": text(p, "compound_id"), "name": text(p, "name"),
        "animal_dose_mg_kg": fmt(opt(p, "animal_dose_mg_kg"), 1),
        "human_equivalent_dose_mg_kg": fmt(opt(p, "human_equivalent_dose_mg_kg"), 3),
        "human_total_daily_dose_mg": fmt(opt(p, "human_total_daily_dose_mg"), 1),
        "projected_human_cl_l_h": fmt(opt(p, "projected_human_cl_l_h"), 2),
        "projected_human_vd_l": fmt(opt(p, "projected_human_vd_l"), 1),
        "projected_human_half_life_h": fmt(opt(p, "projected_human_half_life_h"), 1),
        "noael_mg_kg": fmt(opt(p, "noael_mg_kg"), 1),
        "noael_hed_mg_kg": fmt(opt(p, "noael_hed_mg_kg"), 3),
        "phase1_mrsd_mg": fmt(opt(p, "phase1_mrsd_mg"), 3),
        "therapeutic_index": fmt(opt(p, "therapeutic_index"), 0),
        "brain_kp": fmt(opt(p, "brain_kp"), 2),
        "oral_f_pct": fmt(opt(p, "oral_f_pct"), 1),
        "findings": text(p, "findings"),
        "evidence_status": text(p, "evidence_status"),
    })
}

/// Python's `:g` compact float format.
fn py_g(value: f64) -> String {
    value.to_string()
}

pub fn render_ind_dossier(projections: &[Value], lead_id: Option<&str>,
                          criteria: Option<&Value>) -> String {
    let empty = Value::Object(serde_json::Map::new());
    let criteria = criteria.unwrap_or(&empty);
    let lead = lead_id.and_then(|id| projections.iter().find(|p| text(p, "compound_id") == id))
        .or_else(|| projections.first());
    let mut lines = vec![
        "# Investigational New Drug (IND) Candidate Nomination Dossier".to_string(),
        String::new(),
        "## Module 2.4: Nonclinical Overview & Clinical Starting Dose Justification".to_string(),
        String::new(),
        "> [!IMPORTANT]".to_string(),
        "> **Regulatory Guidance (ICH M3(R2) / S7A / S7B)**: Allometric scaling estimates Human Equivalent Dose (HED) and Maximum Recommended Starting Dose (MRSD) from measured animal dose, clearance, volume and NOAEL data. First-in-Human (FIH) Phase 1 initiation applies a 10-fold safety factor to the NOAEL HED. Values marked UNMEASURED were not supplied and must not be inferred.".to_string(),
        String::new(),
        "## Clinical Candidate Nomination Summary".to_string(),
        String::new(),
    ];
    match lead {
        None => lines.push("- **No candidate records were supplied.**".to_string()),
        Some(l) => {
            lines.extend(vec![
                format!("- **Nominated Lead Compound**: `{}` (**{}**)", text(l, "compound_id"), text(l, "name")),
                format!("- **Evidence Status**: **{}**", text(l, "evidence_status")),
                format!("- **Rodent Efficacious Dose**: {}", display(opt(l, "animal_dose_mg_kg"), 1))
                    + if opt(l, "animal_dose_mg_kg").is_some() { " mg/kg PO" } else { "" },
                format!("- **Human Equivalent Dose (HED)**: {}", display(opt(l, "human_equivalent_dose_mg_kg"), 3))
                    + &match opt(l, "human_total_daily_dose_mg") {
                        Some(v) => format!(" mg/kg ({:.1} mg total daily for 60 kg adult)", v),
                        None => String::new(),
                    },
                format!("- **Projected Human Half-Life ($t_{{1/2}}$)**: {}", display(opt(l, "projected_human_half_life_h"), 1))
                    + &match (opt(l, "projected_human_half_life_h"), opt(l, "projected_human_cl_l_h"), opt(l, "projected_human_vd_l")) {
                        (Some(_), Some(cl), Some(vd)) => format!(" hours (Projected CL: {:.2} L/h, Vd: {:.1} L)", cl, vd),
                        _ => String::new(),
                    },
                format!("- **No Observed Adverse Effect Level (NOAEL)**: {}", display(opt(l, "noael_mg_kg"), 1))
                    + &match opt(l, "noael_hed_mg_kg") {
                        Some(v) => format!(" mg/kg (NOAEL HED: {:.3} mg/kg)", v),
                        None => String::new(),
                    },
                format!("- **Phase 1 First-in-Human Starting Dose (MRSD)**: {}", display(opt(l, "phase1_mrsd_mg"), 2))
                    + if opt(l, "phase1_mrsd_mg").is_some() { " mg (NOAEL HED / 10)" } else { "" },
                format!("- **Therapeutic Window**: {}", display(opt(l, "therapeutic_index"), 1))
                    + if opt(l, "therapeutic_index").is_some() { "-fold over the efficacious dose" } else { "" },
                format!("- **Brain Partition ($K_{{p,\\text{{brain}}}}$)**: {}", display(opt(l, "brain_kp"), 2)),
                format!("- **Oral Bioavailability ($F$)**: {}", display(opt(l, "oral_f_pct"), 1))
                    + if opt(l, "oral_f_pct").is_some() { "%" } else { "" },
                String::new(),
            ]);
        }
    }
    lines.extend(vec![
        "## Candidate Comparison & Scaling Matrix".to_string(), String::new(),
        "| Compound ID | Chemotype | Evidence | Animal Dose (mg/kg) | Human Dose (mg/day) | Human t1/2 (h) | NOAEL HED (mg/kg) | Phase 1 MRSD (mg) | Safety Margin | Key Findings |".to_string(),
        "|---|---|---|---|---|---|---|---|---|---|".to_string(),
    ]);
    for p in projections {
        lines.push(format!("| `{}` | **{}** | {} | {} | {} | {} | {} | {} | {} | {} |",
            text(p, "compound_id"), text(p, "name"), text(p, "evidence_status"),
            display(opt(p, "animal_dose_mg_kg"), 1), display(opt(p, "human_total_daily_dose_mg"), 1),
            display(opt(p, "projected_human_half_life_h"), 1), display(opt(p, "noael_hed_mg_kg"), 3),
            display(opt(p, "phase1_mrsd_mg"), 2),
            match opt(p, "therapeutic_index") { Some(v) => format!("{:.1}x", v), None => "UNMEASURED".to_string() },
            text(p, "findings")));
    }
    let incomplete: Vec<&Value> = projections.iter().filter(|p| text(p, "evidence_status") != "COMPLETE").collect();
    lines.extend(["".to_string(), "## Evidence Gaps".to_string(), String::new()]);
    if !incomplete.is_empty() {
        for p in &incomplete {
            lines.push(format!("- `{}` ({}): {}", text(p, "compound_id"), text(p, "evidence_status"), text(p, "findings")));
        }
        lines.push("- Supply the missing measurements from `pnn.preclinical` (dose, CL, Vd, Kp, F) and `pnn.safety` (most sensitive NOAEL) before this dossier is used for filing.".to_string());
    } else {
        lines.push("- All projection inputs were supplied. Confirm study quality, GLP compliance and exposure margins with a qualified toxicologist before submission.".to_string());
    }
    lines.extend(vec![
        String::new(), "## Safety Pharmacology Checklist (ICH S7A/S7B)".to_string(), String::new(),
        "> These items are filing requirements, not completed findings. `python -m pnn.safety` records the submitted results and progression thresholds; an unchecked item blocks IND filing until evidence exists.".to_string(),
        String::new(),
        "- [ ] **Cardiovascular Safety (hERG IC50)**: required, with the margin over free Cmax recorded by `pnn.safety`.".to_string(),
        "- [ ] **Central Nervous System (Irwin / FOB Screen)**: required, with a CNS safety NOAEL on file.".to_string(),
        "- [ ] **Respiratory Safety**: required, with a respiratory safety NOAEL on file.".to_string(),
        "- [ ] **Genetic Toxicology**: required; bacterial reverse mutation (Ames) and in vitro micronucleus must be negative.".to_string(),
        String::new(),
        "## Recommended Phase 1 Clinical Protocol Architecture".to_string(), String::new(),
        "1. **Study Design**: Randomized, double-blind, placebo-controlled Single Ascending Dose (SAD) followed by 14-day Multiple Ascending Dose (MAD) in healthy adult volunteers.".to_string(),
    ]);
    match lead.and_then(|l| opt(l, "phase1_mrsd_mg")) {
        Some(mrsd) => lines.push(format!("2. **Starting Dose**: Initial cohort starts at **{mrsd:.2} mg** oral capsule (fasted state).")),
        None => lines.push("2. **Starting Dose**: pending. The NOAEL-based MRSD cannot be stated until the NOAEL is measured.".to_string()),
    }
    let factor = criteria.get("safety_factor").and_then(Value::as_f64).unwrap_or(DEFAULT_SAFETY_FACTOR);
    lines.extend(vec![
        "3. **Dose Escalation**: Modified Fibonacci escalation cohorts (e.g. 1x, 2x, 3.3x, 5x, 7.5x) with real-time safety monitoring and dense plasma PK sampling.".to_string(),
        "4. **Biomarker Endpoints**: Lumbar puncture CSF-to-plasma drug partition ($K_{p,\\text{CSF}}$) and metabolic fasting glucose/insulin clamp.".to_string(),
        String::new(), "## Projection Limits".to_string(), String::new(),
        format!("- HED uses the mouse K_m ({}) against the human K_m ({}); the NOAEL HED uses the NOAEL species K_m supplied with the toxicology data.", py_g(KM_MOUSE), py_g(KM_HUMAN)),
        format!("- The 10-fold safety factor is the default ({}). Reconcile the MRSD with the most sensitive species NOAEL in `pnn.safety` before filing.", py_g(factor)),
        "- Allometric scaling is a projection from animal data and never establishes human safety or efficacy.".to_string(),
        String::new(),
    ]);
    lines.join("\n")
}
