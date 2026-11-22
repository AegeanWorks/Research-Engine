//! Atomic CSV, JSON and text report writers shared by the PNN CLI tools
//! (domains/pnn/reports.py).

use std::path::Path;

use serde_json::Value;

use crate::error::{EngineError, Result};
use crate::util::atomic_write_text;

fn cell(value: &Value) -> String {
    match value {
        Value::Null => String::new(),
        Value::Bool(flag) => if *flag { "True".into() } else { "False".into() },
        Value::String(text) => text.clone(),
        other => other.to_string(),
    }
}

/// Python csv's QUOTE_MINIMAL rule with the default CRLF line terminator.
fn csv_field(text: &str) -> String {
    if text.contains(',') || text.contains('"') || text.contains('\r') || text.contains('\n') {
        format!("\"{}\"", text.replace('"', "\"\""))
    } else {
        text.to_string()
    }
}

pub fn write_csv(path: &Path, fieldnames: &[String], rows: &[Value]) -> Result<()> {
    if fieldnames.is_empty() {
        return Err(EngineError::new("fieldnames must not be empty",
            "a CSV report needs at least one column", "pass at least one field name"));
    }
    let mut lines = Vec::with_capacity(rows.len() + 1);
    lines.push(fieldnames.iter().map(|f| csv_field(f)).collect::<Vec<_>>().join(","));
    for row in rows {
        let values: Vec<String> = fieldnames.iter().map(|field| {
            let value = row.get(field).cloned().unwrap_or(Value::Null);
            csv_field(&cell(&value))
        }).collect();
        lines.push(values.join(","));
    }
    atomic_write_text(path, &format!("{}\r\n", lines.join("\r\n")))
}

pub fn write_json(path: &Path, report: &Value) -> Result<()> {
    let text = serde_json::to_string_pretty(report).map_err(|e| EngineError::new(
        format!("cannot serialize report: {e}"), "the report must be JSON-serializable",
        "pass a JSON object"))?;
    atomic_write_text(path, &format!("{text}\n"))
}

pub fn write_text(path: &Path, text: &str) -> Result<()> {
    atomic_write_text(path, text)
}
