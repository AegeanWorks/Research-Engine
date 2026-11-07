"""Stage 3 swarm fixes — failing-first guards for verified true findings.

Each test traces to a reproduced defect from the analysis swarms.
Run: python -m pytest tests/test_stage3_swarm_fixes.py -q -p no:cacheprovider
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_sam_disclosure_exists():
    from domains.atlas.config import AtlasConfig
    from domains.atlas.sam_provider import SamProvider

    p = SamProvider(AtlasConfig(api_key="t"), transport=lambda x: {"raw": ""})
    assert hasattr(p, "disclosure"), "SamProvider.disclosure unreachable (nested in _scan_file_id)"
    assert "figure crop" in p.disclosure().lower()


def test_cache_key_no_concat_collision():
    from domains.atlas.store import AtlasStore

    assert AtlasStore.cache_key("ab", "c") != AtlasStore.cache_key("a", "bc")


def test_trim_text_custom_limit_message():
    from domains.atlas.sources import trim_text

    out = trim_text("a" * 6000, limit=5000)
    assert out.endswith("[truncated: first 5000 chars of the source]"), out[-80:]


def test_ingestion_allows_text_formats():
    from domains.atlas import ingestion as ing

    for ext in (".docx", ".pptx", ".vtt", ".srt", ".json"):
        assert ext in ing.SUPPORTED_EXTENSIONS, f"{ext} missing from SUPPORTED_EXTENSIONS"


def test_parallel_rels_unique_card_ids():
    from domains.atlas import flashcards as fc

    a = {"figure_id": "f", "entities": [{"id": "A", "name": "A"}, {"id": "B", "name": "B"}],
         "relationships": [{"source_id": "A", "target_id": "B", "rel_type": "activates"},
                           {"source_id": "A", "target_id": "B", "rel_type": "inhibits"}]}
    d = fc.build_deck(a)
    ids = [c["id"] for c in d["cards"] if c["kind"] == "relation"]
    assert len(ids) == len(set(ids)) == 2, ids


def test_model3d_quality_sanitized_ids():
    from domains.atlas import models3d as m, quality as q

    a = {"figure_id": "f", "entities": [
        {"id": "a.b", "name": "AB", "category": "other",
         "bbox": {"x_min": 0.1, "y_min": 0.1, "x_max": 0.3, "y_max": 0.3}}],
        "relationships": []}
    obj = m.export_obj(a)
    check = q.model3d_quality(obj, a)["checks"][0]
    assert check["ok"], check
