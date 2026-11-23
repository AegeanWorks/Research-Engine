//! End-to-end Phase 2 lead selection (domains/pnn/selection.py).

use std::collections::BTreeMap;

use serde_json::{json, Value};
use sha2::{Digest, Sha256};

use crate::domains_pnn_compounds as compounds;
use crate::domains_pnn_curation as curation;
use crate::domains_pnn_docking as docking;
use crate::domains_pnn_rank as rank;
use crate::domains_pnn_screen as screen;
use crate::error::{EngineError, Result};

pub const SCHEMA: &str = "pnn.phase2.pipeline/1";
pub const LIMITS: &[&str] = &[
    "Tier labels and consensus scores are prioritisation signals, not measured permeability, binding or PNN softening.",
    "Consensus normalization depends on the docked set; compare runs only with a fixed set.",
    "Exact-SMILES curation is not chemical canonicalization.",
];

/// Minimal CSV reader handling quoted fields and CRLF/LF terminators.
pub fn parse_csv(text: &str) -> Result<Vec<BTreeMap<String, String>>> {
    let text = text.strip_prefix('\u{feff}').unwrap_or(text);
    let mut records: Vec<Vec<String>> = Vec::new();
    let mut field = String::new();
    let mut row: Vec<String> = Vec::new();
    let mut quoted = false;
    let chars: Vec<char> = text.chars().collect();
    let mut i = 0usize;
    while i < chars.len() {
        let c = chars[i];
        if quoted {
            if c == '"' {
                if i + 1 < chars.len() && chars[i + 1] == '"' {
                    field.push('"');
                    i += 1;
                } else {
                    quoted = false;
                }
            } else {
                field.push(c);
            }
        } else {
            match c {
                '"' => quoted = true,
                ',' => { row.push(std::mem::take(&mut field)); }
                '\n' => {
                    if field.ends_with('\r') { field.pop(); }
                    row.push(std::mem::take(&mut field));
                    if !(row.len() == 1 && row[0].is_empty()) { records.push(std::mem::take(&mut row)); }
                }
                _ => field.push(c),
            }
        }
        i += 1;
    }
    if !field.is_empty() || !row.is_empty() {
        if field.ends_with('\r') { field.pop(); }
        row.push(field);
        records.push(row);
    }
    if records.is_empty() {
        return Err(EngineError::new("CSV has no header row", "a compound CSV needs a header", "pass a CSV with columns"));
    }
    let header = &records[0];
    let mut rows = Vec::new();
    for record in records.iter().skip(1) {
        let mut map = BTreeMap::new();
        for (index, key) in header.iter().enumerate() {
            map.insert(key.clone(), record.get(index).cloned().unwrap_or_default());
        }
        rows.push(map);
    }
    Ok(rows)
}

pub fn digest_bytes(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}

fn field(value: &Value, key: &str) -> String {
    value.get(key).and_then(Value::as_str).unwrap_or("").to_string()
}

fn count(value: &Value, key: &str) -> u64 {
    value.get(key).and_then(Value::as_u64).unwrap_or(0)
}

fn optional_display(value: &Value) -> String {
    if value.is_null() { "None".to_string() } else { value.to_string() }
}

fn text_f64(value: Option<&Value>, decimals: usize, missing: &str) -> String {
    match value.and_then(Value::as_f64) {
        Some(number) => format!("{number:.decimals$}"),
        None => missing.to_string(),
    }
}

pub struct SelectionOptions<'a> {
    pub min_tier: &'a str,
    pub per_bin: usize,
    pub bin_width: f64,
    pub max_compounds: Option<usize>,
    pub max_rmsd: Option<f64>,
    pub min_vina: Option<f64>,
}

/// Curate, screen and rank one lead set from compound and docking CSV text.
pub fn select_leads(inputs: &[(String, String)], docking_text: &(String, String),
                    options: &SelectionOptions) -> Result<Value> {
    if inputs.is_empty() {
        return Err(EngineError::new("no input compound CSV was supplied",
            "lead selection needs at least one compound library", "pass one or more input CSVs"));
    }
    let mut loaded: Vec<(String, Vec<Value>)> = Vec::new();
    let mut input_meta = Vec::new();
    for (source, text) in inputs {
        let rows = parse_csv(text)?;
        let compounds = compounds::parse_compounds(&rows, source, true)?;
        input_meta.push(json!({"path": source, "sha256": digest_bytes(text.as_bytes()), "rows": compounds.len()}));
        loaded.push((source.clone(), compounds));
    }
    let candidates = curation::prepare_candidates(&loaded)?;
    let deduped = curation::deduplicate(&candidates)?;
    let unique = deduped["candidates"].as_array().unwrap();
    let curated = curation::curate(unique, options.min_tier, options.per_bin,
        options.bin_width, options.max_compounds)?;
    let selected = curated["candidates"].as_array().unwrap();
    if selected.is_empty() {
        return Err(EngineError::new("no compound survived curation; every input row was rejected or the input set was empty",
            "curation removed all candidates", "add better-characterized compounds or relax --min-tier"));
    }
    let mut screened: Vec<Value> = selected.iter()
        .map(|c| c.get("result").cloned().unwrap_or(Value::Null)).collect();
    screened.sort_by(|a, b| {
        let rank_a = match field(a, "tier").as_str() { "A" => 0, "B" => 1, "C" => 2, _ => 3 };
        let rank_b = match field(b, "tier").as_str() { "A" => 0, "B" => 1, "C" => 2, _ => 3 };
        let sa = a.get("score").and_then(Value::as_f64).unwrap_or(0.0);
        let sb = b.get("score").and_then(Value::as_f64).unwrap_or(0.0);
        let ta = field(a.get("compound").unwrap_or(&Value::Null), "compound_id");
        let tb = field(b.get("compound").unwrap_or(&Value::Null), "compound_id");
        let ord = rank_a.cmp(&rank_b);
        if ord != std::cmp::Ordering::Equal { return ord; }
        let ord = sb.partial_cmp(&sa).unwrap_or(std::cmp::Ordering::Equal);
        if ord != std::cmp::Ordering::Equal { return ord; }
        ta.cmp(&tb)
    });
    let docking_rows = parse_csv(&docking_text.1)?;
    let scores = docking::parse_rows(&docking_rows, "input")?;
    let mut screen_table = BTreeMap::new();
    for result in &screened {
        let compound = result.get("compound").unwrap_or(&Value::Null);
        screen_table.insert(field(compound, "compound_id"), json!({
            "tier": field(result, "tier"),
            "score": format!("{:.4}", result.get("score").and_then(Value::as_f64).unwrap_or(0.0)),
            "name": field(compound, "name"),
            "smiles": field(compound, "smiles"),
        }));
    }
    let ranking = rank::build_shortlist(&scores, Some(&screen_table), options.min_tier,
        options.max_rmsd, options.min_vina)?;
    let shortlist = ranking.get("rows").and_then(Value::as_array).unwrap();
    if shortlist.is_empty() {
        return Err(EngineError::new("no compound survived docking and screening filters; supply Vina-scored docking rows for curated compounds or relax the filters",
            "the shortlist is empty", "relax --max-rmsd or --min-vina"));
    }
    let mut curation_summary = deduped["stats"].as_object().unwrap().clone();
    if let Some(map) = curated["summary"].as_object() { curation_summary.extend(map.clone()); }
    curation_summary.insert("input_rows".into(), Value::from(candidates.len()));
    let screening_summary = screen::summarize(&screened);
    Ok(json!({
        "inputs": input_meta,
        "docking": {"path": docking_text.0, "sha256": digest_bytes(docking_text.1.as_bytes()), "rows": scores.len()},
        "curation": Value::Object(curation_summary),
        "screening": {
            "total": screening_summary["total"].as_u64().unwrap_or(0),
            "by_tier": screening_summary["by_tier"].clone(),
            "average_score": screening_summary["average_score"].clone(),
            "emitted": screened.len(),
        },
        "ranking": ranking,
        "curated": selected.clone(),
        "screened": screened,
    }))
}

pub fn options_json(options: &SelectionOptions) -> Value {
    json!({
        "min_tier": options.min_tier,
        "per_bin": options.per_bin,
        "bin_width": options.bin_width,
        "max_compounds": options.max_compounds,
        "max_rmsd": options.max_rmsd,
        "min_vina": options.min_vina,
    })
}

/// Render the Markdown lead report from a selection payload.
pub fn render_lead_report(selection: &Value, options: &Value, top_n: usize) -> String {
    let inputs = selection["inputs"].as_array().unwrap();
    let docking = &selection["docking"];
    let curation = &selection["curation"];
    let screening = &selection["screening"];
    let ranking = &selection["ranking"];
    let shortlist = ranking["rows"].as_array().unwrap();
    let mut lines = vec![
        "# PNN Phase 2 Lead Selection Report".to_string(),
        String::new(),
        "## Scientific Context & Triage Limits".to_string(),
        String::new(),
        "> [!IMPORTANT]".to_string(),
        "> **Project Guidelines & Evidence Limits (G-001, G-002, G-003)**:".to_string(),
        "> 1. **G-001 (ADR-001)**: Screening tiers (A, B, C) are triage signals only; never report a compound as BBB-penetrant or efficacious without measured permeability and PNN-softening data.".to_string(),
        "> 2. **G-002 (ADR-002)**: Docking consensus scores are relative to the docked candidate set and never substitute for measured binding, PNN-softening or permeability data.".to_string(),
        "> 3. **G-003 (ADR-003)**: Curated libraries retain input source provenance; exact-SMILES deduplication is not chemical canonicalization.".to_string(),
        String::new(),
        "## Input Provenance".to_string(),
        String::new(),
        "### Compound Sources".to_string(),
        String::new(),
        "| Source Path | Rows | SHA-256 Digest |".to_string(),
        "|---|---|---|".to_string(),
    ];
    for input in inputs {
        lines.push(format!("| `{}` | {} | `{}` |", field(input, "path"),
            count(input, "rows"), field(input, "sha256")));
    }
    lines.extend([
        String::new(), "### Docking Source".to_string(), String::new(),
        format!("- **Path**: `{}`", field(docking, "path")),
        format!("- **Docking Rows**: {}", count(docking, "rows")),
        format!("- **SHA-256**: `{}`", field(docking, "sha256")),
        String::new(), "## Stage Summaries".to_string(), String::new(),
        "### 1. Library Curation & Diversity".to_string(), String::new(),
        format!("- **Input Rows**: {}", count(curation, "input_rows")),
        format!("- **Duplicate IDs Resolved**: {}", count(curation, "duplicate_ids")),
        format!("- **Duplicate SMILES Resolved**: {}", count(curation, "duplicate_smiles")),
        format!("- **Retained by Tier Floor ({} or better)**: {} (removed {})",
            field(options, "min_tier"), count(curation, "eligible"), count(curation, "skipped_by_tier")),
        format!("- **Surviving Bin Caps ({}/bin)**: {} (removed {})",
            count(options, "per_bin"), count(curation, "selected"),
            count(curation, "eligible").saturating_sub(count(curation, "selected"))),
    ]);
    if curation.get("truncated_by_max").and_then(Value::as_bool).unwrap_or(false) {
        lines.push(format!("- **Truncated by Global Cap**: True (capped at {})", optional_display(options.get("max_compounds").unwrap_or(&Value::Null))));
    }
    let by_tier = screening.get("by_tier").unwrap_or(&Value::Null);
    lines.extend([
        String::new(), "### 2. CNS/BBB Property Screening".to_string(), String::new(),
        format!("- **Eligible Candidates Screened**: {}", count(screening, "emitted")),
        format!("- **Tier A**: {}", count(by_tier, "A")),
        format!("- **Tier B**: {}", count(by_tier, "B")),
        format!("- **Tier C**: {}", count(by_tier, "C")),
        format!("- **Reject**: {}", count(by_tier, "Reject")),
        String::new(), "### 3. Docking Consensus Ranking".to_string(), String::new(),
        format!("- **Docked Rows Ingested**: {}", count(docking, "rows")),
        format!("- **Shortlist Compounds Emitted**: {}", shortlist.len()),
        format!("- **Full Engine Coverage (Vina + Glide + MM-GBSA)**: {}", count(ranking, "full_coverage")),
        format!("- **Partial Engine Coverage**: {}", count(ranking, "partial_coverage")),
        format!("- **Skipped by Tier Filter**: {}", count(ranking, "skipped_by_tier")),
        format!("- **Filtered by RMSD Threshold**: {}", count(ranking, "filtered_by_rmsd")),
        format!("- **Filtered by Minimum Vina Affinity**: {}", count(ranking, "filtered_by_vina")),
        String::new(),
        format!("## Top Shortlisted Leads (Top {})", shortlist.len().min(top_n)),
        String::new(),
        "| Rank | Compound ID | Name | Tier | Property Score | Best Target | Consensus | Coverage | Vina (kcal/mol) | Glide | MM-GBSA (kcal/mol) | RMSD (A) |".to_string(),
        "|---|---|---|---|---|---|---|---|---|---|---|---|".to_string(),
    ]);
    for row in shortlist.iter().take(top_n) {
        let name = field(row, "name");
        let glide = text_f64(row.get("glide_score"), 2, "-");
        let mmgbsa = text_f64(row.get("mmgbsa_dg"), 2, "-");
        let rmsd = text_f64(row.get("rmsd"), 2, "-");
        lines.push(format!("| {} | `{}` | {} | {} | {} | {} | {:.4} | {:.2} | {:.2} | {} | {} | {} |",
            count(row, "rank"), field(row, "compound_id"), if name.is_empty() { "-".to_string() } else { name },
            field(row, "tier"), field(row, "property_score"), field(row, "target"),
            row.get("consensus").and_then(Value::as_f64).unwrap_or(0.0),
            row.get("coverage").and_then(Value::as_f64).unwrap_or(0.0),
            row.get("vina_affinity").and_then(Value::as_f64).unwrap_or(0.0),
            glide, mmgbsa, rmsd));
    }
    lines.extend([
        String::new(),
        "## Evidence Gaps & Recommended Experimental Progression".to_string(),
        String::new(),
        "1. **Physicochemical vs. Measured Permeability**: All tier allocations stem from in silico physicochemical limits (MW 200-450, logP 1.5-3.5, TPSA < 70 A2). High-priority leads require in vitro PAMPA-BBB and MDCK-MDR1 validation.".to_string(),
        "2. **Target Engagement**: Consensus docking prioritises poses against PTPsigma, LAR, or NgR1. Direct biophysical binding (SPR/ITC) must confirm dissociation constants (Kd).".to_string(),
        "3. **Functional Efficacy**: Verified binders must proceed to primary neuronal/glial cultures for WFA-positive perineuronal net digestion quantification.".to_string(),
        String::new(),
    ]);
    lines.join("\n")
}
