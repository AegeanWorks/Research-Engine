//! Shared query, hashing and output helpers.

use rusqlite::{types::ValueRef, Connection, Params};
use serde_json::{Map, Value};
use sha2::{Digest, Sha256};

use crate::error::Result;

/// Convert one SQLite row into a JSON object keyed by column name.
pub fn row_json(row: &rusqlite::Row<'_>) -> Result<Value> {
    let mut object = Map::new();
    for (index, column) in row.as_ref().column_names().iter().enumerate() {
        let value = match row.get_ref(index)? {
            ValueRef::Null => Value::Null,
            ValueRef::Integer(i) => Value::from(i),
            ValueRef::Real(f) => Value::from(f),
            ValueRef::Text(bytes) => Value::from(String::from_utf8_lossy(bytes).as_ref()),
            ValueRef::Blob(bytes) => Value::from(bytes.to_vec()),
        };
        object.insert((*column).to_string(), value);
    }
    Ok(Value::Object(object))
}

/// Query rows into JSON records; the workhorse behind `--json` output.
pub fn query_json(conn: &Connection, sql: &str, params: impl Params) -> Result<Vec<Value>> {
    let mut statement = conn.prepare(sql)?;
    let columns = statement.column_names();
    let names: Vec<String> = columns.iter().map(|c| c.to_string()).collect();
    let mut rows = statement.query(params)?;
    let mut out = Vec::new();
    while let Some(row) = rows.next()? {
        let mut object = Map::new();
        for (index, name) in names.iter().enumerate() {
            let value = match row.get_ref(index)? {
                ValueRef::Null => Value::Null,
                ValueRef::Integer(i) => Value::from(i),
                ValueRef::Real(f) => Value::from(f),
                ValueRef::Text(bytes) => Value::from(String::from_utf8_lossy(bytes).as_ref()),
                ValueRef::Blob(bytes) => Value::from(bytes.to_vec()),
            };
            object.insert(name.clone(), value);
        }
        out.push(Value::Object(object));
    }
    Ok(out)
}

/// Domain-separated digest: `sha256(kind + "\n" + payload)`.
pub fn digest(kind: &str, payload: impl AsRef<[u8]>) -> String {
    let mut hasher = Sha256::new();
    hasher.update(kind.as_bytes());
    hasher.update(b"\n");
    hasher.update(payload.as_ref());
    format!("{:x}", hasher.finalize())
}

pub fn sha256_text(value: &str) -> String {
    let mut hasher = Sha256::new();
    hasher.update(value.as_bytes());
    format!("{:x}", hasher.finalize())
}

pub fn sha256_bytes(value: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(value);
    format!("{:x}", hasher.finalize())
}

/// Exact port of `engine/events.py::event_hash_for`: newline-joined fields in
/// predecessor-first order, hashed with plain SHA-256.
#[allow(clippy::too_many_arguments)]
pub fn event_hash_for(
    prev_hash: &str, id: &str, at: &str, research_id: &str, kind: &str, subject: &str,
    detail: &str, actor: &str, seq: i64, root_id: &str, parent_id: &str,
) -> String {
    let payload = [prev_hash, id, at, research_id, kind, subject, detail, actor,
        &seq.to_string(), root_id, parent_id].join("\n");
    sha256_text(&payload)
}

/// Python-compatible stable JSON rendering: 2-space indent, sorted keys, trailing newline.
pub fn to_stable_json(value: &Value) -> String {
    let mut text = serde_json::to_string_pretty(value).unwrap_or_else(|_| "{}".to_string());
    text.push('\n');
    text
}

/// Atomic UTF-8 replacement, mirroring `engine/artifacts.py::atomic_write_text`.
pub fn atomic_write_text(path: &std::path::Path, text: &str) -> Result<()> {
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)?;
    }
    let name = path.file_name().and_then(|n| n.to_str()).unwrap_or("output");
    let temp = path.with_file_name(format!(".{name}.tmp_{}", std::process::id()));
    std::fs::write(&temp, text.as_bytes())?;
    let file = std::fs::OpenOptions::new().write(true).open(&temp)?;
    file.sync_all()?;
    std::fs::rename(&temp, path)?;
    Ok(())
}

/// Python's `re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "research"`.
pub fn slugify(title: &str) -> String {
    let lower = title.to_lowercase();
    let mut out = String::new();
    let mut pending_dash = false;
    for c in lower.chars() {
        if c.is_ascii_alphanumeric() {
            if pending_dash && !out.is_empty() { out.push('-'); }
            out.push(c);
            pending_dash = false;
        } else {
            pending_dash = true;
        }
    }
    if out.is_empty() { "research".to_string() } else { out }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn digest_is_domain_separated() {
        assert_ne!(digest("report", b"x"), digest("graph", b"x"));
        assert_eq!(digest("graph", b"x"), digest("graph", b"x"));
    }

    #[test]
    fn slug_matches_python() {
        assert_eq!(slugify("Fluid Universe 101"), "fluid-universe-101");
        assert_eq!(slugify("!!!"), "research");
    }
}
