//! Command-line consensus ranking of docking results (domains/pnn/rank.py).

use std::collections::BTreeMap;

use serde_json::{json, Value};

use crate::domains_pnn_docking as docking;
use crate::error::{EngineError, Result};

pub const RANK_FIELDS: &[&str] = &["rank", "compound_id", "name", "smiles", "tier",
    "property_score", "target", "consensus_score", "coverage", "vina_affinity",
    "glide_score", "mmgbsa_dg", "rmsd", "hbond_count", "key_interactions", "targets_docked"];
const TIER_CEILING: &[(&str, usize)] = &[("A", 0), ("B", 1), ("C", 2)];

fn field(value: &Value, key: &str) -> String {
    value.get(key).and_then(Value::as_str).unwrap_or("").to_string()
}

fn number_or(value: &Value, key: &str, default: f64) -> f64 {
    value.get(key).and_then(Value::as_f64).unwrap_or(default)
}

fn optional_number(value: &Value, key: &str) -> Value {
    value.get(key).cloned().unwrap_or(Value::Null)
}

fn tier_rank(tier: &str) -> Option<usize> {
    TIER_CEILING.iter().find(|(name, _)| *name == tier).map(|(_, rank)| *rank)
}

fn property_score(info: Option<&Value>) -> f64 {
    let raw = info.and_then(|i| i.get("score")).and_then(Value::as_str).unwrap_or("");
    raw.parse::<f64>().unwrap_or(-1.0)
}

/// Filter aggregated compounds by screening evidence and sort by consensus.
fn selected(best: &BTreeMap<String, Value>, screen: Option<&BTreeMap<String, Value>>,
            min_tier: &str) -> Result<(Vec<(Value, Option<Value>)>, usize, usize)> {
    let ceiling = tier_rank(min_tier).ok_or_else(|| EngineError::new(
        format!("unknown screening tier: {min_tier}"), "tiers are A, B or C", "pass A, B or C"))?;
    let mut rows = Vec::new();
    let mut skipped_tier = 0usize;
    let mut skipped_unlisted = 0usize;
    for (compound_id, rank) in best {
        let info = screen.and_then(|s| s.get(compound_id));
        if screen.is_some() {
            match info {
                None => { skipped_unlisted += 1; continue; }
                Some(value) => {
                    let tier = field(value, "tier");
                    let value = match tier_rank(&tier) {
                        Some(r) => r,
                        None => usize::MAX,
                    };
                    if value == usize::MAX || value > ceiling {
                        skipped_tier += 1;
                        continue;
                    }
                }
            }
        }
        rows.push((rank.clone(), info.cloned()));
    }
    rows.sort_by(|a, b| {
        let (ra, ia) = a;
        let (rb, ib) = b;
        let ba = ra.get("best").unwrap_or(&Value::Null);
        let bb = rb.get("best").unwrap_or(&Value::Null);
        let ca = number_or(ba, "consensus", 0.0);
        let cb = number_or(bb, "consensus", 0.0);
        let cov_a = number_or(ba, "coverage", 0.0);
        let cov_b = number_or(bb, "coverage", 0.0);
        let pa = property_score(ia.as_ref());
        let pb = property_score(ib.as_ref());
        let key_a = (-ca, -cov_a, -pa, field(ra, "compound_id"));
        let key_b = (-cb, -cov_b, -pb, field(rb, "compound_id"));
        let ord = key_a.0.partial_cmp(&key_b.0).unwrap_or(std::cmp::Ordering::Equal);
        if ord != std::cmp::Ordering::Equal { return ord; }
        let ord = key_a.1.partial_cmp(&key_b.1).unwrap_or(std::cmp::Ordering::Equal);
        if ord != std::cmp::Ordering::Equal { return ord; }
        let ord = key_a.2.partial_cmp(&key_b.2).unwrap_or(std::cmp::Ordering::Equal);
        if ord != std::cmp::Ordering::Equal { return ord; }
        key_a.3.cmp(&key_b.3)
    });
    Ok((rows, skipped_tier, skipped_unlisted))
}

pub fn build_shortlist(scores: &[Value], screen: Option<&BTreeMap<String, Value>>,
                       min_tier: &str, max_rmsd: Option<f64>,
                       min_vina: Option<f64>) -> Result<Value> {
    if screen.is_some() && tier_rank(min_tier).is_none() {
        return Err(EngineError::new(format!("unknown screening tier: {min_tier}"),
            "tiers are A, B or C", "pass A, B or C"));
    }
    let (kept, dropped) = docking::filter_scores(scores, max_rmsd, min_vina);
    let ranks = docking::normalize_scores(&kept);
    let best = docking::aggregate_best(&ranks);
    let (picked, skipped_tier, skipped_unlisted) = selected(&best, screen, min_tier)?;
    let mut rows = Vec::new();
    for (index, (rank, info)) in picked.iter().enumerate() {
        let compound = rank.get("best").and_then(|b| b.get("score")).unwrap_or(&Value::Null);
        let get = |key: &str| info.as_ref().and_then(|i| i.get(key)).and_then(Value::as_str).unwrap_or("").to_string();
        let consensus = rank.get("best").and_then(|b| b.get("consensus")).and_then(Value::as_f64).unwrap_or(0.0);
        let coverage = rank.get("best").and_then(|b| b.get("coverage")).and_then(Value::as_f64).unwrap_or(0.0);
        let vina = compound.get("vina_affinity").and_then(Value::as_f64).unwrap_or(0.0);
        rows.push(json!({
            "rank": index + 1,
            "compound_id": field(rank, "compound_id"),
            "name": get("name"),
            "smiles": get("smiles"),
            "tier": get("tier"),
            "property_score": get("score"),
            "target": field(compound, "target"),
            "consensus": consensus,
            "coverage": coverage,
            "vina_affinity": vina,
            "glide_score": optional_number(compound, "glide_score"),
            "mmgbsa_dg": optional_number(compound, "mmgbsa_dg"),
            "rmsd": optional_number(compound, "rmsd"),
            "hbond_count": optional_number(compound, "hbond_count"),
            "key_interactions": field(compound, "key_interactions"),
            "targets_docked": rank.get("targets_docked").and_then(Value::as_u64).unwrap_or(0),
        }));
    }
    Ok(json!({
        "rows": rows,
        "summary": {
            "docking_rows": scores.len(),
            "rows_after_filters": kept.len(),
            "skipped_by_filters": dropped,
            "compounds_ranked": best.len(),
            "skipped_by_tier": skipped_tier,
            "skipped_not_in_screen": skipped_unlisted,
            "emitted": rows.len(),
            "weights": {"vina_affinity": 0.5, "glide_score": 0.3, "mmgbsa_dg": 0.2},
            "filters": {"min_tier": min_tier, "max_rmsd": max_rmsd, "min_vina": min_vina},
        },
    }))
}
