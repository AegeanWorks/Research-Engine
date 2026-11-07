"""Migration harness: inspect first, then apply a source fixture without losing provenance."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from engine.migrations import (
    applied_migrations,
    inspect_lattice,
    inspect_n1,
    inspect_obezite,
    inspect_research,
    inspect_tree,
    migrate_lattice,
    migrate_n1,
)
from tests.support import DatabaseCase

_LATTICE = """
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE papers (
    id TEXT PRIMARY KEY, kind TEXT NOT NULL DEFAULT 'paper', title TEXT NOT NULL,
    authors TEXT NOT NULL DEFAULT '', year TEXT NOT NULL DEFAULT '',
    venue TEXT NOT NULL DEFAULT '', doi TEXT NOT NULL DEFAULT '',
    arxiv TEXT NOT NULL DEFAULT '', url TEXT NOT NULL DEFAULT '',
    abstract TEXT NOT NULL DEFAULT '', tags TEXT NOT NULL DEFAULT '',
    study_type TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL
);
CREATE TABLE claims (
    id TEXT PRIMARY KEY, paper_id TEXT NOT NULL, text TEXT NOT NULL, quote TEXT NOT NULL,
    locator TEXT NOT NULL DEFAULT '', stance TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 0.5, created_at TEXT NOT NULL
);
CREATE TABLE questions (
    id TEXT PRIMARY KEY, text TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'open',
    created_at TEXT NOT NULL
);
CREATE TABLE edges (
    id INTEGER PRIMARY KEY AUTOINCREMENT, src TEXT NOT NULL, dst TEXT NOT NULL,
    kind TEXT NOT NULL, note TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL
);
CREATE TABLE screening (
    paper_id TEXT PRIMARY KEY, status TEXT NOT NULL, reason TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '', screened_at TEXT NOT NULL
);
INSERT INTO meta(key, value) VALUES ('schema_version', '2');
INSERT INTO papers(id, title, authors, year, venue, doi, arxiv, url, abstract, tags, study_type, created_at)
    VALUES ('p1', 'Paper One', 'A. Author', '2024', 'Journal', '10.1000/one', '2401.00001',
            'https://example.org/one', 'Abstract one', 'alpha, beta', 'Cohort Study', 'then');
INSERT INTO papers(id, title, year, created_at) VALUES ('p2', 'Paper Two', '2023', 'then');
INSERT INTO claims(id, paper_id, text, quote, locator, stance, confidence, created_at)
    VALUES ('c1', 'p1', 'Signal S rose.', 'Signal S rose in the cohort.', 'Results p.2',
            'supports', 0.8, 'then');
INSERT INTO questions(id, text, status, created_at)
    VALUES ('q1', 'Does S rise?', 'open', 'then');
INSERT INTO edges(src, dst, kind, note, created_at)
    VALUES ('c1', 'q1', 'supports', '', 'then');
INSERT INTO edges(src, dst, kind, note, created_at)
    VALUES ('p1', 'p2', 'cites', '', 'then');
INSERT INTO screening(paper_id, status, reason, screened_at)
    VALUES ('p1', 'included', '', 'then');
"""

_N1 = """
CREATE TABLE interventions (
    id INTEGER PRIMARY KEY, name TEXT NOT NULL, start_date TEXT NOT NULL,
    projected_end_date TEXT, end_date TEXT, dosage TEXT, notes TEXT
);
CREATE TABLE metric_definitions (
    id INTEGER PRIMARY KEY, name TEXT NOT NULL, description TEXT, unit TEXT
);
CREATE TABLE metrics (
    id INTEGER PRIMARY KEY, date TEXT NOT NULL, metric_name TEXT NOT NULL, value REAL NOT NULL,
    intervention_id INTEGER
);
CREATE TABLE events (
    id INTEGER PRIMARY KEY, timestamp TEXT NOT NULL, event_name TEXT NOT NULL,
    severity INTEGER, notes TEXT, intervention_id INTEGER
);
INSERT INTO interventions(id, name, start_date, dosage) VALUES (1, 'Sleep extension', '2026-01-01', '+1 h');
INSERT INTO metric_definitions(id, name, unit) VALUES (1, 'weight', 'kg');
INSERT INTO metrics(id, date, metric_name, value, intervention_id)
    VALUES (1, '2026-01-02', 'weight', 81.5, 1);
INSERT INTO metrics(id, date, metric_name, value, intervention_id)
    VALUES (2, '2026-01-03', 'weight', 81.2, 1);
INSERT INTO events(id, timestamp, event_name, severity, intervention_id)
    VALUES (1, '2026-01-02T10:00:00+00:00', 'headache', 2, 1);
"""


def _fixture(sql: str, name: str) -> Path:
    directory = Path(tempfile.mkdtemp())
    path = directory / name
    raw = sqlite3.connect(str(path))
    raw.executescript(sql)
    raw.commit()
    raw.close()
    return path


class MigrationHarnessTests(DatabaseCase):
    def _lattice(self) -> Path:
        path = _fixture(_LATTICE, "lattice.db")
        self.addCleanup(lambda: __import__("shutil").rmtree(path.parent, ignore_errors=True))
        return path

    def _n1(self) -> Path:
        path = _fixture(_N1, "main.db")
        self.addCleanup(lambda: __import__("shutil").rmtree(path.parent, ignore_errors=True))
        return path

    def test_lattice_inspect_is_read_only_and_counts_rows(self) -> None:
        path = self._lattice()
        before = path.read_bytes()
        report = inspect_lattice(path)
        self.assertEqual(report.tables["papers"], 2)
        self.assertEqual(report.tables["claims"], 1)
        self.assertEqual(report.tables["questions"], 1)
        self.assertEqual(report.tables["edges"], 2)
        self.assertEqual(len(report.source_digest), 64)
        self.assertEqual(path.read_bytes(), before)

    def test_lattice_dry_run_writes_nothing(self) -> None:
        research = self.add_research()
        path = self._lattice()
        report = migrate_lattice(self.conn, research, path, dry_run=True)
        self.assertEqual(report.tables["papers"], 2)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) AS n FROM source").fetchone()["n"], 0)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) AS n FROM claim").fetchone()["n"], 0)

    def test_lattice_apply_preserves_paper_fields_provenance_and_screening(self) -> None:
        research = self.add_research()
        path = self._lattice()
        report = migrate_lattice(self.conn, research, path)
        self.assertEqual(report.inserted["source"], 2)
        source = self.conn.execute(
            "SELECT * FROM source WHERE title = 'Paper One'"
        ).fetchone()
        self.assertEqual(source["doi"], "10.1000/one")
        self.assertEqual(source["arxiv"], "2401.00001")
        self.assertEqual(source["venue"], "Journal")
        self.assertEqual(source["abstract"], "Abstract one")
        self.assertEqual(source["tags"], "alpha, beta")
        self.assertEqual(source["study_type"], "Cohort Study")
        self.assertEqual(source["screening"], "included")
        claim = self.conn.execute("SELECT * FROM claim").fetchone()
        self.assertEqual(claim["text"], "Signal S rose.")
        self.assertEqual(claim["quote"], "Signal S rose in the cohort.")
        self.assertEqual(claim["locator"], "Results p.2")
        self.assertEqual(claim["kind"], "empirical")
        self.assertEqual(claim["status"], "UNVERIFIED")

    def test_lattice_apply_is_recorded_once(self) -> None:
        research = self.add_research()
        path = self._lattice()
        migrate_lattice(self.conn, research, path)
        self.assertEqual(len(applied_migrations(self.conn)), 1)
        self.assertRaises(Exception, migrate_lattice, self.conn, research, path)

    def test_n1_manifest_and_apply_link_metrics_to_interventions(self) -> None:
        research = self.add_research()
        path = self._n1()
        report = inspect_n1(path)
        self.assertEqual(report.tables["interventions"], 1)
        self.assertEqual(report.tables["metrics"], 2)
        migrate_n1(self.conn, research, path)
        intervention = self.conn.execute("SELECT * FROM experiment_intervention").fetchone()
        self.assertEqual(intervention["name"], "Sleep extension")
        metrics = self.conn.execute(
            "SELECT * FROM experiment_metric ORDER BY date"
        ).fetchall()
        self.assertEqual([row["value"] for row in metrics], [81.5, 81.2])
        self.assertEqual({row["intervention_id"] for row in metrics}, {intervention["id"]})
        event = self.conn.execute("SELECT * FROM experiment_event").fetchone()
        self.assertEqual(event["severity"], 2)

    def test_golden_both_sources_share_one_program(self) -> None:
        research = self.add_research("Merged program")
        migrate_lattice(self.conn, research, self._lattice())
        migrate_n1(self.conn, research, self._n1())
        counts = {
            "source": self.conn.execute("SELECT COUNT(*) AS n FROM source").fetchone()["n"],
            "claim": self.conn.execute("SELECT COUNT(*) AS n FROM claim").fetchone()["n"],
            "metric": self.conn.execute(
                "SELECT COUNT(*) AS n FROM experiment_metric"
            ).fetchone()["n"],
        }
        self.assertEqual(counts, {"source": 2, "claim": 1, "metric": 2})
        self.assertEqual(
            self.conn.execute(
                "SELECT COUNT(*) AS n FROM source WHERE research_id <> ?", (research,)
            ).fetchone()["n"],
            0,
        )

    def test_inspect_tree_counts_and_fingerprints_files(self) -> None:
        root = self._lattice().parent
        (root / "notes.md").write_text("note\n", encoding="utf-8")
        (root / "data.json").write_text("{}\n", encoding="utf-8")
        report = inspect_tree(root, "fixture", suffixes=(".md", ".json"))
        self.assertEqual(report.tables, {"files": 2, ".json": 1, ".md": 1})
        self.assertEqual(len(report.source_digest), 64)

    def test_inspect_obezite_counts_verified_and_backfill(self) -> None:
        root = self._lattice().parent
        ledger = root / "iddia-defteri.md"
        ledger.write_text(
            "| **1** | A | L1 | D1 | up | none | **kanitli** | PMID:1 |\n"
            "| **2** | B | L2 | D? | down | q | **backfill** | none |\n",
            encoding="utf-8",
        )
        report = inspect_obezite(ledger)
        self.assertEqual(report.tables, {"claim": 2, "verified": 1, "backfill": 1})

    def test_inspect_research_reads_a_host_database(self) -> None:
        from engine.database import SCHEMA_VERSION, connect, initialize

        path = self._lattice().parent / "research.db"
        conn = connect(path)
        initialize(conn)
        conn.close()
        report = inspect_research(path)
        self.assertEqual(report.tables["research"], 0)
        self.assertEqual(report.tables["source"], 0)
        self.assertEqual(report.tables["schema_version"], SCHEMA_VERSION)
        self.assertEqual(len(report.source_digest), 64)
