"""Shared fixtures: a fresh in-memory database per test."""

from __future__ import annotations

import sqlite3
import unittest

from engine.database import connect, initialize


class DatabaseCase(unittest.TestCase):
    """Give each test an isolated schema and connection."""

    def setUp(self) -> None:
        self.conn = connect(":memory:")
        initialize(self.conn)
        self.addCleanup(self.conn.close)

    def add_research(self, title: str = "Test research") -> str:
        from engine.researches import create_research

        return create_research(self.conn, title).id

    def add_source(self, research: str, title: str = "Test source") -> str:
        from engine.sources import add_source

        return add_source(self.conn, research, title, year=2024).id

    def add_empirical(self, research: str, text: str = "Signal S rose with O.") -> str:
        from engine.claims import add_claim

        source = self.add_source(research)
        claim = add_claim(
            self.conn,
            research,
            text,
            "empirical",
            source_ref=source,
            quote=text,
            locator="Results, paragraph 1",
            kill_test="A replicate in which S falls while O rises.",
        )
        return claim.id


def memory_connection() -> sqlite3.Connection:
    """Return an initialized in-memory connection for direct module tests."""
    conn = connect(":memory:")
    initialize(conn)
    return conn

def force_numeric(conn, claim_id: str, group: str = "g_legacy") -> None:
    """Write a NUMERIC state directly, simulating a record that predates the promotion gate."""
    from engine.database import next_id, transaction

    with transaction(conn):
        conn.execute(
            "INSERT INTO verdict(id, subject_kind, subject_id, status, previous_status,"
            " evidence, note, actor, at, evidence_group)"
            " VALUES (?, 'claim', ?, 'NUMERIC', 'UNVERIFIED', 'legacy record', '', 'test',"
            " '2026-01-01T00:00:00+00:00', ?)",
            (next_id(conn, "v"), claim_id, group),
        )
        conn.execute("UPDATE claim SET status = 'NUMERIC' WHERE id = ?", (claim_id,))
