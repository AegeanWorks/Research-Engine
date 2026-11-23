//! Molecular dynamics trajectory stability analysis (domains/pnn/dynamics.rs).

use serde_json::{json, Value};

use crate::error::{EngineError, Result};

fn number(value: &Value, key: &str) -> f64 {
    value.get(key).and_then(Value::as_f64).unwrap_or(0.0)
}

fn optional(value: &Value, key: &str) -> Option<f64> {
    value.get(key).and_then(Value::as_f64)
}

fn text(value: &Value, key: &str) -> String {
    value.get(key).and_then(Value::as_str).unwrap_or("").to_string()
}

fn display(value: Option<f64>, decimals: usize) -> String {
    match value {
        Some(number) => format!("{number:.decimals$}"),
        None => "UNMEASURED".to_string(),
    }
}

fn calc_stats(values: &[f64]) -> (Option<f64>, Option<f64>, Option<f64>) {
    if values.is_empty() { return (None, None, None); }
    let n = values.len() as f64;
    let mean = values.iter().sum::<f64>() / n;
    let variance = values.iter().map(|v| (v - mean).powi(2)).sum::<f64>() / n;
    (Some(mean), Some(variance.sqrt()), Some(values.iter().copied().fold(f64::NEG_INFINITY, f64::max)))
}

pub fn analyze_trajectory(points: &[Value], compound_id: &str, target_id: &str) -> Result<Value> {
    if points.len() < 2 {
        return Err(EngineError::new("Need at least 2 trajectory points to analyze dynamics.",
            "trajectory analysis needs two or more frames", "pass at least two points"));
    }
    let n = points.len();
    let first = number(&points[0], "time_ns");
    let last = number(&points[n - 1], "time_ns");
    let mut total_time = last - first;
    if total_time <= 0.0 { total_time = n as f64; }
    let lig: Vec<f64> = points.iter().map(|p| number(p, "ligand_rmsd")).collect();
    let prot: Vec<f64> = points.iter().filter_map(|p| optional(p, "protein_rmsd")).collect();
    let contacts: Vec<f64> = points.iter().filter_map(|p| optional(p, "contacts_count")).collect();
    let dgs: Vec<f64> = points.iter().filter_map(|p| optional(p, "mmgbsa_dg")).collect();
    let (mean_lig, std_lig, max_lig) = calc_stats(&lig);
    let (mean_prot, std_prot, _) = calc_stats(&prot);
    let (mean_cnt, _, _) = calc_stats(&contacts);
    let min_cnt = contacts.iter().copied().fold(f64::INFINITY, f64::min);
    let min_contacts = if contacts.is_empty() { None } else { Some(min_cnt as i64) };
    let (mean_dg, std_dg, _) = calc_stats(&dgs);
    let window = (n / 5).max(1);
    let first_mean = lig[..window].iter().sum::<f64>() / window as f64;
    let last_mean = lig[n - window..].iter().sum::<f64>() / window as f64;
    let drift = last_mean - first_mean;
    let mut residue_names: Vec<String> = Vec::new();
    for point in points {
        if let Some(map) = point.get("residue_contacts").and_then(Value::as_object) {
            for key in map.keys() {
                if !residue_names.contains(key) { residue_names.push(key.clone()); }
            }
        }
    }
    residue_names.sort();
    let mut persistence = serde_json::Map::new();
    for res in &residue_names {
        let active = points.iter().filter(|p| p.get("residue_contacts")
            .and_then(|m| m.get(res)).and_then(Value::as_bool).unwrap_or(false)).count();
        persistence.insert(res.clone(), Value::from(active as f64 / n as f64 * 100.0));
    }
    let has_contacts = mean_cnt.is_some();
    let (stability_class, rationale, score) = if !has_contacts {
        ("INSUFFICIENT_EVIDENCE",
            "Contact counts were not supplied, so ligand residence in the pocket cannot be assessed. This trajectory does not support a stability verdict.",
            None)
    } else {
        let mean_l = mean_lig.unwrap();
        let std_l = std_lig.unwrap();
        let max_l = max_lig.unwrap();
        let mean_c = mean_cnt.unwrap();
        let (class, reason) = if mean_l < 2.0 && drift < 1.0 && mean_c >= 2.0 && max_l < 3.2 {
            ("STABLE_POSE", "Ligand maintains stable binding geometry in the pocket (RMSD < 2.0 Å, minimal drift, high contact persistence).")
        } else if mean_l <= 3.5 && drift < 2.0 && mean_c >= 1.0 {
            ("MODERATE_MOBILITY", "Ligand exhibits moderate conformational mobility or pocket breathing (RMSD 2.0-3.5 Å) while preserving core contacts.")
        } else {
            ("UNSTABLE_DRIFT", "Ligand exhibits excessive conformational drift or dissociation from the binding pocket (RMSD > 3.5 Å or lost contacts).")
        };
        let mut value = 100.0;
        if mean_l > 1.5 { value -= (mean_l - 1.5) * 20.0; }
        if std_l > 0.4 { value -= (std_l - 0.4) * 15.0; }
        if drift > 0.5 { value -= (drift - 0.5) * 20.0; }
        if mean_c < 3.0 { value -= (3.0 - mean_c) * 10.0; }
        if max_l > 3.0 { value -= (max_l - 3.0) * 10.0; }
        (class, reason, Some(value.max(0.0).min(100.0)))
    };
    let evidence_status = if stability_class == "INSUFFICIENT_EVIDENCE" {
        "INSUFFICIENT_EVIDENCE"
    } else if mean_prot.is_some() && mean_dg.is_some() {
        "COMPLETE"
    } else {
        "PARTIAL"
    };
    Ok(json!({
        "compound_id": compound_id, "target_id": target_id,
        "total_time_ns": total_time, "frames_count": n,
        "mean_ligand_rmsd": mean_lig, "std_ligand_rmsd": std_lig,
        "max_ligand_rmsd": max_lig, "drift_ligand_rmsd": drift,
        "mean_protein_rmsd": mean_prot, "std_protein_rmsd": std_prot,
        "mean_contacts": mean_cnt, "min_contacts": min_contacts,
        "mean_mmgbsa_dg": mean_dg, "std_mmgbsa_dg": std_dg,
        "residue_persistence": Value::Object(persistence),
        "stability_class": stability_class, "stability_score": score,
        "evidence_status": evidence_status, "verdict_rationale": rationale,
    }))
}

fn status(value: Option<f64>, threshold: f64) -> &'static str {
    match value {
        None => "UNMEASURED",
        Some(v) => if v < threshold { "PASS" } else { "FAIL" },
    }
}

pub fn render_trajectory_report(analysis: &Value) -> String {
    let persistence = analysis.get("residue_persistence").and_then(Value::as_object);
    let persistence_table = match persistence {
        Some(map) if !map.is_empty() => {
            let mut rows = Vec::new();
            for (res, pct) in map {
                let p = pct.as_f64().unwrap_or(0.0);
                let assessment = if p >= 75.0 { "Strong Contact" }
                    else if p >= 50.0 { "Moderate Contact" } else { "Transient Contact" };
                rows.push(format!("| {res} | {p:.1}% | {assessment} |"));
            }
            format!("| Binding Pocket Residue | Contact Persistence | Assessment |\n|:---|:---:|:---|\n{}", rows.join("\n"))
        }
        _ => "*No residue-specific contact columns were detected in trajectory input.*".to_string(),
    };
    let mean_lig = optional(analysis, "mean_ligand_rmsd");
    let std_lig = optional(analysis, "std_ligand_rmsd");
    let mean_pro = optional(analysis, "mean_protein_rmsd");
    let mean_cnt = optional(analysis, "mean_contacts");
    let min_cnt = analysis.get("min_contacts").and_then(Value::as_i64);
    let mean_dg = optional(analysis, "mean_mmgbsa_dg");
    let lig_status = status(mean_lig, 2.0);
    let max_status = status(optional(analysis, "max_ligand_rmsd"), 3.2);
    let drift_status = status(optional(analysis, "drift_ligand_rmsd"), 1.0);
    let protein_status = status(mean_pro, 2.5);
    let cnt_status = match mean_cnt {
        None => "UNMEASURED",
        Some(v) => if v >= 2.0 { "PASS" } else { "LOW" },
    };
    let min_cnt_status = match min_cnt {
        None => "UNMEASURED",
        Some(v) => if v >= 1 { "PASS" } else { "UNBOUND" },
    };
    let dg_status = match mean_dg {
        None => "UNMEASURED",
        Some(v) => if v <= -25.0 { "STRONG" } else { "MODERATE" },
    };
    format!(r#"# Molecular Dynamics Trajectory Stability Report: {compound}

- **Target Receptor**: `{target}`
- **Simulation Duration**: `{total:.1} ns` (`{frames}` frames)
- **Evidence Status**: **`{evidence}`**
- **Pose Stability Class**: **`{stability}`**
- **Overall Stability Score**: **`{score}` / 100**

## 1. Key Metric Summary

| Trajectory Parameter | Observed Value | Recommended Threshold | Status |
|:---|:---:|:---:|:---|
| Ligand RMSD (Mean ± Std) | {ml:.2} ± {sl:.2} Å | < 2.0 Å | {lig_status} |
| Maximum Ligand RMSD | {max:.2} Å | < 3.2 Å | {max_status} |
| RMSD Drift (End - Start) | {drift:.2} Å | < 1.0 Å | {drift_status} |
| Protein Backbone RMSD | {protein} Å | < 2.5 Å | {protein_status} |
| Intermolecular Contacts (Mean) | {cnt} contacts | ≥ 2.0 | {cnt_status} |
| Minimum Contact Count | {min} contacts | ≥ 1 | {min_cnt_status} |
| MM-GBSA Binding Free Energy | {dg} kcal/mol | < -25.0 kcal/mol | {dg_status} |

## 2. Pocket Residue Contact Persistence

{persistence_table}

## 3. Structural Stability Assessment

**Verdict Rationale**: {rationale}

> [!NOTE]
> In silico molecular dynamics simulations provide atomistic insights into pose stability and pocket residence time.
> Per guidelines G-001 and G-002, simulated kinetic metrics serve as mechanistic prioritization hypotheses
> and do not replace experimental biophysical validation (Surface Plasmon Resonance / ITC binding kinetics).
> UNMEASURED values were absent from the input trajectory and are never inferred.
"#,
        compound = text(analysis, "compound_id"),
        target = text(analysis, "target_id"),
        total = number(analysis, "total_time_ns"),
        frames = analysis.get("frames_count").and_then(Value::as_u64).unwrap_or(0),
        evidence = text(analysis, "evidence_status"),
        stability = text(analysis, "stability_class"),
        score = display(optional(analysis, "stability_score"), 1),
        ml = mean_lig.unwrap_or(0.0), sl = std_lig.unwrap_or(0.0),
        max = number(analysis, "max_ligand_rmsd"),
        drift = number(analysis, "drift_ligand_rmsd"),
        protein = display(mean_pro, 2), cnt = display(mean_cnt, 1),
        min = match min_cnt { Some(v) => v.to_string(), None => "UNMEASURED".to_string() },
        dg = display(mean_dg, 1),
        persistence_table = persistence_table, rationale = text(analysis, "verdict_rationale"),
    )
}
