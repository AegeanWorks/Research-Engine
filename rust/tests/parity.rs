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
use serde_json::Value;

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
fn cascade_invalidates_dependents() {
    let path = temp_db("cascade");
    let conn = open(path.to_str().unwrap()).unwrap();
    initialize(&conn).unwrap();
    let research = core::add_research(&conn, "Cascade", "", None).unwrap();
    let root = core::add_claim(&conn, &field(&research, "id"), "root", "derived",
        None, "", "", 0.5, "", "premise", &[]).unwrap();
    let dependent = core::add_claim(&conn, &field(&research, "id"), "dependent", "derived",
        None, "", "", 0.5, "", "", &[field(&root, "id")]).unwrap();
    let preview = research_engine::cascade::preview(&conn, &field(&root, "id")).unwrap();
    assert_eq!(preview.get("affected").and_then(|v| v.as_array()).map(|a| a.len()), Some(1));
    let digest = field(&preview, "digest");
    let result = research_engine::cascade::invalidate(&conn, &field(&root, "id"), "FALSIFIED",
        "bad premise", "run x", "agent", false, &digest).unwrap();
    assert_eq!(result.get("affected").and_then(|v| v.as_array()).map(|a| a.len()), Some(1));
    let dependent = core::get_claim(&conn, &field(&dependent, "id")).unwrap();
    assert_eq!(field(&dependent, "status"), "INVALIDATED");
    let n: i64 = conn.query_row("SELECT COUNT(*) FROM invalidation", [], |r| r.get(0)).unwrap();
    assert_eq!(n, 1);
}

#[test]
fn report_numbers_come_from_the_graph() {
    let path = temp_db("report");
    let conn = open(path.to_str().unwrap()).unwrap();
    initialize(&conn).unwrap();
    let research = core::add_research(&conn, "Report Program", "scope", None).unwrap();
    let claim = core::add_claim(&conn, &field(&research, "id"), "Measured claim", "derived",
        None, "", "", 0.5, "", "basis", &[]).unwrap();
    core::set_verdict(&conn, &field(&claim, "id"), "PROVEN", "evidence", "", "", "agent").unwrap();
    let report = research_engine::synthesis::report(&conn, &field(&research, "id")).unwrap();
    assert!(report.contains("- claims: 1"));
    assert!(report.contains("Measured claim"));
    assert!(report.contains("no hand-written numbers"));
    let scorecard = research_engine::synthesis::scorecard(&conn, &field(&research, "id")).unwrap();
    assert!(scorecard.contains("| PROVEN |"));
}

#[test]
fn protocols_and_observations_enforce_provenance() {
    let path = temp_db("observations");
    let conn = open(path.to_str().unwrap()).unwrap();
    initialize(&conn).unwrap();
    let research = core::add_research(&conn, "Measurements", "", None).unwrap();
    let claim = core::add_claim(&conn, &field(&research, "id"), "Measured", "derived",
        None, "", "", 0.5, "", "basis", &[]).unwrap();

    let protocol = research_engine::protocols::register(&conn, "accuracy_at_1", "top-1 accuracy",
        false, false, "", "", "agent").unwrap();
    assert_eq!(field(&protocol, "id"), "accuracy_at_1");
    assert!(research_engine::protocols::register(&conn, "accuracy_at_1", "duplicate",
        false, false, "", "", "agent").is_err());

    let ob = research_engine::observations::add(&conn, &field(&claim, "id"), "Baseline", 1.5,
        "", "", "", "", "", "", "", "", 1, "raw", "", "unclassified", "", "").unwrap();
    assert_eq!(field(&ob, "group_label"), "baseline");
    assert!(research_engine::observations::add(&conn, &field(&claim, "id"), "bad group", 1.0,
        "", "", "", "", "", "", "", "", 1, "raw", "", "unclassified", "", "").is_err());
    assert!(research_engine::observations::add(&conn, &field(&claim, "id"), "x", f64::NAN,
        "", "", "", "", "", "", "", "", 1, "raw", "", "unclassified", "", "").is_err());

    let amended = research_engine::protocols::amend(&conn, "accuracy_at_1", "top-1 accuracy v2", "clarify", "agent").unwrap();
    assert_eq!(field(&amended, "measures"), "top-1 accuracy v2");
    let findings = integrity::check(&conn).unwrap();
    let codes: Vec<&str> = findings.iter().map(|f| f.get("code").and_then(Value::as_str).unwrap_or("")).collect();
    assert!(codes.contains(&"OBS-001"), "missing OBS-001 in {codes:?}");
    assert!(codes.contains(&"OBS-002"));
    assert!(codes.contains(&"OBS-003"));
}

#[test]
fn analysis_stats_and_trend_record_evidence() {
    let path = temp_db("analysis");
    let conn = open(path.to_str().unwrap()).unwrap();
    initialize(&conn).unwrap();
    let research = core::add_research(&conn, "Analysis", "", None).unwrap();
    let claim = core::add_claim(&conn, &field(&research, "id"), "Compared", "derived",
        None, "", "", 0.5, "", "basis", &[]).unwrap();
    for value in [1.0, 2.0, 3.0, 4.0] {
        research_engine::observations::add(&conn, &field(&claim, "id"), "baseline", value,
            "", "", "", "", "", "", "", "", 1, "raw", "", "unclassified", "", "").unwrap();
    }
    for value in [2.0, 4.0, 5.0, 7.0] {
        research_engine::observations::add(&conn, &field(&claim, "id"), "treatment", value,
            "", "", "", "", "", "", "", "", 1, "raw", "", "unclassified", "", "").unwrap();
    }
    let stats = research_engine::analysis::claim_statistics(&conn, &field(&claim, "id"),
        "baseline", "treatment", 0, 2000, false, false, "agent", "", "", "").unwrap();
    assert_eq!(stats.get("claim").and_then(Value::as_str), Some(field(&claim, "id").as_str()));
    assert_eq!(stats.get("baseline").and_then(|b| b.get("n")).and_then(Value::as_u64), Some(4));
    assert!(stats.get("comparability").is_some());
    let trend = research_engine::analysis::claim_trend(&conn, &field(&claim, "id"),
        "baseline", "agent", "", "").unwrap();
    assert_eq!(trend.get("group").and_then(Value::as_str), Some("baseline"));
    let events: i64 = conn.query_row(
        "SELECT COUNT(*) FROM event WHERE kind IN ('claim.stats','claim.trend')", [], |r| r.get(0)).unwrap();
    assert_eq!(events, 2);
}

#[test]
fn search_is_phrase_first_and_program_scoped() {
    let path = temp_db("search");
    let conn = open(path.to_str().unwrap()).unwrap();
    initialize(&conn).unwrap();
    let research = core::add_research(&conn, "Search Program", "", None).unwrap();
    core::add_source(&conn, &field(&research, "id"), "Quantum Paper", Some(2024), "", "", "", "paper").unwrap();
    core::add_question(&conn, &field(&research, "id"), "Is quantum effect real?").unwrap();
    core::add_claim(&conn, &field(&research, "id"), "Quantum effect measured", "derived",
        None, "", "", 0.5, "", "quantum basis", &[]).unwrap();
    let result = research_engine::search::search(&conn, "quantum", None, None, 5, false, 800).unwrap();
    let hits = result.get("counts").unwrap();
    assert_eq!(hits["claim"]["hits"], 1);
    assert_eq!(hits["source"]["hits"], 1);
    assert_eq!(hits["question"]["hits"], 1);
    for hit in result.get("results").unwrap().as_array().unwrap() {
        assert_eq!(hit.get("score").and_then(Value::as_i64), Some(153));
    }
    assert!(result.get("text").and_then(Value::as_str).unwrap().contains("SEARCH \"quantum\""));
    let scoped = research_engine::search::search(&conn, "quantum", Some(&field(&research, "id")), None, 5, false, 800).unwrap();
    assert_eq!(scoped.get("research").and_then(Value::as_str), Some(field(&research, "id").as_str()));
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
