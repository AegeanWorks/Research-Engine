"""Stage 3 batch 3 — failing-first guards for verified deferred findings.

Each test traces to a reproduced defect from the analysis swarms.
Run: python -m pytest tests/test_stage3_batch3_fixes.py -q -p no:cacheprovider
"""
import os
import sys
import urllib.error

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_pathway_empty_model_raises():
    from domains.atlas import learning as learn
    from domains.atlas import quality as q

    with pytest.raises(ValueError):
        learn.pathway_tracing_challenge({"entities": [], "relationships": []},
                                        seed=0)
    rep = q.learn_quality({"figure_id": "e", "entities": [],
                           "relationships": []})
    assert isinstance(rep["score"], (int, float))


def test_confidence_rejects_str_and_bool():
    from domains.atlas.schema import (VisualEntity, VisualRelationship,
                              coerce_muse_payload)

    with pytest.raises(ValueError):
        VisualEntity(id="a", name="A", category="other", confidence="0.9")
    with pytest.raises(ValueError):
        VisualEntity(id="a", name="A", category="other", confidence=True)
    with pytest.raises(ValueError):
        VisualRelationship(source_id="a", target_id="b", rel_type="activates",
                           confidence="0.8")
    with pytest.raises(ValueError):
        coerce_muse_payload({"entities": [{"id": "a", "name": "A",
                                            "category": "other",
                                            "confidence": "0.9"}],
                             "relationships": []})
    e = VisualEntity(id="a", name="A", category="other", confidence=0.9)
    assert e.confidence == 0.9


def _http_post_cases(monkeypatch, provider_mod, make_provider):
    import urllib.request
    calls = []

    def fail_400(req, timeout=None):
        calls.append(req)
        raise urllib.error.HTTPError(req.full_url, 400, "Bad Request", {}, None)

    monkeypatch.setattr(urllib.request, "urlopen", fail_400)
    monkeypatch.setattr(provider_mod.time, "sleep",
                        lambda s: calls.append(("sleep", s)))
    with pytest.raises(RuntimeError):
        make_provider()._http_post({"ping": 1})
    assert len([c for c in calls if not isinstance(c, tuple)]) == 1, calls
    assert not [c for c in calls if isinstance(c, tuple)], calls

    resets = []

    def flaky(req, timeout=None):
        resets.append(req)
        raise ConnectionResetError("dropped")

    monkeypatch.setattr(urllib.request, "urlopen", flaky)
    sleeps = []
    monkeypatch.setattr(provider_mod.time, "sleep",
                        lambda s: sleeps.append(s))
    with pytest.raises(RuntimeError):
        make_provider()._http_post({"ping": 1})
    assert len(resets) == 3, resets
    assert len(sleeps) == 3, sleeps


def test_http_no_retry_on_400_retries_on_reset_muse(monkeypatch):
    from domains.atlas.config import AtlasConfig
    from domains.atlas import muse_provider as mp

    _http_post_cases(monkeypatch, mp,
                     lambda: mp.MuseProvider(AtlasConfig(api_key="k",
                                                        max_retries=3)))


def test_http_no_retry_on_400_retries_on_reset_sam(monkeypatch):
    from domains.atlas.config import AtlasConfig
    from domains.atlas import sam_provider as sp

    _http_post_cases(monkeypatch, sp,
                     lambda: sp.SamProvider(AtlasConfig(api_key="k",
                                                       max_retries=3)))


def test_markdown_podcast_scored_gracefully():
    from domains.atlas import quality as q

    a = {"figure_id": "f", "entities": [], "relationships": []}
    rep = q.quality_report(a, {"podcast": "# Title\n## HOST -- cold open"})
    assert "podcast" in rep and isinstance(rep["podcast"]["score"],
                                           (int, float))
