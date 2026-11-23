//! Pre-registered analysis plans (engine/plans.py).

use rusqlite::{params, Connection};

use serde_json::{json, Value};

use crate::core;
use crate::db::{next_id, utc_now};
use crate::error::{EngineError, Result};

fn field(value: &Value, key: &str) -> String {
    value.get(key).and_then(Value::as_str).unwrap_or("").to_string()
}

pub fn add_plan(conn: &Connection, claim_ref: &str, baseline: &str, treatment: &str,
                prediction: &str, actor: &str) -> Result<Value> {
    let claim = core::get_claim(conn, claim_ref)?;
    let baseline = baseline.trim().to_lowercase();
    let treatment = treatment.trim().to_lowercase();
    let prediction = prediction.trim();
    if prediction.is_empty() {
        return Err(EngineError::new("analysis plan has no prediction",
            "a plan that predicts nothing cannot be confirmed or surprised.",
            "pass --prediction stating the expected direction or effect."));
    }
    if baseline.is_empty() || treatment.is_empty() {
        return Err(EngineError::new("analysis plan needs two group labels",
            "a comparison needs a baseline and a treatment to mean anything.",
            "pass --baseline and --treatment with the planned group labels."));
    }
    if baseline == treatment {
        return Err(EngineError::new(
            format!("cannot plan group '{baseline}' against itself"),
            "a comparison needs two different groups for a difference to mean anything.",
            "choose a different baseline or treatment label."));
    }
    let tx = conn.unchecked_transaction()?;
    let id = next_id(&tx, "ap")?;
    let research_id = field(&claim, "research_id");
    let claim_id = field(&claim, "id");
    tx.execute(
        "INSERT INTO analysis_plan(id, research_id, claim_id, baseline, treatment, \
         prediction, status, registered_at) VALUES (?1,?2,?3,?4,?5,?6,'PREREGISTERED',?7)",
        params![id, research_id, claim_id, baseline, treatment, prediction, utc_now()])?;
    core::record_event(&tx, &research_id, "analysis.plan", &id,
        &format!("{baseline}->{treatment}: {prediction}"), actor)?;
    tx.commit()?;
    get_plan(conn, &id)
}

pub fn get_plan(conn: &Connection, reference: &str) -> Result<Value> {
    crate::util::query_json(conn, "SELECT * FROM analysis_plan WHERE id = ?1", params![reference])?
        .into_iter().next()
        .ok_or_else(|| EngineError::not_found("analysis_plan", reference))
}

/// Plans preregistered for exactly this claim and group pair.
pub fn match_plan(conn: &Connection, claim_id: &str, baseline: &str,
                  treatment: &str) -> Result<Vec<Value>> {
    crate::util::query_json(conn,
        "SELECT * FROM analysis_plan WHERE claim_id = ?1 AND baseline = ?2 \
         AND treatment = ?3 ORDER BY id",
        params![claim_id, baseline.trim().to_lowercase(), treatment.trim().to_lowercase()])
}

pub fn as_summary(value: &Value) -> Value {
    json!({
        "id": field(value, "id"),
        "research_id": field(value, "research_id"),
        "claim_id": field(value, "claim_id"),
        "baseline": field(value, "baseline"),
        "treatment": field(value, "treatment"),
        "prediction": field(value, "prediction"),
        "status": field(value, "status"),
        "registered_at": field(value, "registered_at"),
    })
}
