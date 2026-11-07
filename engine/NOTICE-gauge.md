# Ported gauge notice

- Source: `projects/gauge`, committed HEAD `e275cfbd3654d1b879efeae9e836c69ee9f2a7b3`.
- License: Aegean License 1.1 (`LicenseRef-AL-1.1`), compatible with the host ASL-1.1.
- Ported: `gauge/series.py` -> `engine/series.py`; `gauge/render.py` -> `engine/charts.py`;
  `tests/test_series.py` and `tests/test_render.py` -> host tests.
- Modifications: module path `gauge.series` -> `engine.series`; no behaviour change.
- The source project stays active and is never modified by the host.
