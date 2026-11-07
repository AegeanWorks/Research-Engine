# Projects folder scan: what is worth implementing

Date: 2026-11-08  
Scope: **all 55 top-level directories** under `projects/` plus the **11 projects under
`projects/archive/`** (66 directories). 47 top-level projects contain Python outside dependency
folders; 8 are JavaScript/TypeScript/C++/docs-only. The first pass ranked Python-bearing projects
by AST public definitions and keyword hits; the appendix below records every directory, including
the non-Python and archived ones.

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
| 9 | ModelDuck | 62 | 1,225 | model harness; Python count is vendored `node_modules`, not project code |
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

## Appendix: every project directory

All 55 top-level directories plus the 11 projects under `archive/` are listed. Decisions are
explicit so no directory is silently skipped.

| Project | Files | Python | Source type | Decision |
|---|---:|---:|---|---|
| `aegean-licensing` | 151 | 36 | Python + .md:75 | reviewed — licensing texts/validator, not a research primitive |
| `aegean-licensing-ops` | 86 | 54 | Python + .md:12 | reviewed — licensing operations, not research |
| `aegean-tge` | 393 | 1 | Python + .md:203, .obj:64 | out of scope — C++ inference engine |
| `AegeanWorks` | 683 | 29 | Python + .webp:197, .js:155 | out of scope — portfolio site |
| `afterimage` | 43 | 1 | Python + .png:10, .md:7 | out of scope — browser perception game |
| `archive` | 611 | 106 | Python + .md:128 | archive/read-only — subtree listed below |
| `article-writer` | 338 | 66 | Python + .md:79, .png:72 | reviewed — writing workspace, not a reusable research primitive |
| `assay` | 75 | 23 | Python + .md:25 | reviewed — audit pack; host already has hash-chain events + manifests |
| `Atlas` | 1601 | 59 | Python + .png:1431 | merged |
| `brain` | 144 | 122 | Python + .json:8 | reviewed — agent memory substrate, not a research primitive |
| `cairn` | 77 | 41 | Python + .md:9 | out of scope — compiler/language |
| `chatduck` | 38 | 0 | .js:10, .json:6, .md:4 | out of scope — browser chat UI |
| `chronos` | 45 | 15 | Python + .md:15 | out of scope — focus/session scheduler |
| `crucible` | 459 | 33 | Python + .json:302, .md:42 | out of scope — model weight tuning |
| `crypt-crawler` | 890 | 54 | Python + .png:678, .md:55 | out of scope — game |
| `cyberpulse` | 180 | 70 | Python + .md:47 | out of scope — game |
| `driftwood` | 39 | 14 | Python + .md:10 | reviewed — git hotspot ranking, not evidence |
| `dupefinder` | 36 | 11 | Python + .md:10 | reviewed — file dedupe; host has source dedupe |
| `dustline` | 289 | 30 | Python + .png:206 | out of scope — game |
| `fluid-universe` | 2094 | 210 | Python + (none):1671 | merged |
| `foundry` | 24 | 9 | Python + .json:7 | out of scope — game content pipeline |
| `gauge` | 43 | 10 | Python + .md:17 | ported — `engine/series.py` + `engine/charts.py` |
| `harness` | 127 | 43 | Python + .json:21 | out of scope — agent test harness |
| `iris` | 51 | 0 | .js:14, .md:7, .json:6 | out of scope — browser puzzle |
| `keystone` | 161 | 130 | Python + .md:7 | out of scope — 3D game engine |
| `lacon` | 54 | 23 | Python + .md:15 | reviewed — compressed reasoning, not a research primitive |
| `lattice` | 102 | 50 | Python + .md:30 | merged |
| `MemoryReconstruction` | 793 | 4 | Python + .png:576, .ts:93 | out of scope — game |
| `meridian` | 49 | 0 | .js:18, .json:6, .png:5 | out of scope — timezone planner |
| `merklock` | 109 | 44 | Python + .md:41 | reviewed — chain; host has hash-chain ledger |
| `mnemo` | 51 | 18 | Python + .md:18 | reviewed — spaced repetition; Atlas pack has study cards |
| `modelduck` | 234 | 0 | .js:106, .mjs:36, .png:32 | out of scope — model server/tuner |
| `muse` | 99 | 35 | Python + .json:26 | out of scope — music generation |
| `NeuralBeat` | 172 | 17 | Python + .md:93, .json:48 | out of scope — documentation/media |
| `NeuralDeck` | 91 | 32 | Python + .md:34 | out of scope — presentation tool |
| `neurocore` | 626 | 379 | Python + .json:69 | consumer app — not a source library |
| `NeuroOptic` | 37 | 3 | Python + .md:16, .json:6 | reviewed — brainwave domain app, not a primitive |
| `NobetWizard` | 33 | 12 | Python + .md:5 | out of scope — duty roster |
| `noesis` | 845 | 9 | Python + .json:158, .xml:146 | reviewed — evidence-table schema; host claims/observations are stronger |
| `nomoreclutter` | 143 | 41 | Python + .md:29 | out of scope — desktop file organizer |
| `obezite-mekanizma-projesi` | 3614 | 154 | Python + .md:1625, .xpt:1535 | merged |
| `orrery` | 93 | 28 | Python + .md:25 | reviewed — N-body sandbox; domain simulation |
| `palette` | 59 | 0 | .js:28, .json:6, .png:5 | out of scope — image editor |
| `pebble` | 70 | 21 | Python + .md:27 | out of scope — toy language |
| `photo-harbor` | 147 | 63 | Python + .class:27 | out of scope — photo server |
| `PNN` | 569 | 53 | Python + .csv:314, .json:126 | merged |
| `pocket-planner` | 19 | 2 | Python + .md:5, .json:3 | out of scope — task manager |
| `primordia` | 100 | 26 | Python + .png:37 | reviewed — evolution sandbox; domain simulation |
| `prism-relay` | 174 | 0 | .png:82, .json:33, .md:22 | out of scope — game |
| `research-engine` | 691 | 413 | Python + .csv:203 | host |
| `shooter` | 93 | 25 | Python + .json:39 | out of scope — game |
| `tally` | 47 | 13 | Python + .md:19 | out of scope — expense ledger |
| `tessera` | 53 | 0 | .js:22, .md:5, .json:5 | out of scope — pattern studio |
| `voidfarer` | 1761 | 158 | Python + .png:640, .md:515 | out of scope — game |
| `weft` | 77 | 0 | .png:22, .js:18, .md:7 | out of scope — game |
| `archive/aldervale` | 231 | 31 | Python + .png:78, .txt:58 | archived game; read-only |
| `archive/capability-showcase` | 19 | 2 | Python + .md:5, .json:3 | archived showcase; read-only |
| `archive/compat-sample-headless` | 28 | 4 | Python + .json:8, .md:5 | archived compat sample; read-only |
| `archive/compat-sample-ui` | 31 | 4 | Python + .json:9, .md:5 | archived compat sample; read-only |
| `archive/fold` | 63 | 17 | Python + .md:14 | archived game; read-only |
| `archive/iris` | 51 | 0 | .js:14, .md:7, .json:6 | archived browser puzzle; read-only |
| `archive/lattice` | 102 | 50 | Python + .md:30 | archived copy of the merged lattice; source already reviewed |
| `archive/N1-Engine` | 77 | 30 | Python + .md:25 | archived copy of the merged N1-Engine; source already reviewed |
| `archive/NeurologyClinicTemplates-TR` | 41 | 1 | Python + .md:16, .txt:14 | archived clinical templates; no code primitive |
| `archive/tempo` | 65 | 17 | Python + .md:20 | archived focus timer; read-only |
| `archive/ui-sandbox` | 56 | 0 | .md:16, .json:8, .mjs:8 | archived UI sandbox; read-only |
