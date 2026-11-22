//! Immutable measurement protocol registry, ported from `engine/protocols.py`.

use rusqlite::{params, Connection};
use serde_json::Value;

use crate::core::record_event;
use crate::db::{next_id, utc_now};
use crate::error::{EngineError, Result};
use crate::util::{query_json, sha256_bytes};

fn field(value: &Value, name: &str) -> String {
    value.get(name).and_then(Value::as_str).unwrap_or("").to_string()
}

fn hex_sha256(value: &str) -> bool {
    value.len() == 64 && value.bytes().all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
}

pub fn get_protocol(conn: &Connection, reference: &str) -> Result<Value> {
    let rows = query_json(conn, "SELECT * FROM protocol WHERE id=?1", params![reference.trim().to_lowercase()])?;
    rows.into_iter().next().ok_or_else(|| EngineError::not_found("protocol", reference))
}

pub fn list_protocols(conn: &Connection) -> Result<Vec<Value>> {
    query_json(conn, "SELECT * FROM protocol ORDER BY id", [])
}

#[allow(clippy::too_many_arguments)]
pub fn register(
    conn: &Connection,
    id: &str,
    measures: &str,
    includes_generation: bool,
    includes_judge: bool,
    doc_digest: &str,
    doc_path: &str,
    actor: &str,
) -> Result<Value> {
    let id = id.trim().to_lowercase();
    // The regex is `[a-z0-9][a-z0-9_-]*` with a full match; spelling out the
    // first-character check avoids a regex dependency.
    let valid = {
        let mut chars = id.chars();
        match chars.next() {
            Some(first) if first.is_ascii_lowercase() || first.is_ascii_digit() => {
                chars.all(|c| c.is_ascii_lowercase() || c.is_ascii_digit() || c == '-' || c == '_')
            }
            _ => false,
        }
    };
    if !valid {
        return Err(EngineError::new(format!("invalid protocol id: {id}"),
            "a protocol id is lowercase letters, digits, hyphens and underscores.",
            "use an id such as `accuracy_at_1` or `end_to_end_judge`."));
    }
    let measures = measures.trim();
    if measures.is_empty() {
        return Err(EngineError::new("protocol has no measures text",
            "a protocol must state what it measures end to end.",
            "pass --measures with a short description."));
    }
    let mut doc_digest = doc_digest.trim().to_string();
    let doc_path = doc_path.trim();
    if !doc_path.is_empty() {
        let bytes = std::fs::read(doc_path).map_err(|_| EngineError::new(
            "protocol document cannot be read",
            "the --doc-path file is missing or unreadable, so no digest can be computed.",
            "pass a readable document path, or omit --doc-path."))?;
        let computed = sha256_bytes(&bytes);
        if !doc_digest.is_empty() && doc_digest != computed {
            return Err(EngineError::new("protocol doc digest does not match document",
                "the pinned digest differs from the SHA-256 of the document at --doc-path.",
                "recompute the digest from the current document, or pin that document."));
        }
        doc_digest = computed;
    }
    if !doc_digest.is_empty() && !hex_sha256(&doc_digest) {
        return Err(EngineError::new("protocol doc digest is not a SHA-256 hex string",
            "a protocol definition is pinned by a 64-character lowercase hex digest.",
            "pass the digest of the protocol document, or omit --doc-digest."));
    }
    let tx = conn.unchecked_transaction()?;
    if tx.query_row("SELECT 1 FROM protocol WHERE id=?1", params![id], |_| Ok(())).is_ok() {
        return Err(EngineError::new(format!("protocol already registered: {id}"),
            "a protocol id is immutable so old measurements keep their meaning.",
            "register a new id for a changed procedure."));
    }
    tx.execute(
        "INSERT INTO protocol(id, measures, includes_generation, includes_judge, doc_digest, registered_at) VALUES (?1,?2,?3,?4,?5,?6)",
        params![id, measures, i64::from(includes_generation), i64::from(includes_judge), doc_digest, utc_now()],
    )?;
    record_event(&tx, "", "protocol.register", &id, measures, actor)?;
    tx.commit()?;
    get_protocol(conn, &id)
}

pub fn amend(conn: &Connection, reference: &str, measures: &str, reason: &str, actor: &str) -> Result<Value> {
    let record = get_protocol(conn, reference)?;
    let measures = measures.trim();
    if measures.is_empty() {
        return Err(EngineError::new("amended measures text is empty",
            "a correction cannot blank the text it fixes.", "pass a non-empty --measures value."));
    }
    let reason = reason.trim();
    if reason.is_empty() {
        return Err(EngineError::new("amendment has no reason",
            "a correction without a stated reason cannot be audited.",
            "pass --reason naming the error being fixed."));
    }
    if measures == field(&record, "measures") {
        return Err(EngineError::new("amendment changes nothing",
            "the supplied measures already match the record.",
            "pass different text, or leave the record alone."));
    }
    let tx = conn.unchecked_transaction()?;
    let id = next_id(&tx, "am")?;
    tx.execute(
        "INSERT INTO amendment(id, subject_kind, subject_id, field, before_value, after_value, reason, actor, at) VALUES (?1,'protocol',?2,'measures',?3,?4,?5,?6,?7)",
        params![id, field(&record, "id"), field(&record, "measures"), measures, reason, actor, utc_now()],
    )?;
    tx.execute("UPDATE protocol SET measures=?1 WHERE id=?2", params![measures, field(&record, "id")])?;
    record_event(&tx, "", "protocol.amend", &field(&record, "id"), reason, actor)?;
    tx.commit()?;
    get_protocol(conn, &field(&record, "id"))
}
