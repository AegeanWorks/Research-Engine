//! PRISMA flow counts over the shared source table (engine/screening.py).

use rusqlite::Connection;

use serde_json::{json, Value};

use crate::core;
use crate::error::Result;

pub const SCREENING_STATUSES: &[&str] = &[
    "identified", "screened_in", "screened_out", "included", "excluded",
];

pub fn prisma_flow(conn: &Connection, research_ref: Option<&str>) -> Result<Value> {
    let research_id = match research_ref {
        Some(reference) => Some(field(&core::get_research(conn, reference)?, "id")),
        None => None,
    };
    let mut counts = serde_json::Map::new();
    for status in SCREENING_STATUSES {
        let count: i64 = match &research_id {
            Some(id) => conn.query_row(
                "SELECT COUNT(*) FROM source WHERE research_id = ? AND screening = ?",
                rusqlite::params![id, status], |row| row.get(0))?,
            None => conn.query_row(
                "SELECT COUNT(*) FROM source WHERE screening = ?",
                rusqlite::params![status], |row| row.get(0))?,
        };
        counts.insert((*status).to_string(), Value::from(count));
    }
    let (sql, params_vec): (&str, Vec<Box<dyn rusqlite::ToSql>>) = match &research_id {
        Some(id) => (
            "SELECT screening_reason AS reason, COUNT(*) AS n FROM source \
             WHERE research_id = ? AND screening IN ('screened_out','excluded') \
             GROUP BY screening_reason ORDER BY reason",
            vec![Box::new(id.clone()) as Box<dyn rusqlite::ToSql>],
        ),
        None => (
            "SELECT screening_reason AS reason, COUNT(*) AS n FROM source \
             WHERE screening IN ('screened_out','excluded') \
             GROUP BY screening_reason ORDER BY reason",
            Vec::new(),
        ),
    };
    let bindings: Vec<&dyn rusqlite::ToSql> = params_vec.iter().map(|b| b.as_ref()).collect();
    let mut stmt = conn.prepare(sql)?;
    let rows = stmt.query_map(bindings.as_slice(), |row| {
        let reason: Option<String> = row.get(0)?;
        let n: i64 = row.get(1)?;
        Ok((reason, n))
    })?;
    let mut reasons = serde_json::Map::new();
    for row in rows {
        let (reason, n) = row?;
        reasons.insert(reason.filter(|s| !s.is_empty()).unwrap_or_else(|| "other".to_string()),
            Value::from(n));
    }
    let total: i64 = counts.values().filter_map(Value::as_i64).sum();
    let included = counts.get("included").and_then(Value::as_i64).unwrap_or(0);
    let fraction = if total > 0 { round4(included as f64 / total as f64) } else { 0.0 };
    Ok(json!({
        "counts": Value::Object(counts),
        "reasons": Value::Object(reasons),
        "total": total,
        "included": included,
        "included_fraction": fraction,
    }))
}

fn field(value: &Value, key: &str) -> String {
    value.get(key).and_then(Value::as_str).unwrap_or("").to_string()
}

fn round4(value: f64) -> f64 {
    (value * 10_000.0).round() / 10_000.0
}
