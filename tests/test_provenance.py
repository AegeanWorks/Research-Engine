"""Workspace provenance: code and input identity used to bind evidence."""

from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

from engine.provenance import (
    code_sha256,
    environment,
    fingerprint,
    git_state,
    inputs_sha256,
    provenance,
)


class ProvenanceTests(unittest.TestCase):
    def test_code_digest_is_stable_and_shaped(self) -> None:
        first, files = code_sha256()
        second, files_again = code_sha256()
        self.assertEqual(first, second)
        self.assertGreater(files, 10)
        self.assertEqual(files, files_again)
        self.assertRegex(first, r"^[0-9a-f]{64}$")

    def test_inputs_digest_tracks_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.csv"
            path.write_text("a,b\n1,2\n", encoding="utf-8")
            before, count = inputs_sha256([str(path)])
            path.write_text("a,b\n1,3\n", encoding="utf-8")
            after, _ = inputs_sha256([str(path)])
            self.assertEqual(count, 1)
            self.assertNotEqual(before, after)
            self.assertEqual(after, inputs_sha256([str(path)])[0])

    def test_missing_input_hashes_distinctly(self) -> None:
        missing, count = inputs_sha256(["does/not/exist.csv"])
        empty, empty_count = inputs_sha256([])
        self.assertEqual(count, 1)
        self.assertEqual(empty_count, 0)
        self.assertNotEqual(missing, empty)

    def test_input_order_does_not_matter(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "a.txt"
            second = Path(directory) / "b.txt"
            first.write_text("a", encoding="utf-8")
            second.write_text("b", encoding="utf-8")
            self.assertEqual(
                inputs_sha256([str(first), str(second)]),
                inputs_sha256([str(second), str(first)]),
            )

    def test_fingerprint_combines_code_and_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.csv"
            path.write_text("x", encoding="utf-8")
            first = fingerprint([str(path)])
            self.assertEqual(first.code_sha256, code_sha256()[0])
            path.write_text("y", encoding="utf-8")
            second = fingerprint([str(path)])
            self.assertEqual(first.code_sha256, second.code_sha256)
            self.assertNotEqual(first.inputs_sha256, second.inputs_sha256)
            self.assertEqual(first.input_files, 1)

    def test_git_state_reports_a_pair(self) -> None:
        commit, dirty = git_state()
        self.assertIsInstance(commit, str)
        self.assertIsInstance(dirty, bool)
        self.assertTrue(commit)

    def test_environment_names_runtime(self) -> None:
        block = environment()
        self.assertRegex(block["python"], r"^\d+\.\d+")
        self.assertTrue(block["platform"])
        self.assertRegex(block["engine"], r"^\d+\.\d+\.\d+$")

    def test_provenance_block_has_binding_and_diagnostics(self) -> None:
        block = provenance()
        for key in ("code_sha256", "inputs_sha256", "git_commit", "git_dirty",
                    "python", "platform", "engine"):
            self.assertIn(key, block)
        self.assertRegex(block["code_sha256"], r"^[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()
