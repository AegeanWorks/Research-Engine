//! N1 experiment records and baseline-vs-intervention analysis.
//! Port of `experiments/models.py` and `experiments/analysis.py`.

use std::collections::{BTreeMap, BTreeSet};

use chrono::{Datelike, NaiveDate};
use rusqlite::{params, Connection};
use serde_json::{json, Value};

use crate::core::get_research;
use crate::db::{next_id, utc_now};
use crate::error::{EngineError, Result};
use crate::stats;
use crate::util::query_json;

const MAX_SAFE_METRICS: usize = 3;
const MIN_BASELINE_DAYS: usize = 7;
const MIN_INTERVENTION_DAYS: usize = 7;
const MIN_DATA_POINTS: usize = 3;

fn field(value: &Value, name: &str) -> String {
    value.get(name).and_then(Value::as_str).unwrap_or("").to_string()
}

fn parse_date(value: &str, name: &str) -> Result<String> {
    NaiveDate::parse_from_str(value.trim(), "%Y-%m-%d")
        .map(|d| d.format("%Y-%m-%d").to_string())
        .map_err(|_| EngineError::new(
            format!("{name} is not an ISO date: {value:?}"),
            "experiment windows compare calendar dates exactly.",
            format!("pass {name} as YYYY-MM-DD.")))
}

fn parse_timestamp(value: &str) -> Result<String> {
    let text = value.trim();
    let iso = chrono::DateTime::parse_from_rfc3339(text)
        .map(|d| d.to_rfc3339())
        .or_else(|_| NaiveDate::parse_from_str(text, "%Y-%m-%d")
            .map(|d| d.and_hms_opt(0, 0, 0).unwrap().and_utc().to_rfc3339()))
        .map_err(|_| EngineError::new(
            format!("timestamp is not ISO-8601: {value:?}"),
            "an event needs an exact time so its order is auditable.",
            "pass an ISO-8601 timestamp such as 2026-01-01T09:00:00+00:00."))?;
    Ok(iso)
}

fn finite(value: f64) -> Result<f64> {
    if value.is_finite() { Ok(value) } else {
        Err(EngineError::new(format!("metric value is not finite: {value:?}"),
            "NaN and infinity cannot be compared or summarised.",
            "record the measurement as a finite number."))
    }
}

fn intervention_id(conn: &Connection, research_id: &str, reference: Option<&str>) -> Result<Option<String>> {
    let Some(reference) = reference.filter(|r| !r.trim().is_empty()) else { return Ok(None); };
    let rows = query_json(conn, "SELECT id, research_id FROM experiment_intervention WHERE id=?1", params![reference])?;
    let row = rows.into_iter().next().ok_or_else(|| EngineError::not_found("intervention", reference))?;
    if field(&row, "research_id") != research_id {
        return Err(EngineError::new("intervention belongs to another research program",
            "an experiment record cannot cross a program boundary.",
            "use the intervention from this program."));
    }
    Ok(Some(field(&row, "id")))
}

pub fn add_intervention(
    conn: &Connection, research_ref: &str, name: &str, start_date: &str,
    projected_end_date: Option<&str>, end_date: Option<&str>, dosage: &str, notes: &str,
) -> Result<Value> {
    let research = get_research(conn, research_ref)?;
    let rid = field(&research, "id");
    let name = name.trim();
    if name.is_empty() {
        return Err(EngineError::new("intervention name is empty", "an intervention needs a stable name.", "pass the intervention name."));
    }
    let start = parse_date(start_date, "start_date")?;
    let projected = match projected_end_date { Some(value) if !value.is_empty() => Some(parse_date(value, "projected_end_date")?), _ => None };
    let ended = match end_date { Some(value) if !value.is_empty() => Some(parse_date(value, "end_date")?), _ => None };
    if projected.as_deref().map(|d| d < start.as_str()).unwrap_or(false) {
        return Err(EngineError::new("projected_end_date precedes start_date", "an intervention cannot end before it starts.", "correct the dates."));
    }
    if ended.as_deref().map(|d| d < start.as_str()).unwrap_or(false) {
        return Err(EngineError::new("end_date precedes start_date", "an intervention cannot end before it starts.", "correct the dates."));
    }
    let tx = conn.unchecked_transaction()?;
    let id = next_id(&tx, "iv")?;
    tx.execute(
        "INSERT INTO experiment_intervention(id, research_id, name, start_date, projected_end_date, end_date, dosage, notes, created_at) VALUES (?1,?2,?3,?4,?5,?6,?7,?8,?9)",
        params![id, rid, name, start, projected, ended, dosage.trim(), notes.trim(), utc_now()])?;
    tx.commit()?;
    get_row(conn, "experiment_intervention", &id)
}

pub fn add_metric_definition(
    conn: &Connection, research_ref: &str, name: &str, description: &str, unit: &str,
) -> Result<Value> {
    let research = get_research(conn, research_ref)?;
    let rid = field(&research, "id");
    let name = name.trim();
    if name.is_empty() {
        return Err(EngineError::new("metric name is empty", "a metric definition needs a stable name.", "pass the metric name."));
    }
    let tx = conn.unchecked_transaction()?;
    let id = next_id(&tx, "md")?;
    let result = tx.execute(
        "INSERT INTO experiment_metric_definition(id, research_id, name, description, unit, created_at) VALUES (?1,?2,?3,?4,?5,?6)",
        params![id, rid, name, description.trim(), unit.trim(), utc_now()]);
    if result.is_err() {
        return Err(EngineError::new(format!("metric already defined in this program: {name}"),
            "one metric name has one definition per program.",
            "reuse the existing definition, or choose a distinct name."));
    }
    tx.commit()?;
    get_row(conn, "experiment_metric_definition", &id)
}

pub fn add_metric(
    conn: &Connection, research_ref: &str, metric_name: &str, date_value: &str,
    value: f64, intervention_ref: Option<&str>, note: &str,
) -> Result<Value> {
    let research = get_research(conn, research_ref)?;
    let rid = field(&research, "id");
    let metric_name = metric_name.trim();
    if metric_name.is_empty() {
        return Err(EngineError::new("metric name is empty", "a measurement needs the metric it belongs to.", "pass the metric name."));
    }
    let intervention = intervention_id(conn, &rid, intervention_ref)?;
    let day = parse_date(date_value, "date")?;
    let number = finite(value)?;
    let tx = conn.unchecked_transaction()?;
    let id = next_id(&tx, "me")?;
    tx.execute(
        "INSERT INTO experiment_metric(id, research_id, intervention_id, metric_name, date, value, note, created_at) VALUES (?1,?2,?3,?4,?5,?6,?7,?8)",
        params![id, rid, intervention, metric_name, day, number, note.trim(), utc_now()])?;
    tx.commit()?;
    get_row(conn, "experiment_metric", &id)
}

pub fn add_event(
    conn: &Connection, research_ref: &str, event_name: &str, timestamp: &str,
    severity: Option<i64>, notes: &str, intervention_ref: Option<&str>,
) -> Result<Value> {
    let research = get_research(conn, research_ref)?;
    let rid = field(&research, "id");
    let event_name = event_name.trim();
    if event_name.is_empty() {
        return Err(EngineError::new("event name is empty", "an event needs a stable name.", "pass the event name."));
    }
    if let Some(severity) = severity {
        if !(1..=5).contains(&severity) {
            return Err(EngineError::new(format!("event severity out of range: {severity:?}"),
                "severity is an integer from 1 (mild) to 5 (severe).",
                "pass a severity between 1 and 5, or omit it."));
        }
    }
    let intervention = intervention_id(conn, &rid, intervention_ref)?;
    let stamp = parse_timestamp(timestamp)?;
    let tx = conn.unchecked_transaction()?;
    let id = next_id(&tx, "ee")?;
    tx.execute(
        "INSERT INTO experiment_event(id, research_id, intervention_id, timestamp, event_name, severity, notes, created_at) VALUES (?1,?2,?3,?4,?5,?6,?7,?8)",
        params![id, rid, intervention, stamp, event_name, severity, notes.trim(), utc_now()])?;
    tx.commit()?;
    get_row(conn, "experiment_event", &id)
}

fn get_row(conn: &Connection, table: &str, id: &str) -> Result<Value> {
    let rows = query_json(conn, &format!("SELECT * FROM {table} WHERE id=?1"), params![id])?;
    rows.into_iter().next().ok_or_else(|| EngineError::not_found(table, id))
}

pub fn list_rows(conn: &Connection, table: &str, research_ref: Option<&str>, order: &str) -> Result<Vec<Value>> {
    if let Some(reference) = research_ref {
        let research = get_research(conn, reference)?;
        query_json(conn, &format!("SELECT * FROM {table} WHERE research_id=?1 ORDER BY {order}"),
            params![field(&research, "id")])
    } else {
        query_json(conn, &format!("SELECT * FROM {table} ORDER BY {order}"), [])
    }
}

pub fn list_metrics(conn: &Connection, research_ref: Option<&str>, metric_name: Option<&str>) -> Result<Vec<Value>> {
    let mut sql = String::from("SELECT * FROM experiment_metric WHERE 1=1");
    let mut bindings: Vec<Box<dyn rusqlite::ToSql>> = Vec::new();
    if let Some(reference) = research_ref {
        sql.push_str(" AND research_id=?");
        bindings.push(Box::new(field(&get_research(conn, reference)?, "id")));
    }
    if let Some(name) = metric_name {
        sql.push_str(" AND metric_name=?");
        bindings.push(Box::new(name.to_string()));
    }
    sql.push_str(" ORDER BY date, id");
    let args: Vec<&dyn rusqlite::ToSql> = bindings.iter().map(|b| b.as_ref()).collect();
    query_json(conn, &sql, args.as_slice())
}

fn mean(values: &[f64]) -> f64 {
    if values.is_empty() { 0.0 } else { values.iter().sum::<f64>() / values.len() as f64 }
}

fn summary(rows: &[Value]) -> Value {
    let values: Vec<f64> = rows.iter().map(|r| r.get("value").and_then(Value::as_f64).unwrap_or(0.0)).collect();
    let mut days: Vec<String> = rows.iter().map(|r| field(r, "date")).collect();
    days.sort();
    json!({
        "start": days.first().cloned().map(Value::String).unwrap_or(Value::Null),
        "end": days.last().cloned().map(Value::String).unwrap_or(Value::Null),
        "count": values.len(),
        "mean": mean(&values),
        "sd": stats::sample_sd(&values),
    })
}

fn trend(rows: &[Value]) -> Value {
    let values: Vec<f64> = rows.iter().map(|r| r.get("value").and_then(Value::as_f64).unwrap_or(0.0)).collect();
    let xs: Vec<f64> = rows.iter().map(|r|
        NaiveDate::parse_from_str(&field(r, "date"), "%Y-%m-%d")
            .map(|d| d.num_days_from_ce() as f64).unwrap_or(0.0)).collect();
    let result = stats::linregress(&xs, &values);
    json!({
        "slope": result.get("slope").cloned().unwrap_or(Value::Null),
        "r": result.get("r").cloned().unwrap_or(Value::Null),
        "p_value": result.get("p").cloned().unwrap_or(Value::Null),
    })
}

pub fn calculate_trend(values: &[f64], dates: Option<&[String]>) -> Value {
    let xs: Vec<f64> = match dates {
        Some(dates) => dates.iter().map(|d| NaiveDate::parse_from_str(d, "%Y-%m-%d")
            .map(|v| v.num_days_from_ce() as f64).unwrap_or(0.0)).collect(),
        None => (0..values.len()).map(|i| i as f64).collect(),
    };
    let result = stats::linregress(&xs, values);
    json!({
        "slope": result.get("slope").cloned().unwrap_or(Value::Null),
        "p_value": result.get("p").cloned().unwrap_or(Value::Null),
        "r": result.get("r").cloned().unwrap_or(Value::Null),
        "n": result.get("n").cloned().unwrap_or(Value::Null),
    })
}

pub fn bootstrap_ci(baseline: &[f64], treatment: &[f64], seed: i64, resamples: usize) -> Value {
    let mut result = stats::bootstrap_ci(baseline, treatment, seed, resamples);
    if let Value::Object(map) = &mut result {
        let low = map.get("low").cloned().unwrap_or(Value::Null);
        let high = map.get("high").cloned().unwrap_or(Value::Null);
        map.insert("lower".to_string(), low);
        map.insert("upper".to_string(), high);
    }
    result
}

fn window_warnings(baseline: &[Value], intervention: &[Value], baseline_days: i64, intervention_days: i64) -> Vec<String> {
    let mut warnings = Vec::new();
    let baseline_span = baseline.iter().map(|r| field(r, "date")).collect::<BTreeSet<_>>().len();
    let intervention_span = intervention.iter().map(|r| field(r, "date")).collect::<BTreeSet<_>>().len();
    if baseline_span < MIN_BASELINE_DAYS {
        warnings.push(format!("Insufficient baseline duration: {baseline_span} days (recommended >= {MIN_BASELINE_DAYS})"));
    }
    if intervention_span < MIN_INTERVENTION_DAYS {
        warnings.push(format!("Insufficient intervention duration: {intervention_span} days (recommended >= {MIN_INTERVENTION_DAYS})"));
    }
    if intervention_days < baseline_days {
        warnings.push(format!("Intervention duration ({intervention_days} days) is shorter than baseline ({baseline_days} days). Power may be reduced."));
    }
    if baseline.is_empty() || intervention.is_empty() { warnings.push("a window has no observations".to_string()); }
    if !baseline.is_empty() && !intervention.is_empty() {
        let b: Vec<f64> = baseline.iter().map(|r| r.get("value").and_then(Value::as_f64).unwrap_or(0.0)).collect();
        let t: Vec<f64> = intervention.iter().map(|r| r.get("value").and_then(Value::as_f64).unwrap_or(0.0)).collect();
        if stats::sample_sd(&b) == 0.0 && stats::sample_sd(&t) == 0.0 {
            warnings.push("Zero variance in both baseline and intervention data.".to_string());
        }
    }
    warnings
}

pub fn analyze_baseline_vs_intervention(
    conn: &Connection, research_ref: &str, metric_name: &str, start_date: &str,
    baseline_days: i64, intervention_days: i64,
) -> Result<Value> {
    let metric_name = metric_name.trim();
    if metric_name.is_empty() { return Err(EngineError::new("metric name is empty", "an analysis needs the metric it compares.", "pass the metric name.")); }
    let start = NaiveDate::parse_from_str(start_date.trim(), "%Y-%m-%d")
        .map_err(|_| EngineError::new(format!("intervention start is not an ISO date: {start_date:?}"),
            "analysis windows are calendar-date ranges.", "pass the start date as YYYY-MM-DD."))?;
    if baseline_days < 1 || intervention_days < 1 {
        return Err(EngineError::new("window must be a positive integer",
            "a window needs at least one calendar day.", "pass one or more days."));
    }
    let baseline_start = start - chrono::Duration::days(baseline_days);
    let intervention_end = start + chrono::Duration::days(intervention_days);
    let rows = list_metrics(conn, Some(research_ref), Some(metric_name))?;
    let mut baseline = Vec::new();
    let mut intervention = Vec::new();
    for row in rows {
        let Ok(day) = NaiveDate::parse_from_str(&field(&row, "date"), "%Y-%m-%d") else { continue; };
        if day >= baseline_start && day < start { baseline.push(row.clone()); }
        if day >= start && day < intervention_end { intervention.push(row); }
    }
    if baseline.len() < MIN_DATA_POINTS || intervention.len() < MIN_DATA_POINTS {
        return Ok(json!({
            "error": format!("Insufficient data points (minimum {MIN_DATA_POINTS} required)"),
            "metric": metric_name,
            "baseline_count": baseline.len(),
            "intervention_count": intervention.len(),
            "baseline_window": {"start": baseline_start.format("%Y-%m-%d").to_string(), "end": start.format("%Y-%m-%d").to_string()},
            "intervention_window": {"start": start.format("%Y-%m-%d").to_string(), "end": intervention_end.format("%Y-%m-%d").to_string()},
        }));
    }
    let bv: Vec<f64> = baseline.iter().map(|r| r.get("value").and_then(Value::as_f64).unwrap_or(0.0)).collect();
    let iv: Vec<f64> = intervention.iter().map(|r| r.get("value").and_then(Value::as_f64).unwrap_or(0.0)).collect();
    let compared = stats::compare_groups(&bv, &iv, 0, 2000);
    let mut warnings = window_warnings(&baseline, &intervention, baseline_days, intervention_days);
    if let Some(list) = compared.get("warnings").and_then(Value::as_array) {
        warnings.extend(list.iter().filter_map(|v| v.as_str().map(|s| s.to_string())));
    }
    let welch = compared.get("welch").cloned().unwrap_or(Value::Null);
    let mann = compared.get("mann_whitney").cloned().unwrap_or(Value::Null);
    let mut interval = serde_json::Map::new();
    if let Some(map) = compared.get("bootstrap").and_then(Value::as_object) {
        for (key, value) in map { interval.insert(key.clone(), value.clone()); }
    }
    interval.insert("lower".to_string(), compared.get("bootstrap").and_then(|b| b.get("low")).cloned().unwrap_or(Value::Null));
    interval.insert("upper".to_string(), compared.get("bootstrap").and_then(|b| b.get("high")).cloned().unwrap_or(Value::Null));
    let mut baseline_window = serde_json::Map::new();
    baseline_window.insert("start".to_string(), json!(baseline_start.format("%Y-%m-%d").to_string()));
    baseline_window.insert("end".to_string(), json!(start.format("%Y-%m-%d").to_string()));
    if let Value::Object(map) = summary(&baseline) { for (key, value) in map { baseline_window.insert(key, value); } }
    let mut intervention_window = serde_json::Map::new();
    intervention_window.insert("start".to_string(), json!(start.format("%Y-%m-%d").to_string()));
    intervention_window.insert("end".to_string(), json!(intervention_end.format("%Y-%m-%d").to_string()));
    if let Value::Object(map) = summary(&intervention) { for (key, value) in map { intervention_window.insert(key, value); } }
    Ok(json!({
        "metric": metric_name,
        "baseline_window": Value::Object(baseline_window),
        "intervention_window": Value::Object(intervention_window),
        "analysis": {
            "mean_difference": compared.get("difference").cloned().unwrap_or(Value::Null),
            "cohens_d": compared.get("cohens_d").cloned().unwrap_or(Value::Null),
            "t_test": {
                "t": welch.get("t").cloned().unwrap_or(Value::Null),
                "statistic": welch.get("t").cloned().unwrap_or(Value::Null),
                "df": welch.get("df").cloned().unwrap_or(Value::Null),
                "p_value": welch.get("p").cloned().unwrap_or(Value::Null),
            },
            "mann_whitney_u": {
                "u": mann.get("u").cloned().unwrap_or(Value::Null),
                "statistic": mann.get("u").cloned().unwrap_or(Value::Null),
                "z": mann.get("z").cloned().unwrap_or(Value::Null),
                "p_value": mann.get("p").cloned().unwrap_or(Value::Null),
                "method": mann.get("method").cloned().unwrap_or(Value::Null),
            },
            "bootstrap_ci": Value::Object(interval),
            "baseline_trend": trend(&baseline),
            "intervention_trend": trend(&intervention),
            "alpha": compared.get("alpha").cloned().unwrap_or(Value::Null),
            "tests_agree": compared.get("tests_agree").cloned().unwrap_or(Value::Null),
            "significant": compared.get("significant").cloned().unwrap_or(Value::Null),
            "warnings": warnings,
        },
    }))
}

pub fn correlation_matrix(conn: &Connection, research_ref: &str, metric_names: Option<&[String]>) -> Result<Value> {
    let rows = list_metrics(conn, Some(research_ref), None)?;
    let available: Vec<String> = {
        let mut set = BTreeSet::new();
        for row in &rows { set.insert(field(row, "metric_name")); }
        set.into_iter().collect()
    };
    let metrics: Vec<String> = match metric_names {
        Some(names) => {
            let selected: Vec<String> = names.iter().map(|n| n.trim().to_string()).filter(|n| !n.is_empty()).collect();
            let unknown: Vec<String> = selected.iter().filter(|n| !available.contains(n)).cloned().collect();
            if !unknown.is_empty() {
                return Err(EngineError::new(format!("unknown metrics: {}", unknown.join(", ")),
                    "a correlation needs recorded metrics.", "use a metric name from this program."));
            }
            let mut seen = BTreeSet::new();
            selected.into_iter().filter(|n| seen.insert(n.clone())).collect()
        }
        None => available,
    };
    let mut totals: BTreeMap<(String, String), Vec<f64>> = BTreeMap::new();
    for row in &rows {
        let name = field(row, "metric_name");
        if !metrics.contains(&name) { continue; }
        totals.entry((name, field(row, "date"))).or_default()
            .push(row.get("value").and_then(Value::as_f64).unwrap_or(0.0));
    }
    let mut by_metric: BTreeMap<String, BTreeMap<String, f64>> = BTreeMap::new();
    for name in &metrics { by_metric.insert(name.clone(), BTreeMap::new()); }
    for ((name, day), values) in totals {
        if let Some(entry) = by_metric.get_mut(&name) { entry.insert(day, mean(&values)); }
    }
    let mut matrix = serde_json::Map::new();
    for left in &metrics {
        let mut row = serde_json::Map::new();
        for right in &metrics {
            let left_days: BTreeSet<_> = by_metric.get(left).map(|m| m.keys().cloned().collect()).unwrap_or_default();
            let right_days: BTreeSet<_> = by_metric.get(right).map(|m| m.keys().cloned().collect()).unwrap_or_default();
            let shared: Vec<String> = left_days.intersection(&right_days).cloned().collect();
            let xs: Vec<f64> = shared.iter().map(|d| by_metric[left][d]).collect();
            let ys: Vec<f64> = shared.iter().map(|d| by_metric[right][d]).collect();
            let result = stats::pearson(&xs, &ys);
            row.insert(right.clone(), json!({
                "r": result.get("r").cloned().unwrap_or(Value::Null),
                "n": result.get("n").cloned().unwrap_or(Value::Null),
            }));
        }
        matrix.insert(left.clone(), Value::Object(row));
    }
    Ok(json!({"metrics": metrics, "matrix": Value::Object(matrix)}))
}

pub fn analyze_multiple_metrics(
    conn: &Connection, research_ref: &str, metric_names: &[String], start_date: &str,
    baseline_days: i64, intervention_days: i64,
) -> Result<Value> {
    let names: Vec<String> = metric_names.iter().map(|n| n.trim().to_string()).filter(|n| !n.is_empty()).collect();
    if names.is_empty() { return Err(EngineError::new("no metrics selected", "a multi-metric analysis needs at least one metric.", "pass one or more metric names.")); }
    if {
        let mut seen = BTreeSet::new();
        names.iter().any(|n| !seen.insert(n))
    } {
        return Err(EngineError::new("duplicate metric selected", "each metric is analyzed once per request.", "remove the duplicate metric name."));
    }
    let mut results = serde_json::Map::new();
    for name in &names {
        results.insert(name.clone(), analyze_baseline_vs_intervention(conn, research_ref, name,
            start_date, baseline_days, intervention_days)?);
    }
    let mut global_warnings = Vec::new();
    if names.len() > MAX_SAFE_METRICS {
        global_warnings.push(format!("Multiple Comparison Risk: {} metrics exceed the safe limit of {MAX_SAFE_METRICS}; treat isolated significant results as exploratory.", names.len()));
    }
    let mut p_values = Vec::new();
    for name in &names {
        if let Some(p) = results.get(name).and_then(|r| r.get("analysis"))
            .and_then(|a| a.get("t_test")).and_then(|t| t.get("p_value")).and_then(Value::as_f64) {
            p_values.push(p);
        }
    }
    let adjusted = if p_values.is_empty() { Value::Null } else { Value::Array(stats::holm_adjust(&p_values)) };
    Ok(json!({"metrics": names, "results": Value::Object(results),
        "global_warnings": global_warnings, "holm_adjustment": adjusted}))
}
