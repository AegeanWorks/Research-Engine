//! Phase 3 in vitro assay ingestion and hit qualification (domains/pnn/assay.rs).

use serde_json::{json, Value};

pub const HIT_FIELDS: &[&str] = &["compound_id", "status", "ec50_nm", "max_degradation_pct",
    "pampa_pe", "mdck_efflux", "cc50_um", "selectivity_index", "bbb_status",
    "toxicity_status", "findings"];

fn field(value: &Value, key: &str) -> String {
    value.get(key).and_then(Value::as_str).unwrap_or("").to_string()
}

fn number(value: &Value, key: &str) -> f64 {
    value.get(key).and_then(Value::as_f64).unwrap_or(0.0)
}

fn optional(value: &Value, key: &str) -> Option<f64> {
    value.get(key).and_then(Value::as_f64)
}

fn text(value: Option<f64>, decimals: usize, missing: &str) -> String {
    match value {
        Some(number) => format!("{number:.decimals$}"),
        None => missing.to_string(),
    }
}

pub struct AssayCriteria {
    pub ec50_ceiling_nm: f64,
    pub max_deg_floor_pct: f64,
    pub pampa_pe_floor: f64,
    pub mdck_efflux_ceiling: f64,
    pub min_selectivity_index: f64,
}

pub fn qualify_leads(degradation: &Value, permeability: Option<&Value>,
                     cytotoxicity: Option<&Value>, criteria: &AssayCriteria) -> Vec<Value> {
    let mut hits = Vec::new();
    let empty = Value::Object(serde_json::Map::new());
    let perm_map = permeability.unwrap_or(&empty);
    let cyto_map = cytotoxicity.unwrap_or(&empty);
    if let Some(degradation) = degradation.as_object() {
        for (cid, deg) in degradation {
            let is_active = number(deg, "ec50_nm") <= criteria.ec50_ceiling_nm
                && number(deg, "max_degradation_pct") >= criteria.max_deg_floor_pct;
            let perm = perm_map.get(cid);
            let pampa_pe = perm.and_then(|p| optional(p, "pe_1e6_cm_s"));
            let mdck_efflux = perm.and_then(|p| optional(p, "efflux_ratio"));
            let (bbb_pass, bbb_status) = match perm {
                None => (false, "UNTESTED"),
                Some(p) => {
                    if pampa_pe.map(|v| v >= criteria.pampa_pe_floor).unwrap_or(false) {
                        (true, "PERMEANT_PAMPA")
                    } else if mdck_efflux.map(|v| v < criteria.mdck_efflux_ceiling).unwrap_or(false) {
                        (true, "PERMEANT_MDCK")
                    } else if optional(p, "logbb").map(|v| v >= -1.0).unwrap_or(false) {
                        (true, "PERMEANT_LOGBB")
                    } else if mdck_efflux.map(|v| v >= criteria.mdck_efflux_ceiling).unwrap_or(false) {
                        (false, "HIGH_EFFLUX")
                    } else {
                        (false, "LOW_PERMEABILITY")
                    }
                }
            };
            let cyto = cyto_map.get(cid);
            let cc50 = cyto.and_then(|c| optional(c, "cc50_um"));
            let si = cc50.map(|c| c * 1000.0 / number(deg, "ec50_nm"));
            let (is_toxic, tox_status) = match cc50 {
                None => (false, "UNTESTED"),
                Some(c) => {
                    let margin = si.unwrap();
                    if c < 20.0 || margin < 10.0 {
                        (true, "CYTOTOXIC")
                    } else if c >= 50.0 || margin >= criteria.min_selectivity_index {
                        (false, "NON_TOXIC")
                    } else {
                        (false, "MODERATE_SAFETY")
                    }
                }
            };
            let mut findings = Vec::new();
            let status = if is_toxic {
                findings.push(format!("Cell viability compromised (CC50={:.1} uM, SI={:.1})",
                    cc50.unwrap(), si.unwrap()));
                "CYTOTOXIC"
            } else if !is_active {
                if number(deg, "ec50_nm") > 50000.0 || number(deg, "max_degradation_pct") < 10.0 {
                    findings.push(format!("Insufficient PNN softening (EC50={:.0} nM, Max={:.1}%)",
                        number(deg, "ec50_nm"), number(deg, "max_degradation_pct")));
                    "INACTIVE"
                } else {
                    findings.push(format!("Sub-threshold softening activity (EC50={:.0} nM)",
                        number(deg, "ec50_nm")));
                    "INCONCLUSIVE"
                }
            } else {
                findings.push(format!("Confirmed PNN softening (EC50={:.1} nM, Max={:.1}%)",
                    number(deg, "ec50_nm"), number(deg, "max_degradation_pct")));
                if bbb_pass && tox_status == "NON_TOXIC" {
                    findings.push(format!("Excellent permeability ({bbb_status}) and safety (SI={:.1})", si.unwrap_or(0.0)));
                    "CONFIRMED_HIT"
                } else if bbb_pass {
                    findings.push(format!("Permeant ({bbb_status}); toxicity status: {tox_status}"));
                    "QUALIFIED_LEAD"
                } else if bbb_status == "UNTESTED" {
                    findings.push("Softening confirmed; pending measured permeability".to_string());
                    "QUALIFIED_LEAD"
                } else {
                    findings.push(format!("Restricted BBB penetration ({bbb_status})"));
                    "INCONCLUSIVE"
                }
            };
            hits.push(json!({
                "compound_id": cid,
                "status": status,
                "ec50_nm": number(deg, "ec50_nm"),
                "max_degradation_pct": number(deg, "max_degradation_pct"),
                "pampa_pe": pampa_pe,
                "mdck_efflux": mdck_efflux,
                "cc50_um": cc50,
                "selectivity_index": si,
                "bbb_status": bbb_status,
                "toxicity_status": tox_status,
                "findings": findings.join("; "),
            }));
        }
    }
    let priority = |status: &str| match status {
        "CONFIRMED_HIT" => 0, "QUALIFIED_LEAD" => 1, "INCONCLUSIVE" => 2,
        "INACTIVE" => 3, "CYTOTOXIC" => 4, _ => 9,
    };
    hits.sort_by(|a, b| {
        let pa = priority(&field(a, "status"));
        let pb = priority(&field(b, "status"));
        let ord = pa.cmp(&pb);
        if ord != std::cmp::Ordering::Equal { return ord; }
        let ord = number(a, "ec50_nm").partial_cmp(&number(b, "ec50_nm"))
            .unwrap_or(std::cmp::Ordering::Equal);
        if ord != std::cmp::Ordering::Equal { return ord; }
        number(b, "max_degradation_pct").partial_cmp(&number(a, "max_degradation_pct"))
            .unwrap_or(std::cmp::Ordering::Equal)
    });
    hits
}

pub fn as_row(hit: &Value) -> Value {
    json!({
        "compound_id": field(hit, "compound_id"),
        "status": field(hit, "status"),
        "ec50_nm": format!("{:.1}", number(hit, "ec50_nm")),
        "max_degradation_pct": format!("{:.1}", number(hit, "max_degradation_pct")),
        "pampa_pe": text(optional(hit, "pampa_pe"), 2, ""),
        "mdck_efflux": text(optional(hit, "mdck_efflux"), 2, ""),
        "cc50_um": text(optional(hit, "cc50_um"), 1, ""),
        "selectivity_index": text(optional(hit, "selectivity_index"), 1, ""),
        "bbb_status": field(hit, "bbb_status"),
        "toxicity_status": field(hit, "toxicity_status"),
        "findings": field(hit, "findings"),
    })
}

fn py_number(value: f64) -> String {
    let text = value.to_string();
    if text.contains('.') || text.contains('e') || text.contains('E') { text } else { format!("{text}.0") }
}

pub fn render_assay_report(hits: &[Value], criteria: &AssayCriteria) -> String {
    let confirmed = hits.iter().filter(|h| field(h, "status") == "CONFIRMED_HIT").count();
    let qualified = hits.iter().filter(|h| field(h, "status") == "QUALIFIED_LEAD").count();
    let toxic = hits.iter().filter(|h| field(h, "status") == "CYTOTOXIC").count();
    let inactive = hits.iter().filter(|h| field(h, "status") == "INACTIVE").count();
    let mut lines = vec![
        "# PNN Phase 3 In Vitro Hit Qualification Report".to_string(),
        String::new(),
        "## Scientific Context & Evidence Invariants".to_string(),
        String::new(),
        "> [!IMPORTANT]".to_string(),
        "> **Guideline G-001 (ADR-001)**: In vitro assay qualification confirms target degradation activity, membrane permeability, and safety windows in cell models. Never claim in vivo hypothalamic efficacy or therapeutic obesity reversal without pharmacokinetic brain-exposure and chronic DIO mouse study data.".to_string(),
        String::new(),
        "## Qualification Summary".to_string(),
        String::new(),
        format!("- **Total Compounds Evaluated**: {}", hits.len()),
        format!("- **Confirmed Hits (Active + Permeant + Non-toxic)**: {confirmed}"),
        format!("- **Qualified Leads (Active, pending complete safety/permeability)**: {qualified}"),
        format!("- **Cytotoxic / Counter-Screen Failures**: {toxic}"),
        format!("- **Inactive / Sub-threshold**: {inactive}"),
        String::new(),
        "## Progression Thresholds".to_string(),
        String::new(),
        format!("- **PNN Degradation**: EC50 <= {} nM and Max Cleavage >= {}%",
            py_number(criteria.ec50_ceiling_nm), py_number(criteria.max_deg_floor_pct)),
        format!("- **BBB Permeability**: PAMPA Pe >= {} x 10^-6 cm/s or MDCK Efflux Ratio < {}",
            py_number(criteria.pampa_pe_floor), py_number(criteria.mdck_efflux_ceiling)),
        format!("- **Safety Window**: CC50 >= 50 uM or Selectivity Index (CC50/EC50) >= {}",
            py_number(criteria.min_selectivity_index)),
        String::new(),
        "## Confirmed In Vitro Hits".to_string(),
        String::new(),
        "| Compound ID | EC50 (nM) | Max Deg (%) | PAMPA Pe | MDCK Efflux | CC50 (uM) | Selectivity Index | Status | Findings |".to_string(),
        "|---|---|---|---|---|---|---|---|---|".to_string(),
    ];
    for hit in hits.iter().filter(|h| matches!(field(h, "status").as_str(), "CONFIRMED_HIT" | "QUALIFIED_LEAD")) {
        lines.push(format!("| `{}` | {:.1} | {:.1}% | {} | {} | {} | {} | **{}** | {} |",
            field(hit, "compound_id"), number(hit, "ec50_nm"), number(hit, "max_degradation_pct"),
            text(optional(hit, "pampa_pe"), 2, "-"), text(optional(hit, "mdck_efflux"), 2, "-"),
            text(optional(hit, "cc50_um"), 1, "-"), text(optional(hit, "selectivity_index"), 1, "-"),
            field(hit, "status"), field(hit, "findings")));
    }
    lines.extend([
        String::new(),
        "## Recommended Next Steps (Phase 4 In Vivo Proof-of-Concept)".to_string(),
        String::new(),
        "1. **Primary ARC Neuron Target Engagement**: Evaluate top confirmed hits for pIR-Y1161 and pAKT-S473 restoration in primary mouse hypothalamic ARC neurons.".to_string(),
        "2. **Single-Dose Pharmacokinetics**: Determine oral bioavailability (F), brain/plasma AUC ratio, and clearance in C57BL/6J mice.".to_string(),
        "3. **Chronic DIO Proof-of-Concept**: Administer oral active leads for 14-28 days in diet-induced obese mice; measure body weight, food intake, and WFA-positive net degradation in the arcuate nucleus.".to_string(),
        String::new(),
    ]);
    lines.join("\n")
}
