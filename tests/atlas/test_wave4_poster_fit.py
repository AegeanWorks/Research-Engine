"""Wave-4 regression guard: poster vertical centering holds the frame.

Commit 5375fd3 added _fit_frame without a pinning test. Locks
translate-only centering, relative-offset preservation, and clamping.
"""

from domains.atlas import materials as mat


def test_top_heavy_content_centers():
    rects = {"e1": (100, 90, 90, 44), "e2": (200, 110, 90, 44)}
    out = mat._fit_frame(rects)
    assert out["e2"][1] - out["e1"][1] == 20
    top, bottom = 72.0, 640 - 34
    assert all(top <= y <= bottom - h for (_, y, _, h) in out.values())
    assert min(y for (_, y, _, _) in out.values()) > 90


def test_empty_is_noop():
    assert mat._fit_frame({}) == {}


def test_clamp_holds_frame():
    rects = {"e1": (100, 72, 90, 44), "e2": (200, 600 - 44, 90, 44)}
    out = mat._fit_frame(rects)
    top, bottom = 72.0, 640 - 34
    assert all(top <= y <= bottom - h for (_, y, _, h) in out.values())
