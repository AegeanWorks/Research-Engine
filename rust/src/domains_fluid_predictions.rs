//! New-prediction audit
//! (fluid_universe/phenomenology/predictions.py).

use serde_json::{json, Value};

use crate::error::{EngineError, Result};

pub fn candidates() -> Value {
    Value::Array(vec![
        json!({"class": "mass relation", "current_statement": "Q = 2/3 (Koide) for pole masses", "new": false, "reason": "Built in; the three-parameter fit accommodates any three masses."}),
        json!({"class": "mass relation (extra)", "current_statement": "none beyond Q = 2/3", "new": false, "reason": "No second relation survives; the fit has three parameters for three masses."}),
        json!({"class": "mixing relation", "current_statement": "minimal circulant branches predict no mixing or trimaximal mixing", "new": false, "reason": "Both branches are excluded by measured angles; no viable prediction."}),
        json!({"class": "dispersion deviation", "current_statement": "equal-K Frank-Oseen gives omega^2 = (K/rho) k^2", "new": false, "reason": "No physical calibration of K, rho, or the UV scale; no numerical deviation."}),
        json!({"class": "defect-spectrum count", "current_statement": "no validated simulation", "new": false, "reason": "No Hopfion solution or validated core; no count to compare."}),
        json!({"class": "RG signature", "current_statement": "Q and r drift by about 3e-6 over 16 decades", "new": false, "reason": "Far below experimental reach and consistent with the SM; not a discriminator."}),
        json!({"class": "neutrino prediction", "current_statement": "Q_nu never reaches 2/3", "new": false, "reason": "A negative result about a Koide extension, not a new positive prediction."}),
    ])
}

pub fn verdict() -> Value {
    json!({
        "new_prediction_found": false,
        "count": 0,
        "note": "No genuinely new falsifiable prediction beyond Q=2/3 was found. The mass fit is a reparametrisation, the minimal mixing branches are excluded, the dispersion has no calibration, and the defect spectrum has no validated simulation.",
    })
}

fn py_bool(value: bool) -> &'static str {
    if value { "True" } else { "False" }
}

/// Render the audit Markdown from a payload with candidates, verdict and meta.
pub fn render_markdown(payload: &Value) -> Result<String> {
    let rows = payload.get("candidates").and_then(Value::as_array).ok_or_else(|| EngineError::new(
        "payload must contain 'candidates'", "the report needs the candidate list",
        "pass a payload object with candidates, verdict and meta"))?;
    let v = payload.get("verdict").ok_or_else(|| EngineError::new(
        "payload must contain a 'verdict' object", "the report needs the audit verdict",
        "pass a payload object with verdict"))?;
    let meta = payload.get("meta").ok_or_else(|| EngineError::new(
        "payload must contain a 'meta' object", "the report needs provenance metadata",
        "pass a payload object with meta"))?;
    let mut lines = vec![
        "# New-prediction audit (claim 16)".to_string(),
        String::new(),
        "| class | current statement | new? | reason |".to_string(),
        "|---|---|---|---|".to_string(),
    ];
    for row in rows {
        let text = |key: &str| row.get(key).and_then(Value::as_str).unwrap_or("").to_string();
        let is_new = row.get("new").and_then(Value::as_bool).unwrap_or(false);
        lines.push(format!("| {} | {} | {} | {} |", text("class"),
            text("current_statement"), py_bool(is_new), text("reason")));
    }
    let found = v.get("new_prediction_found").and_then(Value::as_bool).unwrap_or(false);
    let count = v.get("count").and_then(Value::as_u64).unwrap_or(0);
    let note = v.get("note").and_then(Value::as_str).unwrap_or("");
    let sha = meta.get("config_sha256").and_then(Value::as_str).unwrap_or("");
    let git = meta.get("git").unwrap_or(&Value::Null);
    let commit = git.get("commit").and_then(Value::as_str).unwrap_or("");
    let dirty = git.get("dirty").and_then(Value::as_bool).unwrap_or(false);
    lines.extend([
        String::new(),
        format!("**Verdict:** new prediction found: **{}** (count {}).", py_bool(found), count),
        String::new(),
        note.to_string(),
        String::new(),
        format!("- Config SHA-256: `{sha}`"),
        format!("- Git: `{commit}` (dirty={})", py_bool(dirty)),
        String::new(),
    ]);
    Ok(lines.join("\n"))
}
