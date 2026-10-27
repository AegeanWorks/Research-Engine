"""Database maintenance: integrity verification and verified backups."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from engine.claims import add_claim
from engine.database import SCHEMA_VERSION, connect
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

    def test_backup_of_a_database_with_events_copies_them(self) -> None:
        from engine.events import record

        record(self.conn, "x", "s", "detail")
        result = backup(self.conn, self.dir / "events.db")
        copy = sqlite3.connect(result["path"])
        self.addCleanup(copy.close)
        self.assertEqual(copy.execute("SELECT COUNT(*) FROM event").fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
