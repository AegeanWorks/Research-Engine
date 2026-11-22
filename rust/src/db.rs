//! SQLite connection, schema versioning and atomic transactions.
//!
//! The schema is a byte-for-byte port of `engine/database.py`'s v14 schema so a
//! Rust-built database is readable by the Python engine and vice versa.

use std::path::Path;

use chrono::Utc;
use rusqlite::{params, Connection};

use crate::error::{EngineError, Result};
use crate::vocab::SCHEMA_VERSION;

pub const SCHEMA: &str = r#"
CREATE TABLE IF NOT EXISTS schema_meta (version INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS counters (prefix TEXT PRIMARY KEY, value INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS research (
    id TEXT PRIMARY KEY, slug TEXT NOT NULL UNIQUE, title TEXT NOT NULL,
    scope TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS source (
    id TEXT PRIMARY KEY, research_id TEXT NOT NULL REFERENCES research(id),
    kind TEXT NOT NULL, title TEXT NOT NULL, authors TEXT NOT NULL DEFAULT '',
    year INTEGER, doi TEXT NOT NULL DEFAULT '', url TEXT NOT NULL DEFAULT '',
    retrieved_at TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'active',
    status_note TEXT NOT NULL DEFAULT '', status_at TEXT NOT NULL DEFAULT '',
    screening TEXT NOT NULL DEFAULT 'identified', screening_reason TEXT NOT NULL DEFAULT '',
    screening_at TEXT NOT NULL DEFAULT '', arxiv TEXT NOT NULL DEFAULT '',
    venue TEXT NOT NULL DEFAULT '', abstract TEXT NOT NULL DEFAULT '',
    tags TEXT NOT NULL DEFAULT '', study_type TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS question (
    id TEXT PRIMARY KEY, research_id TEXT NOT NULL REFERENCES research(id),
    text TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'open', created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS claim (
    id TEXT PRIMARY KEY, research_id TEXT NOT NULL REFERENCES research(id),
    source_id TEXT REFERENCES source(id), text TEXT NOT NULL, quote TEXT NOT NULL DEFAULT '',
    locator TEXT NOT NULL DEFAULT '', kind TEXT NOT NULL, basis TEXT NOT NULL DEFAULT '',
    kill_test TEXT NOT NULL DEFAULT '', status TEXT NOT NULL, confidence REAL NOT NULL,
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL, revision_of TEXT REFERENCES claim(id),
    superseded_by TEXT, revision_reason TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS edge (
    id TEXT PRIMARY KEY, src_kind TEXT NOT NULL, src_id TEXT NOT NULL,
    dst_kind TEXT NOT NULL, dst_id TEXT NOT NULL, rel TEXT NOT NULL, created_at TEXT NOT NULL,
    UNIQUE(src_kind, src_id, dst_kind, dst_id, rel));
CREATE TABLE IF NOT EXISTS hypothesis (
    id TEXT PRIMARY KEY, research_id TEXT NOT NULL REFERENCES research(id),
    question_id TEXT REFERENCES question(id), statement TEXT NOT NULL, criterion TEXT NOT NULL,
    confidence REAL NOT NULL, registered_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PREREGISTERED', outcome_note TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS killtest (
    id TEXT PRIMARY KEY, research_id TEXT NOT NULL REFERENCES research(id),
    claim_id TEXT REFERENCES claim(id), hypothesis_id TEXT REFERENCES hypothesis(id),
    name TEXT NOT NULL, command TEXT NOT NULL, expect_exit INTEGER NOT NULL DEFAULT 0,
    timeout_seconds INTEGER NOT NULL DEFAULT 120, created_at TEXT NOT NULL,
    inputs_json TEXT NOT NULL DEFAULT '[]', control_command TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS test_run (
    id TEXT PRIMARY KEY, test_id TEXT NOT NULL REFERENCES killtest(id), run_group TEXT NOT NULL,
    run_tag TEXT NOT NULL, started_at TEXT NOT NULL, duration_ms INTEGER NOT NULL,
    exit_code INTEGER NOT NULL, passed INTEGER NOT NULL, stdout_sha256 TEXT NOT NULL,
    stderr_sha256 TEXT NOT NULL, output_tail TEXT NOT NULL DEFAULT '',
    command_sha256 TEXT NOT NULL DEFAULT '', code_sha256 TEXT NOT NULL DEFAULT '',
    inputs_sha256 TEXT NOT NULL DEFAULT '', git_commit TEXT NOT NULL DEFAULT '',
    git_dirty INTEGER NOT NULL DEFAULT 0, python_version TEXT NOT NULL DEFAULT '',
    platform TEXT NOT NULL DEFAULT '', role TEXT NOT NULL DEFAULT 'main');
CREATE TABLE IF NOT EXISTS test_attempt (
    id TEXT PRIMARY KEY, test_id TEXT NOT NULL REFERENCES killtest(id),
    attempt_no INTEGER NOT NULL, run_group TEXT NOT NULL, outcome TEXT NOT NULL,
    reason TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL,
    UNIQUE(test_id, attempt_no), UNIQUE(test_id, run_group));
CREATE TABLE IF NOT EXISTS verdict (
    id TEXT PRIMARY KEY, subject_kind TEXT NOT NULL, subject_id TEXT NOT NULL,
    status TEXT NOT NULL, previous_status TEXT NOT NULL, evidence TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '', actor TEXT NOT NULL, at TEXT NOT NULL,
    evidence_group TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS observation (
    id TEXT PRIMARY KEY, research_id TEXT NOT NULL REFERENCES research(id),
    claim_id TEXT NOT NULL REFERENCES claim(id), group_label TEXT NOT NULL,
    value REAL NOT NULL, note TEXT NOT NULL DEFAULT '', at TEXT NOT NULL,
    voided INTEGER NOT NULL DEFAULT 0, void_reason TEXT NOT NULL DEFAULT '',
    instrument_kind TEXT NOT NULL DEFAULT '', instrument_id TEXT NOT NULL DEFAULT '',
    instrument_digest TEXT NOT NULL DEFAULT '', rater_kind TEXT NOT NULL DEFAULT '',
    rater_id TEXT NOT NULL DEFAULT '', rater_version TEXT NOT NULL DEFAULT '',
    protocol_id TEXT NOT NULL DEFAULT '', sample_size INTEGER NOT NULL DEFAULT 1,
    aggregation TEXT NOT NULL DEFAULT 'raw', unit TEXT NOT NULL DEFAULT '',
    provenance_class TEXT NOT NULL DEFAULT 'unclassified', producer_path TEXT NOT NULL DEFAULT '',
    producer_digest TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS protocol (
    id TEXT PRIMARY KEY, measures TEXT NOT NULL, includes_generation INTEGER NOT NULL DEFAULT 0,
    includes_judge INTEGER NOT NULL DEFAULT 0, doc_digest TEXT NOT NULL DEFAULT '',
    registered_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS event (
    id TEXT PRIMARY KEY, at TEXT NOT NULL, research_id TEXT NOT NULL DEFAULT '',
    kind TEXT NOT NULL, subject TEXT NOT NULL, detail TEXT NOT NULL DEFAULT '',
    actor TEXT NOT NULL DEFAULT 'agent', seq INTEGER NOT NULL DEFAULT 0,
    root_id TEXT NOT NULL DEFAULT '', parent_id TEXT NOT NULL DEFAULT '',
    prev_hash TEXT NOT NULL DEFAULT '', event_hash TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS invalidation (
    id TEXT PRIMARY KEY, root_kind TEXT NOT NULL, root_id TEXT NOT NULL,
    reason TEXT NOT NULL, actor TEXT NOT NULL, at TEXT NOT NULL, affected_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS ai_artifact (
    id TEXT PRIMARY KEY, research_id TEXT NOT NULL REFERENCES research(id),
    kind TEXT NOT NULL, model_id TEXT NOT NULL, prompt_sha256 TEXT NOT NULL,
    output_sha256 TEXT NOT NULL, cited_json TEXT NOT NULL DEFAULT '[]',
    claim_id TEXT REFERENCES claim(id), hypothesis_id TEXT REFERENCES hypothesis(id),
    test_id TEXT REFERENCES killtest(id), actor TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS analysis_plan (
    id TEXT PRIMARY KEY, research_id TEXT NOT NULL REFERENCES research(id),
    claim_id TEXT NOT NULL REFERENCES claim(id), baseline TEXT NOT NULL, treatment TEXT NOT NULL,
    prediction TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'PREREGISTERED', registered_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS amendment (
    id TEXT PRIMARY KEY, subject_kind TEXT NOT NULL, subject_id TEXT NOT NULL,
    field TEXT NOT NULL, before_value TEXT NOT NULL DEFAULT '', after_value TEXT NOT NULL DEFAULT '',
    reason TEXT NOT NULL, actor TEXT NOT NULL, at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS experiment_intervention (
    id TEXT PRIMARY KEY, research_id TEXT NOT NULL REFERENCES research(id), name TEXT NOT NULL,
    start_date TEXT NOT NULL, projected_end_date TEXT, end_date TEXT,
    dosage TEXT NOT NULL DEFAULT '', notes TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS experiment_metric_definition (
    id TEXT PRIMARY KEY, research_id TEXT NOT NULL REFERENCES research(id), name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '', unit TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL,
    UNIQUE(research_id, name));
CREATE TABLE IF NOT EXISTS experiment_metric (
    id TEXT PRIMARY KEY, research_id TEXT NOT NULL REFERENCES research(id),
    intervention_id TEXT REFERENCES experiment_intervention(id), metric_name TEXT NOT NULL,
    date TEXT NOT NULL, value REAL NOT NULL, note TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS experiment_event (
    id TEXT PRIMARY KEY, research_id TEXT NOT NULL REFERENCES research(id),
    intervention_id TEXT REFERENCES experiment_intervention(id), timestamp TEXT NOT NULL,
    event_name TEXT NOT NULL, severity INTEGER, notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    CHECK (severity IS NULL OR (severity >= 1 AND severity <= 5)));
CREATE TABLE IF NOT EXISTS domain_pack (
    name TEXT PRIMARY KEY, version TEXT NOT NULL, api_version TEXT NOT NULL,
    data_root TEXT NOT NULL DEFAULT '', manifest_sha256 TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'registered', registered_at TEXT NOT NULL,
    CHECK (status IN ('registered', 'disabled')));
CREATE TABLE IF NOT EXISTS migration_run (
    id TEXT PRIMARY KEY, source TEXT NOT NULL, source_digest TEXT NOT NULL,
    target_research TEXT NOT NULL REFERENCES research(id), applied_at TEXT NOT NULL,
    report_json TEXT NOT NULL, UNIQUE(source, source_digest));
CREATE INDEX IF NOT EXISTS idx_claim_research ON claim(research_id);
CREATE INDEX IF NOT EXISTS idx_claim_status ON claim(status);
CREATE INDEX IF NOT EXISTS idx_edge_dst ON edge(dst_kind, dst_id);
CREATE INDEX IF NOT EXISTS idx_edge_src ON edge(src_kind, src_id);
CREATE INDEX IF NOT EXISTS idx_run_test ON test_run(test_id);
CREATE INDEX IF NOT EXISTS idx_attempt_test ON test_attempt(test_id, attempt_no);
CREATE INDEX IF NOT EXISTS idx_verdict_subject ON verdict(subject_kind, subject_id);
CREATE INDEX IF NOT EXISTS idx_event_research ON event(research_id, id);
CREATE INDEX IF NOT EXISTS idx_observation_claim ON observation(claim_id, group_label);
CREATE INDEX IF NOT EXISTS idx_observation_research ON observation(research_id);
"#;

const EXTRA_INDEXES: &str = r#"
CREATE INDEX IF NOT EXISTS idx_source_screening ON source(screening);
CREATE INDEX IF NOT EXISTS idx_claim_head ON claim(research_id, superseded_by);
CREATE INDEX IF NOT EXISTS idx_observation_protocol ON observation(protocol_id);
CREATE INDEX IF NOT EXISTS idx_event_root ON event(root_id, seq);
CREATE INDEX IF NOT EXISTS idx_ai_research ON ai_artifact(research_id);
CREATE INDEX IF NOT EXISTS idx_experiment_intervention_research ON experiment_intervention(research_id);
CREATE INDEX IF NOT EXISTS idx_experiment_metric_research ON experiment_metric(research_id, metric_name, date);
CREATE INDEX IF NOT EXISTS idx_experiment_event_research ON experiment_event(research_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_migration_source ON migration_run(source);
"#;

/// Additive column migrations keyed by the schema version being left.
const MIGRATIONS: &[(i64, &[(&str, &str, &str)])] = &[
    (1, &[
        ("source", "status", "TEXT NOT NULL DEFAULT 'active'"),
        ("source", "status_note", "TEXT NOT NULL DEFAULT ''"),
        ("source", "status_at", "TEXT NOT NULL DEFAULT ''"),
        ("killtest", "inputs_json", "TEXT NOT NULL DEFAULT '[]'"),
        ("test_run", "command_sha256", "TEXT NOT NULL DEFAULT ''"),
        ("test_run", "code_sha256", "TEXT NOT NULL DEFAULT ''"),
        ("test_run", "inputs_sha256", "TEXT NOT NULL DEFAULT ''"),
        ("test_run", "git_commit", "TEXT NOT NULL DEFAULT ''"),
        ("test_run", "git_dirty", "INTEGER NOT NULL DEFAULT 0"),
        ("test_run", "python_version", "TEXT NOT NULL DEFAULT ''"),
        ("test_run", "platform", "TEXT NOT NULL DEFAULT ''"),
    ]),
    (2, &[("verdict", "evidence_group", "TEXT NOT NULL DEFAULT ''")]),
    (3, &[
        ("source", "screening", "TEXT NOT NULL DEFAULT 'identified'"),
        ("source", "screening_reason", "TEXT NOT NULL DEFAULT ''"),
        ("source", "screening_at", "TEXT NOT NULL DEFAULT ''"),
        ("killtest", "control_command", "TEXT NOT NULL DEFAULT ''"),
        ("test_run", "role", "TEXT NOT NULL DEFAULT 'main'"),
    ]),
    (6, &[
        ("claim", "revision_of", "TEXT REFERENCES claim(id)"),
        ("claim", "superseded_by", "TEXT"),
        ("claim", "revision_reason", "TEXT NOT NULL DEFAULT ''"),
    ]),
    (7, &[
        ("observation", "instrument_kind", "TEXT NOT NULL DEFAULT ''"),
        ("observation", "instrument_id", "TEXT NOT NULL DEFAULT ''"),
        ("observation", "instrument_digest", "TEXT NOT NULL DEFAULT ''"),
        ("observation", "rater_kind", "TEXT NOT NULL DEFAULT ''"),
        ("observation", "rater_id", "TEXT NOT NULL DEFAULT ''"),
        ("observation", "rater_version", "TEXT NOT NULL DEFAULT ''"),
        ("observation", "protocol_id", "TEXT NOT NULL DEFAULT ''"),
        ("observation", "sample_size", "INTEGER NOT NULL DEFAULT 1"),
        ("observation", "aggregation", "TEXT NOT NULL DEFAULT 'raw'"),
        ("observation", "unit", "TEXT NOT NULL DEFAULT ''"),
    ]),
    (8, &[
        ("event", "seq", "INTEGER NOT NULL DEFAULT 0"),
        ("event", "root_id", "TEXT NOT NULL DEFAULT ''"),
        ("event", "parent_id", "TEXT NOT NULL DEFAULT ''"),
    ]),
    (9, &[
        ("observation", "provenance_class", "TEXT NOT NULL DEFAULT 'unclassified'"),
        ("observation", "producer_path", "TEXT NOT NULL DEFAULT ''"),
        ("observation", "producer_digest", "TEXT NOT NULL DEFAULT ''"),
    ]),
    (10, &[]),
    (11, &[
        ("event", "prev_hash", "TEXT NOT NULL DEFAULT ''"),
        ("event", "event_hash", "TEXT NOT NULL DEFAULT ''"),
    ]),
    (12, &[]),
    (13, &[
        ("source", "arxiv", "TEXT NOT NULL DEFAULT ''"),
        ("source", "venue", "TEXT NOT NULL DEFAULT ''"),
        ("source", "abstract", "TEXT NOT NULL DEFAULT ''"),
        ("source", "tags", "TEXT NOT NULL DEFAULT ''"),
        ("source", "study_type", "TEXT NOT NULL DEFAULT ''"),
    ]),
];

pub fn utc_now() -> String {
    Utc::now().format("%Y-%m-%dT%H:%M:%S+00:00").to_string()
}

pub fn open(path: &str) -> Result<Connection> {
    if path != ":memory:" {
        if let Some(parent) = Path::new(path).parent() {
            if !parent.as_os_str().is_empty() {
                std::fs::create_dir_all(parent)?;
            }
        }
    }
    let conn = Connection::open(path)?;
    conn.execute_batch(
        "PRAGMA foreign_keys = ON; PRAGMA synchronous = FULL; PRAGMA busy_timeout = 3000;",
    )?;
    if path != ":memory:" {
        // WAL is best-effort: read-only filesystems still allow a rollback-journal DB.
        let _ = conn.execute_batch("PRAGMA journal_mode = WAL;");
    }
    Ok(conn)
}

/// Create the schema, migrate an older one and refuse a future version.
pub fn initialize(conn: &Connection) -> Result<Option<String>> {
    let has_meta: bool = conn.query_row(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_meta'",
        [],
        |_| Ok(true),
    ).unwrap_or(false);
    if has_meta {
        let version: i64 = conn.query_row("SELECT version FROM schema_meta", [], |r| r.get(0))?;
        if version > SCHEMA_VERSION {
            return Err(EngineError::new(
                format!("database schema version {version} is newer than this build"),
                format!("this build reads schema version {SCHEMA_VERSION} only."),
                "use the engine version that wrote this database, or start a new database file.",
            ));
        }
    }
    conn.execute_batch(SCHEMA)?;
    let tx = conn.unchecked_transaction()?;
    let version: Option<i64> = tx.query_row("SELECT version FROM schema_meta", [], |r| r.get(0)).optional()?;
    match version {
        None => {
            tx.execute_batch(EXTRA_INDEXES)?;
            tx.execute("INSERT INTO schema_meta(version) VALUES (?1)", params![SCHEMA_VERSION])?;
            tx.commit()?;
            return Ok(None);
        }
        Some(v) if v == SCHEMA_VERSION => {
            tx.commit()?;
            return Ok(None);
        }
        Some(started) => {
            let mut version = started;
            while version < SCHEMA_VERSION {
                for (table, column, declaration) in
                    MIGRATIONS.iter().find(|(v, _)| *v == version).map(|(_, cols)| *cols).unwrap_or(&[])
                {
                    let exists: bool = {
                        let mut stmt = tx.prepare(&format!("PRAGMA table_info({table})"))?;
                        let rows = stmt.query_map([], |r| r.get::<_, String>(1))?;
                        let mut found = false;
                        for name in rows {
                            if name? == *column { found = true; }
                        }
                        found
                    };
                    if !exists {
                        tx.execute(&format!("ALTER TABLE {table} ADD COLUMN {column} {declaration}"), [])?;
                    }
                }
                version += 1;
            }
            tx.execute_batch(EXTRA_INDEXES)?;
            tx.execute("UPDATE schema_meta SET version = ?1", params![SCHEMA_VERSION])?;
            let ev = next_id(&tx, "ev")?;
            tx.execute(
                "INSERT INTO event(id, at, research_id, kind, subject, detail, actor) VALUES (?1,?2,'','db.migrate','schema_meta',?3,'engine')",
                params![ev, utc_now(), format!("schema {started} -> {SCHEMA_VERSION}")],
            )?;
            tx.commit()?;
            return Ok(Some(format!("schema {started} -> {SCHEMA_VERSION}")));
        }
    }
}

/// Allocate a readable, gap-free identifier inside the current transaction.
pub fn next_id(conn: &Connection, prefix: &str) -> Result<String> {
    let updated = conn.execute("UPDATE counters SET value = value + 1 WHERE prefix = ?1", params![prefix])?;
    if updated == 0 {
        conn.execute("INSERT INTO counters(prefix, value) VALUES (?1, 1)", params![prefix])?;
    }
    let value: i64 = conn.query_row("SELECT value FROM counters WHERE prefix = ?1", params![prefix], |r| r.get(0))?;
    Ok(format!("{prefix}_{value:06}"))
}

/// Convenience extension trait mirroring sqlite3.Row lookups by column name for JSON output.
pub trait RowExt {
    fn get_str(&self, column: &str) -> Result<String>;
}

impl RowExt for rusqlite::Row<'_> {
    fn get_str(&self, column: &str) -> Result<String> {
        let name = column.to_string();
        let value: Option<String> = self.get(name.as_str())?;
        Ok(value.unwrap_or_default())
    }
}

use rusqlite::OptionalExtension;
