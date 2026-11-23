//! Batch analysis across a research program (engine/analysis.py::batch_statistics).

use rusqlite::params;

use serde_json::{json, Value};

use crate::analysis;
use crate::core;
use crate::error::Result;

const MAX_SAFE_CLAIMS: usize = 3;

pub fn batch_statistics(conn: &rusqlite::Connection, research_ref: &str, baseline: &str,
                        treatment: &str, seed: i64, resamples: usize,
                        allow_incomparable: bool, allow_self_reported: bool,
                        actor: &str, since: &str, until: &str,
                        holm: bool) -> Result<Value> {
    let research = core::get_research(conn, research_ref)?;
    let research_id = research.get("id").and_then(Value::as_str).unwrap_or("");
    let (since_norm, until_norm) = analysis::bounds(since, until)?;

    let mut stmt = conn.prepare(
        "SELECT id FROM claim WHERE research_id = ?1 AND superseded_by IS NULL ORDER BY id")?;
    let claim_ids: Vec<String> = stmt.query_map(params![research_id], |row| row.get(0))?
        .collect::<std::result::Result<Vec<_>, _>>()?;
    drop(stmt);

    let mut results = serde_json::Map::new();
    let mut errors = serde_json::Map::new();
    for claim_id in &claim_ids {
        match analysis::claim_statistics(conn, claim_id, baseline, treatment, seed,
            resamples, allow_incomparable, allow_self_reported, actor, "", since, until) {
            Ok(value) => { results.insert(claim_id.clone(), value); }
            Err(error) => {
                errors.insert(claim_id.clone(), json!({
                    "error": error.what, "fix": error.fix, "why": error.why,
                }));
            }
        }
    }
    let compared = results.len() + errors.len();
    let mut warnings = Vec::new();
    if compared > MAX_SAFE_CLAIMS {
        warnings.push(format!(
            "Multiple Comparison Risk: you compared {compared} claims with one \
             baseline/treatment pair. This increases the risk of false positives \
             (Type I error)."));
    }
    let holm_table = if holm && results.len() >= 2 {
        let ordered: Vec<&String> = {
            let mut keys: Vec<&String> = results.keys().collect();
            keys.sort();
            keys
        };
        let welch_ps: Vec<f64> = ordered.iter().map(|cid| {
            results[*cid]["welch"]["p"].as_f64().unwrap_or(1.0)
        }).collect();
        let rank_ps: Vec<f64> = ordered.iter().map(|cid| {
            results[*cid]["mann_whitney"]["p"].as_f64().unwrap_or(1.0)
        }).collect();
        let build = |ps: &[f64]| -> Vec<Value> {
            let adjusted = crate::stats::holm_adjust(ps);
            adjusted.iter().enumerate().map(|(i, row)| json!({
                "claim": ordered[i].clone(),
                "p": row["p"],
                "holm_p": row["holm_p"],
                "reject": row["reject"],
            })).collect()
        };
        Some(json!({
            "claims": ordered,
            "alpha": 0.05,
            "welch": build(&welch_ps),
            "mann_whitney": build(&rank_ps),
        }))
    } else {
        None
    };
    Ok(json!({
        "research": research_id,
        "baseline": baseline.trim().to_lowercase(),
        "treatment": treatment.trim().to_lowercase(),
        "window": { "since": since_norm, "until": until_norm },
        "results": Value::Object(results),
        "errors": Value::Object(errors),
        "global_warnings": warnings,
        "holm": holm_table,
    }))
}
