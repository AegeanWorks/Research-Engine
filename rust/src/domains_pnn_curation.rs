//! Merge, deduplicate and diversify compound libraries for PNN Phase 2
//! (domains/pnn/curation.py).

use serde_json::{json, Value};

use crate::domains_pnn_screen as screen;
use crate::domains_pnn_tables as tables;
use crate::error::{EngineError, Result};

const TIER_CEILING: &[(&str, usize)] = &[("A", 0), ("B", 1), ("C", 2)];

fn tier_rank(tier: &str) -> usize {
    match tier { "A" => 0, "B" => 1, "C" => 2, _ => 3 }
}

fn text(value: &Value, key: &str) -> String {
    value.get(key).and_then(Value::as_str).unwrap_or("").to_string()
}

fn compound(candidate: &Value) -> &Value {
    candidate.get("compound").unwrap_or(&Value::Null)
}

fn result(candidate: &Value) -> &Value {
    candidate.get("result").unwrap_or(&Value::Null)
}

/// (tier rank, -score, missing-SMILES flag, compound id) — Python's _preference.
fn preference(candidate: &Value) -> (usize, f64, bool, String) {
    let score = result(candidate).get("score").and_then(Value::as_f64).unwrap_or(0.0);
    (tier_rank(&text(result(candidate), "tier")), -score,
        text(compound(candidate), "smiles").is_empty(),
        text(compound(candidate), "compound_id"))
}

fn compare(a: &Value, b: &Value) -> std::cmp::Ordering {
    use std::cmp::Ordering;
    let pa = preference(a);
    let pb = preference(b);
    let cmp = pa.0.cmp(&pb.0);
    if cmp != Ordering::Equal { return cmp; }
    let cmp = pa.1.partial_cmp(&pb.1).unwrap_or(Ordering::Equal);
    if cmp != Ordering::Equal { return cmp; }
    let cmp = pa.2.cmp(&pb.2);
    if cmp != Ordering::Equal { return cmp; }
    pa.3.cmp(&pb.3)
}

fn set_text(object: &mut Value, key: &str, value: &str) {
    if let Some(map) = object.as_object_mut() {
        map.insert(key.to_string(), Value::String(value.to_string()));
    }
}

/// Keep the better record, filling a blank SMILES/name from the other source.
fn merge(left: &Value, right: &Value) -> Value {
    let (winner, loser) = if compare(left, right) != std::cmp::Ordering::Greater {
        (left.clone(), right)
    } else {
        (right.clone(), left)
    };
    let mut merged = winner;
    let winner_compound = compound(&merged);
    let smiles = text(winner_compound, "smiles");
    let name = text(winner_compound, "name");
    let loser_smiles = text(compound(loser), "smiles");
    let loser_name = text(compound(loser), "name");
    if smiles.is_empty() && !loser_smiles.is_empty() {
        if let Some(map) = merged.as_object_mut() {
            if let Some(inner) = map.get_mut("compound") { set_text(inner, "smiles", &loser_smiles); }
        }
    }
    if name.is_empty() && !loser_name.is_empty() {
        if let Some(map) = merged.as_object_mut() {
            if let Some(inner) = map.get_mut("compound") { set_text(inner, "name", &loser_name); }
        }
    }
    merged
}

/// Screen every input compound while keeping its source provenance.
pub fn prepare_candidates(inputs: &[(String, Vec<Value>)]) -> Result<Vec<Value>> {
    let mut candidates = Vec::new();
    for (source, compounds) in inputs {
        for record in compounds {
            let evaluated = screen::evaluate_compound(record);
            candidates.push(json!({"compound": record, "source": source, "result": evaluated}));
        }
    }
    if candidates.is_empty() {
        return Err(EngineError::new("no compounds were supplied",
            "curation needs at least one candidate", "pass at least one compound"));
    }
    Ok(candidates)
}

fn positional(candidates: &mut Vec<Value>) {
    candidates.sort_by(compare);
}

/// Collapse duplicate IDs first, then exact non-empty SMILES strings.
pub fn deduplicate(candidates: &[Value]) -> Result<Value> {
    let mut by_id: Vec<(String, Value)> = Vec::new();
    let mut duplicate_ids = 0usize;
    for candidate in candidates {
        let id = text(compound(candidate), "compound_id");
        if let Some((_, existing)) = by_id.iter_mut().find(|(key, _)| *key == id) {
            let left = text(compound(existing), "smiles");
            let right = text(compound(candidate), "smiles");
            if !left.is_empty() && !right.is_empty() && left != right {
                return Err(EngineError::new(
                    format!("compound_id '{id}' has two different SMILES ('{left}' from {}, '{right}' from {})",
                        text(existing, "source"), text(candidate, "source")),
                    "one identifier cannot represent two distinct structures",
                    "give the duplicate a distinct compound_id"));
            }
            *existing = merge(existing, candidate);
            duplicate_ids += 1;
        } else {
            by_id.push((id, candidate.clone()));
        }
    }

    let mut by_smiles: Vec<(String, Value)> = Vec::new();
    let mut without_smiles = Vec::new();
    let mut duplicate_smiles = 0usize;
    for (_, candidate) in by_id {
        let smiles = text(compound(&candidate), "smiles").trim().to_string();
        if smiles.is_empty() {
            without_smiles.push(candidate);
            continue;
        }
        if let Some((_, existing)) = by_smiles.iter_mut().find(|(key, _)| *key == smiles) {
            *existing = merge(existing, &candidate);
            duplicate_smiles += 1;
        } else {
            by_smiles.push((smiles, candidate));
        }
    }

    let mut kept = without_smiles;
    kept.extend(by_smiles.into_iter().map(|(_, candidate)| candidate));
    Ok(json!({
        "candidates": kept,
        "stats": {"duplicate_ids": duplicate_ids, "duplicate_smiles": duplicate_smiles},
    }))
}

fn validate(min_tier: &str, per_bin: i64, bin_width: f64, max_compounds: Option<i64>) -> Result<()> {
    if !TIER_CEILING.iter().any(|(tier, _)| *tier == min_tier) {
        return Err(EngineError::new(format!("unknown screening tier: {min_tier}"),
            "tiers are A, B or C", "pass A, B or C"));
    }
    if per_bin < 1 {
        return Err(EngineError::new("per-bin cap must be at least 1",
            "a bin cap must retain at least one candidate", "pass per_bin >= 1"));
    }
    if bin_width <= 0.0 || bin_width > 1.0 {
        return Err(EngineError::new("bin width must be greater than 0 and at most 1",
            "the bin grid needs a width in (0, 1]", "pass 0 < bin_width <= 1"));
    }
    if let Some(maximum) = max_compounds {
        if maximum < 1 {
            return Err(EngineError::new("max compounds must be at least 1",
                "the global cap must retain at least one candidate", "pass a positive cap"));
        }
    }
    Ok(())
}

/// Filter by tier, cap each property bin, then apply the global size limit.
pub fn curate(candidates: &[Value], min_tier: &str, per_bin: usize,
              bin_width: f64, max_compounds: Option<usize>) -> Result<Value> {
    validate(min_tier, per_bin as i64, bin_width,
        max_compounds.map(|v| v as i64))?;
    let ceiling = TIER_CEILING.iter().find(|(tier, _)| *tier == min_tier).unwrap().1;
    let eligible: Vec<Value> = candidates.iter()
        .filter(|c| tier_rank(&text(result(c), "tier")) <= ceiling)
        .cloned().collect();
    let skipped_by_tier = candidates.len() - eligible.len();
    let eligible_count = eligible.len();

    let mut groups: Vec<(Vec<i64>, Vec<Value>)> = Vec::new();
    for candidate in eligible {
        let bin = tables::property_bin(compound(&candidate), bin_width)?;
        if let Some((_, group)) = groups.iter_mut().find(|(key, _)| *key == bin) {
            group.push(candidate);
        } else {
            groups.push((bin, vec![candidate]));
        }
    }
    let bins = groups.len();
    let mut kept: Vec<Value> = Vec::new();
    for (_, mut group) in groups {
        positional(&mut group);
        kept.extend(group.into_iter().take(per_bin));
    }
    positional(&mut kept);
    let truncated = max_compounds.map(|m| kept.len() > m).unwrap_or(false);
    if let Some(maximum) = max_compounds { kept.truncate(maximum); }

    Ok(json!({
        "candidates": kept,
        "summary": {
            "eligible": eligible_count,
            "skipped_by_tier": skipped_by_tier,
            "bins": bins,
            "per_bin": per_bin,
            "bin_width": bin_width,
            "max_compounds": max_compounds,
            "selected": kept.len(),
            "truncated_by_max": truncated,
        },
    }))
}
