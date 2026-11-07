"""CLI video regression: `video` must render (or refuse honestly), never NameError.

Stage-4 check caught `cmd_video` using `tempfile` with no import, which no
test exercised because every other command imports it locally. This pins the
whole command end to end on an offline model.
"""
import argparse
import json
import os

from domains.atlas import cli as atlas_cli
from domains.atlas.schema import VisualAnalysis
from domains.atlas.store import AtlasStore
from domains.atlas.demo.basal_ganglia_fixture import FIXTURE_ANALYSIS


def _save(tmp_path, figure_id="vid-fig"):
    data = VisualAnalysis.from_dict(FIXTURE_ANALYSIS).to_dict()
    AtlasStore(str(tmp_path)).save_analysis(figure_id, data)
    return figure_id


def test_video_renders_offline_model(tmp_path):
    fid = _save(tmp_path)
    out = str(tmp_path / "study.mp4")
    args = argparse.Namespace(data=str(tmp_path), figure_id=fid, out=out)
    assert atlas_cli.cmd_video(args) == 0
    assert os.path.isfile(out) and os.path.getsize(out) > 0


def test_video_unknown_figure_id_refuses_honestly(tmp_path, capsys):
    args = argparse.Namespace(data=str(tmp_path), figure_id="nope", out="")
    assert atlas_cli.cmd_video(args) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert "nope" in payload["error"]
