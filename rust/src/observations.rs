//! Recorded observations: finite measurements in named groups (engine/observations.py).

use rusqlite::{params, Connection};
use serde_json::{json, Value};

use crate::core::{get_claim, record_event};
use crate::db::{next_id, utc_now};
use crate::error::{EngineError, Result};
use crate::protocols::get_protocol;
use crate::util::query_json;
use crate::vocab::{AGGREGATIONS, INSTRUMENT_KINDS, PROVENANCE_CLASSES, RATER_KINDS};

pub const CSV_TEMPLATE_HEADER: &str = "group_label,value,note,instrument_kind,instrument_id,instrument_digest,rater_kind,rater_id,rater_version,protocol_id,sample_size,aggregation,unit,provenance_class,producer_path,producer_digest";

fn field(value: &Value, name: &str) -> String {
    value.get(name).and_then(Value::as_str).unwrap_or("").to_string()
}

fn hex_sha256(value: &str) -> bool {
    value.len() == 64 && value.bytes().all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
}

#[allow(clippy::too_many_arguments)]
pub fn add(
    conn: &Connection,
    claim_ref: &str,
    group_label: &str,
    value: f64,
    note: &str,
    instrument_kind: &str,
    instrument_id: &str,
    instrument_digest: &str,
    rater_kind: &str,
    rater_id: &str,
    rater_version: &str,
    protocol_id: &str,
    sample_size: i64,
    aggregation: &str,
    unit: &str,
    provenance_class: &str,
    producer_path: &str,
    producer_digest: &str,
) -> Result<Value> {
    let claim = get_claim(conn, claim_ref)?;
    if !field(&claim, "superseded_by").is_empty() {
        return Err(EngineError::new(
            format!("claim {} is superseded by {}", field(&claim, "id"), field(&claim, "superseded_by")),
            "a measurement on history cannot support the live graph.",
            "record the measurement on the current head.",
        ));
    }
    let label = group_label.trim().to_lowercase();
    if label.is_empty() {
        return Err(EngineError::new("observation has no group",
            "a measurement is only comparable inside a named group such as `baseline`.",
            "pass --group with a label."));
    }
    if !label.chars().all(|c| c.is_ascii_alphanumeric() || c == '-' || c == '_') {
        return Err(EngineError::new(format!("invalid group label: {group_label}"),
            "group labels are letters, digits, hyphens and underscores.",
            "use a label such as `baseline` or `treatment-2`."));
    }
    if !value.is_finite() {
        return Err(EngineError::new(format!("observation value is not finite: {value}"),
            "NaN and infinity cannot enter a mean or an interval.",
            "record the missing value as an observation note instead, or omit it."));
    }
    let provenance = [instrument_kind, instrument_id, instrument_digest, rater_kind,
        rater_id, rater_version, protocol_id];
    let (instrument_kind, instrument_id, instrument_digest, rater_kind, rater_id,
        rater_version, protocol_id) = if provenance.iter().any(|v| !v.trim().is_empty()) {
        let names = ["instrument_kind", "instrument_id", "instrument_digest", "rater_kind",
            "rater_id", "rater_version", "protocol_id"];
        let missing: Vec<&str> = names.iter().zip(provenance.iter())
            .filter(|(_, v)| v.trim().is_empty()).map(|(n, _)| *n).collect();
        if !missing.is_empty() {
            return Err(EngineError::new("measurement provenance is incomplete",
                format!("missing: {}.", missing.join(", ")),
                "pass the instrument, rater and protocol together, or none of them."));
        }
        let instrument_kind = instrument_kind.trim().to_lowercase();
        let rater_kind = rater_kind.trim().to_lowercase();
        if !INSTRUMENT_KINDS.contains(&instrument_kind.as_str()) {
            return Err(EngineError::new(format!("unknown instrument kind: {instrument_kind}"),
                format!("allowed kinds are {}.", INSTRUMENT_KINDS.join(", ")),
                "pass one of the listed kinds."));
        }
        if !RATER_KINDS.contains(&rater_kind.as_str()) {
            return Err(EngineError::new(format!("unknown rater kind: {rater_kind}"),
                format!("allowed kinds are {}.", RATER_KINDS.join(", ")),
                "pass one of the listed kinds."));
        }
        let protocol_id = protocol_id.trim().to_lowercase();
        get_protocol(conn, &protocol_id)?;
        (instrument_kind, instrument_id.trim().to_string(), instrument_digest.trim().to_string(),
            rater_kind, rater_id.trim().to_string(), rater_version.trim().to_string(), protocol_id)
    } else {
        (String::new(), String::new(), String::new(), String::new(), String::new(),
            String::new(), String::new())
    };
    if sample_size < 1 {
        return Err(EngineError::new(format!("sample size must be positive: {sample_size}"),
            "an aggregate over zero observations has no value.",
            "pass --sample-size 1 or more."));
    }
    let aggregation = {
        let a = aggregation.trim().to_lowercase();
        if a.is_empty() { "raw".to_string() } else { a }
    };
    if !AGGREGATIONS.contains(&aggregation.as_str()) {
        return Err(EngineError::new(format!("unknown aggregation: {aggregation}"),
            format!("allowed aggregations are {}.", AGGREGATIONS.join(", ")),
            "pass one of the listed aggregations."));
    }
    let unit = unit.trim();
    let provenance_class = {
        let p = provenance_class.trim().to_lowercase();
        if p.is_empty() { "unclassified".to_string() } else { p }
    };
    if !PROVENANCE_CLASSES.contains(&provenance_class.as_str()) {
        return Err(EngineError::new(format!("unknown provenance class: {provenance_class}"),
            "allowed classes are independent, self_reported and unclassified.",
            "pass one of the listed classes."));
    }
    let producer_path = producer_path.trim();
    let producer_digest = producer_digest.trim();
    if provenance_class == "self_reported" && producer_path.is_empty() {
        return Err(EngineError::new("self-reported measurement has no producer path",
            "a self-reported number must name the component that produced it.",
            "pass --producer-path with the module or script that generated the value."));
    }
    if !producer_digest.is_empty() && !hex_sha256(producer_digest) {
        return Err(EngineError::new("producer digest is not a SHA-256 hex string",
            "a producer is pinned by a 64-character lowercase hex digest.",
            "pass the digest of the producer, or omit --producer-digest."));
    }
    let tx = conn.unchecked_transaction()?;
    let id = next_id(&tx, "ob")?;
    tx.execute(
        "INSERT INTO observation(id, research_id, claim_id, group_label, value, note, at, voided, void_reason, instrument_kind, instrument_id, instrument_digest, rater_kind, rater_id, rater_version, protocol_id, sample_size, aggregation, unit, provenance_class, producer_path, producer_digest) VALUES (?1,?2,?3,?4,?5,?6,?7,0,'',?8,?9,?10,?11,?12,?13,?14,?15,?16,?17,?18,?19,?20)",
        params![id, field(&claim, "research_id"), field(&claim, "id"), label, value, note.trim(),
            utc_now(), instrument_kind, instrument_id, instrument_digest, rater_kind, rater_id,
            rater_version, protocol_id, sample_size, aggregation, unit, provenance_class,
            producer_path, producer_digest],
    )?;
    tx.commit()?;
    get_observation(conn, &id)
}

pub fn get_observation(conn: &Connection, reference: &str) -> Result<Value> {
    let rows = query_json(conn, "SELECT * FROM observation WHERE id=?1", params![reference])?;
    rows.into_iter().next().ok_or_else(|| EngineError::not_found("observation", reference))
}

pub fn list_observations(
    conn: &Connection,
    claim_ref: &str,
    group: Option<&str>,
    include_voided: bool,
) -> Result<Vec<Value>> {
    let claim = get_claim(conn, claim_ref)?;
    let mut sql = String::from("SELECT * FROM observation WHERE claim_id=?1");
    let mut bindings: Vec<Box<dyn rusqlite::ToSql>> = vec![Box::new(field(&claim, "id"))];
    if let Some(group) = group {
        sql.push_str(" AND group_label=?2");
        bindings.push(Box::new(group.trim().to_lowercase()));
    }
    if !include_voided {
        sql.push_str(" AND voided=0");
    }
    sql.push_str(" ORDER BY id");
    let args: Vec<&dyn rusqlite::ToSql> = bindings.iter().map(|b| b.as_ref()).collect();
    query_json(conn, &sql, args.as_slice())
}

pub fn void_observation(conn: &Connection, reference: &str, reason: &str, actor: &str) -> Result<Value> {
    let observation = get_observation(conn, reference)?;
    if observation.get("voided").and_then(Value::as_i64) == Some(1) {
        return Err(EngineError::new(format!("observation already voided: {reference}"),
            "a void is recorded once and never rewritten.", "inspect the observation instead."));
    }
    let reason = reason.trim();
    if reason.is_empty() {
        return Err(EngineError::new("void has no reason",
            "a measurement is only retired with a recorded reason.",
            "pass --reason with the transcription error or exclusion criterion."));
    }
    let tx = conn.unchecked_transaction()?;
    tx.execute("UPDATE observation SET voided=1, void_reason=?1 WHERE id=?2",
        params![reason, field(&observation, "id")])?;
    record_event(&tx, &field(&observation, "research_id"), "observation.void",
        &field(&observation, "id"),
        &format!("claim {}: {reason}", field(&observation, "claim_id")), actor)?;
    tx.commit()?;
    get_observation(conn, &field(&observation, "id"))
}

/// Non-voided values per group in insertion order, optionally time-bounded.
pub fn group_values(
    conn: &Connection,
    claim_ref: &str,
    since: Option<&str>,
    until: Option<&str>,
) -> Result<Vec<(String, Vec<f64>)>> {
    let claim = get_claim(conn, claim_ref)?;
    let mut sql = String::from("SELECT group_label, value FROM observation WHERE claim_id=?1 AND voided=0");
    let mut bindings: Vec<Box<dyn rusqlite::ToSql>> = vec![Box::new(field(&claim, "id"))];
    if let Some(since) = since { sql.push_str(" AND at>=?2"); bindings.push(Box::new(since.to_string())); }
    if let Some(until) = until { sql.push_str(" AND at<=?3"); bindings.push(Box::new(until.to_string())); }
    sql.push_str(" ORDER BY id");
    let args: Vec<&dyn rusqlite::ToSql> = bindings.iter().map(|b| b.as_ref()).collect();
    let rows = query_json(conn, &sql, args.as_slice())?;
    let mut groups: Vec<(String, Vec<f64>)> = Vec::new();
    for row in rows {
        let label = field(&row, "group_label");
        let value = row.get("value").and_then(Value::as_f64).unwrap_or(0.0);
        if let Some((_, values)) = groups.iter_mut().find(|(name, _)| *name == label) {
            values.push(value);
        } else {
            groups.push((label, vec![value]));
        }
    }
    Ok(groups)
}

fn parse_csv(text: &str) -> Vec<Vec<String>> {
    let mut rows = Vec::new();
    let mut row = Vec::new();
    let mut cell = String::new();
    let mut quoted = false;
    let mut chars = text.chars().peekable();
    while let Some(c) = chars.next() {
        if quoted {
            if c == '"' {
                if chars.peek() == Some(&'"') { chars.next(); cell.push('"'); }
                else { quoted = false; }
            } else { cell.push(c); }
        } else if c == '"' && cell.trim().is_empty() {
            quoted = true;
        } else if c == ',' {
            row.push(std::mem::take(&mut cell));
        } else if c == '\n' || c == '\r' {
            if c == '\r' && chars.peek() == Some(&'\n') { chars.next(); }
            row.push(std::mem::take(&mut cell));
            if row.iter().any(|v| !v.trim().is_empty()) { rows.push(std::mem::take(&mut row)); }
            else { row.clear(); }
        } else {
            cell.push(c);
        }
    }
    if !cell.is_empty() || !row.is_empty() {
        row.push(cell);
        rows.push(row);
    }
    rows
}

pub fn import_csv(
    conn: &Connection,
    claim_ref: &str,
    path: &str,
    dry_run: bool,
) -> Result<Value> {
    let text = std::fs::read_to_string(path).map_err(|_| EngineError::new(
        format!("observations CSV cannot be read: {path}"),
        "a bulk import needs a readable UTF-8 file.", "check the path and retry."))?;
    let rows = parse_csv(text.trim_start_matches('\u{feff}'));
    let header = rows.first().ok_or_else(|| EngineError::new(
        format!("observations CSV has no header: {path}"),
        "a bulk import needs named columns to mean anything.",
        "add a header row with group_label,value and retry."))?;
    let normalized: Vec<String> = header.iter().map(|h| h.trim().to_lowercase()).collect();
    let group_index = ["group_label", "group"].iter().find_map(|k| normalized.iter().position(|n| n == k));
    let value_index = normalized.iter().position(|n| n == "value");
    let (Some(group_index), Some(value_index)) = (group_index, value_index) else {
        return Err(EngineError::new(
            "observations CSV must contain columns ['group_label', 'group'] and value",
            "a measurement is only comparable inside a named group.",
            "add group_label,value columns and retry."));
    };
    let cell = |row: &[String], names: &[&str]| -> String {
        for name in names {
            if let Some(index) = normalized.iter().position(|n| n == name) {
                if let Some(value) = row.get(index) {
                    if !value.trim().is_empty() { return value.trim().to_string(); }
                }
            }
        }
        String::new()
    };
    let mut imported = 0usize;
    let mut skipped: Vec<Value> = Vec::new();
    let tx = conn.unchecked_transaction()?;
    for (line_number, row) in rows.iter().enumerate().skip(1) {
        let group = row.get(group_index).cloned().unwrap_or_default();
        let raw_value = row.get(value_index).cloned().unwrap_or_default();
        if group.trim().is_empty() && raw_value.trim().is_empty() { continue; }
        let value: f64 = match raw_value.trim().parse() {
            Ok(number) => number,
            Err(_) => {
                skipped.push(json!({"line": line_number + 1, "reason": "value is not a number"}));
                continue;
            }
        };
        let sample: i64 = cell(row, &["sample_size"]).parse().unwrap_or(1);
        let result = add(&tx, claim_ref, &group, value, &cell(row, &["note"]),
            &cell(row, &["instrument_kind"]), &cell(row, &["instrument_id"]),
            &cell(row, &["instrument_digest"]), &cell(row, &["rater_kind"]),
            &cell(row, &["rater_id"]), &cell(row, &["rater_version"]),
            &cell(row, &["protocol_id", "protocol"]), sample,
            &cell(row, &["aggregation"]), &cell(row, &["unit"]),
            &cell(row, &["provenance_class"]), &cell(row, &["producer_path"]),
            &cell(row, &["producer_digest"]));
        match result {
            Ok(_) => imported += 1,
            Err(error) => skipped.push(json!({"line": line_number + 1, "reason": error.what})),
        }
    }
    if dry_run { tx.rollback()?; } else { tx.commit()?; }
    Ok(json!({"imported": imported, "skipped": skipped, "dry_run": dry_run}))
}
