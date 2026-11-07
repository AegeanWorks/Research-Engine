# Projects folder scan: what is worth implementing

Date: 2026-11-08  
Scope: every directory under `projects/` that contains Python files (50 projects). The scan used
an AST inventory of public functions/classes plus keyword hits for evidence, claims, experiments,
statistics, audit, research, knowledge graph, reporting, schema and export.

## Ranked candidates

| Rank | Project | Score | Public defs | Read |
|---:|---|---:|---:|---|
| 1 | research-engine | 805 | 1,736 | host itself |
| 2 | NeuroCore | 498 | 3,024 | consumer app; not a source library |
| 3 | fluid-universe | 220 | 1,085 | already merged |
| 4 | lattice | 200 | 180 | already merged |
| 5 | VoidFarer | 99 | 653 | game; not research |
| 6 | Keystone | 81 | 360 | 3D game engine; not research |
| 7 | Brain | 75 | 269 | memory service; not a research primitive |
| 8 | Atlas | 63 | 259 | already merged |
| 9 | ModelDuck | 62 | 1,225 | model benchmark harness; not research |
| 10 | Merklock | 58 | 264 | blockchain; hash-chain ideas already in host |
| 11 | aegean-licensing-ops | 51 | 196 | licensing operations; not research |
| 12 | Cairn | 51 | 137 | compiler; not research |
| 13 | PNN | 51 | 223 | already merged |
| 14 | article-writer | 36 | 198 | writing UI; not a research primitive |
| 15 | N1-Engine | 38 | 62 | already merged |
| 16 | pebble | 28 | 37 | toy language; not research |
| 17 | obezite | 26 | 380 | already merged |
| 18 | **gauge** | 10 | 27 | **numeric series summaries and charts** |
| 19 | assay | 24 | 69 | audit evidence pack; host already has hash-chained events + manifests |
| 20 | harness | 21 | 91 | sandboxed agent harness; not research |

Full scan JSON was produced by `C:\Users\Yunus-Emre\AppData\Local\Temp\scan_projects.py`; the
project list and counts are reproducible from the AST.

## Decision

Only **gauge** adds a reusable primitive that the host does not already have: numerical series
parsing, robust summaries, percentiles, histograms, box plots and terminal charts. It is
standard-library-only and AL-1.1, so it was ported:

- `projects/gauge/gauge/series.py` -> `engine/series.py`
- `projects/gauge/gauge/render.py` -> `engine/charts.py`
- `tests/test_series.py`, `tests/test_render.py` -> `tests/test_series.py`, `tests/test_charts.py`
- source SHA `e275cfbd3654d1b879efeae9e836c69ee9f2a7b3`
- notice: `engine/NOTICE-gauge.md`

## Why the others were not ported

- **VoidFarer, Keystone, Shooter**: games/3D engines; no lifecycle or research primitive.
- **Cairn, Pebble**: languages/compilers; not research analysis.
- **Merklock, aegean-licensing, aegean-tms**: chain/licensing operations.
- **Brain, mnemo, lacon, noesis**: memory, spaced repetition, compressed reasoning and a small
  evidence schema; the host already has stronger claims, observations, hypotheses and reports.
- **ModelDuck, crucible, harness**: model training/benchmark harnesses, not evidence functions.
- **article-writer, photo-harbor, tally, chronos, dupefinder**: writing, media, finance, scheduling
  and duplicate files; useful in their own projects, not in the research lifecycle.
- **Assay**: closest candidate, but the host already has a hash-chained event ledger, atomic
  export with a self-check digest and report manifests with content/graph digests. Porting Assay
  would duplicate those with a second record model.

## Gauge evidence

```text
python -m unittest tests.test_series tests.test_charts -q
Ran 71 tests in 0.005s
OK
```

The port keeps the source contracts: nearest-rank percentiles, population standard deviation,
right-open histogram bins with a closed last bin, flat-series special cases, overflow-safe
summaries, sparkline resampling, signed bar charts and box-plot rendering.
