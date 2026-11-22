//! Lattice integrity gate (adapters/lattice/checks.py).

use std::collections::{BTreeMap, BTreeSet};

use regex::Regex;
use rusqlite::Connection;
use serde_json::{json, Value};

use crate::lattice::normalize_text;
use crate::lattice_repo::SCHEMA_VERSION;
use crate::util::query_json;

fn field(value: &Value, name: &str) -> String {
    value.get(name).and_then(Value::as_str).unwrap_or("").to_string()
}

fn issue(level: &str, code: &str, message: String, errors: &mut Vec<Value>, warnings: &mut Vec<Value>) {
    let value = json!({"level": level, "code": code, "message": message});
    if level == "error" { errors.push(value); } else { warnings.push(value); }
}

pub fn run_checks(conn: &Connection) -> Value {
    let mut errors = Vec::new();
    let mut warnings = Vec::new();
    let schema = conn.query_row("SELECT value FROM meta WHERE key='schema_version'", [],
        |r| r.get::<_, String>(0)).unwrap_or_default();
    if schema != SCHEMA_VERSION.to_string() {
        issue("error", "schema.version",
            format!("schema version {schema} does not match the supported {SCHEMA_VERSION}"),
            &mut errors, &mut warnings);
    }

    let claims = query_json(conn, &(
        "SELECT c.id, c.text, c.quote, c.locator, c.paper_id, p.id AS found,"
        .to_owned() + ", p.title AS paper_title, p.abstract AS paper_abstract"
        + " FROM claims c LEFT JOIN papers p ON p.id=c.paper_id"), []).unwrap_or_default();
    for row in &claims {
        let id = field(row, "id");
        if field(row, "text").trim().is_empty() || field(row, "quote").trim().is_empty() {
            issue("error", "claim.provenance", format!("{id} has empty text or quote; every claim needs both"), &mut errors, &mut warnings);
        }
        if field(row, "locator").trim().is_empty() {
            issue("error", "claim.locator_missing", format!("{id} has no locator; no locator, no entry"), &mut errors, &mut warnings);
        }
        if field(row, "found").is_empty() {
            issue("error", "claim.source",
                format!("{id} points at missing paper {}", field(row, "paper_id")), &mut errors, &mut warnings);
            continue;
        }
        let locator: String = field(row, "locator").split_whitespace().collect::<Vec<_>>().join(" ");
        if !locator.starts_with("text:") {
            let quote = normalize_text(&field(row, "quote"));
            let haystack = normalize_text(&format!("{} {}", field(row, "paper_title"), field(row, "paper_abstract")));
            if !quote.is_empty() && !haystack.contains(&quote) {
                issue("error", "claim.quote_drift",
                    format!("{id} quote no longer matches paper {} (drifted or key_findings-only)", field(row, "paper_id")),
                    &mut errors, &mut warnings);
            }
        }
        let re = Regex::new(r"(abstract|text)(?::s(\d+))?").unwrap();
        if let Some(captures) = re.captures(&locator) {
            if captures.get(0).map(|m| m.as_str()) != Some(locator.as_str()) { continue; }
            let source = captures.get(1).map(|m| m.as_str()).unwrap_or("");
            if let Some(number) = captures.get(2).and_then(|m| m.as_str().parse::<i64>().ok()) {
                if number < 1 {
                    issue("error", "claim.locator_unresolvable",
                        format!("{id} locator {locator:?} is out of range"), &mut errors, &mut warnings);
                } else if source == "abstract" {
                    let abstract_text = field(row, "paper_abstract");
                    let sentences: Vec<&str> = abstract_text.split(". ").filter(|s| !s.trim().is_empty()).collect();
                    let total = sentences.len().max(1) as i64;
                    if number > total {
                        issue("error", "claim.locator_unresolvable",
                            format!("{id} locator {locator:?} is rotted (abstract has {total} sentence(s))"),
                            &mut errors, &mut warnings);
                    }
                }
            } else if source == "abstract" {
                let quote = normalize_text(&field(row, "quote"));
                let haystack = normalize_text(&field(row, "paper_abstract"));
                if !quote.is_empty() && !haystack.contains(&quote) {
                    issue("error", "claim.locator_unresolvable",
                        format!("{id} locator 'abstract' does not resolve (quote not in abstract)"),
                        &mut errors, &mut warnings);
                }
            }
        }
    }

    for column in ["doi", "arxiv"] {
        for row in query_json(conn,
            &format!("SELECT lower({column}) AS value, COUNT(*) AS n FROM papers WHERE {column} != '' GROUP BY lower({column}) HAVING n > 1"),
            []).unwrap_or_default() {
            issue("error", format!("paper.duplicate_{column}").as_str(),
                format!("{} papers share {} '{}'", row.get("n").and_then(Value::as_i64).unwrap_or(0),
                    column, field(&row, "value")), &mut errors, &mut warnings);
        }
    }
    let mut title_groups: BTreeMap<String, Vec<String>> = BTreeMap::new();
    for row in query_json(conn, "SELECT id, title, year FROM papers", []).unwrap_or_default() {
        let key = format!("{}|{}", normalize_text(&field(&row, "title")), field(&row, "year"));
        title_groups.entry(key).or_default().push(field(&row, "id"));
    }
    for (key, ids) in title_groups {
        if ids.len() > 1 {
            issue("error", "paper.duplicate_title",
                format!("normalized title/year {:?} is shared by {}", key.split('|').next().unwrap_or(""),
                    ids.join(", ")), &mut errors, &mut warnings);
        }
    }

    let endpoints: BTreeSet<String> = ["papers", "claims", "questions"].iter()
        .flat_map(|table| query_json(conn, &format!("SELECT id FROM {table}"), [])
            .unwrap_or_default().into_iter().map(|r| field(&r, "id")))
        .collect();
    for row in query_json(conn, "SELECT id, src, dst FROM edges ORDER BY id", []).unwrap_or_default() {
        for reference in [field(&row, "src"), field(&row, "dst")] {
            let id = field(&row, "id");
            let exists = endpoints.contains(reference.trim_start_matches(|c: char| !c.is_ascii_alphanumeric() && c != '_').trim_start_matches("paper:").trim_start_matches("claim:").trim_start_matches("question:"))
                || reference.split(':').nth(1).map(|bare| endpoints.contains(bare)).unwrap_or(false);
            if !exists {
                issue("error", "edge.endpoint", format!("edge {id} names missing endpoint {reference}"),
                    &mut errors, &mut warnings);
            }
        }
    }

    let passed = errors.is_empty();
    json!({"passed": passed, "errors": errors, "warnings": warnings})
}
