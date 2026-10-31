"""Declared inputs: glob expansion, directory refusal, absence and collision safety."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from engine.errors import EngineError
from engine.provenance import inputs_sha256, resolve_inputs


class InputTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.dir = Path(directory.name)

    def test_glob_expands_to_each_matching_file(self) -> None:
        (self.dir / "a.csv").write_text("1", encoding="utf-8")
        (self.dir / "b.csv").write_text("2", encoding="utf-8")
        names = resolve_inputs([str(self.dir / "*.csv")])
        self.assertEqual([Path(name).name for name in names], ["a.csv", "b.csv"])

    def test_glob_result_tracks_content(self) -> None:
        (self.dir / "a.csv").write_text("1", encoding="utf-8")
        pattern = str(self.dir / "*.csv")
        before = inputs_sha256([pattern])[0]
        (self.dir / "a.csv").write_text("2", encoding="utf-8")
        self.assertNotEqual(before, inputs_sha256([pattern])[0])

    def test_a_new_file_matching_the_glob_changes_the_digest(self) -> None:
        (self.dir / "a.csv").write_text("1", encoding="utf-8")
        pattern = str(self.dir / "*.csv")
        before = inputs_sha256([pattern])[0]
        (self.dir / "b.csv").write_text("2", encoding="utf-8")
        self.assertNotEqual(before, inputs_sha256([pattern])[0])

    def test_unmatched_glob_is_recorded_and_changes_when_files_appear(self) -> None:
        pattern = str(self.dir / "*.csv")
        before, count = inputs_sha256([pattern])
        self.assertEqual(count, 1)
        (self.dir / "a.csv").write_text("1", encoding="utf-8")
        self.assertNotEqual(before, inputs_sha256([pattern])[0])

    def test_directory_input_is_refused(self) -> None:
        with self.assertRaises(EngineError):
            resolve_inputs([str(self.dir)])

    def test_absent_file_does_not_collide_with_the_word_missing(self) -> None:
        path = self.dir / "x.txt"
        path.write_text("missing", encoding="utf-8")
        present = inputs_sha256([str(path)])[0]
        path.unlink()
        absent = inputs_sha256([str(path)])[0]
        self.assertNotEqual(present, absent)

    def test_declarations_are_deduplicated_and_sorted(self) -> None:
        (self.dir / "a.csv").write_text("1", encoding="utf-8")
        names = resolve_inputs([str(self.dir / "a.csv"), str(self.dir / "*.csv")])
        self.assertEqual(len(names), 1)

    def test_directory_contents_are_not_silently_ignored(self) -> None:
        (self.dir / "a.csv").write_text("1", encoding="utf-8")
        with self.assertRaises(EngineError):
            inputs_sha256([str(self.dir)])


if __name__ == "__main__":
    unittest.main()
