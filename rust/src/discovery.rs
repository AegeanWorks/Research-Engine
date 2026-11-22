//! Discovery and ranking over the graph (engine/analysis.py).

use std::collections::{BTreeMap, BTreeSet};

use rusqlite::{params, Connection};
use serde_json::{json, Value};

use crate::analysis::{bounds, comparability, group_provenance};
use crate::cascade::dependents;
use crate::core::{get_claim, get_research};
use crate::error::Result;
use crate::observations::group_values;
use crate::stats;
use crate::synthesis::stances;
use crate::util::query_json;

const STOPWORDS: &[&str] = &[
    "a", "an", "the", "and", "or", "of", "in", "on", "for", "to", "with", "by", "from",
    "as", "is", "are", "was", "were", "be", "been", "being", "that", "this", "these",
    "those", "it", "its", "at", "into", "over", "under", "than", "then", "so", "such",
    "not", "no", "but", "if", "while", "because", "we", "our", "they", "their", "he",
    "she", "his", "her", "which", "who", "whom", "what", "when", "where", "how", "can",
    "cannot", "may", "might", "will", "would", "should", "could", "do", "does", "did",
    "done", "have", "has", "had", "more", "most", "less", "least", "also",
];
const NEGATIONS: &[&str] = &["not", "no", "never", "neither", "nor", "none", "cannot", "without", "n't"];

fn field(value: &Value, name: &str) -> String {
    value.get(name).and_then(Value::as_str).unwrap_or("").to_string()
}

/// Python `re.findall(r"[A-Za-z][A-Za-z'\-]+", text)`.
fn words(text: &str) -> Vec<String> {
    let chars: Vec<char> = text.chars().collect();
    let mut result = Vec::new();
    let mut index = 0;
    while index < chars.len() {
        if chars[index].is_ascii_alphabetic() {
            let start = index;
            index += 1;
            while index < chars.len()
                && (chars[index].is_ascii_alphabetic() || chars[index] == '\'' || chars[index] == '-')
            { index += 1; }
            result.push(chars[start..index].iter().collect());
        } else { index += 1; }
    }
    result
}

fn keywords(text: &str) -> BTreeSet<String> {
    words(text).into_iter().map(|w| w.to_lowercase())
        .filter(|w| !STOPWORDS.contains(&w.as_str())).collect()
}

fn overlap(left: &str, right: &str) -> f64 {
    let a = keywords(left);
    let b = keywords(right);
    if a.is_empty() || b.is_empty() { return 0.0; }
    let intersection = a.intersection(&b).count();
    let union = a.union(&b).count();
    intersection as f64 / union as f64
}

fn negated(text: &str) -> bool {
    words(text).iter().any(|w| {
        let lower = w.to_lowercase();
        NEGATIONS.contains(&lower.as_str()) || lower.ends_with("n't")
    })
}

fn polarity_mismatch(left: &str, right: &str) -> bool { negated(left) != negated(right) }

fn round4(value: f64) -> f64 { (value * 10000.0).round() / 10000.0 }

pub fn contradictions(conn: &Connection, reference: &str, min_score: f64) -> Result<Vec<Value>> {
    let research = get_research(conn, reference)?;
    let rid = field(&research, "id");
    let mut found = Vec::new();
    let mut seen: BTreeSet<(String, String, String)> = BTreeSet::new();
    let questions = query_json(conn, "SELECT * FROM question WHERE research_id=?1 ORDER BY id", params![rid])?;
    for question in questions {
        let qid = field(&question, "id");
        let stances = stances(conn, &qid)?;
        let live: Vec<&Value> = stances.iter()
            .filter(|(_, _, row)| row.get("superseded_by").and_then(Value::as_str).unwrap_or("").is_empty()
                && !["RETRACTED", "INVALIDATED"].contains(&field(row, "status").as_str()))
            .map(|(_, _, row)| row).collect();
        let support: Vec<&Value> = stances.iter().filter(|(_, rel, row)| {
            (rel == "supports" || rel == "answers") && live.iter().any(|l| l.get("id") == row.get("id"))
        }).map(|(_, _, row)| row).collect();
        let against: Vec<&Value> = stances.iter().filter(|(_, rel, row)| {
            rel == "contradicts" && live.iter().any(|l| l.get("id") == row.get("id"))
        }).map(|(_, _, row)| row).collect();
        for left in &support {
            for right in &against {
                let a = field(left, "id");
                let b = field(right, "id");
                let mut pair = [a.clone(), b.clone()];
                pair.sort();
                let key = (qid.clone(), pair[0].clone(), pair[1].clone());
                if seen.contains(&key) { continue; }
                let confidence = (left.get("confidence").and_then(Value::as_f64).unwrap_or(0.0)
                    + right.get("confidence").and_then(Value::as_f64).unwrap_or(0.0)) / 2.0;
                let overlap_value = overlap(&field(left, "text"), &field(right, "text"));
                let score = round4(0.6 * confidence + 0.4 * overlap_value);
                if score < min_score { continue; }
                seen.insert(key);
                found.push(json!({
                    "question": qid, "support": a, "contradicts": b, "score": score,
                    "overlap": round4(overlap_value),
                    "polarity_mismatch": polarity_mismatch(&field(left, "text"), &field(right, "text")),
                    "support_text": field(left, "text"),
                    "contradicts_text": field(right, "text"),
                }));
            }
        }
    }
    found.sort_by(|a, b| {
        let sa = a.get("score").and_then(Value::as_f64).unwrap_or(0.0);
        let sb = b.get("score").and_then(Value::as_f64).unwrap_or(0.0);
        sb.partial_cmp(&sa).unwrap_or(std::cmp::Ordering::Equal)
            .then_with(|| field(a, "support").cmp(&field(b, "support")))
            .then_with(|| field(a, "contradicts").cmp(&field(b, "contradicts")))
    });
    Ok(found)
}

pub fn unlinked_contradictions(conn: &Connection, reference: &str, min_score: f64) -> Result<Vec<Value>> {
    let research = get_research(conn, reference)?;
    let rid = field(&research, "id");
    let claims = query_json(conn,
        "SELECT * FROM claim WHERE research_id=?1 AND status NOT IN ('RETRACTED','INVALIDATED') AND (superseded_by IS NULL OR superseded_by='') ORDER BY id",
        params![rid])?;
    let mut existing = BTreeSet::new();
    for row in query_json(conn,
        "SELECT src_id, dst_id FROM edge WHERE src_kind='claim' AND dst_kind='claim' AND rel='contradicts'", [])? {
        let mut pair = [field(&row, "src_id"), field(&row, "dst_id")];
        pair.sort();
        existing.insert((pair[0].clone(), pair[1].clone()));
    }
    let mut proposals = Vec::new();
    for (index, left) in claims.iter().enumerate() {
        for right in claims.iter().skip(index + 1) {
            let mut pair = [field(left, "id"), field(right, "id")];
            pair.sort();
            if existing.contains(&(pair[0].clone(), pair[1].clone())) { continue; }
            let confidence = (left.get("confidence").and_then(Value::as_f64).unwrap_or(0.0)
                + right.get("confidence").and_then(Value::as_f64).unwrap_or(0.0)) / 2.0;
            let score = round4(0.4 * confidence + 0.6 * overlap(&field(left, "text"), &field(right, "text")));
            if score < min_score { continue; }
            proposals.push(json!({
                "left": field(left, "id"), "right": field(right, "id"), "score": score,
                "polarity_mismatch": polarity_mismatch(&field(left, "text"), &field(right, "text")),
                "left_text": field(left, "text"), "right_text": field(right, "text"),
            }));
        }
    }
    proposals.sort_by(|a, b| {
        let sa = a.get("score").and_then(Value::as_f64).unwrap_or(0.0);
        let sb = b.get("score").and_then(Value::as_f64).unwrap_or(0.0);
        sb.partial_cmp(&sa).unwrap_or(std::cmp::Ordering::Equal)
            .then_with(|| field(a, "left").cmp(&field(b, "left")))
            .then_with(|| field(a, "right").cmp(&field(b, "right")))
    });
    Ok(proposals)
}

pub fn evidence_matrix(conn: &Connection, reference: &str) -> Result<Value> {
    let research = get_research(conn, reference)?;
    let rid = field(&research, "id");
    let questions = query_json(conn, "SELECT * FROM question WHERE research_id=?1 ORDER BY id", params![rid])?;
    let sources = query_json(conn, "SELECT id, title, year FROM source WHERE research_id=?1 ORDER BY id", params![rid])?;
    let mut counts: BTreeMap<(String, String), i64> = BTreeMap::new();
    for row in query_json(conn,
        "SELECT c.id, c.source_id, e.dst_id AS question_id FROM claim c JOIN edge e ON e.src_kind='claim' AND e.src_id=c.id AND e.dst_kind='question' WHERE c.research_id=?1 AND c.source_id IS NOT NULL",
        params![rid])? {
        let key = (field(&row, "source_id"), field(&row, "question_id"));
        *counts.entry(key).or_insert(0) += 1;
    }
    let columns: Vec<String> = questions.iter().map(|q| field(q, "id")).collect();
    let mut rows = Vec::new();
    for source in &sources {
        let cells: Vec<i64> = columns.iter().map(|column|
            *counts.get(&(field(source, "id"), column.clone())).unwrap_or(&0)).collect();
        rows.push(json!({"source": field(source, "id"), "title": field(source, "title"),
            "year": source.get("year").cloned().unwrap_or(Value::Null),
            "cells": cells, "total": cells.iter().sum::<i64>()}));
    }
    let gaps: Vec<Value> = columns.iter().map(|column| json!({
        "question": column,
        "covered": rows.iter().filter(|row| {
            counts.get(&(field(row, "source"), column.clone())).copied().unwrap_or(0) > 0
        }).count(),
    })).collect();
    Ok(json!({"questions": columns, "rows": rows, "gaps": gaps}))
}

pub fn keystone_claims(conn: &Connection, reference: &str, limit: i64) -> Result<Vec<Value>> {
    let research = get_research(conn, reference)?;
    let rid = field(&research, "id");
    let rows = query_json(conn,
        "SELECT id, status, confidence, text FROM claim WHERE research_id=?1 AND (superseded_by IS NULL OR superseded_by='') ORDER BY id",
        params![rid])?;
    let mut inbound: BTreeMap<String, i64> = BTreeMap::new();
    for row in query_json(conn, "SELECT dst_id, COUNT(*) AS n FROM edge WHERE dst_kind='claim' GROUP BY dst_id", [])? {
        inbound.insert(field(&row, "dst_id"), row.get("n").and_then(Value::as_i64).unwrap_or(0));
    }
    let mut ranked = Vec::new();
    for row in &rows {
        let id = field(row, "id");
        let downstream = dependents(conn, &id);
        let count = inbound.get(&id).copied().unwrap_or(0);
        ranked.push(json!({
            "claim": id, "status": field(row, "status"),
            "confidence": row.get("confidence").and_then(Value::as_f64).unwrap_or(0.0),
            "dependents": downstream.len(),
            "max_depth": downstream.iter().map(|(_, depth)| *depth).max().unwrap_or(0),
            "inbound": count,
            "text": field(row, "text"),
            "weight": downstream.len() as i64 + count,
        }));
    }
    // Python order: -weight, -dependents, claim.
    ranked.sort_by(|a, b| {
        b.get("weight").and_then(Value::as_i64).unwrap_or(0)
            .cmp(&a.get("weight").and_then(Value::as_i64).unwrap_or(0))
            .then_with(|| b.get("dependents").and_then(Value::as_u64).unwrap_or(0)
                .cmp(&a.get("dependents").and_then(Value::as_u64).unwrap_or(0)))
            .then_with(|| field(a, "claim").cmp(&field(b, "claim")))
    });
    let limit = limit.max(1) as usize;
    Ok(ranked.into_iter().take(limit).collect())
}

pub fn expose(conn: &Connection, reference: &str) -> Result<Value> {
    let claim = get_claim(conn, reference)?;
    let id = field(&claim, "id");
    let downstream: Vec<Value> = dependents(conn, &id).into_iter()
        .map(|(id, depth)| json!({"id": id, "depth": depth})).collect();
    let inbound = query_json(conn,
        "SELECT rel, src_kind, src_id FROM edge WHERE dst_kind='claim' AND dst_id=?1 ORDER BY rel, src_id",
        params![id])?;
    Ok(json!({"claim": id, "status": field(&claim, "status"),
        "dependents": downstream, "inbound": inbound}))
}

#[allow(clippy::too_many_arguments)]
pub fn group_correlations(
    conn: &Connection,
    claim_ref: &str,
    groups: Option<&[String]>,
    allow_incomparable: bool,
    allow_self_reported: bool,
    since: &str,
    until: &str,
) -> Result<Vec<Value>> {
    let claim = get_claim(conn, claim_ref)?;
    let claim_id = field(&claim, "id");
    let (since, until) = bounds(since, until)?;
    let values = group_values(conn, &claim_id, Some(&since), Some(&until))?;
    let labels: Vec<String> = match groups {
        Some(groups) => groups.iter().map(|g| g.trim().to_lowercase()).filter(|g| !g.is_empty()).collect(),
        None => values.iter().map(|(name, _)| name.clone()).collect(),
    };
    if let Some(missing) = labels.iter().find(|label| !values.iter().any(|(name, _)| name == *label)) {
        let available = values.iter().map(|(name, _)| name.clone()).collect::<Vec<_>>().join(", ");
        return Err(crate::error::EngineError::new(
            format!("no observations in group(s) {missing} for {claim_id}"),
            "a correlation needs recorded values in each named group.",
            format!("add values with `observation add`, or choose one of: {}.", if available.is_empty() { "none".to_string() } else { available })));
    }
    if labels.len() < 2 {
        return Err(crate::error::EngineError::new(
            format!("fewer than two groups for {claim_id}: {}", labels.join(", ")),
            "a correlation needs two recorded groups to mean anything.",
            "record a second group with `observation add`."));
    }
    let mut pairs = Vec::new();
    for (position, left) in labels.iter().enumerate() {
        for right in labels.iter().skip(position + 1) {
            let first = values.iter().find(|(name, _)| name == left).map(|(_, v)| v.clone()).unwrap_or_default();
            let second = values.iter().find(|(name, _)| name == right).map(|(_, v)| v.clone()).unwrap_or_default();
            let truncated = first.len().min(second.len());
            let bp = group_provenance(conn, &claim_id, left, &since, &until)?;
            let tp = group_provenance(conn, &claim_id, right, &since, &until)?;
            let comparison = comparability(&bp, &tp, allow_incomparable, allow_self_reported);
            let (comparable, reason, details) = match comparison {
                Ok(value) => value,
                Err(error) => {
                    pairs.push(json!({"claim": claim_id, "left": left, "right": right, "n": 0,
                        "r": 0.0, "comparable": false, "reason": error.what, "warnings": [error.what]}));
                    continue;
                }
            };
            let display_reason = field(&details, "reason");
            let mut warnings = Vec::new();
            if first.len() != second.len() {
                warnings.push(format!("groups truncated to {truncated} pairs by recording order ({left} n={}, {right} n={})", first.len(), second.len()));
            }
            if truncated < 3 {
                warnings.push("fewer than 3 paired observations; no correlation is estimated".to_string());
                pairs.push(json!({"claim": claim_id, "left": left, "right": right, "n": truncated,
                    "r": 0.0, "comparable": comparable, "reason": display_reason, "warnings": warnings}));
                continue;
            }
            if !comparable { warnings.push(format!("incomparable comparison allowed: {reason}")); }
            else if details.get("unprovenanced").and_then(Value::as_bool) == Some(true) {
                warnings.push("one or both groups have no measurement provenance; the correlation is unverified".to_string());
            }
            let outcome = stats::pearson(&first[..truncated], &second[..truncated]);
            pairs.push(json!({"claim": claim_id, "left": left, "right": right,
                "n": outcome.get("n").and_then(Value::as_u64).unwrap_or(0),
                "r": outcome.get("r").and_then(Value::as_f64).unwrap_or(0.0),
                "comparable": comparable, "reason": display_reason, "warnings": warnings}));
        }
    }
    pairs.sort_by(|a, b| {
        let ra = a.get("r").and_then(Value::as_f64).unwrap_or(0.0).abs();
        let rb = b.get("r").and_then(Value::as_f64).unwrap_or(0.0).abs();
        rb.partial_cmp(&ra).unwrap_or(std::cmp::Ordering::Equal)
            .then_with(|| field(a, "left").cmp(&field(b, "left")))
            .then_with(|| field(a, "right").cmp(&field(b, "right")))
    });
    Ok(pairs)
}
