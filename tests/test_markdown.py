"""Untrusted text: control characters, newlines and table syntax must not escape a cell."""

from __future__ import annotations

import unittest

from engine.markdown import bullet, cell, code, sanitize


class SanitizeTests(unittest.TestCase):
    def test_newlines_collapse(self) -> None:
        self.assertEqual(sanitize("one\ntwo\r\nthree"), "one two three")

    def test_control_characters_are_removed(self) -> None:
        self.assertEqual(sanitize("a\x00b\x07c\x1bd"), "abcd")

    def test_heading_injection_cannot_survive(self) -> None:
        self.assertEqual(sanitize("x\n## Injected"), "x ## Injected")

    def test_width_is_respected_and_marked(self) -> None:
        value = sanitize("word " * 40, width=20)
        self.assertEqual(len(value), 20)
        self.assertTrue(value.endswith("\u2026"))

    def test_zero_width_means_no_cap(self) -> None:
        self.assertEqual(sanitize("abc", width=0), "abc")


class CellTests(unittest.TestCase):
    def test_pipe_is_escaped(self) -> None:
        self.assertEqual(cell("a | b"), "a \\| b")

    def test_backtick_is_escaped(self) -> None:
        self.assertEqual(cell("run `now`"), "run \\`now\\`")

    def test_backslash_is_escaped_first(self) -> None:
        self.assertIn("\\\\", cell("a\\b"))

    def test_cell_is_a_single_line(self) -> None:
        rendered = cell("a\nb | c")
        self.assertNotIn("\n", rendered)
        self.assertIn("\\|", rendered)

    def test_bullet_and_code_are_single_line(self) -> None:
        self.assertNotIn("\n", bullet("a\n# b"))
        self.assertNotIn("`", code("a `b` c"))


if __name__ == "__main__":
    unittest.main()
