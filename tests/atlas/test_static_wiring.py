"""Static UI wiring: every element id the workspace JS touches must exist in HTML.

Catches the classic single-page-app rot where a renamed id silently kills a
button handler with no test failure. No browser needed.
"""
import os
import re

STATIC = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "domains", "atlas", "static")


def test_every_js_referenced_id_exists_in_html():
    with open(os.path.join(STATIC, "index.html"), encoding="utf-8") as fh:
        html = fh.read()
    with open(os.path.join(STATIC, "app.js"), encoding="utf-8") as fh:
        js = fh.read()
    html_ids = set(re.findall(r'id="([\w-]+)"', html))
    js_refs = set(re.findall(r'\$\("([\w-]+)"\)', js))
    js_refs |= set(re.findall(r"getElementById\('([\w-]+)'\)", js))
    assert js_refs, "no DOM references found - regex drift?"
    missing = [i for i in js_refs if i not in html_ids]
    assert not missing, f"JS touches ids missing from HTML: {missing}"
    all_ids = re.findall(r'id="([\w-]+)"', html)
    dupes = sorted({i for i in all_ids if all_ids.count(i) > 1})
    assert not dupes, f"duplicate element ids (getElementById would misbehave): {dupes}"


def test_static_assets_referenced_exist():
    with open(os.path.join(STATIC, "index.html"), encoding="utf-8") as fh:
        html = fh.read()
    for asset in re.findall(r'(?:src|href)="(/(?:static/)?[\w.\-/]+)"', html):
        if asset.startswith(("http", "#")):
            continue
        local = asset.replace("/static/", "")
        assert os.path.isfile(os.path.join(STATIC, local)), asset
