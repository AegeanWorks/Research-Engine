"""Schema migration: an older database is repaired, not rejected or wiped."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from engine.database import SCHEMA_VERSION, connect, initialize
from engine.errors import EngineError

# The version-1 shape of the two tables that changed, without the v2 columns.
_V1 = """
CREATE TABLE schema_meta (version INTEGER NOT NULL);
CREATE TABLE source (
    id TEXT PRIMARY KEY, research_id TEXT NOT NULL, kind TEXT NOT NULL, title TEXT NOT NULL,
    authors TEXT NOT NULL DEFAULT '', year INTEGER, doi TEXT NOT NULL DEFAULT '',
    url TEXT NOT NULL DEFAULT '', retrieved_at TEXT NOT NULL
);
CREATE TABLE killtest (
    id TEXT PRIMARY KEY, research_id TEXT NOT NULL, claim_id TEXT, hypothesis_id TEXT,
    name TEXT NOT NULL, command TEXT NOT NULL, expect_exit INTEGER NOT NULL DEFAULT 0,
    timeout_seconds INTEGER NOT NULL DEFAULT 120, created_at TEXT NOT NULL
);
CREATE TABLE test_run (
    id TEXT PRIMARY KEY, test_id TEXT NOT NULL, run_group TEXT NOT NULL, run_tag TEXT NOT NULL,
    started_at TEXT NOT NULL, duration_ms INTEGER NOT NULL, exit_code INTEGER NOT NULL,
    passed INTEGER NOT NULL, stdout_sha256 TEXT NOT NULL, stderr_sha256 TEXT NOT NULL,
    output_text TEXT NOT NULL DEFAULT ''
);
CREATE TABLE claim (
    id TEXT PRIMARY KEY, research_id TEXT NOT NULL, source_id TEXT, text TEXT NOT NULL,
    quote TEXT NOT NULL DEFAULT '', locator TEXT NOT NULL DEFAULT '', kind TEXT NOT NULL,
    basis TEXT NOT NULL DEFAULT '', kill_test TEXT NOT NULL DEFAULT '', status TEXT NOT NULL,
    confidence REAL NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE verdict (
    id TEXT PRIMARY KEY, subject_kind TEXT NOT NULL, subject_id TEXT NOT NULL,
    status TEXT NOT NULL, previous_status TEXT NOT NULL, evidence TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '', actor TEXT NOT NULL, at TEXT NOT NULL
);
INSERT INTO schema_meta(version) VALUES (1);
INSERT INTO source(id, research_id, kind, title, retrieved_at)
    VALUES ('s_old', 'r_old', 'paper', 'Old source', 'then');
INSERT INTO killtest(id, research_id, name, command, created_at)
    VALUES ('t_old', 'r_old', 'Old test', 'true', 'then');
INSERT INTO test_run(id, test_id, run_group, run_tag, started_at, duration_ms, exit_code,
    passed, stdout_sha256, stderr_sha256, output_text)
    VALUES ('u_old', 't_old', 'g_old', 'run1', 'then', 1, 0, 1, 'a', 'b', '');
INSERT INTO claim(id, research_id, source_id, text, quote, locator, kind, kill_test, status,
    confidence, created_at, updated_at)
    VALUES ('c_old', 'r_old', 's_old', 'Old numeric claim', 'q', 'p.1', 'empirical',
            'A replicate.', 'NUMERIC', 0.8, 'then', 'then');
INSERT INTO verdict(id, subject_kind, subject_id, status, previous_status, evidence, actor, at)
    VALUES ('v_old', 'claim', 'c_old', 'NUMERIC', 'UNVERIFIED', 'old evidence', 'agent', 'then');
"""


class MigrationTests(unittest.TestCase):
    def _old_database(self) -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "old.db"
        raw = sqlite3.connect(str(path))
        raw.executescript(_V1)
        raw.commit()
        raw.close()
        return path

    def test_version_one_database_is_migrated_in_place(self) -> None:
        path = self._old_database()
        conn = connect(path)
        self.addCleanup(conn.close)
        initialize(conn)
        version = conn.execute("SELECT version FROM schema_meta").fetchone()["version"]
        self.assertEqual(version, SCHEMA_VERSION)
        source_columns = {row["name"] for row in conn.execute("PRAGMA table_info(source)")}
        self.assertTrue({"status", "status_note", "status_at"} <= source_columns)
        run_columns = {row["name"] for row in conn.execute("PRAGMA table_info(test_run)")}
        self.assertTrue(
            {"command_sha256", "code_sha256", "inputs_sha256", "git_commit", "git_dirty",
             "python_version", "platform"} <= run_columns
        )
        test_columns = {row["name"] for row in conn.execute("PRAGMA table_info(killtest)")}
        self.assertIn("inputs_json", test_columns)

    def test_existing_rows_are_preserved(self) -> None:
        path = self._old_database()
        conn = connect(path)
        self.addCleanup(conn.close)
        initialize(conn)
        source = conn.execute("SELECT * FROM source WHERE id = 's_old'").fetchone()
        self.assertEqual(source["title"], "Old source")
        self.assertEqual(source["status"], "active")
        run = conn.execute("SELECT * FROM test_run WHERE id = 'u_old'").fetchone()
        self.assertEqual(run["run_group"], "g_old")
        self.assertEqual(run["code_sha256"], "")
        self.assertEqual(
            conn.execute("SELECT COUNT(*) AS n FROM test_attempt").fetchone()["n"], 0
        )

    def test_migration_creates_the_attempt_table(self) -> None:
        path = self._old_database()
        conn = connect(path)
        self.addCleanup(conn.close)
        initialize(conn)
        tables = {
            row["name"]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        self.assertIn("test_attempt", tables)

    def test_migration_adds_the_claim_revision_columns(self) -> None:
        path = self._old_database()
        conn = connect(path)
        self.addCleanup(conn.close)
        initialize(conn)
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(claim)")}
        self.assertTrue({"revision_of", "superseded_by", "revision_reason"} <= columns)

    def test_migration_is_idempotent(self) -> None:
        path = self._old_database()
        conn = connect(path)
        self.addCleanup(conn.close)
        initialize(conn)
        initialize(conn)
        self.assertEqual(
            conn.execute("SELECT version FROM schema_meta").fetchone()["version"], SCHEMA_VERSION
        )

    def test_future_version_is_refused_without_changes(self) -> None:
        path = self._old_database()
        conn = connect(path)
        self.addCleanup(conn.close)
        initialize(conn)
        conn.execute("UPDATE schema_meta SET version = ?", (SCHEMA_VERSION + 1,))
        with self.assertRaises(EngineError):
            initialize(conn)
        self.assertEqual(
            conn.execute("SELECT version FROM schema_meta").fetchone()["version"],
            SCHEMA_VERSION + 1,
        )

    def test_future_version_is_refused_before_creating_tables(self) -> None:
        conn = connect(":memory:")
        self.addCleanup(conn.close)
        conn.execute("CREATE TABLE schema_meta(version INTEGER NOT NULL)")
        conn.execute("INSERT INTO schema_meta VALUES (?)", (SCHEMA_VERSION + 1,))
        with self.assertRaises(EngineError):
            initialize(conn)
        tables = {
            row["name"]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        self.assertEqual(tables, {"schema_meta"})

    def test_fresh_database_declares_the_current_version(self) -> None:
        conn = connect(":memory:")
        self.addCleanup(conn.close)
        initialize(conn)
        self.assertEqual(
            conn.execute("SELECT version FROM schema_meta").fetchone()["version"], SCHEMA_VERSION
        )




    def test_verdict_gains_the_evidence_group_column(self) -> None:
        path = self._old_database()
        conn = connect(path)
        self.addCleanup(conn.close)
        initialize(conn)
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(verdict)")}
        self.assertIn("evidence_group", columns)

    def test_migration_reports_the_unbound_numeric_claims(self) -> None:
        path = self._old_database()
        conn = connect(path)
        self.addCleanup(conn.close)
        report = initialize(conn)
        self.assertIsNotNone(report)
        self.assertEqual(report["migrated_from"], 1)
        self.assertEqual(report["migrated_to"], SCHEMA_VERSION)
        self.assertEqual(report["unbound_numeric_claims"], 1)

    def test_version_two_database_gains_only_the_verdict_column(self) -> None:
        path = self._old_database()
        conn = connect(path)
        self.addCleanup(conn.close)
        initialize(conn)
        conn.execute("ALTER TABLE verdict DROP COLUMN evidence_group")
        conn.execute("UPDATE schema_meta SET version = 2")
        report = initialize(conn)
        self.assertEqual(report["migrated_from"], 2)
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(verdict)")}
        self.assertIn("evidence_group", columns)
        self.assertEqual(
            conn.execute("SELECT COUNT(*) AS n FROM source").fetchone()["n"], 1
        )


    def test_observation_table_exists_after_migration(self) -> None:
        path = self._old_database()
        conn = connect(path)
        self.addCleanup(conn.close)
        initialize(conn)
        tables = {
            row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        self.assertIn("observation", tables)
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(observation)")}
        self.assertTrue({"claim_id", "group_label", "value", "voided"} <= columns)

    def test_version_four_database_gains_the_observation_table(self) -> None:
        path = self._old_database()
        conn = connect(path)
        self.addCleanup(conn.close)
        initialize(conn)
        conn.execute("DROP TABLE observation")
        conn.execute("UPDATE schema_meta SET version = 4")
        report = initialize(conn)
        self.assertEqual(report["migrated_from"], 4)
        tables = {
            row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        self.assertIn("observation", tables)


if __name__ == "__main__":
    unittest.main()
