//! PNN IND-enabling safety assessment (domains/pnn/safety.py).

use std::collections::{BTreeMap, BTreeSet};

use serde_json::{json, Value};

use crate::error::{EngineError, Result};

const KM_BY_SPECIES: &[(&str, f64)] = &[
    ("mouse", 3.0), ("rat", 6.0), ("hamster", 5.0), ("guinea pig", 7.0), ("rabbit", 12.0),
    ("dog", 20.0), ("monkey", 12.0), ("marmoset", 12.0), ("human", 37.0),
];
const HUMAN_KM: f64 = 37.0;

fn field(value: &Value, name: &str) -> String {
    value.get(name).and_then(Value::as_str).unwrap_or("").to_string()
}

fn num(value: &Value, name: &str) -> Option<f64> {
    value.get(name).and_then(Value::as_f64)
}

fn species_key(species: &str) -> String {
    species.trim().to_lowercase().replace('_', " ").split_whitespace().collect::<Vec<_>>().join(" ")
}

pub fn noael_hed(noael: f64, species: &str, human_km: f64) -> Result<f64> {
    let key = species_key(species);
    let factor = KM_BY_SPECIES.iter().find(|(name, _)| *name == key).map(|(_, value)| *value)
        .ok_or_else(|| EngineError::new(
            format!("Unsupported species '{species}'; supported: {}",
                KM_BY_SPECIES.iter().map(|(name, _)| *name).collect::<Vec<_>>().join(", ")),
            "a K_m factor is required for the human equivalent dose", "pass a supported species"))?;
    Ok(noael * (factor / human_km))
}

fn most_sensitive(studies: &[Value]) -> Option<Value> {
    studies.iter().min_by(|a, b| {
        let ha = noael_hed(num(a, "noael_mg_kg").unwrap_or(0.0), &field(a, "species"), HUMAN_KM).unwrap_or(f64::MAX);
        let hb = noael_hed(num(b, "noael_mg_kg").unwrap_or(0.0), &field(b, "species"), HUMAN_KM).unwrap_or(f64::MAX);
        ha.partial_cmp(&hb).unwrap_or(std::cmp::Ordering::Equal)
            .then_with(|| field(a, "species").cmp(&field(b, "species")))
            .then_with(|| field(a, "study_type").cmp(&field(b, "study_type")))
    }).cloned()
}

fn genotoxicity(pharm: Option<&Value>) -> &'static str {
    let Some(pharm) = pharm else { return "UNKNOWN"; };
    let ames = pharm.get("ames_positive").and_then(Value::as_bool);
    let micro = pharm.get("micronucleus_positive").and_then(Value::as_bool);
    if ames == Some(true) || micro == Some(true) { return "POSITIVE"; }
    if ames == Some(false) && micro == Some(false) { return "NEGATIVE"; }
    "UNKNOWN"
}

pub fn assess(
    tox_studies: &[Value],
    pharm: Option<&Value>,
    safety_factor: f64,
    herg_margin_min: f64,
    herg_margin_fail: f64,
    cyp_max_pct: f64,
    cyp_caution_pct: f64,
    human_weight_kg: f64,
) -> Result<Vec<Value>> {
    if safety_factor <= 0.0 {
        return Err(EngineError::new("safety_factor must be > 0", "a positive factor is required", "pass a positive factor"));
    }
    if !(0.0 < herg_margin_fail && herg_margin_fail <= herg_margin_min) {
        return Err(EngineError::new("herg_margin_fail must be > 0 and <= herg_margin_min",
            "hERG thresholds must be ordered", "pass valid hERG thresholds"));
    }
    if !(0.0 <= cyp_caution_pct && cyp_caution_pct < cyp_max_pct && cyp_max_pct <= 100.0) {
        return Err(EngineError::new("CYP thresholds must satisfy 0 <= caution < max <= 100",
            "CYP thresholds must be ordered", "pass valid CYP thresholds"));
    }
    let mut by_compound: BTreeMap<String, Vec<Value>> = BTreeMap::new();
    for study in tox_studies {
        by_compound.entry(field(study, "compound_id")).or_default().push(study.clone());
    }
    let pharm_map: BTreeMap<String, Value> = pharm.map(|value| {
        value.as_object().map(|map| map.iter()
            .map(|(key, item)| (key.clone(), item.clone())).collect()).unwrap_or_default()
    }).unwrap_or_default();
    let mut ids: BTreeSet<String> = by_compound.keys().cloned().collect();
    ids.extend(pharm_map.keys().cloned());
    let mut assessments = Vec::new();
    for id in ids {
        let mut studies = by_compound.get(&id).cloned().unwrap_or_default();
        studies.sort_by(|a, b| (num(a, "noael_mg_kg").unwrap_or(0.0), field(a, "species"), field(a, "study_type"))
            .partial_cmp(&(num(b, "noael_mg_kg").unwrap_or(0.0), field(b, "species"), field(b, "study_type")))
            .unwrap_or(std::cmp::Ordering::Equal));
        let sensitive = most_sensitive(&studies);
        let study_pharm = pharm_map.get(&id);
        let mut failures = Vec::new();
        let mut cautions = Vec::new();
        let mut evidence = Vec::new();
        let noael = sensitive.as_ref().and_then(|s| num(s, "noael_mg_kg"));
        let species = sensitive.as_ref().map(|s| field(s, "species")).unwrap_or_default();
        let mut hed = None;
        let mut mrsd = None;
        if let Some(study) = &sensitive {
            let raw = num(study, "noael_mg_kg").unwrap_or(0.0);
            hed = Some(noael_hed(raw, &species, HUMAN_KM)?);
            mrsd = Some(hed.unwrap() / safety_factor * human_weight_kg);
            evidence.push(format!("Most sensitive NOAEL {raw:.1} mg/kg in {species} (HED {:.3} mg/kg)", hed.unwrap()));
        } else {
            cautions.push("No repeat-dose toxicology study submitted".to_string());
        }
        let mut organs: Vec<String> = studies.iter().map(|s| field(s, "target_organ"))
            .filter(|organ| !organ.is_empty() && !["none", "na", "n/a", "-"].contains(&organ.to_lowercase().as_str()))
            .collect();
        organs.sort();
        organs.dedup();
        if !organs.is_empty() { evidence.push(format!("Target organs: {}", organs.join(", "))); }
        let geno = genotoxicity(study_pharm);
        match geno {
            "POSITIVE" => failures.push("Positive genotoxicity finding (Ames or micronucleus)".to_string()),
            "UNKNOWN" => cautions.push("Genotoxicity data incomplete".to_string()),
            _ => evidence.push("Ames and micronucleus negative".to_string()),
        }
        let ic50 = study_pharm.and_then(|p| num(p, "herg_ic50_um"));
        let cmax = study_pharm.and_then(|p| num(p, "free_cmax_um"));
        let margin = match (ic50, cmax) {
            (Some(ic50), Some(cmax)) => {
                let margin = ic50 / cmax;
                if margin < herg_margin_fail {
                    failures.push(format!("Narrow hERG margin ({margin:.1}-fold < {herg_margin_fail:.0}-fold)"));
                } else if margin < herg_margin_min {
                    cautions.push(format!("hERG margin below target ({margin:.1}-fold < {herg_margin_min:.0}-fold)"));
                } else {
                    evidence.push(format!("hERG margin {margin:.1}-fold"));
                }
                Some(margin)
            }
            _ => { cautions.push("hERG margin not computable (missing IC50 or free Cmax)".to_string()); None }
        };
        let cyp = study_pharm.and_then(|p| num(p, "cyp3a4_inhibition_pct"));
        match cyp {
            None => cautions.push("CYP3A4 inhibition not measured".to_string()),
            Some(value) if value >= cyp_max_pct =>
                failures.push(format!("CYP3A4 inhibition {value:.1}% >= {cyp_max_pct:.0}%")),
            Some(value) if value >= cyp_caution_pct =>
                cautions.push(format!("CYP3A4 inhibition {value:.1}% approaching the {cyp_max_pct:.0}% ceiling")),
            Some(value) => evidence.push(format!("CYP3A4 inhibition {value:.1}%")),
        }
        match study_pharm {
            None => cautions.push("Safety pharmacology panel not submitted".to_string()),
            Some(p) => {
                let missing: Vec<&str> = [("respiratory", num(p, "respiratory_noael_mg_kg")), ("CNS", num(p, "cns_noael_mg_kg"))]
                    .into_iter().filter(|(_, value)| value.is_none()).map(|(label, _)| label).collect();
                if missing.is_empty() { evidence.push("CNS and respiratory safety NOAELs recorded".to_string()); }
                else { cautions.push(format!("Missing {} safety NOAEL", missing.join("/"))); }
            }
        }
        let status = if !failures.is_empty() { "FAIL_SAFETY" }
            else if !cautions.is_empty() { "CAUTION" } else { "SAFE_TO_PROGRESS" };
        assessments.push(json!({
            "compound_id": id, "status": status, "most_sensitive_species": species,
            "noael_mg_kg": noael, "noael_hed_mg_kg": hed, "phase1_mrsd_mg": mrsd,
            "herg_ic50_um": ic50, "free_cmax_um": cmax, "herg_margin": margin,
            "cyp3a4_inhibition_pct": cyp, "genotoxicity": geno,
            "target_organs": organs.join("; "),
            "findings": failures.into_iter().chain(cautions).chain(evidence).collect::<Vec<_>>().join("; "),
        }));
    }
    let priority = |status: &str| match status { "SAFE_TO_PROGRESS" => 0, "CAUTION" => 1, _ => 2 };
    assessments.sort_by(|a, b| (priority(&field(a, "status")), field(a, "compound_id"))
        .cmp(&(priority(&field(b, "status")), field(b, "compound_id"))));
    Ok(assessments)
}

fn fmt(value: Option<f64>, decimals: usize, suffix: &str) -> String {
    match value {
        Some(number) => format!("{:.*}", decimals, number) + suffix,
        None => "-".to_string(),
    }
}

pub fn render_report(assessments: &[Value], criteria: &Value) -> String {
    let count = |status: &str| assessments.iter().filter(|a| field(a, "status") == status).count();
    let mut lines = vec![
        "# PNN IND-Enabling Safety Pharmacology & Toxicology Package".to_string(),
        String::new(),
        "> [!IMPORTANT]".to_string(),
        "> **Evidence limit (G-001)**: This package summarizes submitted study results and applies deterministic progression thresholds. It is not a GLP audit, does not replace histopathology or pathologist review, and never establishes that a compound is safe for human administration. Missing values stay UNKNOWN and are never treated as passes.".to_string(),
        String::new(),
        "## Assessment Summary".to_string(), String::new(),
        format!("- **Compounds assessed**: {}", assessments.len()),
        format!("- **Safe to progress**: {}", count("SAFE_TO_PROGRESS")),
        format!("- **Caution / incomplete evidence**: {}", count("CAUTION")),
        format!("- **Failed safety thresholds**: {}", count("FAIL_SAFETY")),
        String::new(),
        "## Progression Thresholds".to_string(), String::new(),
        format!("- **NOAEL to HED**: species K_m / human K_m = {}; safety factor {}x",
            format!("{:?}", criteria.get("human_km").and_then(Value::as_f64).unwrap_or(HUMAN_KM)),
            format!("{:?}", criteria.get("safety_factor").and_then(Value::as_f64).unwrap_or(10.0))),
        format!("- **hERG margin**: >= {}-fold; fail below {}-fold",
            format!("{:?}", criteria.get("herg_margin_min").and_then(Value::as_f64).unwrap_or(30.0)),
            format!("{:?}", criteria.get("herg_margin_fail").and_then(Value::as_f64).unwrap_or(10.0))),
        format!("- **CYP3A4 inhibition**: caution at {}%, fail at {}%",
            format!("{:?}", criteria.get("cyp_caution_pct").and_then(Value::as_f64).unwrap_or(30.0)),
            format!("{:?}", criteria.get("cyp_max_pct").and_then(Value::as_f64).unwrap_or(50.0))),
        "- **Genetic toxicology**: Ames and micronucleus must both be negative; any positive result fails".to_string(),
        String::new(),
        "## Candidate Safety Matrix".to_string(), String::new(),
        "| Compound ID | Status | Sensitive Species | NOAEL (mg/kg) | NOAEL HED (mg/kg) | Phase 1 MRSD (mg) | hERG Margin | CYP3A4 (%) | Genotoxicity | Target Organs |".to_string(),
        "|---|---|---|---|---|---|---|---|---|---|".to_string(),
    ];
    for a in assessments {
        let organs = field(a, "target_organs");
        lines.push(format!("| `{}` | **{}** | {} | {} | {} | {} | {} | {} | {} | {} |",
            field(a, "compound_id"), field(a, "status"),
            if field(a, "most_sensitive_species").is_empty() { "-".to_string() } else { field(a, "most_sensitive_species") },
            fmt(num(a, "noael_mg_kg"), 1, ""), fmt(num(a, "noael_hed_mg_kg"), 3, ""),
            fmt(num(a, "phase1_mrsd_mg"), 2, ""), fmt(num(a, "herg_margin"), 1, "x"),
            fmt(num(a, "cyp3a4_inhibition_pct"), 1, ""), field(a, "genotoxicity"),
            if organs.is_empty() { "-".to_string() } else { organs }));
    }
    lines.extend(["".to_string(), "## Findings".to_string(), String::new()]);
    for a in assessments {
        lines.push(format!("- `{}`: {}", field(a, "compound_id"), field(a, "findings")));
    }
    let blockers: Vec<&Value> = assessments.iter().filter(|a| field(a, "status") != "SAFE_TO_PROGRESS").collect();
    lines.extend(["".to_string(), "## Evidence Gaps & Required Follow-Up".to_string(), String::new()]);
    if blockers.is_empty() {
        lines.push("- No gaps detected in the submitted datasets. Confirm the underlying studies are GLP-compliant, pathologist-reviewed and reflected in the final regulatory submission.".to_string());
    } else {
        for a in blockers {
            lines.push(format!("- `{}` ({}): resolve the flagged findings with a complete GLP repeat-dose study, ICH S7A/S7B battery and definitive genotoxicity package before IND filing.",
                field(a, "compound_id"), field(a, "status")));
        }
    }
    lines.extend([
        String::new(), "## Package Limits".to_string(), String::new(),
        "1. Study quality, GLP compliance and pathology peer review are outside this deterministic check.".to_string(),
        "2. The MRSD here is a NOAEL-based projection; reconcile it with the allometric projection in `pnn.ind` before selecting a first-in-human starting dose.".to_string(),
        "3. Species coverage, exposure margins and toxicokinetic data must be reviewed by a qualified toxicologist before any regulatory submission.".to_string(),
        String::new(),
    ]);
    lines.join("\n")
}
