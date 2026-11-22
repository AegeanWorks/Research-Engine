//! Deterministic JSONL export and the content/record digests used by manifests.

use std::collections::BTreeSet;

use rusqlite::params;
use serde_json::{json, Value};

use crate::core::get_research;
use crate::db::utc_now;
use crate::error::Result;
use crate::util::{atomic_write_text, digest, query_json, to_python_json};
use crate::vocab::SCHEMA_VERSION;

pub const BRIDGE: &str = "articles/1";

const ORDER: &[&str] = &[
    "research", "protocol", "source", "question", "claim", "hypothesis", "killtest",
    "edge", "test_run", "test_attempt", "verdict", "invalidation", "observation",
    "ai_artifact", "event",
];
const VOLATILE_RUN_FIELDS: &[&str] = &["id", "run_group", "started_at", "duration_ms", "output_tail"];

fn field(value: &Value, name: &str) -> String {
    value.get(name).and_then(Value::as_str).unwrap_or("").to_string()
}

fn as_python_str(value: &Value) -> String {
    match value {
        Value::Null => "None".to_string(),
        Value::Bool(flag) => if *flag { "True".to_string() } else { "False".to_string() },
        Value::String(text) => text.clone(),
        other => to_python_json(other),
    }
}

fn rows_for(conn: &rusqlite::Connection, table: &str, research_id: Option<&str>) -> Result<Vec<Value>> {
    let sql = match table {
        "research" => match research_id {
            Some(_) => "SELECT * FROM research WHERE id=?1 ORDER BY id".to_string(),
            None => "SELECT * FROM research ORDER BY id".to_string(),
        },
        "protocol" => "SELECT * FROM protocol ORDER BY id".to_string(),
        "source" | "question" | "claim" | "hypothesis" | "killtest" | "observation"
        | "ai_artifact" | "event" => match research_id {
            Some(_) => format!("SELECT * FROM {table} WHERE research_id=?1 ORDER BY id"),
            None => format!("SELECT * FROM {table} ORDER BY id"),
        },
        "edge" | "test_run" | "test_attempt" | "verdict" | "invalidation" => {
            format!("SELECT * FROM {table} ORDER BY id")
        }
        other => return Err(crate::error::EngineError::new(
            format!("unknown bundle table: {other}"), "the export order is a closed vocabulary.",
            "use one of the declared tables.")),
    };
    let scoped_column = matches!(table,
        "source" | "question" | "claim" | "hypothesis" | "killtest" | "observation"
        | "ai_artifact" | "event" | "research");
    let rows = match research_id {
        Some(id) if scoped_column => query_json(conn, &sql, params![id])?,
        Some(_) => query_json(conn, &sql, [])?,
        None => query_json(conn, &sql, [])?,
    };
    let Some(research_id) = research_id else { return Ok(rows); };
    if table == "protocol" { return Ok(rows); }
    let result = match table {
        "edge" => {
            let mut members = BTreeSet::new();
            for entity in ["claim", "question", "hypothesis"] {
                for row in query_json(conn, &format!("SELECT id FROM {entity} WHERE research_id=?1"), params![research_id])? {
                    members.insert(field(&row, "id"));
                }
            }
            rows.into_iter().filter(|row| members.contains(&field(row, "src_id"))
                || members.contains(&field(row, "dst_id"))).collect()
        }
        "test_run" | "test_attempt" => {
            let mut tests = BTreeSet::new();
            for row in query_json(conn, "SELECT id FROM killtest WHERE research_id=?1", params![research_id])? {
                tests.insert(field(&row, "id"));
            }
            rows.into_iter().filter(|row| tests.contains(&field(row, "test_id"))).collect()
        }
        "verdict" => {
            let mut members = BTreeSet::new();
            for entity in ["claim", "hypothesis"] {
                for row in query_json(conn, &format!("SELECT id FROM {entity} WHERE research_id=?1"), params![research_id])? {
                    members.insert(field(&row, "id"));
                }
            }
            rows.into_iter().filter(|row| members.contains(&field(row, "subject_id"))).collect()
        }
        "invalidation" => {
            let mut claims = BTreeSet::new();
            for row in query_json(conn, "SELECT id FROM claim WHERE research_id=?1", params![research_id])? {
                claims.insert(field(&row, "id"));
            }
            rows.into_iter().filter(|row| claims.contains(&field(row, "root_id"))).collect()
        }
        _ => rows,
    };
    Ok(result)
}

pub fn export_records(conn: &rusqlite::Connection, reference: Option<&str>) -> Result<(Vec<Value>, Value)> {
    let research_id = match reference {
        Some(reference) => Some(field(&get_research(conn, reference)?, "id")),
        None => None,
    };
    let mut records = Vec::new();
    let mut counts = serde_json::Map::new();
    for table in ORDER {
        let rows = rows_for(conn, table, research_id.as_deref())?;
        counts.insert(table.to_string(), json!(rows.len()));
        for row in rows {
            let mut payload = serde_json::Map::new();
            payload.insert("type".to_string(), json!(table));
            if let Value::Object(map) = row { for (key, value) in map { payload.insert(key, value); } }
            records.push(Value::Object(payload));
        }
    }
    Ok((records, Value::Object(counts)))
}

pub fn evidence_records(records: &[Value]) -> Vec<Value> {
    records.iter().filter(|r| field(r, "type") != "event").cloned().collect()
}

pub fn content_records(records: &[Value]) -> Vec<Value> {
    let mut runs: BTreeSet<Vec<(String, String)>> = BTreeSet::new();
    let mut attempts: BTreeSet<(String, String, String)> = BTreeSet::new();
    let mut kept = Vec::new();
    for record in records {
        match field(record, "type").as_str() {
            "test_run" => {
                let mut projection = Vec::new();
                if let Value::Object(map) = record {
                    for (key, value) in map {
                        if !VOLATILE_RUN_FIELDS.contains(&key.as_str()) {
                            projection.push((key.clone(), as_python_str(value)));
                        }
                    }
                }
                projection.sort();
                runs.insert(projection);
            }
            "test_attempt" => {
                attempts.insert((field(record, "test_id"), field(record, "outcome"), field(record, "reason")));
            }
            _ => kept.push(record.clone()),
        }
    }
    for fields in runs {
        let get = |key: &str| fields.iter().find(|(name, _)| name == key).map(|(_, value)| value.clone()).unwrap_or_default();
        let identity = format!("run:{}:{}", get("test_id"), get("run_tag"));
        let projection: Vec<Value> = fields.into_iter().map(|(k, v)| json!([k, v])).collect();
        kept.push(json!({"type": "test_run", "id": identity, "projection": projection}));
    }
    for (test_id, outcome, reason) in attempts {
        kept.push(json!({
            "type": "test_attempt",
            "id": format!("attempt:{test_id}:{outcome}:{reason}"),
            "projection": [test_id, outcome, reason],
        }));
    }
    kept
}

fn digest_records(records: &[Value], kind: &str) -> String {
    let blob = records.iter().map(to_python_json).collect::<Vec<_>>().join("\n");
    digest(kind, blob)
}

pub fn graph_sha256(conn: &rusqlite::Connection, reference: Option<&str>) -> Result<String> {
    let (records, _) = export_records(conn, reference)?;
    Ok(digest_records(&evidence_records(&records), "graph/1"))
}

pub fn content_sha256(conn: &rusqlite::Connection, reference: Option<&str>) -> Result<String> {
    let (records, _) = export_records(conn, reference)?;
    Ok(digest_records(&content_records(&evidence_records(&records)), "content/1"))
}

pub fn export_digest(records: &[Value]) -> String {
    digest_records(records, "export/1")
}

pub fn export_jsonl(conn: &rusqlite::Connection, path: &std::path::Path, reference: Option<&str>) -> Result<Value> {
    let (records, counts) = export_records(conn, reference)?;
    let meta = json!({
        "type": "meta",
        "bridge": BRIDGE,
        "schema": SCHEMA_VERSION,
        "engine": "research-engine",
        "exported_at": utc_now(),
        "research": reference.unwrap_or("all"),
        "records": records.len(),
        "export_digest": export_digest(&records),
    });
    let mut lines = vec![to_python_json(&meta)];
    lines.extend(records.iter().map(to_python_json));
    lines.push(String::new());
    atomic_write_text(path, &lines.join("\n"))?;
    Ok(counts)
}

pub fn verify_export(path: &std::path::Path) -> Result<Value> {
    let text = std::fs::read_to_string(path)?;
    let mut lines = text.lines();
    let meta: Value = serde_json::from_str(lines.next().unwrap_or("")).map_err(|e| {
        crate::error::EngineError::new(format!("invalid export meta: {e}"),
            "an export must carry a digest in its first line.", "regenerate the snapshot with `export`.")
    })?;
    let mut records = Vec::new();
    for line in lines {
        if line.trim().is_empty() { continue; }
        records.push(serde_json::from_str::<Value>(line)?);
    }
    let recorded = field(&meta, "export_digest");
    if recorded.is_empty() {
        return Err(crate::error::EngineError::new(
            format!("snapshot carries no digest: {}", path.to_string_lossy()),
            "this export predates self-verification, so its contents cannot be proven intact.",
            "re-export the snapshot with this engine version."));
    }
    let actual = export_digest(&records);
    let recorded_count = meta.get("records").and_then(Value::as_i64);
    let counts_match = recorded_count.map(|n| n == records.len() as i64).unwrap_or(true);
    let schema = meta.get("schema").cloned().unwrap_or(Value::Null);
    Ok(json!({
        "path": path.to_string_lossy(),
        "ok": recorded.is_ascii() && recorded == actual,
        "digest": actual,
        "recorded_digest": recorded,
        "records": records.len(),
        "recorded_records": recorded_count,
        "counts_match": counts_match,
        "schema": schema,
        "schema_supported": schema.as_i64() == Some(SCHEMA_VERSION),
        "research": meta.get("research").cloned().unwrap_or(Value::Null),
        "exported_at": meta.get("exported_at").cloned().unwrap_or(Value::Null),
    }))
}
