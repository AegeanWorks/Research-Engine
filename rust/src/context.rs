//! Token-budgeted graph views, ported from `engine/context.py`.

use std::collections::BTreeSet;

use rusqlite::{params, Connection};
use serde_json::{json, Value};

use crate::core::{get_claim, get_research, research_counts};
use crate::error::Result;
use crate::integrity;
use crate::killtest::list_runs;
use crate::markdown::{estimate_tokens, pack, sanitize};
use crate::synthesis::{consensus_display, stances};
use crate::util::query_json;
use crate::vocab::{CLAIM_STATUSES, SCREENING_STATUSES};

fn field(value: &Value, name: &str) -> String {
    value.get(name).and_then(Value::as_str).unwrap_or("").to_string()
}

fn render(lines: &[String], budget: i64) -> Result<Value> {
    if budget <= 0 {
        return Err(crate::error::EngineError::new(
            format!("budget must be positive: {budget}"),
            "a view needs at least one token to render its anchor line.",
            "pass --budget 800 or more.",
        ));
    }
    let (mut kept, omitted, _) = pack(lines, budget as usize);
    if omitted > 0 {
        kept.push(format!("OMITTED: {omitted} more line(s); raise --budget to see them"));
    }
    let mut text = kept.join("\n");
    text.push('\n');
    Ok(json!({"text": text, "tokens": estimate_tokens(&text), "omitted": omitted}))
}

pub fn prisma_flow(conn: &Connection, reference: Option<&str>) -> Result<Value> {
    let research_id = match reference {
        Some(reference) => Some(field(&get_research(conn, reference)?, "id")),
        None => None,
    };
    let mut counts = serde_json::Map::new();
    let mut total = 0i64;
    for status in SCREENING_STATUSES {
        let n = match &research_id {
            Some(id) => conn.query_row(
                "SELECT COUNT(*) FROM source WHERE research_id=?1 AND screening=?2",
                params![id, status], |r| r.get::<_, i64>(0))?,
            None => conn.query_row(
                "SELECT COUNT(*) FROM source WHERE screening=?1", params![status], |r| r.get::<_, i64>(0))?,
        };
        total += n;
        counts.insert(status.to_string(), json!(n));
    }
    let sql = match &research_id {
        Some(_) => "SELECT screening_reason AS reason, COUNT(*) AS n FROM source WHERE research_id=?1 AND screening IN ('screened_out','excluded') GROUP BY screening_reason ORDER BY screening_reason",
        None => "SELECT screening_reason AS reason, COUNT(*) AS n FROM source WHERE screening IN ('screened_out','excluded') GROUP BY screening_reason ORDER BY screening_reason",
    };
    let rows = match &research_id {
        Some(id) => query_json(conn, sql, params![id])?,
        None => query_json(conn, sql, [])?,
    };
    let mut reasons = serde_json::Map::new();
    for row in rows {
        let reason = field(&row, "reason");
        let key = if reason.is_empty() { "other".to_string() } else { reason };
        reasons.insert(key, row.get("n").cloned().unwrap_or(json!(0)));
    }
    let included = counts.get("included").and_then(Value::as_i64).unwrap_or(0);
    let fraction = if total == 0 { 0.0 } else { (included as f64 / total as f64 * 10000.0).round() / 10000.0 };
    Ok(json!({"counts": Value::Object(counts), "reasons": Value::Object(reasons),
        "total": total, "included": included, "included_fraction": fraction}))
}

pub fn findings_for_research(conn: &Connection, research_id: &str) -> Result<Vec<Value>> {
    let mut ids: BTreeSet<String> = BTreeSet::new();
    ids.insert(research_id.to_string());
    for table in ["claim", "question", "hypothesis", "source", "killtest", "ai_artifact"] {
        for row in query_json(conn, &format!("SELECT id FROM {table} WHERE research_id=?1"), params![research_id])? {
            ids.insert(field(&row, "id"));
        }
    }
    let members: Vec<String> = ids.iter().cloned().collect();
    if !members.is_empty() {
        let marks = vec!["?"; members.len()].join(", ");
        let sql = format!("SELECT id FROM edge WHERE src_id IN ({marks}) OR dst_id IN ({marks})");
        let bindings: Vec<&dyn rusqlite::ToSql> = members.iter().chain(members.iter())
            .map(|s| s as &dyn rusqlite::ToSql).collect();
        for row in query_json(conn, &sql, bindings.as_slice())? { ids.insert(field(&row, "id")); }
    }
    Ok(integrity::check(conn)?.into_iter()
        .filter(|f| ids.contains(&field(f, "subject"))).collect())
}

fn status_counts(conn: &Connection, research_id: &str) -> Result<Vec<String>> {
    let mut lines = Vec::new();
    for status in CLAIM_STATUSES {
        let n: i64 = conn.query_row(
            "SELECT COUNT(*) FROM claim WHERE research_id=?1 AND status=?2 AND (superseded_by IS NULL OR superseded_by='')",
            params![research_id, status], |r| r.get(0))?;
        if n > 0 { lines.push(format!("  claims {status}: {n}")); }
    }
    Ok(lines)
}

pub fn outline(conn: &Connection, reference: &str, budget: i64) -> Result<Value> {
    let research = get_research(conn, reference)?;
    let rid = field(&research, "id");
    let counts = research_counts(conn, &rid)?;
    let count = |key: &str| counts.get(key).and_then(Value::as_i64).unwrap_or(0);
    let mut lines = vec![
        format!("OUTLINE {} {}: {}", rid, field(&research, "slug"), sanitize(&field(&research, "title"), 80)),
        format!("  sources {} questions {} claims {} hypotheses {} tests {}",
            count("source"), count("question"), count("claim"), count("hypothesis"), count("killtest")),
    ];
    lines.extend(status_counts(conn, &rid)?);
    let flow = prisma_flow(conn, Some(&rid))?;
    if flow.get("total").and_then(Value::as_i64).unwrap_or(0) > 0 {
        lines.push(format!("  sources included {}/{} ({:.0}%)",
            flow.get("included").and_then(Value::as_i64).unwrap_or(0),
            flow.get("total").and_then(Value::as_i64).unwrap_or(0),
            flow.get("included_fraction").and_then(Value::as_f64).unwrap_or(0.0) * 100.0));
    }
    for row in query_json(conn, "SELECT * FROM question WHERE research_id=?1 ORDER BY id", params![rid])? {
        let qid = field(&row, "id");
        lines.push(format!("Q {} [{}] evidence={} consensus={} {}", qid, field(&row, "status"),
            stances(conn, &qid)?.len(), consensus_display(conn, &qid), sanitize(&field(&row, "text"), 90)));
    }
    for row in query_json(conn, "SELECT * FROM hypothesis WHERE research_id=?1 ORDER BY id", params![rid])? {
        lines.push(format!("H {} [{}] {:.2} {}", field(&row, "id"), field(&row, "status"),
            row.get("confidence").and_then(Value::as_f64).unwrap_or(0.0),
            sanitize(&field(&row, "statement"), 80)));
    }
    for row in query_json(conn, "SELECT * FROM killtest WHERE research_id=?1 ORDER BY id", params![rid])? {
        let id = field(&row, "id");
        let runs = list_runs(conn, Some(&id), 1)?;
        let latest = if runs.is_empty() { "never run".to_string() }
            else if runs[0].get("passed").and_then(Value::as_i64) == Some(1) { "pass".to_string() }
            else { "fail".to_string() };
        let target = {
            let claim = field(&row, "claim_id");
            if claim.is_empty() { field(&row, "hypothesis_id") } else { claim }
        };
        lines.push(format!("T {} {} -> {} {}", id, latest, target, sanitize(&field(&row, "name"), 60)));
    }
    let findings = findings_for_research(conn, &rid)?;
    let errors = findings.iter().filter(|f| field(f, "severity") == "error").count();
    let warnings = findings.iter().filter(|f| field(f, "severity") == "warning").count();
    lines.push(format!("  audit errors {errors} warnings {warnings}"));
    render(&lines, budget)
}

pub fn brief(conn: &Connection, reference: &str, budget: i64) -> Result<Value> {
    let research = get_research(conn, reference)?;
    let rid = field(&research, "id");
    let mut lines = vec![format!("BRIEF {} {}", rid, field(&research, "slug"))];
    for row in query_json(conn, "SELECT * FROM question WHERE research_id=?1 ORDER BY id", params![rid])? {
        let qid = field(&row, "id");
        let stances = stances(conn, &qid)?;
        lines.push(format!("Q {} consensus={} evidence={} {}", qid, consensus_display(conn, &qid),
            stances.len(), sanitize(&field(&row, "text"), 80)));
        for (label, wanted) in [("+", ["supports", "answers"].as_slice()), ("-", ["contradicts"].as_slice())] {
            let group: Vec<&Value> = stances.iter().filter(|(_, rel, _)| wanted.contains(&rel.as_str()))
                .map(|(_, _, row)| row).collect();
            if let Some(best) = group.into_iter().max_by(|a, b| {
                let pa = a.get("confidence").and_then(Value::as_f64).unwrap_or(0.0);
                let pb = b.get("confidence").and_then(Value::as_f64).unwrap_or(0.0);
                pa.partial_cmp(&pb).unwrap_or(std::cmp::Ordering::Equal)
            }) {
                lines.push(format!("  {} {} [{}] {:.2} {}", label, field(best, "id"), field(best, "status"),
                    best.get("confidence").and_then(Value::as_f64).unwrap_or(0.0),
                    sanitize(&field(best, "text"), 90)));
            }
        }
        if stances.is_empty() { lines.push("  no linked evidence".to_string()); }
    }
    render(&lines, budget)
}

pub fn claim_context(conn: &Connection, reference: &str, budget: i64) -> Result<Value> {
    let claim = get_claim(conn, reference)?;
    let id = field(&claim, "id");
    let mut lines = vec![
        format!("CLAIM {} [{}] confidence {:.2}", id, field(&claim, "status"),
            claim.get("confidence").and_then(Value::as_f64).unwrap_or(0.0)),
        format!("  {}", sanitize(&field(&claim, "text"), 160)),
        format!("  kind {} source {}", field(&claim, "kind"),
            if field(&claim, "source_id").is_empty() { "none".to_string() } else { field(&claim, "source_id") }),
    ];
    if !field(&claim, "quote").is_empty() { lines.push(format!("  quote {}", sanitize(&field(&claim, "quote"), 120))); }
    if !field(&claim, "locator").is_empty() { lines.push(format!("  locator {}", sanitize(&field(&claim, "locator"), 80))); }
    if !field(&claim, "kill_test").is_empty() { lines.push(format!("  kill test {}", sanitize(&field(&claim, "kill_test"), 120))); }
    for row in query_json(conn,
        "SELECT c.* FROM edge e JOIN claim c ON c.id=e.dst_id WHERE e.src_kind='claim' AND e.src_id=?1 AND e.dst_kind='claim' AND e.rel IN ('derived_from','depends_on') ORDER BY c.id",
        params![id])? {
        lines.push(format!("  premise {} [{}] {}", field(&row, "id"), field(&row, "status"),
            sanitize(&field(&row, "text"), 90)));
    }
    for row in query_json(conn,
        "SELECT status, evidence, at FROM verdict WHERE subject_kind='claim' AND subject_id=?1 ORDER BY id",
        params![id])? {
        lines.push(format!("  verdict {} at {} evidence {}", field(&row, "status"), field(&row, "at"),
            sanitize(&field(&row, "evidence"), 90)));
    }
    render(&lines, budget)
}
