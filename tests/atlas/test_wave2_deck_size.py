"""Wave-2 regression guard: unreviewably large decks flag but don't block.

Commit cdd8c7c added deck-size-sane without a pinning test. Locks the
300-card threshold and flag-not-block scoring.
"""

from domains.atlas import quality


def _cards(n):
    return [{"id": str(i), "entity_id": "e", "kind": "recall",
             "front": {"text": "q" + str(i)},
             "back": {"text": "a", "evidence": "ev"}} for i in range(n)]


def test_large_deck_flags_but_scores_75():
    r = quality.flashcard_quality(
        {"cards": _cards(321)}, {"entities": [], "relationships": []})
    assert r["score"] == 75
    assert any(c["name"] == "deck-size-sane" and not c["ok"]
               for c in r["checks"])


def test_small_deck_stays_100():
    r = quality.flashcard_quality(
        {"cards": _cards(10)}, {"entities": [], "relationships": []})
    assert r["score"] == 100
