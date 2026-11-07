"""Stage 3 batch 2 — failing-first guards for verified deferred findings.

Each test traces to a reproduced defect from the analysis swarms.
Run: python -m pytest tests/test_stage3_batch2_fixes.py -q -p no:cacheprovider
"""
import json
import os
import sys
import threading
import urllib.error
import urllib.request
from http.server import HTTPServer

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_report_uses_supplied_flashcards_alias():
    from domains.atlas import quality as q

    a = {"figure_id": "f",
         "entities": [{"id": "a", "name": "A"}, {"id": "b", "name": "B"}],
         "relationships": []}
    custom = {"figure_id": "f", "cards": [
        {"id": "hl-a", "entity_id": "a", "kind": "identify-highlight",
         "front": {"text": "Which structure is highlighted?"},
         "back": {"text": "A", "evidence": "e"}}]}
    cov = q.quality_report(a, {"flashcards": custom})["flashcards"]["checks"][0]
    assert cov["name"] == "entity-coverage", cov
    assert not cov["ok"], cov  # custom deck covers 1/2, not the rebuilt 2/2


def test_post_invalid_json_reports_parse_error(tmp_path):
    from domains.atlas import app as atlas_app
    from domains.atlas.config import AtlasConfig

    atlas_app.Handler.store = None
    atlas_app.Handler.config = AtlasConfig.from_env(data_dir=str(tmp_path))
    server = HTTPServer(("127.0.0.1", 0), atlas_app.Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        req = urllib.request.Request(  # noqa: S310
            f"http://127.0.0.1:{port}/api/auto-create",
            data=b"{{{not-json", method="POST",
            headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30):  # noqa: S310
                pytest.fail("expected HTTP 400 for malformed JSON")
        except urllib.error.HTTPError as e:
            assert e.code == 400, e.code
            body = json.loads(e.read().decode("utf-8"))
            assert "invalid json" in body["error"].lower(), body
            assert "missing 'path'" not in body["error"], body
    finally:
        server.shutdown()
        thread.join(timeout=5)
        atlas_app.Handler.store = None


def test_schema_missing_keys_raise_valueerror():
    from domains.atlas.schema import VisualAnalysis, coerce_muse_payload

    with pytest.raises(ValueError):
        coerce_muse_payload({"entities": [{"name": "X", "category": "other",
                                            "confidence": 0.5}],
                             "relationships": []})
    with pytest.raises(ValueError):
        coerce_muse_payload({"entities": [],
                             "relationships": [{"source_id": "a",
                                                "target_id": "b"}]})
    with pytest.raises(ValueError):
        VisualAnalysis.from_dict(
            {"entities": [{"id": "a", "name": "A", "category": "other",
                           "confidence": 0.5, "bbox": {"x_min": 0}}],
             "relationships": []})
    with pytest.raises(ValueError):
        VisualAnalysis.from_dict({"entities": [], "relationships": [],
                                  "source_page": None})
