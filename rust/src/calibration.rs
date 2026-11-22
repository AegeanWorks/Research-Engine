//! Hypothesis calibration scorecard (engine/calibration.py::summary).

use rusqlite::{params, Connection};
use serde_json::{json, Value};

use crate::core::{get_research, record_event};
use crate::error::Result;
use crate::util::query_json;

const BIN_EDGES: &[(f64, f64)] = &[(0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.0)];

fn field(value: &Value, name: &str) -> String {
    value.get(name).and_then(Value::as_str).unwrap_or("").to_string()
}

fn round(value: f64, places: i32) -> f64 {
    let factor = 10f64.powi(places);
    (value * factor).round() / factor
}

pub fn score(conn: &Connection, reference: &str, min_resolved: i64, actor: &str) -> Result<Value> {
    let result = summary(conn, reference, min_resolved)?;
    let rid = field(&result, "research");
    let counts = result.get("counts").unwrap();
    let detail = if result.get("brier").and_then(Value::as_f64).is_none() {
        format!("n=0 coverage={:.4} no resolved outcome", result.get("coverage").and_then(Value::as_f64).unwrap_or(0.0))
    } else {
        format!("n={} brier={:.4} log_loss={:.4} coverage={:.4}",
            counts.get("resolved").and_then(Value::as_i64).unwrap_or(0),
            result.get("brier").and_then(Value::as_f64).unwrap_or(0.0),
            result.get("log_loss").and_then(Value::as_f64).unwrap_or(0.0),
            result.get("coverage").and_then(Value::as_f64).unwrap_or(0.0))
    };
    record_event(conn, &rid, "hypothesis.calibration", &rid, &detail, actor)?;
    Ok(result)
}

pub fn summary(conn: &Connection, reference: &str, min_resolved: i64) -> Result<Value> {
    let research = get_research(conn, reference)?;
    let rows = query_json(conn,
        "SELECT id, confidence, status FROM hypothesis WHERE research_id=?1 ORDER BY id",
        params![field(&research, "id")])?;
    let mut counts = serde_json::Map::new();
    for key in ["total", "resolved", "supported", "refuted", "inconclusive", "preregistered"] {
        counts.insert(key.to_string(), json!(0));
    }
    let bump = |map: &mut serde_json::Map<String, Value>, key: &str| {
        let n = map.get(key).and_then(Value::as_i64).unwrap_or(0) + 1;
        map.insert(key.to_string(), json!(n));
    };
    bump(&mut counts, "total");
    // Reset: the loop below counts each row.
    counts.insert("total".to_string(), json!(rows.len()));
    let mut pairs: Vec<(String, f64, f64)> = Vec::new();
    for row in &rows {
        let status = field(row, "status");
        let confidence = row.get("confidence").and_then(Value::as_f64).unwrap_or(0.0);
        match status.as_str() {
            "SUPPORTED" => { bump(&mut counts, "resolved"); bump(&mut counts, "supported");
                pairs.push((field(row, "id"), confidence, 1.0)); }
            "REFUTED" => { bump(&mut counts, "resolved"); bump(&mut counts, "refuted");
                pairs.push((field(row, "id"), confidence, 0.0)); }
            "INCONCLUSIVE" => bump(&mut counts, "inconclusive"),
            _ => bump(&mut counts, "preregistered"),
        }
    }
    let total = rows.len() as i64;
    let resolved = pairs.len() as i64;
    let coverage = if total == 0 { 0.0 } else { round(resolved as f64 / total as f64, 4) };
    let (brier, log_loss, base_rate, brier_baseline, skill) = if resolved > 0 {
        let b = pairs.iter().map(|(_, p, o)| (p - o).powi(2)).sum::<f64>() / resolved as f64;
        let clip = |p: f64| p.min(1.0 - 1e-12).max(1e-12);
        let ll = -pairs.iter().map(|(_, p, o)| o * clip(*p).ln() + (1.0 - o) * clip(1.0 - p).ln())
            .sum::<f64>() / resolved as f64;
        let rate = pairs.iter().map(|(_, _, o)| *o).sum::<f64>() / resolved as f64;
        let baseline = pairs.iter().map(|(_, _, o)| (rate - o).powi(2)).sum::<f64>() / resolved as f64;
        let s = if baseline > 0.0 { Some(1.0 - b / baseline) } else { None };
        (Some(b), Some(ll), Some(rate), Some(baseline), s)
    } else { (None, None, None, None, None) };
    let bin_index = |p: f64| -> usize {
        BIN_EDGES.iter().position(|(low, high)| *low <= p && p < *high).unwrap_or(BIN_EDGES.len() - 1)
    };
    let mut bins = Vec::new();
    let mut warnings: Vec<String> = Vec::new();
    let mut bin_warnings: Vec<String> = Vec::new();
    for (index, (low, high)) in BIN_EDGES.iter().enumerate() {
        let members: Vec<(f64, f64)> = pairs.iter()
            .filter(|(_, p, _)| bin_index(*p) == index).map(|(_, p, o)| (*p, *o)).collect();
        let (n, mean_confidence, observed, gap) = if members.is_empty() {
            (0, Value::Null, Value::Null, Value::Null)
        } else {
            let mc = members.iter().map(|(p, _)| *p).sum::<f64>() / members.len() as f64;
            let ob = members.iter().map(|(_, o)| *o).sum::<f64>() / members.len() as f64;
            (members.len(), json!(round(mc, 4)), json!(round(ob, 4)), json!(round(ob - mc, 4)))
        };
        if n > 0 {
            let gap_value = gap.as_f64().unwrap_or(0.0);
            if gap_value.abs() >= 0.2 {
                let direction = if gap_value < 0.0 { "overconfident" } else { "underconfident" };
                bin_warnings.push(format!("bin {low:.1}-{high:.1} is {direction} by {:.2}", gap_value.abs()));
            }
        }
        bins.push(json!({"low": low, "high": high, "n": n,
            "mean_confidence": mean_confidence, "observed": observed, "gap": gap}));
    }
    if resolved == 0 {
        warnings.push("no hypothesis has a recorded outcome; calibration is undefined".to_string());
    } else if resolved < min_resolved {
        warnings.push(format!("{resolved} resolved hypothesis(es); scores are descriptive below {min_resolved}"));
    }
    if let Some(rate) = base_rate {
        if rate == 0.0 || rate == 1.0 {
            warnings.push("every resolved outcome has the same label; discrimination cannot be measured".to_string());
        }
    }
    warnings.extend(bin_warnings);
    Ok(json!({
        "research": field(&research, "id"),
        "counts": Value::Object(counts),
        "coverage": coverage,
        "min_resolved": min_resolved,
        "brier": brier.map(|v| json!(round(v, 6))).unwrap_or(Value::Null),
        "log_loss": log_loss.map(|v| json!(round(v, 6))).unwrap_or(Value::Null),
        "base_rate": base_rate.map(|v| json!(round(v, 6))).unwrap_or(Value::Null),
        "brier_baseline": brier_baseline.map(|v| json!(round(v, 6))).unwrap_or(Value::Null),
        "skill": skill.map(|v| json!(round(v, 6))).unwrap_or(Value::Null),
        "bins": bins,
        "warnings": warnings,
    }))
}
