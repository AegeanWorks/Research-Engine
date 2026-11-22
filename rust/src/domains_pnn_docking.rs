//! PNN docking-score ingestion and consensus ranking (domains/pnn/docking.py).

use std::collections::BTreeMap;

use serde_json::{json, Value};

use crate::error::{EngineError, Result};

const SCORE_FIELDS: &[&str] = &["vina_affinity", "glide_score", "mmgbsa_dg"];
const WEIGHTS: &[(&str, f64)] = &[("vina_affinity", 0.5), ("glide_score", 0.3), ("mmgbsa_dg", 0.2)];

fn field_aliases() -> &'static BTreeMap<&'static str, &'static str> {
    static MAP: std::sync::OnceLock<BTreeMap<&'static str, &'static str>> = std::sync::OnceLock::new();
    MAP.get_or_init(|| [
        ("compoundid", "compound_id"), ("id", "compound_id"), ("compound", "compound_id"),
        ("target", "target"), ("targetname", "target"), ("receptor", "target"),
        ("vina", "vina_affinity"), ("vinaaffinity", "vina_affinity"), ("affinity", "vina_affinity"),
        ("glide", "glide_score"), ("glidescore", "glide_score"),
        ("mmgbsa", "mmgbsa_dg"), ("mmgbsadg", "mmgbsa_dg"), ("deltag", "mmgbsa_dg"),
        ("deltagbind", "mmgbsa_dg"), ("rmsd", "rmsd"), ("rmsdligand", "rmsd"),
        ("hbondcount", "hbond_count"), ("hbonds", "hbond_count"),
        ("keyinteractions", "key_interactions"), ("interactions", "key_interactions"),
        ("tier", "tier"), ("score", "score"), ("name", "name"), ("compoundname", "name"),
        ("smiles", "smiles"), ("canonicalsmiles", "smiles"),
    ].into_iter().collect())
}

fn token(name: &str) -> String {
    let base = name.split('(').next().unwrap_or("").split('[').next().unwrap_or("");
    base.trim().to_lowercase().chars().filter(|c| c.is_alphanumeric()).collect()
}

fn canonical_field(name: &str) -> Option<&'static str> {
    let key = token(name);
    if let Some(value) = field_aliases().get(key.as_str()) { return Some(*value); }
    field_aliases().values().find(|value| **value == key).copied()
}

fn number(raw: &str, field: &str, where_: &str) -> Result<f64> {
    let text = raw.trim().replace(',', "");
    let value: f64 = text.parse().map_err(|_| EngineError::new(
        format!("{where_}: field '{field}' is not a number: {raw:?}"),
        "docking fields must be numeric", "pass a finite number"))?;
    if !value.is_finite() {
        return Err(EngineError::new(format!("{where_}: field '{field}' must be finite, got {raw:?}"),
            "non-finite docking values are not comparable", "pass a finite number"));
    }
    if (field == "rmsd" || field == "hbond_count") && value < 0.0 {
        return Err(EngineError::new(format!("{where_}: field '{field}' must not be negative, got {raw:?}"),
            "RMSD and hydrogen-bond counts cannot be negative", "pass a non-negative number"));
    }
    Ok(value)
}

fn optional(values: &BTreeMap<String, String>, field: &str, where_: &str) -> Result<Option<f64>> {
    let raw = values.get(field).map(String::as_str).unwrap_or("").trim();
    if raw.is_empty() { Ok(None) } else { Ok(Some(number(raw, field, where_)?) ) }
}

/// Parse raw CSV-like rows into docking records, using canonical field aliases.
pub fn parse_rows(rows: &[BTreeMap<String, String>], source: &str) -> Result<Vec<Value>> {
    let mut scores = Vec::new();
    let mut seen: BTreeMap<(String, String), usize> = BTreeMap::new();
    for (index, raw) in rows.iter().enumerate() {
        let where_ = format!("{source} row {}", index + 2);
        let mut values = BTreeMap::new();
        for (key, value) in raw {
            if let Some(field) = canonical_field(key) {
                values.insert(field.to_string(), value.trim().to_string());
            }
        }
        let mut missing = Vec::new();
        for field in ["compound_id", "target"] {
            if values.get(field).map(|v| v.trim().is_empty()).unwrap_or(true) { missing.push(field); }
        }
        if !missing.is_empty() {
            return Err(EngineError::new(format!("{where_}: missing required field(s): {}", missing.join(", ")),
                "a docking row needs a compound and a target", "add both fields"));
        }
        let mut scores_map = BTreeMap::new();
        for field in SCORE_FIELDS {
            scores_map.insert(*field, optional(&values, field, &where_)?);
        }
        if scores_map.values().all(|v| v.is_none()) {
            return Err(EngineError::new(format!("{where_}: needs at least one of {}", SCORE_FIELDS.join(", ")),
                "a docking row needs a score", "add vina, glide or mmgbsa"));
        }
        let score = json!({
            "compound_id": values.get("compound_id").cloned().unwrap_or_default(),
            "target": values.get("target").cloned().unwrap_or_default(),
            "vina_affinity": scores_map["vina_affinity"],
            "glide_score": scores_map["glide_score"],
            "mmgbsa_dg": scores_map["mmgbsa_dg"],
            "rmsd": optional(&values, "rmsd", &where_)?,
            "hbond_count": optional(&values, "hbond_count", &where_)?,
            "key_interactions": values.get("key_interactions").cloned().unwrap_or_default(),
        });
        let key = (field(&score, "compound_id"), field(&score, "target"));
        if let Some(first) = seen.get(&key) {
            return Err(EngineError::new(
                format!("{where_}: duplicate docking result for '{}/{}' (first seen on row {})", key.0, key.1, first),
                "each compound/target pair is recorded once", "remove the duplicate row"));
        }
        seen.insert(key, index + 2);
        scores.push(score);
    }
    if scores.is_empty() {
        return Err(EngineError::new(format!("{source}: no docking rows found"),
            "a docking table needs at least one row", "add docking results"));
    }
    Ok(scores)
}

fn field(value: &Value, name: &str) -> String {
    value.get(name).and_then(Value::as_str).unwrap_or("").to_string()
}

fn number_field(value: &Value, name: &str) -> Option<f64> {
    value.get(name).and_then(Value::as_f64)
}

pub fn filter_scores(scores: &[Value], max_rmsd: Option<f64>, min_vina: Option<f64>) -> (Vec<Value>, usize) {
    let mut kept = Vec::new();
    let mut dropped = 0usize;
    for score in scores {
        let Some(vina) = number_field(score, "vina_affinity") else { dropped += 1; continue; };
        if let (Some(limit), Some(rmsd)) = (max_rmsd, number_field(score, "rmsd")) {
            if rmsd > limit { dropped += 1; continue; }
        }
        if let Some(minimum) = min_vina {
            if vina > minimum { dropped += 1; continue; }
        }
        kept.push(score.clone());
    }
    (kept, dropped)
}

pub fn normalize_scores(scores: &[Value]) -> Vec<Value> {
    let mut bounds = BTreeMap::new();
    for field in SCORE_FIELDS {
        let values: Vec<f64> = scores.iter().filter_map(|s| number_field(s, field)).collect();
        if !values.is_empty() {
            let low = values.iter().copied().fold(f64::INFINITY, f64::min);
            let high = values.iter().copied().fold(f64::NEG_INFINITY, f64::max);
            bounds.insert(*field, (low, high));
        }
    }
    let mut ranks = Vec::new();
    for score in scores {
        let available: Vec<&str> = SCORE_FIELDS.iter().copied()
            .filter(|field| number_field(score, field).is_some()).collect();
        if available.is_empty() { continue; }
        let total_weight: f64 = WEIGHTS.iter().filter(|(field, _)| available.contains(field))
            .map(|(_, weight)| *weight).sum();
        let mut quality = 0.0;
        for field_name in &available {
            let value = number_field(score, field_name).unwrap_or(0.0);
            let (low, high) = bounds.get(field_name).copied().unwrap_or((value, value));
            let normalized = if high == low { 1.0 } else { (high - value) / (high - low) };
            let weight = WEIGHTS.iter().find(|(name, _)| name == field_name).map(|(_, w)| *w).unwrap_or(0.0);
            quality += normalized * weight;
        }
        ranks.push(json!({"score": score, "consensus": quality / total_weight, "coverage": total_weight}));
    }
    ranks
}

pub fn aggregate_best(ranks: &[Value]) -> BTreeMap<String, Value> {
    let mut grouped: BTreeMap<String, Vec<Value>> = BTreeMap::new();
    for rank in ranks {
        let score = rank.get("score").unwrap_or(&Value::Null);
        if number_field(score, "vina_affinity").is_none() { continue; }
        grouped.entry(field(score, "compound_id")).or_default().push(rank.clone());
    }
    let key = |rank: &Value| {
        let consensus = rank.get("consensus").and_then(Value::as_f64).unwrap_or(0.0);
        let coverage = rank.get("coverage").and_then(Value::as_f64).unwrap_or(0.0);
        let vina = number_field(rank.get("score").unwrap_or(&Value::Null), "vina_affinity").unwrap_or(0.0);
        (consensus, coverage, -vina)
    };
    let mut best = BTreeMap::new();
    for (compound_id, candidates) in grouped {
        // Python's max() keeps the first element on a tie, so only replace on a strict win.
        let mut winner = candidates[0].clone();
        for candidate in candidates.iter().skip(1) {
            if key(candidate) > key(&winner) { winner = candidate.clone(); }
        }
        best.insert(compound_id.clone(), json!({
            "compound_id": compound_id, "best": winner, "targets_docked": candidates.len(),
        }));
    }
    best
}
