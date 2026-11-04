"""Database maintenance: integrity verification and verified backups."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from engine.claims import add_claim
from engine.database import SCHEMA_VERSION, connect, initialize
from engine.errors import EngineError
from engine.maintenance import backup, integrity_check
from tests.support import DatabaseCase


class MaintenanceTests(DatabaseCase):
    def setUp(self) -> None:
        super().setUp()
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.dir = Path(directory.name)

    def test_integrity_reports_ok_and_counts(self) -> None:
        research = self.add_research()
        add_claim(self.conn, research, "A.", "assumption", basis="a")
        result = integrity_check(self.conn)
        self.assertTrue(result["ok"])
        self.assertEqual(result["integrity"], ["ok"])
        self.assertEqual(result["foreign_key_violations"], [])
        self.assertEqual(result["schema_version"], SCHEMA_VERSION)
        self.assertEqual(result["counts"]["claim"], 1)

    def test_integrity_detects_a_foreign_key_violation(self) -> None:
        self.conn.execute("PRAGMA foreign_keys = OFF")
        self.conn.execute(
            "INSERT INTO claim(id, research_id, text, kind, status, confidence, created_at,"
            " updated_at) VALUES ('c_bad', 'r_missing', 'x', 'assumption', 'UNVERIFIED', 0.5,"
            " 'now', 'now')"
        )
        result = integrity_check(self.conn)
        self.assertFalse(result["ok"])
        self.assertEqual(result["foreign_key_violations"][0]["table"], "claim")

    def test_backup_produces_a_readable_copy(self) -> None:
        research = self.add_research()
        add_claim(self.conn, research, "A.", "assumption", basis="a")
        result = backup(self.conn, self.dir / "copy.db")
        self.assertTrue(Path(result["path"]).is_file())
        self.assertEqual(result["integrity"], "ok")
        copy = connect(Path(result["path"]))
        self.addCleanup(copy.close)
        self.assertEqual(copy.execute("SELECT COUNT(*) AS n FROM claim").fetchone()["n"], 1)
        self.assertEqual(
            copy.execute("SELECT version FROM schema_meta").fetchone()["version"], SCHEMA_VERSION
        )

    def test_backup_refuses_to_overwrite(self) -> None:
        target = self.dir / "copy.db"
        target.write_text("existing", encoding="utf-8")
        with self.assertRaises(EngineError):
            backup(self.conn, target)
        self.assertEqual(target.read_text(encoding="utf-8"), "existing")

    def test_backup_leaves_no_temporary_file(self) -> None:
        backup(self.conn, self.dir / "copy.db")
        leftovers = [p.name for p in self.dir.iterdir() if p.name.startswith(".copy.db")]
        self.assertEqual(leftovers, [])

    def test_connect_uses_a_lock_wait_timeout(self) -> None:
        conn = connect(str(self.dir / "f.db"))
        self.addCleanup(conn.close)
        self.assertEqual(conn.execute("PRAGMA busy_timeout").fetchone()[0], 5000)

    def test_locked_database_reports_an_engine_error(self) -> None:
        from engine.database import initialize, transaction

        first = connect(str(self.dir / "lock.db"))
        self.addCleanup(first.close)
        initialize(first)
        first.execute("BEGIN IMMEDIATE")
        self.addCleanup(first.execute, "ROLLBACK")
        second = connect(str(self.dir / "lock.db"))
        self.addCleanup(second.close)
        second.execute("PRAGMA busy_timeout = 50")
        with self.assertRaises(EngineError):
            initialize(second)
        with self.assertRaises(EngineError):
            with transaction(second):
                second.execute(
                    "INSERT INTO research(id, title, scope, slug, created_at, updated_at)"
                    " VALUES ('r_x', 'X', '', 'x', 't', 't')"
                )

    def test_backup_preserves_the_journal_mode(self) -> None:
        source = connect(str(self.dir / "src.db"))
        self.addCleanup(source.close)
        initialize(source)
        source.execute("PRAGMA journal_mode = WAL")
        self.assertEqual(source.execute("PRAGMA journal_mode").fetchone()[0], "wal")
        result = backup(source, self.dir / "copy.db")
        copy = sqlite3.connect(result["path"])
        self.addCleanup(copy.close)
        self.assertEqual(copy.execute("PRAGMA journal_mode").fetchone()[0], "wal")

    def test_backup_refuses_an_open_write_transaction(self) -> None:
        self.conn.execute("BEGIN IMMEDIATE")
        self.addCleanup(self.conn.execute, "ROLLBACK")
        with self.assertRaises(EngineError):
            backup(self.conn, self.dir / "copy.db")
        self.assertFalse((self.dir / "copy.db").exists())

    def test_counts_cover_edges_and_ai_artifacts(self) -> None:
        from engine.ai import record_artifact
        from engine.claims import link_claims

        research = self.add_research()
        left = add_claim(self.conn, research, "Left.", "assumption", basis="a")
        right = add_claim(self.conn, research, "Right.", "assumption", basis="b")
        link_claims(self.conn, left.id, right.id, "related")
        record_artifact(self.conn, research, "sweep", "model:x", "prompt", "output")
        counts = integrity_check(self.conn)["counts"]
        self.assertEqual(counts["edge"], 1)
        self.assertEqual(counts["ai_artifact"], 1)

    def test_version_skew_fails_the_gate(self) -> None:
        research = self.add_research()
        add_claim(self.conn, research, "A.", "assumption", basis="a")
        self.conn.execute("UPDATE schema_meta SET version = 1")
        result = integrity_check(self.conn)
        self.assertFalse(result["ok"])
        self.assertEqual(result["schema_version"], 1)
        self.assertEqual(result["expected_schema_version"], SCHEMA_VERSION)

    def test_corrupt_version_fails_closed(self) -> None:
        research = self.add_research()
        add_claim(self.conn, research, "A.", "assumption", basis="a")
        self.conn.execute("UPDATE schema_meta SET version = 'abc'")
        result = integrity_check(self.conn)
        self.assertFalse(result["ok"])
        self.conn.execute("DELETE FROM schema_meta")
        result = integrity_check(self.conn)
        self.assertFalse(result["ok"])
        self.assertEqual(result["schema_version"], 0)

    def test_backup_of_a_database_with_events_copies_them(self) -> None:
        from engine.events import record

        record(self.conn, "x", "s", "detail")
        result = backup(self.conn, self.dir / "events.db")
        copy = sqlite3.connect(result["path"])
        self.addCleanup(copy.close)
        self.assertEqual(copy.execute("SELECT COUNT(*) FROM event").fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
