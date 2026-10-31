"""Cheap information-quality checks over stored claim quotes.

The engine stores only a quote and a locator string, not the source body. These checks
therefore cover the zero-classes that need no corpus: a quote that restates a linked
question, a duplicate of another claim's quote, and a quote with no content terms.
"""

from __future__ import annotations

import re
from typing import Iterable, Sequence, Tuple

_WORD = re.compile(r"\w+", re.UNICODE)
_STOPWORDS = frozenset(
    "a an and are as at be but by for from has have if in into is it its of on or that the"
    " their then there these this to was were will with".split()
)


def normalize(text: str) -> str:
    """Fold case and punctuation so two quotes compare on their words."""
    return " ".join(_WORD.findall(text.casefold()))


def content_terms(text: str) -> Tuple[str, ...]:
    """Words that carry information, excluding the small English stopword set."""
    return tuple(term for term in _WORD.findall(text.casefold()) if term not in _STOPWORDS)


def restates_question(quote: str, questions: Sequence[str]) -> bool:
    """Whether the quote is a substring of a question it is supposed to answer."""
    normalized = normalize(quote)
    if len(content_terms(quote)) < 2:
        return False
    return any(normalized and normalized in normalize(question) for question in questions)


def duplicate_quote(quote: str, other_quotes: Iterable[str]) -> bool:
    """Whether the same quote already supports another claim in the same program."""
    normalized = normalize(quote)
    return bool(normalized) and any(normalized == normalize(other) for other in other_quotes)


def stopword_only(quote: str) -> bool:
    """Whether the quote has no content terms at all."""
    return not content_terms(quote)


def quote_classes(
    quote: str,
    questions: Sequence[str] = (),
    other_quotes: Iterable[str] = (),
) -> Tuple[str, ...]:
    """Return the stable, additive information classes of one quote."""
    classes = []
    if restates_question(quote, questions):
        classes.append("restates_question")
    if duplicate_quote(quote, other_quotes):
        classes.append("duplicate_quote")
    if stopword_only(quote):
        classes.append("stopword_only")
    return tuple(classes)
