//! Core contract tests for the Rust engine.
//!
//! Each test builds a fresh schema-14 graph and checks the invariants the Python
//! engine enforces: provenance rules, append-only verdicts, a verifiable event
//! ledger and cross-implementation readability.

use std::path::PathBuf;
use std::sync::atomic::{AtomicUsize, Ordering};

use research_engine::core;
use research_engine::db::{initialize, open};
use research_engine::error::EngineError;
use research_engine::integrity;
use research_engine::vocab::SCHEMA_VERSION;

static COUNTER: AtomicUsize = AtomicUsize::new(0);

fn temp_db(name: &str) -> PathBuf {
    let n = COUNTER.fetch_add(1, Ordering::Relaxed);
    let mut path = std::env::temp_dir();
    path.push(format!("re-rust-{name}-{}-{n}.db", std::process::id()));
    let _ = std::fs::remove_file(&path);
    let _ = std::fs::remove_file(path.with_extension("db-wal"));
    let _ = std::fs::remove_file(path.with_extension("db-shm"));
    path
}

fn field(row: &serde_json::Value, key: &str) -> String {
    row.get(key).and_then(serde_json::Value::as_str).unwrap_or("").to_string()
}

#[test]
fn init_writes_schema_14() {
    let path = temp_db("schema");
    let conn = open(path.to_str().unwrap()).unwrap();
    assert!(initialize(&conn).unwrap().is_none());
    let version: i64 = conn.query_row("SELECT version FROM schema_meta", [], |r| r.get(0)).unwrap();
    assert_eq!(version, SCHEMA_VERSION);
    let tables: i64 = conn.query_row(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'",
        [], |r| r.get(0)).unwrap();
    assert_eq!(tables, 25, "schema has {tables} tables, expected the 25 v14 tables");
}

#[test]
fn core_lifecycle_is_coherent() {
    let path = temp_db("lifecycle");
    let conn = open(path.to_str().unwrap()).unwrap();
    initialize(&conn).unwrap();

    let research = core::add_research(&conn, "Fluid Universe", "replication", None).unwrap();
    let source = core::add_source(&conn, &field(&research, "id"), "Nature 2024", Some(2024), "10.1/x", "", "", "paper").unwrap();
    let question = core::add_question(&conn, &field(&research, "id"), "Is it reproducible?").unwrap();
    let claim = core::add_claim(&conn, &field(&research, "id"), "Effect measured", "empirical",
        Some(&field(&source, "id")), "we observed 3.2", "p4", 0.5, "python -c pass", "", &[]).unwrap();
    let verdict = core::set_verdict(&conn, &field(&claim, "id"), "PROVEN", "verified group", "", "", "agent").unwrap();

    assert_eq!(field(&verdict, "status"), "PROVEN");
    let findings = integrity::check(&conn).unwrap();
    assert!(!integrity::has_errors(&findings), "unexpected findings: {findings:?}");
    let ledger = core::verify_events(&conn).unwrap();
    assert_eq!(ledger.get("ok").and_then(|v| v.as_bool()), Some(true));
    assert_eq!(field(&question, "status"), "open");
}

#[test]
fn empirical_provenance_gate_refuses_missing_quote() {
    let path = temp_db("provenance");
    let conn = open(path.to_str().unwrap()).unwrap();
    initialize(&conn).unwrap();
    let research = core::add_research(&conn, "Gate", "", None).unwrap();
    let source = core::add_source(&conn, &field(&research, "id"), "Web source", None, "", "https://x", "", "paper").unwrap();
    let error: EngineError = core::add_claim(&conn, &field(&research, "id"), "Bad claim", "empirical",
        Some(&field(&source, "id")), "", "", 0.5, "", "", &[]).unwrap_err();
    assert_eq!(error.what, "empirical claim has no quote or locator");
    assert!(!error.why.is_empty() && !error.fix.is_empty());
    let count: i64 = conn.query_row("SELECT COUNT(*) FROM claim", [], |r| r.get(0)).unwrap();
    assert_eq!(count, 0);
}

#[test]
fn verdict_is_append_only() {
    let path = temp_db("verdicts");
    let conn = open(path.to_str().unwrap()).unwrap();
    initialize(&conn).unwrap();
    let research = core::add_research(&conn, "Corrections", "", None).unwrap();
    let claim = core::add_claim(&conn, &field(&research, "id"), "Correct me", "derived",
        None, "", "", 0.5, "", "because", &[]).unwrap();
    core::set_verdict(&conn, &field(&claim, "id"), "PROVEN", "first", "", "", "agent").unwrap();
    core::set_verdict(&conn, &field(&claim, "id"), "FALSIFIED", "second", "", "", "agent").unwrap();
    let count: i64 = conn.query_row("SELECT COUNT(*) FROM verdict WHERE subject_kind='claim'", [], |r| r.get(0)).unwrap();
    assert_eq!(count, 2, "a correction must be a new verdict, never an edit");
    let previous: String = conn.query_row(
        "SELECT previous_status FROM verdict ORDER BY id DESC LIMIT 1", [], |r| r.get(0)).unwrap();
    assert_eq!(previous, "PROVEN");
}

#[test]
fn event_hash_matches_python_algorithm() {
    // Known-answer vector produced by engine/events.py::event_hash_for.
    let expected = "3aeec2a90f93534620f34bc6221960af490a48d6d61ac926d51105ad56abd46e";
    let actual = research_engine::util::event_hash_for(
        "", "ev_000001", "2026-01-01T00:00:00+00:00", "r_000001", "research.add",
        "r_000001", "", "engine", 1, "ev_000001", "",
    );
    assert_eq!(actual, expected);
}
