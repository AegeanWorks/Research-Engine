"""3D export + flashcard decks (0.7.0 slice)."""
import os

from domains.atlas import flashcards as fc
from domains.atlas import models3d as m3d
from domains.atlas.schema import VisualAnalysis
from domains.atlas.demo.basal_ganglia_fixture import FIXTURE_ANALYSIS


def _analysis():
    return VisualAnalysis.from_dict(FIXTURE_ANALYSIS).to_dict()


def test_iso_view_layers_and_skips():
    view = m3d.iso_view(_analysis())
    assert len(view["polygons"]) == 7 and view["skipped"] == []
    layers = [m3d.layer_of(p["category"]) for p in view["polygons"]]
    assert layers == sorted(layers)
    for p in view["polygons"]:
        assert len(p["top"]) == 4 and len(p["base"]) == 4


def test_iso_skips_boxless_entities():
    a = _analysis()
    a["entities"][0]["bbox"] = None
    view = m3d.iso_view(a)
    assert view["skipped"] == [a["entities"][0]["id"]]
    assert len(view["polygons"]) == 6


def test_obj_export_counts_and_groups():
    text = m3d.export_obj(_analysis())
    lines = text.splitlines()
    verts = [l for l in lines if l.startswith("v ")]
    faces = [l for l in lines if l.startswith("f ")]
    groups = [l for l in lines if l.startswith("g ")]
    assert len(verts) == 7 * 8 and len(faces) == 7 * 6 and len(groups) == 7
    assert "striatum" in text


def test_obj_refuses_geometryless_model():
    import pytest
    a = {"figure_id": "t", "entities": [{"id": "x", "name": "X", "category": "process"}],
         "relationships": []}
    with pytest.raises(ValueError, match="no located entities"):
        m3d.export_obj(a)


def test_deck_covers_entities_and_relations(tmp_path):
    deck = fc.build_deck(_analysis())
    kinds = {c["kind"] for c in deck["cards"]}
    assert {"identify-highlight", "identify-description", "relation"} <= kinds
    hl = [c for c in deck["cards"] if c["kind"] == "identify-highlight"]
    assert {c["entity_id"] for c in hl} == {e["id"] for e in _analysis()["entities"]}
    tsv = fc.to_anki_tsv(deck)
    rows = tsv.strip().split("\n")
    assert len(rows) == len(deck["cards"]) and all("\t" in r for r in rows)
    assert "Striatum" in tsv


def test_deck_empty_refuses_anki():
    import pytest
    with pytest.raises(ValueError, match="no cards"):
        fc.to_anki_tsv({"figure_id": "x", "cards": []})


def test_cli_deck_and_obj(tmp_path, capsys):
    from domains.atlas.cli import main
    from domains.atlas.store import AtlasStore
    AtlasStore(str(tmp_path)).save_analysis("bg", _analysis())
    assert main(["--data", str(tmp_path), "deck", "bg"]) == 0
    out = capsys.readouterr().out
    assert "identify-highlight" in out
    tsv = str(tmp_path / "bg.tsv")
    assert main(["--data", str(tmp_path), "deck", "bg", "--anki", tsv]) == 0
    assert os.path.isfile(tsv)
    obj = str(tmp_path / "bg.obj")
    assert main(["--data", str(tmp_path), "obj", "bg", "--out", obj]) == 0
    assert os.path.isfile(obj)


def test_model3d_and_flashcards_endpoints(tmp_path):
    import json
    import threading
    import urllib.request
    import urllib.error
    from http.server import HTTPServer
    from domains.atlas import app as atlas_app
    from domains.atlas.config import AtlasConfig
    from domains.atlas.store import AtlasStore

    AtlasStore(str(tmp_path)).save_analysis("bg", _analysis())
    atlas_app.Handler.store = None
    atlas_app.Handler.config = AtlasConfig.from_env(data_dir=str(tmp_path))
    server = HTTPServer(("127.0.0.1", 0), atlas_app.Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with urllib.request.urlopen(  # noqa: S310
                f"http://127.0.0.1:{port}/api/model3d?figure_id=bg", timeout=10) as r:
            view = json.load(r)
        assert len(view["polygons"]) == 7
        with urllib.request.urlopen(  # noqa: S310
                f"http://127.0.0.1:{port}/api/model3d?figure_id=bg&format=obj",
                timeout=10) as r:
            obj = r.read().decode()
        assert obj.count("\ng ") == 7
        req = urllib.request.Request(f"http://127.0.0.1:{port}/api/flashcards",
                                     data=json.dumps({"analysis": _analysis()}).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as r:  # noqa: S310
            deck = json.load(r)
        assert len(deck["cards"]) > 7
        with urllib.request.urlopen(  # noqa: S310
                f"http://127.0.0.1:{port}/api/flashcards/export?figure_id=bg",
                timeout=10) as r:
            assert r.status == 200 and b"\t" in r.read()
    finally:
        server.shutdown()
        thread.join(timeout=5)
        atlas_app.Handler.store = None
