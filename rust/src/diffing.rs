//! Snapshot comparison (engine/diffing.py).

use std::collections::{BTreeMap, BTreeSet};

use serde_json::{json, Value};

use crate::bundle::content_records;
use crate::error::{EngineError, Result};
use crate::util::{sha256_text, to_python_json};

const VOLATILE_FIELDS: &[&str] = &["id", "run_group", "started_at", "duration_ms", "output_tail"];

fn field(value: &Value, name: &str) -> String {
    value.get(name).and_then(Value::as_str).unwrap_or("").to_string()
}

pub fn load_jsonl(path: &std::path::Path) -> Result<Vec<Value>> {
    if !path.is_file() {
        return Err(EngineError::new(format!("snapshot not found: {}", path.to_string_lossy()),
            "a diff needs two exported snapshots to compare.",
            "create one with `export PATH --research REF`."));
    }
    let text = std::fs::read_to_string(path)?;
    let mut records = Vec::new();
    for (index, line) in text.lines().enumerate() {
        if line.trim().is_empty() { continue; }
        let record: Value = serde_json::from_str(line).map_err(|error| EngineError::new(
            format!("snapshot line {} is not valid JSON: {}", index + 1, path.to_string_lossy()),
            error.to_string(), "re-export the snapshot with this engine version."))?;
        if !record.is_object() {
            return Err(EngineError::new(
                format!("snapshot line {} is not an object: {}", index + 1, path.to_string_lossy()),
                "a snapshot record must be a JSON object with a type field.",
                "re-export the snapshot with this engine version."));
        }
        if field(&record, "type") == "meta" { continue; }
        records.push(record);
    }
    Ok(records)
}

fn key(record: &Value) -> (String, String) {
    let mut identity = field(record, "id");
    if identity.is_empty() {
        if let Some(projection) = record.get("projection") {
            identity = format!("run:{}", &sha256_text(&to_python_json(projection))[..16]);
        }
    }
    (field(record, "type"), identity)
}

fn strip(record: &Value) -> Value {
    match record.as_object() {
        Some(map) => Value::Object(map.iter()
            .filter(|(name, _)| !VOLATILE_FIELDS.contains(&name.as_str()))
            .map(|(name, value)| (name.clone(), value.clone())).collect()),
        None => record.clone(),
    }
}

fn index(records: &[Value], semantic: bool) -> BTreeMap<(String, String), Value> {
    let projected;
    let records = if semantic {
        projected = content_records(records);
        projected.as_slice()
    } else { records };
    let mut buckets: BTreeMap<(String, String), Vec<Value>> = BTreeMap::new();
    for record in records {
        buckets.entry(key(record)).or_default().push(strip(record));
    }
    buckets.into_iter().map(|(id, mut values)| {
        if values.len() == 1 {
            (id, values.remove(0))
        } else {
            values.sort_by(|a, b| to_python_json(a).cmp(&to_python_json(b)));
            (id, Value::Array(values))
        }
    }).collect()
}

pub fn diff_records(old: &[Value], new: &[Value], semantic: bool) -> Value {
    let before = index(old, semantic);
    let after = index(new, semantic);
    let before_keys: BTreeSet<_> = before.keys().cloned().collect();
    let after_keys: BTreeSet<_> = after.keys().cloned().collect();
    let added: Vec<_> = after_keys.difference(&before_keys).cloned().collect();
    let removed: Vec<_> = before_keys.difference(&after_keys).cloned().collect();
    let changed: Vec<_> = before_keys.intersection(&after_keys)
        .filter(|id| before.get(*id) != after.get(*id)).cloned().collect();
    let convert = |items: Vec<(String, String)>| -> Value {
        Value::Array(items.into_iter().map(|(kind, id)| json!({"type": kind, "id": id})).collect())
    };
    let identical = added.is_empty() && removed.is_empty() && changed.is_empty();
    json!({
        "semantic": semantic,
        "added": convert(added.clone()),
        "removed": convert(removed.clone()),
        "changed": convert(changed.clone()),
        "counts": {"added": added.len(), "removed": removed.len(), "changed": changed.len()},
        "identical": identical,
    })
}

pub fn diff_files(old: &std::path::Path, new: &std::path::Path, semantic: bool) -> Result<Value> {
    Ok(diff_records(&load_jsonl(old)?, &load_jsonl(new)?, semantic))
}

pub fn render(result: &Value) -> String {
    let counts = result.get("counts").unwrap_or(&Value::Null);
    let mode = if result.get("semantic").and_then(Value::as_bool).unwrap_or(false) { "semantic" } else { "exact" };
    let mut lines = vec![format!("diff ({}): {} added, {} removed, {} changed", mode,
        counts.get("added").and_then(Value::as_u64).unwrap_or(0),
        counts.get("removed").and_then(Value::as_u64).unwrap_or(0),
        counts.get("changed").and_then(Value::as_u64).unwrap_or(0))];
    for (label, key) in [("+", "added"), ("-", "removed"), ("~", "changed")] {
        if let Some(items) = result.get(key).and_then(Value::as_array) {
            for item in items {
                lines.push(format!("  {label} {}:{}", field(item, "type"), field(item, "id")));
            }
        }
    }
    if result.get("identical").and_then(Value::as_bool).unwrap_or(false) {
        lines.push("  no differences".to_string());
    }
    lines.join("\n") + "\n"
}
