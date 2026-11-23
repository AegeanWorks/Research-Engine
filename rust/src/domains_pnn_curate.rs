//! Command-line merge and diversity curation of PNN compound libraries
//! (domains/pnn/curate.py).

use std::collections::BTreeMap;
use std::path::Path;

use serde_json::{json, Value};

use crate::domains_pnn_compounds as compounds;
use crate::domains_pnn_curation as curation;
use crate::domains_pnn_reports as reports;
use crate::domains_pnn_tables as tables;
use crate::error::{EngineError, Result};

pub struct CurateOptions<'a> {
    pub out_path: &'a str,
    pub json_path: Option<&'a str>,
    pub min_tier: &'a str,
    pub per_bin: usize,
    pub bin_width: f64,
    pub max_compounds: Option<usize>,
}

/// Merge, deduplicate, curate and write the curated library and optional summary.
pub fn run_curation(inputs: &[(String, Vec<BTreeMap<String, String>>)],
                    options: &CurateOptions) -> Result<Value> {
    let mut parsed_inputs: Vec<(String, Vec<Value>)> = Vec::new();
    for (source, rows) in inputs {
        let records = compounds::parse_compounds(rows, source, true)?;
        parsed_inputs.push((source.clone(), records));
    }
    let candidates = curation::prepare_candidates(&parsed_inputs)?;
    let deduped = curation::deduplicate(&candidates)?;
    let unique = deduped.get("candidates").and_then(Value::as_array).unwrap();
    let counts = deduped.get("stats").cloned().unwrap_or(json!({}));
    let curated = curation::curate(unique, options.min_tier, options.per_bin,
        options.bin_width, options.max_compounds)?;
    let summary = curated.get("summary").cloned().unwrap_or(json!({}));
    let selected = curated.get("candidates").and_then(Value::as_array).unwrap();
    if selected.is_empty() {
        return Err(EngineError::new("no compounds survived curation.",
            "every input compound was rejected by the tier floor or the input set was empty.",
            "add better-characterized compounds or relax --min-tier."));
    }
    let mut rows = Vec::new();
    for candidate in selected {
        rows.push(tables::curated_row(candidate, options.bin_width)?);
    }
    let fields: Vec<String> = tables::CURATED_FIELDS.iter().map(|s| s.to_string()).collect();
    reports::write_csv(Path::new(options.out_path), &fields, &rows)?;
    let mut input_counts = serde_json::Map::new();
    for (source, records) in &parsed_inputs {
        input_counts.insert(source.clone(), Value::from(records.len()));
    }
    let report = json!({
        "output": options.out_path,
        "inputs": Value::Object(input_counts),
        "input_rows": candidates.len(),
        "duplicate_ids": counts.get("duplicate_ids").cloned().unwrap_or(Value::Null),
        "duplicate_smiles": counts.get("duplicate_smiles").cloned().unwrap_or(Value::Null),
        "eligible": summary.get("eligible").cloned().unwrap_or(Value::Null),
        "skipped_by_tier": summary.get("skipped_by_tier").cloned().unwrap_or(Value::Null),
        "bins": summary.get("bins").cloned().unwrap_or(Value::Null),
        "per_bin": summary.get("per_bin").cloned().unwrap_or(Value::Null),
        "bin_width": summary.get("bin_width").cloned().unwrap_or(Value::Null),
        "max_compounds": summary.get("max_compounds").cloned().unwrap_or(Value::Null),
        "selected": summary.get("selected").cloned().unwrap_or(Value::Null),
        "truncated_by_max": summary.get("truncated_by_max").cloned().unwrap_or(Value::Null),
    });
    if let Some(path) = options.json_path {
        reports::write_json(Path::new(path), &report)?;
    }
    Ok(json!({"report": report, "rows": rows, "input_rows": candidates.len()}))
}
