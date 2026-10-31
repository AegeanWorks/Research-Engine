"""Event log: append-only record of actions that are not verdicts."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from engine.claims import add_claim
from engine.errors import EngineError
from engine.events import count, event_path, event_tree, list_events, record
from engine.manifest import write_report
from engine.merging import merge_claims
from engine.screening import set_screening
from engine.sources import add_source, set_source_status
from tests.support import DatabaseCase


class EventTests(DatabaseCase):
    def test_record_and_list_newest_first(self) -> None:
        record(self.conn, "test.one", "a", "first")
        record(self.conn, "test.two", "b", "second")
        events = list_events(self.conn, limit=10)
        self.assertEqual([event.kind for event in events], ["test.two", "test.one"])
        self.assertEqual(count(self.conn), 2)

    def test_filters_by_kind_and_research(self) -> None:
        research = self.add_research()
        record(self.conn, "x", "s1", research_id=research)
        record(self.conn, "y", "s2", research_id=research)
        record(self.conn, "x", "s3")
        self.assertEqual([e.subject for e in list_events(self.conn, research, "x")], ["s1"])

    def test_detail_is_flattened(self) -> None:
        event = record(self.conn, "x", "s", "line one\nline two\x00")
        self.assertEqual(event.detail, "line one line two")

    def test_nested_events_form_a_tree_and_path(self) -> None:
        research = self.add_research()
        root = record(self.conn, "root", "a", research_id=research)
        child = record(self.conn, "child", "b", research_id=research, parent_id=root.id)
        grand = record(self.conn, "grand", "c", research_id=research, parent_id=child.id)
        self.assertEqual([root.seq, child.seq, grand.seq], [1, 2, 3])
        self.assertEqual(child.root_id, root.id)
        self.assertEqual(grand.root_id, root.id)
        tree = event_tree(self.conn, root.id)
        self.assertEqual(
            [(item["depth"], item["event"].id) for item in tree],
            [(0, root.id), (1, child.id), (2, grand.id)],
        )
        self.assertEqual(
            [event.id for event in event_path(self.conn, grand.id)],
            [root.id, child.id, grand.id],
        )

    def test_orphan_parent_is_refused(self) -> None:
        with self.assertRaises(EngineError):
            record(self.conn, "child", "b", parent_id="ev_999999")

    def test_cross_program_parent_is_refused(self) -> None:
        first = self.add_research("First")
        second = self.add_research("Second")
        root = record(self.conn, "root", "a", research_id=first)
        with self.assertRaises(EngineError):
            record(self.conn, "child", "b", research_id=second, parent_id=root.id)

    def test_tree_rejects_a_non_root(self) -> None:
        research = self.add_research()
        root = record(self.conn, "root", "a", research_id=research)
        child = record(self.conn, "child", "b", research_id=research, parent_id=root.id)
        with self.assertRaises(EngineError):
            event_tree(self.conn, child.id)

    def test_source_status_is_recorded(self) -> None:
        research = self.add_research()
        source = add_source(self.conn, research, "S", year=2026).id
        set_source_status(self.conn, source, "expression_of_concern", "notice")
        events = [e for e in list_events(self.conn) if e.kind == "source.status"]
        self.assertEqual(len(events), 1)
        self.assertIn("active -> expression_of_concern", events[0].detail)

    def test_screening_is_recorded(self) -> None:
        research = self.add_research()
        source = add_source(self.conn, research, "S", year=2026).id
        set_screening(self.conn, source, "excluded", "not_relevant")
        events = [e for e in list_events(self.conn) if e.kind == "source.screening"]
        self.assertEqual(len(events), 1)
        self.assertIn("not_relevant", events[0].detail)

    def test_merge_is_recorded_once(self) -> None:
        research = self.add_research()
        keep = add_claim(self.conn, research, "A.", "assumption", basis="a")
        drop = add_claim(self.conn, research, "A.", "assumption", basis="b")
        merge_claims(self.conn, keep.id, [drop.id])
        events = [e for e in list_events(self.conn) if e.kind == "claim.merge"]
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].subject, keep.id)
        self.assertIn(drop.id, events[0].detail)

    def test_report_generation_is_recorded(self) -> None:
        research = self.add_research()
        add_claim(self.conn, research, "A.", "assumption", basis="a")
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        write_report(self.conn, research, Path(directory.name) / "r.md")
        events = [e for e in list_events(self.conn) if e.kind == "report.write"]
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].research_id, research)

    def test_migration_records_an_event(self) -> None:
        import sqlite3

        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "old.db"
        raw = sqlite3.connect(str(path))
        raw.executescript(
            "CREATE TABLE schema_meta (version INTEGER NOT NULL);"
            "INSERT INTO schema_meta(version) VALUES (1);"
        )
        raw.commit()
        raw.close()
        from engine.database import connect, initialize

        conn = connect(path)
        self.addCleanup(conn.close)
        initialize(conn)
        events = [e for e in list_events(conn) if e.kind == "db.migrate"]
        self.assertEqual(len(events), 1)
        self.assertIn("schema 1 ->", events[0].detail)


if __name__ == "__main__":
    unittest.main()
