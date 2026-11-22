//! Generated-report manifests and drift detection (engine/manifest.py).

use std::path::{Path, PathBuf};

use rusqlite::Connection;
use serde_json::{json, Value};

use crate::bundle::{content_sha256, graph_sha256};
use crate::context::findings_for_research;
use crate::core::{get_research, research_counts, record_event};
use crate::db::utc_now;
use crate::error::{EngineError, Result};
use crate::synthesis::{self, LIMITS};
use crate::util::{atomic_write_text, digest, to_stable_json};
use crate::vocab::VERSION;

pub const REPORT_SCHEMA: &str = "research-engine.report/3";
pub const LICENSE_ID: &str = "ASL-1.1";
pub const MANIFEST_SUFFIX: &str = ".manifest.json";

pub fn license_block() -> Value {
    let path = Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap_or(Path::new(".")).join("LICENSE");
    match std::fs::read(&path) {
        Ok(raw) => {
            let normalized = String::from_utf8_lossy(&raw).replace("\r\n", "\n").replace('\r', "\n");
            json!({"id": LICENSE_ID, "sha256": digest("license/1", normalized.as_bytes())})
        }
        Err(_) => json!({"id": "unknown", "sha256": ""}),
    }
}

pub fn manifest_path(path: &Path) -> PathBuf {
    if path.to_string_lossy().ends_with(MANIFEST_SUFFIX) { path.to_path_buf() }
    else { PathBuf::from(format!("{}{}", path.to_string_lossy(), MANIFEST_SUFFIX)) }
}

pub fn build_manifest(conn: &Connection, reference: &str, text: &str) -> Result<Value> {
    let research = get_research(conn, reference)?;
    let rid = research.get("id").and_then(Value::as_str).unwrap_or("");
    let findings = findings_for_research(conn, rid)?;
    let errors = findings.iter().filter(|f| f.get("severity").and_then(Value::as_str) == Some("error")).count();
    let warnings = findings.iter().filter(|f| f.get("severity").and_then(Value::as_str) == Some("warning")).count();
    Ok(json!({
        "schema": REPORT_SCHEMA,
        "engine": VERSION,
        "research": {"id": research.get("id").cloned().unwrap_or_default(),
                     "slug": research.get("slug").cloned().unwrap_or_default()},
        "generated_at": utc_now(),
        "license": license_block(),
        "report_sha256": digest("report/1", text.as_bytes()),
        "content_sha256": content_sha256(conn, Some(rid))?,
        "graph_sha256": graph_sha256(conn, Some(rid))?,
        "counts": research_counts(conn, rid)?,
        "findings": {"errors": errors, "warnings": warnings},
        "limits": LIMITS,
    }))
}

pub fn write_report(conn: &Connection, reference: &str, path: &Path) -> Result<Value> {
    let text = synthesis::report(conn, reference)?;
    let manifest = build_manifest(conn, reference, &text)?;
    let sidecar = manifest_path(path);
    atomic_write_text(path, &text)?;
    atomic_write_text(&sidecar, &to_stable_json(&manifest))?;
    record_event(conn, "", "report.write", &sidecar.to_string_lossy(),
        &format!("report {} graph {}",
            manifest.get("report_sha256").and_then(Value::as_str).unwrap_or("").chars().take(16).collect::<String>(),
            manifest.get("graph_sha256").and_then(Value::as_str).unwrap_or("").chars().take(16).collect::<String>()),
        manifest.get("research").and_then(|r| r.get("id")).and_then(Value::as_str).unwrap_or(""))?;
    Ok(json!({
        "report": path.to_string_lossy(),
        "manifest": sidecar.to_string_lossy(),
        "report_sha256": manifest.get("report_sha256").cloned().unwrap_or_default(),
        "content_sha256": manifest.get("content_sha256").cloned().unwrap_or_default(),
        "graph_sha256": manifest.get("graph_sha256").cloned().unwrap_or_default(),
    }))
}

fn load_manifest(path: &Path) -> Result<Value> {
    if !path.is_file() {
        return Err(EngineError::new(format!("manifest not found: {}", path.to_string_lossy()),
            "a generated report is only verifiable together with its manifest.",
            "regenerate it with `report REF --out PATH`, then commit both files."));
    }
    let text = std::fs::read_to_string(path)?;
    let stored: Value = serde_json::from_str(&text)?;
    if stored.get("schema").and_then(Value::as_str) != Some(REPORT_SCHEMA) {
        return Err(EngineError::new(
            format!("unsupported manifest schema: {:?}", stored.get("schema")),
            format!("this build reads {REPORT_SCHEMA} only."),
            "regenerate the report with this engine version."));
    }
    Ok(stored)
}

pub fn check_report(conn: &Connection, reference: &str, path: &Path, strict: bool) -> Result<Value> {
    let sidecar = manifest_path(path);
    let stored = load_manifest(&sidecar)?;
    let research = get_research(conn, reference)?;
    let rid = research.get("id").and_then(Value::as_str).unwrap_or("");
    let reported_id = stored.get("research").and_then(|r| r.get("id")).and_then(Value::as_str).unwrap_or("");
    let mut drift = Vec::new();
    if reported_id != rid { drift.push(format!("research {reported_id} != {rid}")); }
    let current_content = content_sha256(conn, Some(rid))?;
    if stored.get("content_sha256").and_then(Value::as_str) != Some(current_content.as_str()) {
        drift.push("graph content changed since the report was generated".to_string());
    }
    let current_graph = graph_sha256(conn, Some(rid))?;
    if strict && stored.get("graph_sha256").and_then(Value::as_str) != Some(current_graph.as_str()) {
        drift.push("record set changed since the report was generated (strict)".to_string());
    }
    let current_text = synthesis::report(conn, rid)?;
    let current_report = digest("report/1", current_text.as_bytes());
    if stored.get("report_sha256").and_then(Value::as_str) != Some(current_report.as_str()) {
        drift.push("rendered report changed since it was generated".to_string());
    }
    let mut report_path = path.to_path_buf();
    if path.to_string_lossy().ends_with(MANIFEST_SUFFIX) {
        let raw = path.to_string_lossy();
        report_path = PathBuf::from(&raw[..raw.len() - MANIFEST_SUFFIX.len()]);
    }
    match std::fs::read(&report_path) {
        Ok(bytes) => {
            if digest("report/1", &bytes) != stored.get("report_sha256").and_then(Value::as_str).unwrap_or("") {
                drift.push("report file bytes differ from the manifest digest".to_string());
            }
        }
        Err(_) => drift.push(format!("report file missing: {}", report_path.to_string_lossy())),
    }
    if stored.get("license") != Some(&license_block()) {
        drift.push("license terms changed since the report was generated".to_string());
    }
    if stored.get("counts") != Some(&research_counts(conn, rid)?) {
        drift.push("record counts changed since the report was generated".to_string());
    }
    Ok(json!({
        "manifest": sidecar.to_string_lossy(),
        "clean": drift.is_empty(),
        "strict": strict,
        "drift": drift,
        "content_sha256": current_content,
        "graph_sha256": current_graph,
        "report_sha256": current_report,
        "generated_at": stored.get("generated_at").cloned().unwrap_or_default(),
    }))
}
