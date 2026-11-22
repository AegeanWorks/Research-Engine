//! Evidence synthesis: graph-derived consensus and generated reports (G-006).

use rusqlite::{params, Connection};
use serde_json::{json, Value};

use crate::core::{get_research, research_counts};
use crate::error::{EngineError, Result};
use crate::markdown::{bullet, code, sanitize};
use crate::util::query_json;

fn cell(text: &str, width: usize) -> String {
    crate::markdown::cell(text, width)
}

fn field(value: &Value, name: &str) -> String {
    value.get(name).and_then(Value::as_str).unwrap_or("").to_string()
}

pub const LIMITS: &[&str] = &[
    "PROVEN records an evidence path and a named kill test; it is not a machine-checked proof.",
    "Consensus is a display heuristic over recorded stances; it never changes a verdict.",
    "Numeric evidence is current only while its verified run matches the engine code, declared inputs and command.",
    "UNKNOWN records that the evidence is missing; it never counts as support.",
    "A numeric test without a negative control has not shown that it can fail.",
    "Sources are registered explicitly; the engine performs no literature crawling.",
    "Single-writer SQLite; concurrent authorship is out of scope.",
];

const WEIGHTS: &[(&str, f64)] = &[
    ("PROVEN", 1.0), ("NUMERIC", 0.9), ("UNKNOWN", 0.0), ("UNVERIFIED", 0.4),
    ("FALSIFIED", 0.0), ("RETRACTED", 0.0), ("INVALIDATED", 0.0),
];
const COVERED: &[&str] = &["PROVEN", "NUMERIC", "FALSIFIED"];

pub fn stances(conn: &Connection, question_id: &str) -> Result<Vec<(String, String, Value)>> {
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

/// Python's `:.4g` general format for the numbers rendered into reports.
fn fmt_g(value: f64, precision: usize) -> String {
    if value == 0.0 { return "0".to_string(); }
    let exponent = value.abs().log10().floor() as i32;
    if exponent < -4 || exponent >= precision as i32 {
        let text = format!("{:.*e}", precision - 1, value);
        let (mantissa, exp) = text.split_once('e').unwrap_or((&text, "0"));
        let mantissa = mantissa.trim_end_matches('0').trim_end_matches('.');
        let exp_value: i32 = exp.parse().unwrap_or(0);
        format!("{mantissa}e{exp_value:+03}")
    } else {
        let decimals = (precision as i32 - 1 - exponent).max(0) as usize;
        let text = format!("{:.*}", decimals, value);
        if text.contains('.') { text.trim_end_matches('0').trim_end_matches('.').to_string() } else { text }
    }
}

fn provenance_cell(_conn: &Connection, row: &Value) -> String {
    if field(row, "kind") == "empirical" {
        format!("quote at {}", field(row, "locator"))
    } else if !field(row, "basis").is_empty() {
        field(row, "basis")
    } else if !field(row, "source_id").is_empty() {
        format!("source {}", field(row, "source_id"))
    } else { "-".to_string() }
    .chars().collect()
}

fn contradictions(_conn: &Connection, _question_id: &str, stances: &[(String, String, Value)]) -> Vec<(String, String)> {
    let supports: Vec<String> = stances.iter()
        .filter(|(_, rel, _)| rel == "supports" || rel == "answers")
        .map(|(id, _, _)| id.clone()).collect();
    let against: Vec<String> = stances.iter()
        .filter(|(_, rel, _)| rel == "contradicts")
        .map(|(id, _, _)| id.clone()).collect();
    supports.iter().flat_map(|a| against.iter().map(move |b| (a.clone(), b.clone()))).collect()
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
    let findings = crate::context::findings_for_research(conn, &rid)?;
    let errors = findings.iter().filter(|f| f.get("severity").and_then(Value::as_str) == Some("error")).count();
    let warnings = findings.iter().filter(|f| f.get("severity").and_then(Value::as_str) == Some("warning")).count();
    let mut lines = vec![
        format!("# {}", sanitize(&field(&research, "title"), 200)),
        String::new(),
        format!("**Program:** `{}` (`{}`)  ", rid, field(&research, "slug")),
        format!("**Scope:** {}  ", if field(&research, "scope").is_empty() { "not stated".to_string() } else { sanitize(&field(&research, "scope"), 400) }),
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
    let flow = crate::context::prisma_flow(conn, Some(&rid))?;
    if flow.get("total").and_then(Value::as_i64).unwrap_or(0) > 0 {
        lines.extend(["## Source screening".to_string(), String::new()]);
        let values: Vec<String> = flow.get("counts").and_then(Value::as_object)
            .map(|m| m.values().filter_map(|v| v.as_i64()).map(|n| n.to_string()).collect())
            .unwrap_or_default();
        lines.push(format!("| {} | included fraction |", values.join(" | ")));
        lines.push(format!("|{}|", "---|".repeat(values.len() + 1)));
        lines.push(format!("| {} | {:.2}% |", values.join(" | "),
            flow.get("included_fraction").and_then(Value::as_f64).unwrap_or(0.0) * 100.0));
        lines.push(String::new());
        let reasons = flow.get("reasons").and_then(Value::as_object).cloned().unwrap_or_default();
        if !reasons.is_empty() {
            let parts: Vec<String> = reasons.iter().map(|(name, value)|
                format!("{} ({})", cell(name, 160), value.as_i64().unwrap_or(0))).collect();
            lines.push(format!("Exclusions: {}", parts.join(", ")));
            lines.push(String::new());
        }
    }
    lines.extend(["## Questions".to_string(), String::new()]);
    let questions = query_json(conn, "SELECT * FROM question WHERE research_id=?1 ORDER BY id", params![rid])?;
    if questions.is_empty() { lines.push("_No questions recorded._".to_string()); }
    for question in &questions {
        let qid = field(question, "id");
        let stance_rows = stances(conn, &qid)?;
        lines.extend([
            format!("### {qid}: {}", bullet(&field(question, "text"), 160)),
            String::new(),
            format!("- status: {}", field(question, "status")),
            format!("- consensus: {} (support vs contradiction, weighted)", consensus_display(conn, &qid)),
            format!("- evidence: {} claim(s)", stance_rows.len()),
            String::new(),
        ]);
        if stance_rows.is_empty() {
            lines.push("_No claim is linked to this question._".to_string());
        } else {
            lines.extend([
                "| Claim | Stance | Status | Confidence | Assertion | Provenance |".to_string(),
                "|---|---|---|---|---|---|".to_string(),
            ]);
            for (claim_id, rel, row) in &stance_rows {
                lines.push(format!("| {} | {} | {} | {:.2} | {} | {} |", claim_id, rel,
                    field(row, "status"), row.get("confidence").and_then(Value::as_f64).unwrap_or(0.0),
                    cell(&field(row, "text"), 160), cell(&provenance_cell(conn, row), 160)));
            }
            lines.push(String::new());
        }
        let pairs = contradictions(conn, &qid, &stance_rows);
        if !pairs.is_empty() {
            let names: Vec<String> = pairs.iter().map(|(a, b)| format!("{a} vs {b}")).collect();
            lines.push(format!("**Contradictions:** {}", names.join(", ")));
            lines.push(String::new());
        }
    }
    lines.extend(["## Hypotheses".to_string(), String::new()]);
    let hypotheses = query_json(conn, "SELECT * FROM hypothesis WHERE research_id=?1 ORDER BY id", params![rid])?;
    if hypotheses.is_empty() { lines.push("_No hypotheses pre-registered._".to_string()); }
    for row in &hypotheses {
        lines.extend([
            format!("### {}: {}", field(row, "id"), bullet(&field(row, "statement"), 160)),
            String::new(),
            format!("- status: {}", field(row, "status")),
            format!("- confidence: {:.2}", row.get("confidence").and_then(Value::as_f64).unwrap_or(0.0)),
            format!("- registered: {}", field(row, "registered_at")),
            format!("- verification criterion: {}", bullet(&field(row, "criterion"), 400)),
            format!("- outcome note: {}", {
                let note = bullet(&field(row, "outcome_note"), 400);
                if note.is_empty() { "-".to_string() } else { note }
            }),
            String::new(),
        ]);
    }
    let calibration = crate::calibration::summary(conn, &rid, 10)?;
    if calibration.get("counts").and_then(|c| c.get("resolved")).and_then(Value::as_i64).unwrap_or(0) > 0 {
        lines.extend(["### Hypothesis calibration".to_string(), String::new()]);
        let counts_obj = calibration.get("counts").unwrap();
        lines.push(format!("- resolved: {} of {} (coverage {:.0}%)",
            counts_obj.get("resolved").and_then(Value::as_i64).unwrap_or(0),
            counts_obj.get("total").and_then(Value::as_i64).unwrap_or(0),
            calibration.get("coverage").and_then(Value::as_f64).unwrap_or(0.0) * 100.0));
        let skill = match calibration.get("skill") {
            Some(Value::Null) | None => "n/a".to_string(),
            Some(value) => format!("{:+.4}", value.as_f64().unwrap_or(0.0)),
        };
        for key in ["brier", "log_loss", "brier_baseline"] {
            let _ = key;
        }
        lines.push(format!("- Brier: {:.4}; log loss: {:.4}; baseline Brier: {:.4}; skill: {}",
            calibration.get("brier").and_then(Value::as_f64).unwrap_or(0.0),
            calibration.get("log_loss").and_then(Value::as_f64).unwrap_or(0.0),
            calibration.get("brier_baseline").and_then(Value::as_f64).unwrap_or(0.0), skill));
        for bin in calibration.get("bins").and_then(Value::as_array).into_iter().flatten() {
            if bin.get("n").and_then(Value::as_i64).unwrap_or(0) == 0 { continue; }
            lines.push(format!("- bin {:.1}-{:.1}: n={}, predicted {:.2}, observed {:.2}, gap {:+.2}",
                bin.get("low").and_then(Value::as_f64).unwrap_or(0.0),
                bin.get("high").and_then(Value::as_f64).unwrap_or(0.0),
                bin.get("n").and_then(Value::as_i64).unwrap_or(0),
                bin.get("mean_confidence").and_then(Value::as_f64).unwrap_or(0.0),
                bin.get("observed").and_then(Value::as_f64).unwrap_or(0.0),
                bin.get("gap").and_then(Value::as_f64).unwrap_or(0.0)));
        }
        for warning in calibration.get("warnings").and_then(Value::as_array).into_iter().flatten() {
            lines.push(format!("- warning: {}", warning.as_str().unwrap_or("")));
        }
        lines.push(String::new());
    }
    lines.extend(["## Kill tests".to_string(), String::new()]);
    let tests = query_json(conn, "SELECT * FROM killtest WHERE research_id=?1 ORDER BY id", params![rid])?;
    if tests.is_empty() {
        lines.push("_No executable kill tests._".to_string());
    } else {
        lines.extend(["| Test | Target | Command | Control | Latest run |".to_string(), "|---|---|---|---|---|".to_string()]);
        for row in &tests {
            let latest = query_json(conn,
                "SELECT * FROM test_run WHERE test_id=?1 AND role='main' ORDER BY id DESC LIMIT 1",
                params![field(row, "id")])?.into_iter().next();
            let outcome = match latest {
                None => "never run".to_string(),
                Some(run) => format!("{} (exit {})",
                    if run.get("passed").and_then(Value::as_i64) == Some(1) { "PASS" } else { "FAIL" },
                    run.get("exit_code").and_then(Value::as_i64).unwrap_or(0)),
            };
            let target = if !field(row, "claim_id").is_empty() { field(row, "claim_id") } else { field(row, "hypothesis_id") };
            let control = if field(row, "control_command").is_empty() { "none" } else { "declared" };
            lines.push(format!("| {} | {} | `{}` | {} | {} |", field(row, "id"), target,
                code(&field(row, "command"), 160), control, outcome));
        }
        lines.push(String::new());
    }
    lines.extend(["## Measurements".to_string(), String::new()]);
    let measured = query_json(conn, &(
        "SELECT claim_id, group_label, COUNT(*) AS n, AVG(value) AS mean, MIN(value) AS low, MAX(value) AS high,"
        .to_owned() + " GROUP_CONCAT(DISTINCT protocol_id) AS protocols, GROUP_CONCAT(DISTINCT unit) AS units,"
        + " GROUP_CONCAT(DISTINCT instrument_id) AS instruments, GROUP_CONCAT(DISTINCT provenance_class) AS classes"
        + " FROM observation WHERE research_id=?1 AND voided=0 GROUP BY claim_id, group_label ORDER BY claim_id, group_label"),
        params![rid])?;
    let main_rows: Vec<&Value> = measured.iter().filter(|r| !field(r, "classes").contains("self_reported")).collect();
    let self_rows: Vec<&Value> = measured.iter().filter(|r| field(r, "classes").contains("self_reported")).collect();
    if measured.is_empty() {
        lines.push("_No observations recorded._".to_string());
    } else {
        let header = [
            "| Claim | Group | n | min | mean | max | Protocol | Unit | Instrument | Class |".to_string(),
            "|---|---|---|---|---|---|---|---|---|---|".to_string(),
        ];
        if !main_rows.is_empty() {
            lines.extend(header.iter().cloned());
            for row in &main_rows { lines.push(measurement_row(row, false)); }
        }
        if !self_rows.is_empty() {
            lines.extend(["".to_string(), "### Self-reported measurements".to_string(), String::new()]);
            lines.extend(header.iter().cloned());
            for row in &self_rows { lines.push(measurement_row(row, true)); }
        }
        let events = query_json(conn,
            "SELECT subject, kind, at, detail FROM event WHERE research_id=?1 AND kind IN ('claim.stats','claim.trend') ORDER BY id",
            params![rid])?;
        let mut seen: Vec<(String, Value)> = Vec::new();
        for row in events {
            let subject = field(&row, "subject");
            if let Some(entry) = seen.iter_mut().find(|(id, _)| *id == subject) { entry.1 = row; }
            else { seen.push((subject, row)); }
        }
        seen.sort_by(|a, b| a.0.cmp(&b.0));
        for (claim_id, row) in &seen {
            lines.push(format!("- {} last {} at {}: {}", claim_id, field(row, "kind"), field(row, "at"),
                bullet(&field(row, "detail"), 200)));
        }
        lines.push(String::new());
    }
    lines.extend(["## Audit".to_string(), String::new()]);
    if findings.is_empty() { lines.push("_No integrity findings._".to_string()); }
    for finding in &findings {
        lines.push(format!("- **{} {}** `{}`: {}", field(finding, "severity").to_uppercase(),
            field(finding, "code"), field(finding, "subject"), sanitize(&field(finding, "message"), 400)));
    }
    lines.extend(["".to_string(), "## Limits".to_string(), String::new()]);
    for limit in LIMITS { lines.push(format!("- {limit}")); }
    Ok(lines.join("\n") + "\n")
}

fn measurement_row(row: &Value, self_reported: bool) -> String {
    let class = field(row, "classes");
    let class_cell = if self_reported { class } else if class.is_empty() { "-".to_string() } else { class };
    let protocols = { let v = field(row, "protocols"); if v.is_empty() { "-".to_string() } else { v } };
    let units = { let v = field(row, "units"); if v.is_empty() { "-".to_string() } else { v } };
    let instruments = { let v = field(row, "instruments"); if v.is_empty() { "-".to_string() } else { v } };
    format!("| {} | {} | {} | {} | {} | {} | {} | {} | {} | {} |",
        field(row, "claim_id"), cell(&field(row, "group_label"), 40),
        row.get("n").and_then(Value::as_i64).unwrap_or(0),
        fmt_g(row.get("low").and_then(Value::as_f64).unwrap_or(0.0), 4),
        fmt_g(row.get("mean").and_then(Value::as_f64).unwrap_or(0.0), 4),
        fmt_g(row.get("high").and_then(Value::as_f64).unwrap_or(0.0), 4),
        cell(&protocols, 40), cell(&units, 20), cell(&instruments, 40), class_cell)
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
            row.get("confidence").and_then(Value::as_f64).unwrap_or(0.0), cell(&field(&row, "text"), 160)));
    }
    Ok(lines.join("\n") + "\n")
}
