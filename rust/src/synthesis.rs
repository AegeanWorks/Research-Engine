//! Evidence synthesis: graph-derived consensus and generated reports (G-006).

use rusqlite::{params, Connection};
use serde_json::{json, Value};

use crate::core::{get_research, research_counts};
use crate::error::{EngineError, Result};
use crate::integrity;
use crate::util::query_json;

fn field(value: &Value, name: &str) -> String {
    value.get(name).and_then(Value::as_str).unwrap_or("").to_string()
}

fn cell(value: &str) -> String {
    value.replace('|', "\\|").replace('\n', " ")
}

const WEIGHTS: &[(&str, f64)] = &[
    ("PROVEN", 1.0), ("NUMERIC", 0.9), ("UNKNOWN", 0.0), ("UNVERIFIED", 0.4),
    ("FALSIFIED", 0.0), ("RETRACTED", 0.0), ("INVALIDATED", 0.0),
];
const COVERED: &[&str] = &["PROVEN", "NUMERIC", "FALSIFIED"];

fn stances(conn: &Connection, question_id: &str) -> Result<Vec<(String, String, Value)>> {
    let rows = query_json(conn,
        "SELECT e.rel AS stance, c.* FROM edge e JOIN claim c ON c.id=e.src_id WHERE e.src_kind='claim' AND e.dst_kind='question' AND e.dst_id=?1 AND e.rel IN ('supports','contradicts','answers','mentions') ORDER BY c.id",
        params![question_id])?;
    Ok(rows.into_iter().map(|row| (field(&row, "id"), field(&row, "stance"), row)).collect())
}

pub fn consensus(conn: &Connection, question_id: &str) -> f64 {
    let mut support = 0.0;
    let mut against = 0.0;
    for (_id, rel, row) in stances(conn, question_id).unwrap_or_default() {
        let status = field(&row, "status");
        let weight = WEIGHTS.iter().find(|(s, _)| *s == status).map(|(_, w)| *w).unwrap_or(0.0)
            * row.get("confidence").and_then(Value::as_f64).unwrap_or(0.0);
        if rel == "supports" || rel == "answers" { support += weight; }
        if rel == "contradicts" { against += weight; }
    }
    let total = support + against;
    if total == 0.0 { 0.0 } else { ((support - against) / total * 10000.0).round() / 10000.0 }
}

pub fn coverage(conn: &Connection, question_id: &str) -> Value {
    let list = stances(conn, question_id).unwrap_or_default();
    let total = list.len();
    let covered = list.iter().filter(|(_, _, row)| COVERED.contains(&field(row, "status").as_str())).count();
    let mut sources = std::collections::HashSet::new();
    for (_, _, row) in &list {
        let source = field(row, "source_id");
        if !source.is_empty() { sources.insert(source); }
    }
    let sufficient = total >= 2 && covered as f64 / total as f64 >= 0.5 && sources.len() != 1;
    json!({"total": total, "covered": covered, "distinct_sources": sources.len(), "sufficient": sufficient})
}

pub fn consensus_display(conn: &Connection, question_id: &str) -> String {
    let detail = coverage(conn, question_id);
    let total = detail.get("total").and_then(Value::as_u64).unwrap_or(0);
    if total == 0 { return "insufficient coverage (no linked claims)".to_string(); }
    if detail.get("sufficient").and_then(Value::as_bool) != Some(true) {
        let covered = detail.get("covered").and_then(Value::as_u64).unwrap_or(0);
        let mut note = format!("{covered}/{total} tested");
        if detail.get("distinct_sources").and_then(Value::as_u64) == Some(1) { note.push_str(", single source"); }
        return format!("insufficient coverage ({note})");
    }
    format!("{:+.4}", consensus(conn, question_id))
}

fn verdict_count(conn: &Connection, research_id: &str) -> i64 {
    conn.query_row(
        "SELECT COUNT(*) FROM verdict WHERE (subject_kind='claim' AND subject_id IN (SELECT id FROM claim WHERE research_id=?1)) OR (subject_kind='hypothesis' AND subject_id IN (SELECT id FROM hypothesis WHERE research_id=?1))",
        params![research_id], |r| r.get(0)).unwrap_or(0)
}

/// Render a reproducible report; every number comes from the graph.
pub fn report(conn: &Connection, research_ref: &str) -> Result<String> {
    let research = get_research(conn, research_ref)?;
    let rid = field(&research, "id");
    let counts = research_counts(conn, &rid)?;
    let count = |key: &str| counts.get(key).and_then(Value::as_i64).unwrap_or(0);
    if count("claim") > 0 && verdict_count(conn, &rid) == 0 {
        return Err(EngineError::new("report has no answered items",
            "the program records claims but no verdict adjudicates any of them.",
            "record verdicts, or read the work-in-progress with `brief`, `outline` or `scorecard`."));
    }
    let findings = integrity::check(conn)?;
    let errors = findings.iter().filter(|f| f.get("severity").and_then(Value::as_str) == Some("error")).count();
    let warnings = findings.iter().filter(|f| f.get("severity").and_then(Value::as_str) == Some("warning")).count();
    let mut lines = vec![
        format!("# {}", field(&research, "title")),
        String::new(),
        format!("**Program:** `{}` (`{}`)  ", rid, field(&research, "slug")),
        format!("**Scope:** {}  ", if field(&research, "scope").is_empty() { "not stated".to_string() } else { field(&research, "scope") }),
        "**Generated from:** the engine database (no hand-written numbers)".to_string(),
        String::new(),
        "## Inventory".to_string(), String::new(),
        format!("- sources: {}", count("source")),
        format!("- questions: {} ({} open)", count("question"), count("open_questions")),
        format!("- claims: {}", count("claim")),
        format!("- hypotheses: {}", count("hypothesis")),
        format!("- kill tests: {}", count("killtest")),
        format!("- integrity: {errors} error(s), {warnings} warning(s)"),
        String::new(),
    ];
    lines.push("## Questions".to_string());
    lines.push(String::new());
    lines.push("| Question | Status | Stances | Consensus |".to_string());
    lines.push("|---|---|---|---|".to_string());
    for row in query_json(conn, "SELECT * FROM question WHERE research_id=?1 ORDER BY id", params![rid])? {
        let qid = field(&row, "id");
        let c = coverage(conn, &qid);
        lines.push(format!("| {} | {} | {} | {} |", cell(&field(&row, "text")),
            field(&row, "status"), c.get("total").and_then(Value::as_u64).unwrap_or(0),
            consensus_display(conn, &qid)));
    }
    lines.push(String::new());
    lines.push("## Claims".to_string());
    lines.push(String::new());
    lines.push("| Claim | Status | Confidence | Assertion |".to_string());
    lines.push("|---|---|---|---|".to_string());
    for row in query_json(conn, "SELECT * FROM claim WHERE research_id=?1 AND (superseded_by IS NULL OR superseded_by='') ORDER BY id", params![rid])? {
        lines.push(format!("| {} | {} | {:.2} | {} |", field(&row, "id"), field(&row, "status"),
            row.get("confidence").and_then(Value::as_f64).unwrap_or(0.0), cell(&field(&row, "text"))));
    }
    lines.push(String::new());
    lines.push("## Limits".to_string());
    lines.push(String::new());
    for limit in [
        "PROVEN records an evidence path and a named kill test; it is not a machine-checked proof.",
        "Consensus is a display heuristic over recorded stances; it never changes a verdict.",
        "UNKNOWN records that the evidence is missing; it never counts as support.",
        "Sources are registered explicitly; the engine performs no literature crawling.",
    ] {
        lines.push(format!("- {limit}"));
    }
    Ok(lines.join("\n") + "\n")
}

pub fn scorecard(conn: &Connection, research_ref: &str) -> Result<String> {
    let research = get_research(conn, research_ref)?;
    let order = ["FALSIFIED", "INVALIDATED", "RETRACTED", "UNVERIFIED", "UNKNOWN", "NUMERIC", "PROVEN"];
    let mut rows = query_json(conn,
        "SELECT * FROM claim WHERE research_id=?1 AND (superseded_by IS NULL OR superseded_by='') ORDER BY id",
        params![field(&research, "id")])?;
    rows.sort_by_key(|row| {
        let status = field(row, "status");
        let rank = order.iter().position(|s| *s == status).unwrap_or(99);
        (rank, field(row, "id"))
    });
    let mut lines = vec![format!("# Scorecard: {}", field(&research, "title")), String::new(),
        "| Claim | Status | Confidence | Assertion |".to_string(), "|---|---|---|---|".to_string()];
    if rows.is_empty() {
        lines.push("| - | - | - | no claims |".to_string());
    }
    for row in rows {
        lines.push(format!("| {} | {} | {:.2} | {} |", field(&row, "id"), field(&row, "status"),
            row.get("confidence").and_then(Value::as_f64).unwrap_or(0.0), cell(&field(&row, "text"))));
    }
    Ok(lines.join("\n") + "\n")
}
