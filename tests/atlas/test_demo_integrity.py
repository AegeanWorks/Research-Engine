"""Demo-data integrity: every committed real analysis and artifact stays valid.

The demo/real_analyses folder is Atlas's proof on real materials. This test
pins it: hand-authored and live analyses validate, TSVs stay Anki-shaped,
SVGs parse, OBJs keep the cuboid invariant, and every analysis has a report.
"""
import glob
import json
import os
import xml.etree.ElementTree as ET

import pytest

from domains.atlas.schema import VisualAnalysis

DEMO = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "domains", "atlas", "demo", "real_analyses")

pytestmark = pytest.mark.skipif(
    not os.path.isdir(DEMO),
    reason="source demo corpus stays external",
)


def _load(name):
    with open(os.path.join(DEMO, name), encoding="utf-8") as fh:
        return json.load(fh)


def test_all_committed_analyses_validate():
    files = sorted(glob.glob(os.path.join(DEMO, "*_manual.json"))
                   + glob.glob(os.path.join(DEMO, "*_live.json")))
    assert len(files) >= 6, "hand + live analyses must ship with the repo"
    for path in files:
        with open(path, encoding="utf-8") as fh:
            raw = json.load(fh)
        assert VisualAnalysis.from_dict(raw).validate() == []
        assert raw["analysis_version"].startswith("domains.atlas.visual-knowledge/")


def test_tsvs_are_anki_shaped():
    for path in sorted(glob.glob(os.path.join(DEMO, "*.tsv"))):
        with open(path, encoding="utf-8") as fh:
            rows = fh.read().strip().split("\n")
        assert rows, path
        assert all(r.count("\t") == 1 for r in rows), path


def test_svgs_parse_and_objs_hold_cuboid_invariant():
    for path in sorted(glob.glob(os.path.join(DEMO, "*.svg"))):
        ET.parse(path)
    for path in sorted(glob.glob(os.path.join(DEMO, "*.obj"))):
        with open(path, encoding="utf-8") as fh:
            lines = fh.read().splitlines()
        v = sum(1 for l in lines if l.startswith("v "))
        f = sum(1 for l in lines if l.startswith("f "))
        g = sum(1 for l in lines if l.startswith("g "))
        assert v == 8 * g and f == 6 * g, path


def test_report_covers_every_committed_analysis():
    with open(os.path.join(DEMO, "REPORT.md"), encoding="utf-8") as fh:
        report = fh.read()
    for name in ["mito-frame-manual", "methionine-cycle-manual",
                 "petechial-rash-manual", "richest-babylon-book"]:
        assert name in report, name
