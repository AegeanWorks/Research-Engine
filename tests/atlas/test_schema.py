import pytest

from domains.atlas.schema import (BoundingBox, VisualAnalysis, VisualEntity,
                          VisualRelationship, coerce_muse_payload)


def test_bbox_validation():
    with pytest.raises(ValueError):
        BoundingBox(0.5, 0.5, 0.2, 0.8)
    with pytest.raises(ValueError):
        BoundingBox(-0.1, 0, 1, 1)
    b = BoundingBox(0.1, 0.2, 0.5, 0.6)
    assert b.to_grid1000() == [100, 200, 500, 600]
    assert BoundingBox.from_grid1000([100, 200, 500, 600]).to_grid1000() == [100, 200, 500, 600]
    # edge clamp: model may emit 1001 for edge-touching objects
    assert BoundingBox.from_grid1000([0, 0, 1001, 1001]).to_grid1000() == [0, 0, 1000, 1000]


def test_entity_relationship_validation():
    with pytest.raises(ValueError):
        VisualEntity(id="a", name="A", category="nope")
    with pytest.raises(ValueError):
        VisualRelationship(source_id="a", target_id="a", rel_type="inhibits")
    with pytest.raises(ValueError):
        VisualRelationship(source_id="a", target_id="b", rel_type="hugs")


def test_analysis_rejects_dangling_relationship():
    e = VisualEntity(id="a", name="A", category="component",
                     bbox=BoundingBox(0, 0, 0.5, 0.5))
    bad = VisualAnalysis(entities=[e], relationships=[
        VisualRelationship(source_id="a", target_id="ghost", rel_type="activates")])
    assert bad.validate()
    with pytest.raises(ValueError):
        VisualAnalysis.from_dict({"entities": [e.to_dict()],
                                  "relationships": [{"source_id": "a", "target_id": "ghost",
                                                     "rel_type": "activates", "confidence": 1.0}]})


def test_person_place_categories_accepted():
    from domains.atlas.schema import coerce_muse_payload
    a = coerce_muse_payload(
        {"entities": [{"id": "p", "name": "Arkad", "category": "person", "confidence": 0.9},
                      {"id": "l", "name": "Babylon", "category": "place", "confidence": 0.9}],
         "relationships": []})
    assert {e.category for e in a.entities} == {"person", "place"}


def test_coerce_muse_payload():
    payload = {"entities": [
        {"id": "striatum", "name": "Striatum", "category": "anatomical-structure",
         "box": [320, 220, 680, 360], "confidence": 0.9}],
        "relationships": []}
    a = coerce_muse_payload(payload, document_ref="d", source_page=1, figure_id="f")
    assert a.entities[0].bbox.to_grid1000() == [320, 220, 680, 360]
    assert a.entities[0].model_inferred is True
