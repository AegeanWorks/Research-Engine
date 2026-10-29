"""Cheap information-quality checks over stored claim quotes."""

from __future__ import annotations

import unittest

from engine.information import (
    content_terms,
    duplicate_quote,
    normalize,
    quote_classes,
    restates_question,
    stopword_only,
)


class InformationTests(unittest.TestCase):
    def test_normalize_folds_case_and_punctuation(self) -> None:
        self.assertEqual(normalize("S rose, WITH O."), "s rose with o")

    def test_restates_question_exact_and_substring(self) -> None:
        self.assertTrue(restates_question("Does the mechanism hold?", ["Does the mechanism hold?"]))
        self.assertTrue(restates_question("the mechanism hold", ["Does the mechanism hold?"]))

    def test_restates_question_needs_two_content_terms(self) -> None:
        self.assertFalse(restates_question("the", ["the answer is yes"]))

    def test_duplicate_quote_is_case_and_punctuation_insensitive(self) -> None:
        self.assertTrue(duplicate_quote("S rose with O.", ["s rose with o"]))
        self.assertFalse(duplicate_quote("S rose with O.", ["S fell with O."]))

    def test_stopword_only_quote_has_no_content_terms(self) -> None:
        self.assertEqual(content_terms("the of and"), ())
        self.assertTrue(stopword_only("the of and"))
        self.assertFalse(stopword_only("S rose with O"))

    def test_quote_classes_are_stable_and_additive(self) -> None:
        classes = quote_classes(
            "Does the mechanism hold?",
            questions=["Does the mechanism hold?"],
            other_quotes=["does the mechanism hold"],
        )
        self.assertEqual(classes, ("restates_question", "duplicate_quote"))

    def test_distinct_quote_has_no_classes(self) -> None:
        self.assertEqual(
            quote_classes(
                "S rose with O in the synthetic cohort.",
                questions=["Does S rise with O?"],
                other_quotes=["The cohort had 40 participants."],
            ),
            (),
        )


if __name__ == "__main__":
    unittest.main()
