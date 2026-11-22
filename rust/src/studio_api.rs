//! Studio public API facade: evidence matrix and per-question evidence views.

use std::collections::BTreeMap;

use rusqlite::Connection;
use serde_json::{json, Value};

use crate::error::{EngineError, Result};
use crate::lattice::{bare_id, entity_type};
use crate::lattice_repo as repo;
use crate::util::query_json;

fn field(value: &Value, name: &str) -> String {
    value.get(name).and_then(Value::as_str).unwrap_or("").to_string()
}

pub fn build_evidence_matrix(conn: &Connection) -> Result<Value> {
    let papers: Vec<Value> = query_json(conn,
        "SELECT id, title, authors, year, doi, tags, study_type FROM papers ORDER BY year DESC, title", [])?;
    let claim_rows = query_json(conn,
        "SELECT id, paper_id, text, stance, confidence FROM claims ORDER BY id", [])?;
    let mut claim_by_id = BTreeMap::new();
    for row in &claim_rows {
        claim_by_id.insert(field(row, "id"), row.clone());
    }
    let question_rows = query_json(conn, "SELECT id, text, status FROM questions ORDER BY id", [])?;
    let edges = query_json(conn, "SELECT src, dst, kind FROM edges", [])?;
    let mut q_claims: BTreeMap<String, Vec<Value>> = BTreeMap::new();
    for row in &question_rows { q_claims.insert(field(row, "id"), Vec::new()); }
    for row in &edges {
        let src = field(row, "src");
        let dst = field(row, "dst");
        let pair = match (entity_type(&src), entity_type(&dst)) {
            (Ok(kind_a), Ok(kind_b)) if kind_a == "claim" && kind_b == "question" =>
                Some((bare_id(&src).unwrap_or_default(), bare_id(&dst).unwrap_or_default())),
            (Ok(kind_a), Ok(kind_b)) if kind_b == "claim" && kind_a == "question" =>
                Some((bare_id(&dst).unwrap_or_default(), bare_id(&src).unwrap_or_default())),
            _ => None,
        };
        if let Some((claim_id, question_id)) = pair {
            if let Some(claims) = q_claims.get_mut(&question_id) {
                if let Some(claim) = claim_by_id.get(&claim_id) { claims.push(claim.clone()); }
            }
        }
    }
    let mut cells = Vec::new();
    let mut questions = Vec::new();
    let mut gaps = Vec::new();
    for row in &question_rows {
        let qid = field(row, "id");
        let prompt = field(row, "text");
        let linked = q_claims.get(&qid).cloned().unwrap_or_default();
        let mut by_paper: BTreeMap<String, Vec<Value>> = BTreeMap::new();
        let mut supporting = 0usize;
        let mut contradicting = 0usize;
        for claim in &linked {
            by_paper.entry(field(claim, "paper_id")).or_default().push(claim.clone());
            match field(claim, "stance").as_str() {
                "supports" => supporting += 1,
                "contradicts" => contradicting += 1,
                _ => {}
            }
        }
        for (paper_id, claims) in &by_paper {
            let stances: Vec<String> = claims.iter().map(|c| field(c, "stance")).collect();
            let dominant = if stances.contains(&"supports".to_string()) && stances.contains(&"contradicts".to_string()) {
                "contested"
            } else if stances.contains(&"supports".to_string()) { "supports" }
            else if stances.contains(&"contradicts".to_string()) { "contradicts" }
            else { "mentions" };
            let max_confidence = claims.iter()
                .map(|c| c.get("confidence").and_then(Value::as_f64).unwrap_or(0.0))
                .fold(f64::NEG_INFINITY, f64::max);
            cells.push(json!({
                "paper_id": paper_id, "question_id": qid,
                "claim_ids": claims.iter().map(|c| field(c, "id")).collect::<Vec<_>>(),
                "stances": stances, "dominant_stance": dominant, "max_confidence": max_confidence,
            }));
        }
        let has_gap = by_paper.is_empty();
        questions.push(json!({
            "id": qid, "prompt": prompt, "status": field(row, "status"),
            "supporting_count": supporting, "contradicting_count": contradicting,
            "answering_paper_count": by_paper.len(), "coverage_gap": has_gap,
        }));
        if has_gap {
            gaps.push(json!({"question_id": qid, "prompt": prompt,
                "reason": "Zero papers have linked empirical claims for this research question."}));
        } else if supporting > 0 && contradicting > 0 {
            gaps.push(json!({"question_id": qid, "prompt": prompt,
                "reason": format!("Contested evidence ({supporting} supporting vs {contradicting} contradicting claims).")}));
        }
    }
    Ok(json!({"papers": papers, "questions": questions, "cells": cells, "gaps": gaps}))
}

fn question_key(value: &str) -> Result<String> {
    let mut text = value.trim().to_string();
    if text.contains(':') {
        let (kind, identifier) = text.split_once(':').unwrap();
        if kind.trim().to_lowercase() != "question" {
            return Err(EngineError::new(format!("'{value}' is not a question reference"),
                "the evidence matrix is filtered by research question ids",
                "pass question:q_xxx references or bare q_xxx ids"));
        }
        text = identifier.trim().to_string();
    }
    let valid = text.starts_with("q_") && text.len() > 2
        && text[2..].chars().all(|c| c.is_ascii_alphanumeric() || c == '_' || c == '-');
    if !valid {
        return Err(EngineError::new(format!("'{value}' is not a question reference"),
            "question identifiers look like q_000001",
            "pass question:q_xxx references or bare q_xxx ids"));
    }
    Ok(text)
}

pub fn get_evidence_matrix(conn: &Connection, question_ids: Option<&[String]>) -> Result<Value> {
    let Some(ids) = question_ids else { return build_evidence_matrix(conn); };
    let wanted: std::collections::BTreeSet<String> = ids.iter()
        .map(|id| question_key(id)).collect::<Result<_>>()?;
    if wanted.is_empty() {
        return Ok(json!({"papers": [], "questions": [], "cells": [], "gaps": []}));
    }
    let matrix = build_evidence_matrix(conn)?;
    let filter = |array_key: &str, field_key: &str| -> Vec<Value> {
        matrix.get(array_key).and_then(Value::as_array).map(|items| items.iter()
            .filter(|item| wanted.contains(&field(item, field_key))).cloned().collect()).unwrap_or_default()
    };
    let questions = filter("questions", "id");
    let cells = filter("cells", "question_id");
    let gaps = filter("gaps", "question_id");
    let paper_ids: std::collections::BTreeSet<String> = cells.iter().map(|c| field(c, "paper_id")).collect();
    let papers = matrix.get("papers").and_then(Value::as_array).map(|items| items.iter()
        .filter(|p| paper_ids.contains(&field(p, "id"))).cloned().collect::<Vec<_>>()).unwrap_or_default();
    Ok(json!({"papers": papers, "questions": questions, "cells": cells, "gaps": gaps}))
}

pub fn question_evidence(conn: &Connection, reference: &str) -> Result<Value> {
    let resolved = crate::lattice_repo::resolve_ref(reference)?;
    if entity_type(&resolved)? != "question" {
        return Err(EngineError::new(format!("'{reference}' is not a question reference"),
            "evidence is grouped per question", "pass a question:q_xxx reference"));
    }
    let question = repo::get_question(conn, &resolved)?;
    let edges = query_json(conn, "SELECT * FROM edges WHERE src=?1 OR dst=?2 ORDER BY id",
        rusqlite::params![resolved, resolved])?;
    let mut groups = serde_json::Map::new();
    for key in ["supports", "contradicts", "answers", "other"] {
        groups.insert(key.to_string(), json!([]));
    }
    for row in &edges {
        let other = if field(row, "src") == resolved { field(row, "dst") } else { field(row, "src") };
        if entity_type(&other)? != "claim" { continue; }
        let summary = crate::lattice_repo::summary_public(conn, &other);
        let item = json!({"link": field(row, "kind"), "note": field(row, "note"), "claim": summary});
        let bucket = field(row, "kind");
        let target = if groups.contains_key(&bucket) { bucket } else { "other".to_string() };
        groups.get_mut(&target).and_then(Value::as_array_mut).map(|list| list.push(item));
    }
    let total: usize = groups.values().filter_map(Value::as_array).map(|list| list.len()).sum();
    let mut gaps = Vec::new();
    if total == 0 { gaps.push("No claims are linked to this question yet.".to_string()); }
    if groups.get("contradicts").and_then(Value::as_array).map(|v| v.is_empty()).unwrap_or(true) {
        gaps.push("No contradicting evidence has been linked.".to_string());
    }
    Ok(json!({
        "question": question, "ref": resolved,
        "supports": groups.get("supports").cloned().unwrap_or(json!([])),
        "contradicts": groups.get("contradicts").cloned().unwrap_or(json!([])),
        "answers": groups.get("answers").cloned().unwrap_or(json!([])),
        "other": groups.get("other").cloned().unwrap_or(json!([])),
        "evidence_count": total, "gaps": gaps,
    }))
}
