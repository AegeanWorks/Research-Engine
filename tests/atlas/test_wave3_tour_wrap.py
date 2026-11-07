"""Wave-3 regression guards: tour duration gate and unbreakable-token split.

Commits a624e55 (tour-duration-sane) and f76a391 (hard-split) added
behavior without pinning tests. Locks the 30-minute flag-not-block
window and the frame-fitting wrap.
"""

from PIL import Image, ImageDraw

from domains.atlas import quality
from domains.atlas import materials as mat


def _valid_tour(n):
    analysis = {"entities": [{"id": "e1", "bbox": {"x_min": 0, "y_min": 0,
                                                   "x_max": 1, "y_max": 1}}],
                "relationships": []}
    tour = {"stops": [{"entity_id": "e1", "observe": "look",
                       "name": "e1", "layer": 0, "connections": [],
                       "camera": "c"} for _ in range(n)]}
    return tour, analysis


def test_long_tour_flags_duration_only():
    tour, analysis = _valid_tour(600)
    r = quality.tour_quality(tour, analysis)
    assert r["score"] == 75
    assert any(c["name"] == "tour-duration-sane" and not c["ok"]
               for c in r["checks"])


def test_short_tour_stays_100():
    tour, analysis = _valid_tour(7)
    r = quality.tour_quality(tour, analysis)
    assert r["score"] == 100


def test_unbreakable_token_splits_to_frame():
    img = Image.new("RGB", (200, 100), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    font, _ = mat._font(16)
    token = "X" * 60
    lines = mat._wrap(draw, token, font, 150.0)
    assert len(lines) > 1
    assert all(draw.textlength(l, font=font) <= 150.0 or len(l) == 1
               for l in lines)
