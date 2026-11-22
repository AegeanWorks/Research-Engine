//! Deterministic lexical graph search, ported from `engine/search.py`.

use rusqlite::Connection;
use serde_json::{json, Map, Value};

use crate::core::get_research;
use crate::error::{EngineError, Result};
use crate::markdown::{estimate_tokens, pack, sanitize};
use crate::util::query_json;

const KINDS: &[&str] = &["claim", "source", "question", "hypothesis"];
const STOPWORDS: &[&str] = &[
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from", "has", "have",
    "if", "in", "into", "is", "it", "its", "of", "on", "or", "that", "the", "their", "then",
    "there", "these", "this", "to", "was", "were", "will", "with",
];

fn field(value: &Value, name: &str) -> String {
    value.get(name).and_then(Value::as_str).unwrap_or("").to_string()
}

fn words(query: &str) -> Vec<String> {
    let mut result = Vec::new();
    let mut current = String::new();
    for c in query.chars() {
        if c.is_alphanumeric() && c != '_' {
            current.push(c.to_lowercase().next().unwrap_or(c));
        } else if !current.is_empty() {
            if current.chars().count() >= 2 { result.push(std::mem::take(&mut current)); }
            else { current.clear(); }
        }
    }
    if current.chars().count() >= 2 { result.push(current); }
    let mut unique = Vec::new();
    for word in result { if !unique.contains(&word) { unique.push(word); } }
    let content: Vec<String> = unique.iter().filter(|w| !STOPWORDS.contains(&w.as_str())).cloned().collect();
    if content.is_empty() { unique } else { content }
}

fn score(needle: &str, terms: &[String], blob: &str, primary: &str) -> (i64, Vec<String>) {
    let mut value = 0i64;
    if !needle.is_empty() && blob.contains(needle) { value += 100; }
    if !needle.is_empty() && primary.contains(needle) { value += 50; }
    let matched: Vec<String> = terms.iter().filter(|term| blob.contains(term.as_str())).cloned().collect();
    if !matched.is_empty() {
        value += matched.iter().map(|term| if primary.contains(term.as_str()) { 3 } else { 1 }).sum::<i64>();
    }
    (value, matched)
}

fn snippet(text: &str, needle: &str, terms: &[String]) -> String {
    let flat = text.split_whitespace().collect::<Vec<_>>().join(" ");
    if flat.is_empty() { return String::new(); }
    let lower = flat.to_lowercase();
    let mut positions = Vec::new();
    for candidate in std::iter::once(needle).chain(terms.iter().map(String::as_str)) {
        if candidate.is_empty() { continue; }
        if let Some(index) = lower.find(candidate) { positions.push(index); }
    }
    let position = positions.iter().copied().min().unwrap_or(0);
    let mut start = position.saturating_sub(120 / 3);
    let mut end = (start + 120).min(flat.len());
    if start > 0 {
        if let Some(space) = flat[..start].rfind(' ') {
            if start - space <= 20 { start = space + 1; }
        }
    }
    if end < flat.len() {
        if let Some(space) = flat[end..].find(' ') {
            if space <= 20 { end += space; }
        }
    }
    let prefix = if start > 0 { "…" } else { "" };
    let suffix = if end < flat.len() { "…" } else { "" };
    sanitize(&format!("{prefix}{}{suffix}", &flat[start..end]), 122)
}

fn fields(kind: &str, row: &Value) -> Vec<(String, String)> {
    let pair = |name: &str| (name.to_string(), field(row, name));
    match kind {
        "claim" => vec![pair("text"), pair("quote"), pair("basis"), pair("kill_test"), pair("locator")],
        "source" => vec![pair("title"), pair("authors"), pair("doi"), pair("url"), pair("kind")],
        "question" => vec![pair("text")],
        _ => vec![pair("statement"), pair("criterion"), pair("outcome_note")],
    }
}

#[allow(clippy::too_many_arguments)]
pub fn search(
    conn: &Connection,
    query: &str,
    research_ref: Option<&str>,
    kinds: Option<&[String]>,
    limit: i64,
    include_superseded: bool,
    budget: i64,
) -> Result<Value> {
    let value = query.split_whitespace().collect::<Vec<_>>().join(" ");
    if value.is_empty() {
        return Err(EngineError::new("search query is empty",
            "an empty query would match every record and rank nothing.", "pass a word or phrase."));
    }
    if limit < 1 || budget < 1 {
        return Err(EngineError::new(format!("invalid search bounds: limit={limit}, budget={budget}"),
            "a result set and a text view both need positive bounds.", "pass --limit 1 and --budget 1 or more."));
    }
    let selected: Vec<String> = match kinds {
        Some(kinds) => kinds.to_vec(),
        None => KINDS.iter().map(|k| k.to_string()).collect(),
    };
    for kind in &selected {
        if !KINDS.contains(&kind.as_str()) {
            return Err(EngineError::new(format!("unknown search kind: {kind}"),
                format!("allowed kinds are {}.", KINDS.join(", ")),
                "pass one of the listed kinds with --kind."));
        }
    }
    let research_id = match research_ref {
        Some(reference) => Some(field(&get_research(conn, reference)?, "id")),
        None => None,
    };
    let needle = value.to_lowercase();
    let terms = words(&value);
    let mut found: Vec<Value> = Vec::new();
    let mut counts: Map<String, Value> = Map::new();
    for kind in &selected {
        let mut sql = format!("SELECT * FROM {kind} WHERE 1=1");
        let mut bindings: Vec<Box<dyn rusqlite::ToSql>> = Vec::new();
        if let Some(rid) = &research_id { sql.push_str(" AND research_id=?"); bindings.push(Box::new(rid.clone())); }
        if kind == "claim" && !include_superseded { sql.push_str(" AND superseded_by IS NULL"); }
        sql.push_str(" ORDER BY id");
        let args: Vec<&dyn rusqlite::ToSql> = bindings.iter().map(|b| b.as_ref()).collect();
        let rows = query_json(conn, &sql, args.as_slice())?;
        let mut hits: Vec<(i64, String, Value)> = Vec::new();
        for row in rows {
            let props = fields(kind, &row);
            let blob = props.iter().map(|(_, text)| text.as_str()).collect::<Vec<_>>().join(" ").to_lowercase();
            let primary = props.first().map(|(_, text)| text.to_lowercase()).unwrap_or_default();
            let (points, matched) = score(&needle, &terms, &blob, &primary);
            if points <= 0 { continue; }
            let mut chosen = props.first().cloned().unwrap_or_default();
            for (name, candidate) in &props {
                let lowered = candidate.to_lowercase();
                if (!needle.is_empty() && lowered.contains(&needle)) || terms.iter().any(|t| lowered.contains(t)) {
                    chosen = (name.clone(), candidate.clone());
                    break;
                }
            }
            let status = if kind == "hypothesis" { field(&row, "status") } else { field(&row, "status") };
            let hit = json!({
                "kind": kind, "id": field(&row, "id"), "score": points, "status": status,
                "field": chosen.0, "snippet": snippet(&chosen.1, &needle, &terms), "matched": matched,
            });
            hits.push((points, field(&row, "id"), hit));
        }
        hits.sort_by(|a, b| (-a.0, &a.1).cmp(&(-b.0, &b.1)));
        counts.insert(kind.clone(), json!({"hits": hits.len(), "returned": hits.len().min(limit as usize)}));
        for (_, _, hit) in hits.into_iter().take(limit as usize) { found.push(hit); }
    }
    let order = |kind: &str| KINDS.iter().position(|k| *k == kind).unwrap_or(99);
    found.sort_by(|a, b| {
        let sa = a.get("score").and_then(Value::as_i64).unwrap_or(0);
        let sb = b.get("score").and_then(Value::as_i64).unwrap_or(0);
        (-sa, order(a.get("kind").and_then(Value::as_str).unwrap_or("")),
            field(a, "id")).cmp(&(-sb, order(b.get("kind").and_then(Value::as_str).unwrap_or("")), field(b, "id")))
    });
    let total_hits: usize = counts.values().filter_map(|v| v.get("hits").and_then(Value::as_u64)).sum::<u64>() as usize;
    let returned = found.len();
    let mut lines = vec![format!("SEARCH \"{}\": {total_hits} hit(s), {returned} result(s)", sanitize(&value, 80))];
    for item in &found {
        lines.push(format!("  {} {} [{}] score={} {}: {}", field(item, "kind"), field(item, "id"),
            if field(item, "status").is_empty() { "-".to_string() } else { field(item, "status") },
            item.get("score").and_then(Value::as_i64).unwrap_or(0), field(item, "field"), field(item, "snippet")));
    }
    let (kept, omitted, _) = pack(&lines, budget as usize);
    let mut text = kept.join("\n");
    text.push('\n');
    if omitted > 0 {
        text.push_str(&format!("OMITTED: {omitted} more line(s); raise --budget to see them\n"));
    }
    Ok(json!({
        "query": value,
        "research": research_id.unwrap_or_else(|| "all".to_string()),
        "budget_tokens": budget,
        "tokens": estimate_tokens(&text),
        "counts": counts,
        "results": found,
        "omitted": total_hits - returned,
        "budget_omitted": omitted,
        "text": text,
    }))
}
