"""Schema 14: lattice paper fields, N1 experiment tables and the pack registry."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from engine.database import SCHEMA_VERSION, connect, initialize
from engine.sources import add_source, get_source
from tests.support import DatabaseCase

_V13_SOURCE = """
CREATE TABLE schema_meta (version INTEGER NOT NULL);
CREATE TABLE source (
    id TEXT PRIMARY KEY,
    research_id TEXT NOT NULL,
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
INSERT INTO schema_meta(version) VALUES (13);
INSERT INTO source(id, research_id, kind, title, retrieved_at)
    VALUES ('s_old', 'r_old', 'paper', 'Old paper', 'then');
"""


class Schema14MigrationTests(unittest.TestCase):
    def _v13(self) -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "v13.db"
        raw = sqlite3.connect(str(path))
        raw.executescript(_V13_SOURCE)
        raw.commit()
        raw.close()
        return path

    def test_version_13_source_gains_paper_columns_and_keeps_rows(self) -> None:
        path = self._v13()
        conn = connect(path)
        self.addCleanup(conn.close)
        report = initialize(conn)
        self.assertEqual(report["migrated_from"], 13)
        self.assertEqual(report["migrated_to"], SCHEMA_VERSION)
        self.assertGreaterEqual(SCHEMA_VERSION, 14)
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(source)")}
        self.assertTrue({"arxiv", "venue", "abstract", "tags", "study_type"} <= columns)
        row = conn.execute("SELECT * FROM source WHERE id = 's_old'").fetchone()
        self.assertEqual(row["title"], "Old paper")
        self.assertEqual(row["arxiv"], "")
        self.assertEqual(row["tags"], "")

    def test_version_14_creates_experiment_and_pack_tables(self) -> None:
        conn = connect(":memory:")
        self.addCleanup(conn.close)
        initialize(conn)
        tables = {
            row["name"]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        self.assertTrue(
            {
                "experiment_intervention",
                "experiment_metric_definition",
                "experiment_metric",
                "experiment_event",
                "domain_pack",
                "migration_run",
            }
            <= tables
        )


class PaperFieldTests(DatabaseCase):
    def test_source_round_trips_paper_metadata(self) -> None:
        research = self.add_research()
        source = add_source(
            self.conn,
            research,
            "A title",
            year=2024,
            doi="10.1000/x",
            authors="A. Author",
            arxiv="2401.00001",
            venue="Journal of Tests",
            abstract="An abstract.",
            tags="alpha, beta",
            study_type="Cohort Study",
        )
        loaded = get_source(self.conn, source.id)
        self.assertEqual(loaded.arxiv, "2401.00001")
        self.assertEqual(loaded.venue, "Journal of Tests")
        self.assertEqual(loaded.abstract, "An abstract.")
        self.assertEqual(loaded.tags, "alpha, beta")
        self.assertEqual(loaded.study_type, "Cohort Study")
