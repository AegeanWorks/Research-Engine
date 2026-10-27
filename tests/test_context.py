"""Token-budgeted views: estimation, packing and omission accounting."""

from __future__ import annotations

import unittest

from engine.context import (
    DEFAULT_BUDGET,
    brief,
    claim_brief,
    estimate_tokens,
    outline,
    pack,
)
from tests.support import DatabaseCase


class TokenTests(unittest.TestCase):
    def test_estimate_is_character_quarters(self) -> None:
        self.assertEqual(estimate_tokens(""), 0)
        self.assertEqual(estimate_tokens("abcd"), 1)
        self.assertEqual(estimate_tokens("abcde"), 2)
        self.assertEqual(estimate_tokens("x" * 4000), 1000)

    def test_pack_keeps_the_first_line_even_when_over_budget(self) -> None:
        lines = ["anchor " + "x" * 400, "second", "third"]
        kept, omitted, used = pack(lines, 20)
        self.assertEqual(len(kept), 1)
        self.assertEqual(omitted, 2)
        self.assertGreater(used, 0)

    def test_pack_keeps_everything_that_fits(self) -> None:
        lines = ["a", "b", "c"]
        kept, omitted, _used = pack(lines, 5000)
        self.assertEqual(kept, lines)
        self.assertEqual(omitted, 0)

    def test_pack_rejects_a_non_positive_budget(self) -> None:
        with self.assertRaises(ValueError):
            pack(["a"], 0)


class ViewTests(DatabaseCase):
    def setUp(self) -> None:
        super().setUp()
        from engine.demo import seed_demo

        self.demo = seed_demo(self.conn)

    def test_outline_lists_questions_hypotheses_tests_and_audit(self) -> None:
        view = outline(self.conn, self.demo["research"])
        for marker in ("OUTLINE", "Q q_000001", "H h_000001", "T t_000001", "audit errors"):
            self.assertIn(marker, view.text)

    def test_outline_reports_omissions(self) -> None:
        view = outline(self.conn, self.demo["research"], budget=60)
        self.assertGreater(view.omitted, 0)
        self.assertIn("OMITTED:", view.text)

    def test_brief_shows_support_and_contradiction(self) -> None:
        view = brief(self.conn, self.demo["research"])
        self.assertIn("consensus=", view.text)
        self.assertIn("+ c_000001", view.text)
        self.assertIn("- c_000003", view.text)

    def test_views_are_deterministic(self) -> None:
        first = outline(self.conn, self.demo["research"]).text
        second = outline(self.conn, self.demo["research"]).text
        self.assertEqual(first, second)

    def test_default_budget_is_positive(self) -> None:
        self.assertGreater(DEFAULT_BUDGET, 0)

    def test_claim_view_carries_provenance_and_verdicts(self) -> None:
        view = claim_brief(self.conn, self.demo["claim"])
        self.assertIn("CLAIM c_000001", view.text)
        self.assertIn("quote ", view.text)
        self.assertIn("verdict NUMERIC", view.text)
        self.assertIn("premise", claim_brief(self.conn, self.demo["derived_claim"]).text)

    def test_budget_is_respected(self) -> None:
        view = brief(self.conn, self.demo["research"], budget=40)
        self.assertLessEqual(view.tokens, 60)


if __name__ == "__main__":
    unittest.main()
