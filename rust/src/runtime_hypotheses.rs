//! Hypothesis pre-registration card and amendments (engine/hypotheses.py).

use rusqlite::{params, Connection};

use serde_json::Value;

use crate::core;
use crate::db::{next_id, utc_now};
use crate::error::{EngineError, Result};

fn field(value: &Value, key: &str) -> String {
    value.get(key).and_then(Value::as_str).unwrap_or("").to_string()
}

pub fn preregistration_card(conn: &Connection, reference: &str) -> Result<String> {
    let hypothesis = core::get_hypothesis(conn, reference)?;
    Ok(format!(
        "# K13 Pre-registration: {}\n\n**Registered:** {}\n**Statement:** {}\n\
         **Confidence:** {:.2}\n**Verification criterion:** {}\n\
         **Most likely to be wrong:** {}\n**Status:** {}\n",
        field(&hypothesis, "id"), field(&hypothesis, "registered_at"),
        field(&hypothesis, "statement"),
        hypothesis.get("confidence").and_then(Value::as_f64).unwrap_or(0.0),
        field(&hypothesis, "criterion"), field(&hypothesis, "criterion"),
        field(&hypothesis, "status"),
    ))
}

pub fn amend_hypothesis(conn: &Connection, reference: &str, reason: &str,
                        statement: Option<&str>, criterion: Option<&str>,
                        actor: &str) -> Result<Value> {
    let hypothesis = core::get_hypothesis(conn, reference)?;
    if field(&hypothesis, "status") != "PREREGISTERED" {
        return Err(EngineError::new(
            format!("hypothesis already has outcome {}", field(&hypothesis, "status")),
            "a closed hypothesis is frozen; correcting it would rewrite history",
            "register a new hypothesis instead of editing a decided one"));
    }
    let reason = reason.trim();
    if reason.is_empty() {
        return Err(EngineError::new("amendment has no reason",
            "a correction without a stated reason cannot be audited",
            "pass --reason naming the error being fixed"));
    }
    let mut updates: Vec<String> = Vec::new();
    let mut values: Vec<String> = Vec::new();
    for (name, supplied) in [("statement", statement), ("criterion", criterion)] {
        let Some(value) = supplied else { continue };
        let cleaned = value.trim();
        if cleaned.is_empty() {
            return Err(EngineError::new(format!("amended {name} is empty"),
                "a correction cannot blank the field it fixes",
                "pass a non-empty value, or omit the field"));
        }
        let before = field(&hypothesis, name);
        if cleaned == before { continue; }
        let id = next_id(conn, "am")?;
        let stamp = utc_now();
        conn.execute(
            "INSERT INTO amendment(id, subject_kind, subject_id, field, before_value, \
             after_value, reason, actor, at) VALUES (?1,'hypothesis',?2,?3,?4,?5,?6,?7,?8)",
            params![id, field(&hypothesis, "id"), name, before, cleaned, reason, actor, stamp],
        )?;
        updates.push(format!("{name} = ?"));
        values.push(cleaned.to_string());
    }
    if updates.is_empty() {
        return Err(EngineError::new("amendment changes nothing",
            "every supplied value already matches the record",
            "pass a different value, or leave the record alone"));
    }
    values.push(utc_now());
    values.push(field(&hypothesis, "id"));
    let mut sql = format!("UPDATE hypothesis SET {}, updated_at = ? WHERE id = ?", updates.join(", "));
    let mut stmt = conn.prepare(&mut sql)?;
    let mut index = 1;
    for value in &values {
        stmt.raw_bind_parameter(index, value)?;
        index += 1;
    }
    stmt.raw_execute()?;
    core::record_event(conn, &field(&hypothesis, "research_id"), "hypothesis.amend",
        &field(&hypothesis, "id"), reason, actor)?;
    core::get_hypothesis(conn, &field(&hypothesis, "id"))
}
