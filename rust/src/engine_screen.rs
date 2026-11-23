//! Tiering and ranking for the PNN Phase 2 property screen
//! (domains/pnn/screen.py).

use serde_json::{json, Value};

use crate::engine_rules as rules;

const TIER_A_SCORE: f64 = 0.80;
const TIER_B_SCORE: f64 = 0.60;
const MAX_CORE_FAILURES_FOR_TRIAGE: usize = 3;
const MAX_UNKNOWNS_FOR_TIER_A: usize = 2;

fn tier_rank(tier: &str) -> usize {
    match tier {
        "A" => 0, "B" => 1, "C" => 2, _ => 3,
    }
}

fn status(criterion: &Value) -> &str {
    criterion.get("status").and_then(Value::as_str).unwrap_or("")
}

fn name(criterion: &Value) -> &str {
    criterion.get("name").and_then(Value::as_str).unwrap_or("")
}

fn score(criterion: &Value) -> f64 {
    criterion.get("score").and_then(Value::as_f64).unwrap_or(0.0)
}

pub fn weighted_score(criteria: &[Value]) -> f64 {
    let scored: Vec<&Value> = criteria.iter().filter(|c| status(c) != "UNKNOWN").collect();
    let total_weight: f64 = scored.iter().map(|c| rules::weight(name(c))).sum();
    if total_weight == 0.0 { return 0.0; }
    scored.iter().map(|c| score(c) * rules::weight(name(c))).sum::<f64>() / total_weight
}

pub fn tier(criteria: &[Value], value: f64) -> String {
    let hard_failures = criteria.iter().any(|c|
        rules::HARD_REJECT_CRITERIA.contains(&name(c)) && status(c) == "FAIL");
    let core_failures = criteria.iter().filter(|c|
        rules::CORE_CRITERIA.contains(&name(c)) && status(c) == "FAIL").count();
    let unknowns = criteria.iter().filter(|c| status(c) == "UNKNOWN").count();
    if hard_failures || core_failures >= MAX_CORE_FAILURES_FOR_TRIAGE {
        return "Reject".to_string();
    }
    if core_failures == 0 && value >= TIER_A_SCORE && unknowns <= MAX_UNKNOWNS_FOR_TIER_A {
        return "A".to_string();
    }
    if core_failures == 0 && value >= TIER_B_SCORE {
        return "B".to_string();
    }
    "C".to_string()
}

fn failed_criteria(criteria: &[Value]) -> Vec<Value> {
    criteria.iter().filter(|c| status(c) == "FAIL")
        .map(|c| Value::String(name(c).to_string())).collect()
}

fn unknown_criteria(criteria: &[Value]) -> Vec<Value> {
    criteria.iter().filter(|c| status(c) == "UNKNOWN")
        .map(|c| Value::String(name(c).to_string())).collect()
}

/// Fill the Compound dataclass defaults before echoing a record.
fn normalize_compound(compound: &Value) -> Value {
    let number = |key: &str| -> Value {
        compound.get(key).and_then(Value::as_f64).map(Value::from).unwrap_or_else(|| Value::from(0.0))
    };
    let text = |key: &str| -> Value {
        Value::String(compound.get(key).and_then(Value::as_str).unwrap_or("").to_string())
    };
    let optional = |key: &str| -> Value {
        compound.get(key).cloned().unwrap_or(Value::Null)
    };
    json!({
        "compound_id": text("compound_id"),
        "mw": number("mw"), "logp": number("logp"), "tpsa": number("tpsa"),
        "hbd": number("hbd"), "hba": number("hba"), "rotatable_bonds": number("rotatable_bonds"),
        "name": text("name"), "smiles": text("smiles"),
        "pka": optional("pka"), "charge": text("charge"), "logbb": optional("logbb"),
        "brain_plasma_ratio": optional("brain_plasma_ratio"),
        "oral_bioavailability": optional("oral_bioavailability"),
        "cyp3a4_inhibition": optional("cyp3a4_inhibition"),
        "herg_liability": optional("herg_liability"),
        "pnn_ec50_nm": optional("pnn_ec50_nm"),
    })
}

fn screen_result(compound: &Value) -> Value {
    let normalized = normalize_compound(compound);
    let criteria = rules::evaluate(&normalized);
    let value = weighted_score(&criteria);
    let assigned = tier(&criteria, value);
    json!({
        "compound": normalized,
        "tier": assigned,
        "score": value,
        "criteria": criteria,
        "failed_criteria": failed_criteria(&criteria),
        "unknown_criteria": unknown_criteria(&criteria),
    })
}

pub fn screen_compounds(compounds: &[Value]) -> Vec<Value> {
    let mut results: Vec<Value> = compounds.iter().map(screen_result).collect();
    results.sort_by(|a, b| {
        let ta = a.get("tier").and_then(Value::as_str).unwrap_or("");
        let tb = b.get("tier").and_then(Value::as_str).unwrap_or("");
        let sa = a.get("score").and_then(Value::as_f64).unwrap_or(0.0);
        let sb = b.get("score").and_then(Value::as_f64).unwrap_or(0.0);
        let ia = a.get("compound").and_then(|c| c.get("compound_id")).and_then(Value::as_str).unwrap_or("");
        let ib = b.get("compound").and_then(|c| c.get("compound_id")).and_then(Value::as_str).unwrap_or("");
        let tier_cmp = tier_rank(ta).cmp(&tier_rank(tb));
        if tier_cmp != std::cmp::Ordering::Equal { return tier_cmp; }
        let score_cmp = sb.partial_cmp(&sa).unwrap_or(std::cmp::Ordering::Equal);
        if score_cmp != std::cmp::Ordering::Equal { return score_cmp; }
        ia.cmp(ib)
    });
    results
}

/// Python's round(value, 4): round-half-even at the 4th decimal.
fn round_four(value: f64) -> f64 {
    let scaled = value * 10_000.0;
    let floor = scaled.floor();
    let fraction = scaled - floor;
    let rounded = if fraction > 0.5 {
        floor + 1.0
    } else if fraction < 0.5 {
        floor
    } else if (floor as i64) % 2 == 0 {
        floor
    } else {
        floor + 1.0
    };
    rounded / 10_000.0
}

pub fn summarize(results: &[Value]) -> Value {
    let mut counts = serde_json::Map::new();
    for key in ["A", "B", "C", "Reject"] {
        counts.insert(key.to_string(), Value::from(0));
    }
    for result in results {
        let key = result.get("tier").and_then(Value::as_str).unwrap_or("");
        if let Some(entry) = counts.get_mut(key) {
            *entry = Value::from(entry.as_u64().unwrap_or(0) + 1);
        }
    }
    let average = if results.is_empty() { 0.0 } else {
        results.iter().map(|r| r.get("score").and_then(Value::as_f64).unwrap_or(0.0)).sum::<f64>()
            / results.len() as f64
    };
    json!({
        "total": results.len(),
        "by_tier": Value::Object(counts),
        "average_score": round_four(average),
    })
}

pub fn evaluate_compound(compound: &Value) -> Value {
    screen_result(compound)
}
