"""SQLite connection, schema versioning and atomic transactions."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from engine.artifacts import utc_now
from engine.errors import EngineError

SCHEMA_VERSION = 8

_SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_meta (
    version INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS counters (
    prefix TEXT PRIMARY KEY,
    value INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS research (
    id TEXT PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    scope TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS source (
    id TEXT PRIMARY KEY,
    research_id TEXT NOT NULL REFERENCES research(id),
    kind TEXT NOT NULL,
    title TEXT NOT NULL,
    authors TEXT NOT NULL DEFAULT '',
    year INTEGER,
    doi TEXT NOT NULL DEFAULT '',
    url TEXT NOT NULL DEFAULT '',
    retrieved_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    status_note TEXT NOT NULL DEFAULT '',
    status_at TEXT NOT NULL DEFAULT '',
    screening TEXT NOT NULL DEFAULT 'identified',
    screening_reason TEXT NOT NULL DEFAULT '',
    screening_at TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS question (
    id TEXT PRIMARY KEY,
    research_id TEXT NOT NULL REFERENCES research(id),
    text TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS claim (
    id TEXT PRIMARY KEY,
    research_id TEXT NOT NULL REFERENCES research(id),
    source_id TEXT REFERENCES source(id),
    text TEXT NOT NULL,
    quote TEXT NOT NULL DEFAULT '',
    locator TEXT NOT NULL DEFAULT '',
    kind TEXT NOT NULL,
    basis TEXT NOT NULL DEFAULT '',
    kill_test TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL,
    confidence REAL NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    revision_of TEXT REFERENCES claim(id),
    superseded_by TEXT,
    revision_reason TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS edge (
    id TEXT PRIMARY KEY,
    src_kind TEXT NOT NULL,
    src_id TEXT NOT NULL,
    dst_kind TEXT NOT NULL,
    dst_id TEXT NOT NULL,
    rel TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(src_kind, src_id, dst_kind, dst_id, rel)
);
CREATE TABLE IF NOT EXISTS hypothesis (
    id TEXT PRIMARY KEY,
    research_id TEXT NOT NULL REFERENCES research(id),
    question_id TEXT REFERENCES question(id),
    statement TEXT NOT NULL,
    criterion TEXT NOT NULL,
    confidence REAL NOT NULL,
    registered_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PREREGISTERED',
    outcome_note TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS killtest (
    id TEXT PRIMARY KEY,
    research_id TEXT NOT NULL REFERENCES research(id),
    claim_id TEXT REFERENCES claim(id),
    hypothesis_id TEXT REFERENCES hypothesis(id),
    name TEXT NOT NULL,
    command TEXT NOT NULL,
    expect_exit INTEGER NOT NULL DEFAULT 0,
    timeout_seconds INTEGER NOT NULL DEFAULT 120,
    created_at TEXT NOT NULL,
    inputs_json TEXT NOT NULL DEFAULT '[]',
    control_command TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS test_run (
    id TEXT PRIMARY KEY,
    test_id TEXT NOT NULL REFERENCES killtest(id),
    run_group TEXT NOT NULL,
    run_tag TEXT NOT NULL,
    started_at TEXT NOT NULL,
    duration_ms INTEGER NOT NULL,
    exit_code INTEGER NOT NULL,
    passed INTEGER NOT NULL,
    stdout_sha256 TEXT NOT NULL,
    stderr_sha256 TEXT NOT NULL,
    output_tail TEXT NOT NULL DEFAULT '',
    command_sha256 TEXT NOT NULL DEFAULT '',
    code_sha256 TEXT NOT NULL DEFAULT '',
    inputs_sha256 TEXT NOT NULL DEFAULT '',
    git_commit TEXT NOT NULL DEFAULT '',
    git_dirty INTEGER NOT NULL DEFAULT 0,
    python_version TEXT NOT NULL DEFAULT '',
    platform TEXT NOT NULL DEFAULT '',
    role TEXT NOT NULL DEFAULT 'main'
);
CREATE TABLE IF NOT EXISTS test_attempt (
    id TEXT PRIMARY KEY,
    test_id TEXT NOT NULL REFERENCES killtest(id),
    attempt_no INTEGER NOT NULL,
    run_group TEXT NOT NULL,
    outcome TEXT NOT NULL,
    reason TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    UNIQUE(test_id, attempt_no),
    UNIQUE(test_id, run_group)
);
CREATE TABLE IF NOT EXISTS verdict (
    id TEXT PRIMARY KEY,
    subject_kind TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    status TEXT NOT NULL,
    previous_status TEXT NOT NULL,
    evidence TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    actor TEXT NOT NULL,
    at TEXT NOT NULL,
    evidence_group TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS observation (
    id TEXT PRIMARY KEY,
    research_id TEXT NOT NULL REFERENCES research(id),
    claim_id TEXT NOT NULL REFERENCES claim(id),
    group_label TEXT NOT NULL,
    value REAL NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    at TEXT NOT NULL,
    voided INTEGER NOT NULL DEFAULT 0,
    void_reason TEXT NOT NULL DEFAULT '',
    instrument_kind TEXT NOT NULL DEFAULT '',
    instrument_id TEXT NOT NULL DEFAULT '',
    instrument_digest TEXT NOT NULL DEFAULT '',
    rater_kind TEXT NOT NULL DEFAULT '',
    rater_id TEXT NOT NULL DEFAULT '',
    rater_version TEXT NOT NULL DEFAULT '',
    protocol_id TEXT NOT NULL DEFAULT '',
    sample_size INTEGER NOT NULL DEFAULT 1,
    aggregation TEXT NOT NULL DEFAULT 'raw',
    unit TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS protocol (
    id TEXT PRIMARY KEY,
    measures TEXT NOT NULL,
    includes_generation INTEGER NOT NULL DEFAULT 0,
    includes_judge INTEGER NOT NULL DEFAULT 0,
    doc_digest TEXT NOT NULL DEFAULT '',
    registered_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS event (
    id TEXT PRIMARY KEY,
    at TEXT NOT NULL,
    research_id TEXT NOT NULL DEFAULT '',
    kind TEXT NOT NULL,
    subject TEXT NOT NULL,
    detail TEXT NOT NULL DEFAULT '',
    actor TEXT NOT NULL DEFAULT 'agent'
);
CREATE TABLE IF NOT EXISTS invalidation (
    id TEXT PRIMARY KEY,
    root_kind TEXT NOT NULL,
    root_id TEXT NOT NULL,
    reason TEXT NOT NULL,
    actor TEXT NOT NULL,
    at TEXT NOT NULL,
    affected_json TEXT NOT NULL
);
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
"""


def connect(path: Path | str) -> sqlite3.Connection:
    """Open a database with durability pragmas suitable for a state file."""
    if str(path) != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA synchronous = FULL")
    if str(path) != ":memory:":
        conn.execute("PRAGMA journal_mode = WAL")
    return conn


# Additive migrations from one schema version to the next. `CREATE TABLE IF NOT EXISTS` never
# adds a column to an existing table, so an older database is repaired here instead.
_MIGRATIONS = {
    1: (
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
    ),
    2: (
        ("verdict", "evidence_group", "TEXT NOT NULL DEFAULT ''"),
    ),
    3: (
        ("source", "screening", "TEXT NOT NULL DEFAULT 'identified'"),
        ("source", "screening_reason", "TEXT NOT NULL DEFAULT ''"),
        ("source", "screening_at", "TEXT NOT NULL DEFAULT ''"),
        ("killtest", "control_command", "TEXT NOT NULL DEFAULT ''"),
        ("test_run", "role", "TEXT NOT NULL DEFAULT 'main'"),
    ),
    6: (
        ("claim", "revision_of", "TEXT REFERENCES claim(id)"),
        ("claim", "superseded_by", "TEXT"),
        ("claim", "revision_reason", "TEXT NOT NULL DEFAULT ''"),
    ),
    7: (
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
    ),
}


def _ensure_indexes(conn: sqlite3.Connection) -> None:
    """Create indexes that depend on migrated columns; safe to run after every migration."""
    conn.execute("CREATE INDEX IF NOT EXISTS idx_source_screening ON source(screening)")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_claim_head ON claim(research_id, superseded_by)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_observation_protocol ON observation(protocol_id)"
    )


def _add_missing_columns(conn: sqlite3.Connection, version: int) -> None:
    """Apply the additive column migrations for one older schema version."""
    for table, column, declaration in _MIGRATIONS.get(version, ()):
        existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
        if column not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {declaration}")


def initialize(conn: sqlite3.Connection) -> dict | None:
    """Create the schema, migrate an older one, and refuse a future version.

    Returns a migration report when an older database was upgraded, otherwise None, so a caller
    can tell the operator that upgrading changed what the gate will accept.
    """
    existing = None
    if conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'schema_meta'"
    ).fetchone() is not None:
        existing = conn.execute("SELECT version FROM schema_meta").fetchone()
    if existing is not None and int(existing["version"]) > SCHEMA_VERSION:
        raise EngineError(
            f"database schema version {int(existing['version'])} is newer than this build",
            f"this build reads schema version {SCHEMA_VERSION} only.",
            "use the engine version that wrote this database, or start a new database file.",
        )
    conn.executescript(_SCHEMA)
    with transaction(conn):
        row = conn.execute("SELECT version FROM schema_meta").fetchone()
        if row is None:
            _ensure_indexes(conn)
            conn.execute("INSERT INTO schema_meta(version) VALUES (?)", (SCHEMA_VERSION,))
            return None
        version = int(row["version"])
        if version > SCHEMA_VERSION:
            raise EngineError(
                f"database schema version {version} is newer than this build",
                f"this build reads schema version {SCHEMA_VERSION} only.",
                "use the engine version that wrote this database, or start a new database file.",
            )
        if version == SCHEMA_VERSION:
            return None
        started_from = version
        while version < SCHEMA_VERSION:
            _add_missing_columns(conn, version)
            version += 1
        _ensure_indexes(conn)
        conn.execute("UPDATE schema_meta SET version = ?", (SCHEMA_VERSION,))
        # Inline event insert: importing engine.events here would close an import cycle.
        counter = conn.execute(
            "UPDATE counters SET value = value + 1 WHERE prefix = 'ev'"
        )
        if counter.rowcount == 0:
            conn.execute("INSERT INTO counters(prefix, value) VALUES ('ev', 1)")
        event_id = "ev_%06d" % conn.execute(
            "SELECT value FROM counters WHERE prefix = 'ev'"
        ).fetchone()["value"]
        conn.execute(
            "INSERT INTO event(id, at, research_id, kind, subject, detail, actor)"
            " VALUES (?, ?, '', 'db.migrate', 'schema_meta', ?, 'engine')",
            (
                event_id,
                utc_now(),
                f"schema {started_from} -> {SCHEMA_VERSION}",
            ),
        )
        report = {
            "migrated_from": started_from,
            "migrated_to": SCHEMA_VERSION,
            "unbound_numeric_claims": _count_unbound_numeric(conn),
        }
    return report


def _count_unbound_numeric(conn: sqlite3.Connection) -> int:
    """Numeric claims whose promotion verdict predates evidence binding."""
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM claim c WHERE c.status = 'NUMERIC' AND NOT EXISTS ("
        " SELECT 1 FROM verdict v WHERE v.subject_kind = 'claim' AND v.subject_id = c.id"
        " AND v.status = 'NUMERIC' AND v.evidence_group <> '')"
    ).fetchone()
    return int(row["n"])


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Run a write atomically; nested calls join the outer transaction."""
    owns = not conn.in_transaction
    if owns:
        conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        if owns and conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
    else:
        if owns and conn.in_transaction:
            conn.execute("COMMIT")


def next_id(conn: sqlite3.Connection, prefix: str) -> str:
    """Allocate a readable, gap-free identifier inside the current transaction."""
    updated = conn.execute(
        "UPDATE counters SET value = value + 1 WHERE prefix = ?", (prefix,)
    )
    if updated.rowcount == 0:
        conn.execute("INSERT INTO counters(prefix, value) VALUES (?, 1)", (prefix,))
    row = conn.execute("SELECT value FROM counters WHERE prefix = ?", (prefix,)).fetchone()
    return f"{prefix}_{int(row['value']):06d}"
