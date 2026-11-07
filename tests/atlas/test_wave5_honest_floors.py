"""Wave-5 regression guards: boxless honesty and quality floors.

Commits e4e7f06 (spatial-recall refuses boxless) and e16cc31
(weakest/floor surfaced) added contract behavior without pinning tests.
"""

import pytest

from domains.atlas import learning, quality


def test_boxless_spatial_refuses_with_text_route():
    analysis = {"entities": [{"id": "e1", "name": "A"}], "relationships": []}
    with pytest.raises(ValueError, match="visual-identification"):
        learning.spatial_recall_challenge(analysis)


def test_weakest_and_floor_surface_weak_artifact():
    deck = {"cards": [{"id": str(i), "entity_id": "e", "kind": "recall",
                       "front": {"text": "q" + str(i)},
                       "back": {"text": "a", "evidence": "ev"}}
                      for i in range(10)]}
    report = quality.quality_report(
        {"entities": [], "relationships": []},
        {"deck": deck, "podcast": "[bad"})
    assert report["flashcards"]["score"] == 100
    assert report["podcast"]["score"] == 0
    assert report["weakest"] == "podcast"
    assert report["floor"] is False
