//! Graph-backed analysis commands: `analysis stats` and `analysis trend`.

use chrono::{DateTime, NaiveDate, TimeZone, Utc};
use rusqlite::{params, Connection};
use serde_json::{json, Value};

use crate::core::{get_claim, record_event};
use crate::db::utc_now;
use crate::error::{EngineError, Result};
use crate::observations::group_values;
use crate::stats;
use crate::util::query_json;

fn field(value: &Value, name: &str) -> String {
    value.get(name).and_then(Value::as_str).unwrap_or("").to_string()
}

fn parse_bound(value: &str, name: &str) -> Result<String> {
    let text = value.trim();
    if text.is_empty() { return Ok(String::new()); }
    let full = if text.len() == 10 && text.as_bytes().get(4) == Some(&b'-') && text.as_bytes().get(7) == Some(&b'-') {
        if name == "until" { format!("{text}T23:59:59+00:00") } else { format!("{text}T00:00:00+00:00") }
    } else { text.to_string() };
    let parsed = DateTime::parse_from_rfc3339(&full).or_else(|_| {
        NaiveDate::parse_from_str(text, "%Y-%m-%d")
            .ok()
            .and_then(|d| d.and_hms_opt(0, 0, 0))
            .map(|dt| Utc.from_utc_datetime(&dt).fixed_offset())
            .ok_or(())
    }).map_err(|_| EngineError::new(
        format!("invalid --{name} timestamp: {full:?}"),
        "a time window bound must be ISO-8601 (`YYYY-MM-DD` or full timestamp).",
        format!("pass --{name} 2026-01-01 or --{name} 2026-01-01T00:00:00+00:00."),
    ))?;
    Ok(parsed.with_timezone(&Utc).format("%Y-%m-%dT%H:%M:%S+00:00").to_string())
}

pub(crate) fn bounds(since: &str, until: &str) -> Result<(String, String)> {
    let since = parse_bound(since, "since")?;
    let until = parse_bound(until, "until")?;
    if !since.is_empty() && !until.is_empty() && since > until {
        return Err(EngineError::new(format!("empty time window: {since} is after {until}"),
            "a comparison over no record time has no values in either group.",
            "pass --since at or before --until."));
    }
    Ok((since, until))
}

pub(crate) fn group_provenance(
    conn: &Connection, claim_id: &str, group: &str, since: &str, until: &str,
) -> Result<Value> {
    let mut sql = String::from("SELECT protocol_id, instrument_id, instrument_digest, rater_id, rater_version, unit, provenance_class FROM observation WHERE claim_id=?1 AND group_label=?2 AND voided=0");
    let mut bindings: Vec<Box<dyn rusqlite::ToSql>> = vec![Box::new(claim_id.to_string()), Box::new(group.to_string())];
    if !since.is_empty() { sql.push_str(" AND at>=?3"); bindings.push(Box::new(since.to_string())); }
    if !until.is_empty() { sql.push_str(" AND at<=?4"); bindings.push(Box::new(until.to_string())); }
    sql.push_str(" ORDER BY id");
    let args: Vec<&dyn rusqlite::ToSql> = bindings.iter().map(|b| b.as_ref()).collect();
    let rows = query_json(conn, &sql, args.as_slice())?;
    let mut protocols: Vec<String> = Vec::new();
    let mut instruments: Vec<String> = Vec::new();
    let mut units: Vec<String> = Vec::new();
    let mut classes: Vec<String> = Vec::new();
    let mut missing = false;
    for row in &rows {
        let protocol = field(row, "protocol_id");
        if protocol.trim().is_empty() { missing = true; } else if !protocols.contains(&protocol) { protocols.push(protocol); }
        let instrument = format!("{}|{}|{}|{}", field(row, "instrument_id"), field(row, "instrument_digest"),
            field(row, "rater_id"), field(row, "rater_version"));
        if (!field(row, "instrument_id").trim().is_empty() || !field(row, "rater_id").trim().is_empty())
            && !instruments.contains(&instrument) { instruments.push(instrument); }
        let unit = field(row, "unit");
        if !unit.trim().is_empty() && !units.contains(&unit) { units.push(unit); }
        let class = field(row, "provenance_class");
        if !classes.contains(&class) { classes.push(class); }
    }
    protocols.sort(); instruments.sort(); units.sort(); classes.sort();
    Ok(json!({"protocols": protocols, "instruments": instruments, "units": units,
        "classes": classes, "missing": missing}))
}

pub(crate) fn comparability(
    baseline: &Value, treatment: &Value, allow_incomparable: bool, allow_self_reported: bool,
) -> Result<(bool, String, Value)> {
    let b_protocols = baseline.get("protocols").and_then(Value::as_array).cloned().unwrap_or_default();
    let t_protocols = treatment.get("protocols").and_then(Value::as_array).cloned().unwrap_or_default();
    let b_missing = baseline.get("missing").and_then(Value::as_bool).unwrap_or(false);
    let t_missing = treatment.get("missing").and_then(Value::as_bool).unwrap_or(false);
    if !b_protocols.is_empty() && b_missing {
        return Err(EngineError::new("baseline group mixes provenanced and unprovenanced observations",
            "a group with some protocol records and some legacy rows cannot be compared.",
            "void the legacy rows or record their provenance before comparing."));
    }
    if !t_protocols.is_empty() && t_missing {
        return Err(EngineError::new("treatment group mixes provenanced and unprovenanced observations",
            "a group with some protocol records and some legacy rows cannot be compared.",
            "void the legacy rows or record their provenance before comparing."));
    }
    let classes = |group: &Value| -> Vec<String> {
        group.get("classes").and_then(Value::as_array)
            .map(|a| a.iter().map(|v| v.as_str().unwrap_or("").to_string()).collect())
            .unwrap_or_default()
    };
    for (label, group) in [("baseline", baseline), ("treatment", treatment)] {
        let items = classes(group);
        if items.iter().any(|c| c == "self_reported")
            && items.iter().filter(|c| c.as_str() != "unclassified").count() > 1 {
            return Err(EngineError::new(format!("{label} group mixes self-reported and independent measurements"),
                "a self-reported number is not interchangeable with an independent one.",
                "split the group, or mark the whole group self-reported."));
        }
    }
    let b_classes = classes(baseline);
    let t_classes = classes(treatment);
    let self_reported = b_classes.iter().chain(t_classes.iter()).any(|c| c == "self_reported");
    if self_reported && !allow_self_reported {
        return Err(EngineError::new("self-reported measurement cannot be compared",
            "a number produced by the system under study is not independent evidence.",
            "pass --allow-self-reported with a caveat, or record an independent measurement."));
    }
    let as_text = |v: &Value| v.as_str().unwrap_or("").to_string();
    let bp = b_protocols.first().map(as_text).unwrap_or_default();
    let tp = t_protocols.first().map(as_text).unwrap_or_default();
    let b_instruments = baseline.get("instruments").and_then(Value::as_array).cloned().unwrap_or_default();
    let t_instruments = treatment.get("instruments").and_then(Value::as_array).cloned().unwrap_or_default();
    let b_units = baseline.get("units").and_then(Value::as_array).cloned().unwrap_or_default();
    let t_units = treatment.get("units").and_then(Value::as_array).cloned().unwrap_or_default();
    let reason = if self_reported { "self-reported measurement".to_string() }
        else if b_protocols.len() > 1 || t_protocols.len() > 1 { "a group records more than one protocol".to_string() }
        else if !bp.is_empty() && !tp.is_empty() && bp != tp { format!("different protocols: {bp} vs {tp}") }
        else if b_instruments.len() > 1 || t_instruments.len() > 1 { "a group records more than one instrument or rater".to_string() }
        else if !b_instruments.is_empty() && !t_instruments.is_empty() && b_instruments != t_instruments { "same protocol, different instrument or rater".to_string() }
        else if !b_units.is_empty() && !t_units.is_empty() && b_units != t_units {
            let names = |items: &Vec<Value>| items.iter().map(as_text).collect::<Vec<_>>().join(", ");
            format!("different units: {} vs {}", names(&b_units), names(&t_units))
        } else { String::new() };
    if !reason.is_empty() && !(allow_incomparable || (self_reported && allow_self_reported)) {
        return Err(EngineError::new(format!("measurements are not comparable: {reason}"),
            "a delta between different protocols, instruments or units is not the same quantity.",
            "record comparable measurements, or pass --allow-incomparable with a stated caveat."));
    }
    let comparable = reason.is_empty();
    let all_classes: Vec<String> = b_classes.iter().chain(t_classes.iter()).cloned().collect();
    let provenance_class = if all_classes.iter().any(|c| c == "self_reported")
        && all_classes.iter().any(|c| c == "independent" || c == "unclassified") { "mixed" }
        else if all_classes.iter().any(|c| c == "self_reported") { "self_reported" }
        else if all_classes.iter().any(|c| c == "independent") { "independent" }
        else { "unclassified" };
    let details = json!({
        "comparable": comparable,
        "reason": if reason.is_empty() { "same protocol, instrument and unit".to_string() } else { reason.clone() },
        "baseline_protocol": bp,
        "treatment_protocol": tp,
        "baseline_unit": if b_units.len() == 1 { as_text(&b_units[0]) } else { String::new() },
        "treatment_unit": if t_units.len() == 1 { as_text(&t_units[0]) } else { String::new() },
        "unprovenanced": bp.is_empty() || tp.is_empty(),
        "provenance_class": provenance_class,
        "self_reported": self_reported,
    });
    Ok((comparable, reason, details))
}

#[allow(clippy::too_many_arguments)]
pub fn claim_statistics(
    conn: &Connection,
    claim_ref: &str,
    baseline: &str,
    treatment: &str,
    seed: i64,
    resamples: usize,
    allow_incomparable: bool,
    allow_self_reported: bool,
    actor: &str,
    plan_ref: &str,
    since: &str,
    until: &str,
) -> Result<Value> {
    let claim = get_claim(conn, claim_ref)?;
    let baseline = baseline.trim().to_lowercase();
    let treatment = treatment.trim().to_lowercase();
    if baseline == treatment {
        return Err(EngineError::new(format!("cannot compare group {baseline:?} with itself"),
            "a comparison needs two different groups for a difference to mean anything.",
            "choose a different baseline or treatment label."));
    }
    if resamples < 10 {
        return Err(EngineError::new(format!("too few bootstrap resamples: {resamples}"),
            "a percentile interval from fewer than ten resamples is noise.",
            "pass --resamples 2000 or more."));
    }
    let (since, until) = bounds(since, until)?;
    let groups = group_values(conn, &field(&claim, "id"), Some(&since), Some(&until))?;
    let lookup = |label: &str| -> Option<Vec<f64>> {
        groups.iter().find(|(name, _)| name == label).map(|(_, values)| values.clone())
    };
    let (b_values, t_values) = match (lookup(&baseline), lookup(&treatment)) {
        (Some(b), Some(t)) => (b, t),
        _ => {
            let missing = if lookup(&baseline).is_none() { &baseline } else { &treatment };
            let mut available: Vec<String> = groups.iter().map(|(name, _)| name.clone()).collect();
            available.sort();
            return Err(EngineError::new(
                format!("no observations in group '{missing}' for {}", field(&claim, "id")),
                "a comparison needs recorded values in both groups.",
                format!("add values with `observation add`, or choose one of: {}." ,
                    if available.is_empty() { "none".to_string() } else { available.join(", ") })));
        }
    };
    let plan_ref = plan_ref.trim();
    let mut result_plan = String::new();
    let mut planned = false;
    if !plan_ref.is_empty() {
        let plans = query_json(conn, "SELECT * FROM analysis_plan WHERE id=?1", params![plan_ref])?;
        let plan = plans.into_iter().next().ok_or_else(|| EngineError::not_found("analysis plan", plan_ref))?;
        if field(&plan, "claim_id") != field(&claim, "id") {
            return Err(EngineError::new("analysis plan belongs to another claim",
                "a plan predicts one claim's comparison, not any comparison.",
                "cite a plan preregistered for this claim."));
        }
        if field(&plan, "baseline") != baseline || field(&plan, "treatment") != treatment {
            return Err(EngineError::new("analysis plan predicts a different group pair",
                "the cited plan compares other groups than this run.",
                "cite the plan matching this baseline and treatment."));
        }
        result_plan = field(&plan, "id");
    } else {
        planned = !query_json(conn,
            "SELECT 1 FROM analysis_plan WHERE claim_id=?1 AND baseline=?2 AND treatment=?3",
            params![field(&claim, "id"), baseline, treatment])?.is_empty();
    }
    let bp = group_provenance(conn, &field(&claim, "id"), &baseline, &since, &until)?;
    let tp = group_provenance(conn, &field(&claim, "id"), &treatment, &since, &until)?;
    let (comparable, reason, details) = comparability(&bp, &tp, allow_incomparable, allow_self_reported)?;
    let mut result = stats::compare_groups(&b_values, &t_values, seed, resamples);
    let mut warnings: Vec<Value> = result.get("warnings").and_then(Value::as_array).cloned().unwrap_or_default();
    if !comparable { warnings.push(json!(format!("incomparable comparison allowed: {reason}"))); }
    else if details.get("unprovenanced").and_then(Value::as_bool) == Some(true) {
        warnings.push(json!("one or both groups have no measurement provenance; the comparison is unverified"));
    }
    if groups.len() > 2 {
        warnings.push(json!(format!("{} groups recorded; this single pairwise test is uncorrected", groups.len())));
    }
    if planned && result_plan.is_empty() {
        warnings.push(json!("exploratory: preregistered plans exist for this comparison and none is cited; cite one with --plan or record why this run is unplanned"));
    }
    {
        let object = result.as_object_mut().expect("comparison object");
        object.insert("comparability".to_string(), details.clone());
        object.insert("claim".to_string(), json!(field(&claim, "id")));
        object.insert("baseline_label".to_string(), json!(baseline));
        object.insert("treatment_label".to_string(), json!(treatment));
        object.insert("plan".to_string(), json!(result_plan));
        object.insert("window".to_string(), json!({"since": since, "until": until}));
        object.insert("warnings".to_string(), Value::Array(warnings));
    }
    let detail = format!("{}->{} n={}/{} d={:.3} welch_p={:.4} mwu_p={:.4}", baseline, treatment,
        b_values.len(), t_values.len(),
        result.get("cohens_d").and_then(Value::as_f64).unwrap_or(0.0),
        result.get("welch").and_then(|w| w.get("p")).and_then(Value::as_f64).unwrap_or(1.0),
        result.get("mann_whitney").and_then(|w| w.get("p")).and_then(Value::as_f64).unwrap_or(1.0));
    record_event(conn, &field(&claim, "research_id"), "claim.stats", &field(&claim, "id"), &detail, actor)?;
    Ok(result)
}

pub fn claim_trend(conn: &Connection, claim_ref: &str, group: &str, actor: &str, since: &str, until: &str) -> Result<Value> {
    let claim = get_claim(conn, claim_ref)?;
    let group = group.trim().to_lowercase();
    let (since, until) = bounds(since, until)?;
    let groups = group_values(conn, &field(&claim, "id"), Some(&since), Some(&until))?;
    let values = groups.iter().find(|(name, _)| *name == group).map(|(_, v)| v.clone())
        .ok_or_else(|| {
            let mut available: Vec<String> = groups.iter().map(|(n, _)| n.clone()).collect();
            available.sort();
            EngineError::new(format!("no observations in group '{group}' for {}", field(&claim, "id")),
                "a trend needs a recorded sequence.",
                format!("add values with `observation add`, or choose one of: {}.",
                    if available.is_empty() { "none".to_string() } else { available.join(", ") }))
        })?;
    let xs: Vec<f64> = (1..=values.len()).map(|i| i as f64).collect();
    let mut result = stats::linregress(&xs, &values);
    let object = result.as_object_mut().expect("regression object");
    let mut warnings = Vec::new();
    if values.len() < 3 { warnings.push("fewer than 3 observations; no trend is estimated".to_string()); }
    object.insert("claim".to_string(), json!(field(&claim, "id")));
    object.insert("group".to_string(), json!(group));
    object.insert("warnings".to_string(), json!(warnings));
    object.insert("window".to_string(), json!({"since": since, "until": until}));
    let detail = if values.len() < 3 {
        format!("{group} n={} insufficient for a trend", values.len())
    } else {
        format!("{group} n={} slope={:.6} r={:.3} p={:.4}", values.len(),
            result.get("slope").and_then(Value::as_f64).unwrap_or(0.0),
            result.get("r").and_then(Value::as_f64).unwrap_or(0.0),
            result.get("p").and_then(Value::as_f64).unwrap_or(1.0))
    };
    record_event(conn, &field(&claim, "research_id"), "claim.trend", &field(&claim, "id"), &detail, actor)?;
    let _ = utc_now();
    Ok(result)
}
