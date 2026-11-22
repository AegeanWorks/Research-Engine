# Research Engine — Rust implementation

This crate is the Rust rewrite of the host lifecycle. It writes the **same
schema-14 SQLite graph** as `engine/`, so a database built by either
implementation is readable by the other, and migration is incremental rather
than a flag day.

## Build and test

The crate pins the GNU toolchain because this workspace has no MSVC linker:

```bash
cd rust
cargo build
cargo test
```

`rust-toolchain.toml` and `.cargo/config.toml` select
`stable-x86_64-pc-windows-gnu` and `gcc`; `Cargo.lock` pins every dependency.
Declared dependencies: `rusqlite` (bundled SQLite), `clap`, `chrono`,
`serde_json`, `regex`, `sha2`.

Run the binary with the same global flags as the Python entry point:

```bash
target/x86_64-pc-windows-gnu/debug/research-engine.exe --db research.db init
target/x86_64-pc-windows-gnu/debug/research-engine.exe --db research.db demo
target/x86_64-pc-windows-gnu/debug/research-engine.exe --db research.db check
```

`--json` is a **global** flag and must precede the subcommand, exactly as
argparse requires in `python -m engine`.

## Ported surface

| Area | Commands / behaviour |
|---|---|
| Storage | schema 14, additive v1→v14 migrations, future-version refusal, WAL + FULL sync, gap-free counters |
| Programs | `research add/list/show`, slug collision handling, counts |
| Sources | `source add/list/status/screen`, closed screening taxonomy, identifier gate |
| Questions | `question add/list/close` |
| Claims | `claim add/list/show/link/link-question/verdict/history`, G-001 provenance gate, append-only verdicts |
| Hypotheses | `hypothesis add/list/outcome`, pre-registration fields |
| Kill tests | `test add/list/run/verify/runs/attempts`, command/input binding, negative control, two agreeing runs, authoritative run group, G-003 NUMERIC gate |
| Cascade | `cascade preview`, `claim invalidate`, `source retract`, preview digests and the 10-record bulk tripwire (G-004/G-005) |
| Synthesis | `report`, `scorecard`, graph-derived consensus and coverage (G-006) |
| Measurements | `protocol add/list/amend`, `observation add/list/void/import-csv`, provenance and group gates, `OBS-001`..`OBS-004` |
| Analysis | `analysis stats`, `trend`, `calibration`, `contradictions`, `matrix`, `keystone`, `expose`, `correlation` with CPython-compatible MT19937 bootstrap, Welch t, Mann-Whitney U, keyword/polarity discovery and comparability gates |
| Views | `outline`, `brief`, `claim context` with exact token-budget packing and pruning |
| Manifests | `report --out/--check/--strict` with schema-3 manifests, license pin, content/graph digests and drift detection |
| Export | `export` JSONL with byte-identical records, `export --check` self-verification |
| AI provenance | `ai sweep/extract/idea/propose-test/draft/artifacts` with hash-only notarization, fixed probe templates and refuse-on-error ingest |
| Diff | `diff` with semantic run-churn collapsing and exact mode |
| Experiments | N1 intervention/metric/event records and baseline-vs-intervention, correlation and multi-metric analysis (`experiment` CLI) |
| Lattice adapter | Identity rules (SHA-1 paper ids, study types, tags, refs) and BibTeX/RIS/CSV/CSL-JSON parsers (`lattice` CLI) |
| Lattice repository | Schema-v2 paper/claim/question/edge graph with duplicate merging, lexical search, stats and detail views (`lattice-repo` CLI, `--db` points at a lattice store) |
| Lattice snapshots | JSONL, BibTeX, GraphML and Cytoscape exports with byte-identical serializers (`lattice-snap` CLI) |
| Meta-analysis | Fixed/DerSimonian-Laird random-effects pooling, Q/I²/τ², Hedges' g study construction and ASCII forest plots (`meta` CLI) |
| Lattice queries | Contradiction detection, bounded outline/search views and GraphRAG context packs (`lattice-query` CLI) |
| Lattice discovery | Offline corpus plus arXiv/Crossref/OpenAlex/EuropePMC URL builders and response parsers with injectable fetchers (`discovery`, `providers` CLI) |
| Studio API | Paper×Question evidence matrix, filtered matrices and per-question evidence grouping (`studio` CLI) |
| Studio MCP | JSON-RPC dispatcher with all 28 tool declarations, resources, prompts and ported tool handlers (`mcp` CLI) |
| Studio web | GET and POST request dispatchers for the UI, overview, matrix bundle, search, literature, exports, mutations and integrity checks (`web` CLI) |
| Studio client | `LatticeClient` facade: tool/resource/prompt schemas, read-only policy and MCP tool calls (`client` CLI) |
| Domains: Atlas | Visual-knowledge schema validation, Muse payload coercion, analysis merging and JSON Schema (`atlas` CLI) |
| Domains: PNN safety | NOAEL→HED conversion, most-sensitive study selection, IND safety thresholds and Markdown report (`pnn-safety` CLI) |
| Domains: fluid bridge | Diffusivity, horizon, Pinney coefficients and bridge paths (`fluid-bridge` CLI) |
| Domains: Frank-Oseen | Linearised director elastic matrix, transverse dispersion, equal-K mode, anisotropy and mode classification (`fluid-frank-oseen` CLI) |
| Domains: vortex core | HO-1 finite-core node probe: pre-registered radius, oscillator width, exact norm, sampled density/phase/velocity, analytic and finite-difference Q (`fluid-vortex-core` CLI) |
| Domains: hydrogen nodes | Hydrogen-2s two-branch split, nodal shell, pi phase slip, radial norm/overlap/peaks, 1s force-balance residuals and 2p loop circulation (`hydrogen-radial` CLI) |
| Domains: topology | Nematic RP² homotopy audit, Z3 extension review and claim-13 Markdown report (`fluid-topology` CLI) |
| Domains: circulant | Hermitian 3×3 circulant algebra: eigenvalues, DFT vectors, Koide Q variants, inverse DFT, mass fit and tau prediction (`fluid-circulant` CLI) |
| Domains: reduction | Wall tension, 2D lower bound, power-tail moment integrability, numeric moment and claim-6b Markdown report (`fluid-reduction` CLI) |
| Domains: variational width | Gaussian Ritz width selection: G-M vs Yasui actions, derivatives, analytic/grid/Newton extrema, Ermakov cross-check and claim-49 scales (`fluid-variational-width` CLI) |
| Domains: obezite | Citation-number extraction with bibliography-noise stripping and claim-row de-duplication (`obezite` CLI) |
| Domains: PNN rules | CNS/property design-rule evaluation and criterion weighting (`pnn-rules` CLI) |
| Domains: PNN docking | Docking-score alias parsing, RMSD/Vina filtering, weighted consensus normalization and per-compound best-target aggregation (`pnn-docking` CLI) |
| Search | deterministic phrase-first lexical `search` with exact snippet/token-budget output |
| Markdown | `sanitize`/`cell`/`estimate_tokens`/`pack` shared with reports and search |
| Integrity | 24 finding codes including `PROV-*`, `EVID-*`, `GRAPH-*`, `GAP-*`, `LEDGER-001` |
| Events | hash-chained event ledger, byte-identical hash algorithm to Python |
| Maintenance | `db integrity`, `db backup`, `events --verify`, `inventory`, `check` |

## Compatibility contracts verified by tests

- `cargo test` builds fresh graphs and checks provenance refusal, append-only
  verdicts, a verifiable ledger and the integrity report.
- The event hash has a Python-generated known-answer vector.
- `code_sha256` for an unchanged `engine/` tree matches Python's
  `provenance.code_sha256()` (`16f01351…` at the time of writing).
- A graph written by the Rust binary passes `python -m engine --db … check`
  with the same findings as the Rust `check`.
- `parity_check.py <db>` compares Rust and Python JSON for `search`,
  `observation list` and `check` on the same graph; all three compare equal.
- `analysis_parity.py <db>` compares `analysis stats` and `analysis trend` JSON;
  both compare equal.
- `views_parity.py <db>` compares `outline`, `brief`, `claim context`, report
  manifests and export verification; digests and checks compare equal.
- `analysis_extra_parity.py <db>` compares the remaining `analysis` commands;
  all seven compare equal.
- `ai_parity.py` copies a base graph and compares all six `ai` commands plus
  `diff`; all seven compare equal.
- `experiments_parity.py` compares the N1 experiment record and analysis CLI
  against the Python `experiments` API; all 34 checks match (floats within 1e-12).
- `lattice_parity.py` compares the lattice identity rules and four bibliography
  parsers against Python; all 11 checks match.
- `lattice_repo_parity.py` compares the schema-v2 repository writes, search,
  detail views and stats against Python; all 8 checks match.
- `lattice_snapshots_parity.py` compares JSONL records, BibTeX, Cytoscape and
  GraphML serialization against Python; all four formats match.
- `meta_parity.py` compares study construction, pooling and forest rendering;
  all five checks match.
- `lattice_query_parity.py` compares contradiction detection, outline, compact
  search and both context-pack formats; all five checks match.
- `discovery_parity.py` compares provider names, offline ranking, ingest,
  de-duplication and the bibliographic helper parsers; all six checks match.
- `studio_api_parity.py` compares the evidence matrix, filtered matrix and
  question evidence against the Python studio facade; all three checks match.
- `mcp_parity.py` compares initialize/ping/list/read/tool-call messages; all
  11 checks match (timestamps normalized).
- `web_parity.py` compares all implemented GET and POST routes including the UI
  page, overview, matrix bundle, exports and mutations; all 16 checks match.
- `client_parity.py` compares schemas, read-only filtering, tool calls and
  resources; all 8 checks match.
- `atlas_parity.py` compares Muse coercion, schema and chunk merging; all three
  checks match.
- `pnn_safety_parity.py` compares safety assessments and the Markdown package;
  both match.
- `fluid_bridge_parity.py` compares the bridge primitives; all four checks match.
- `obezite_parity.py` compares citation extraction and de-duplication outputs;
  all four checks match.
- `pnn_rules_parity.py` compares compound rule verdicts and weights; all four
  checks match.
- `providers_parity.py` compares all four provider URLs and parsed candidates;
  all eight checks match.
- `pnn_docking_parity.py` compares score parsing, default/filtered ranking and
  best-target aggregation; all three checks match.
- `fluid_frank_oseen_parity.py` compares the elastic matrix, dispersion,
  equal-K modes, anisotropy and mode metadata; all twelve checks match.
- `fluid_vortex_core_parity.py` compares the core radius, width, norm, sampled
  density/phase/velocity and both Q estimators; all sixteen checks match.
- `hydrogen_radial_parity.py` compares both radial curves, the branch split,
  norm/overlap/peaks, balance residuals, circulation and the full scales bundle;
  all twelve checks match.
- `fluid_topology_parity.py` compares the homotopy audit and rendered Markdown;
  all five checks match.
- `fluid_circulant_parity.py` compares the matrix, spectra, DFT vectors, all Q
  variants, inverse DFT, mass fit and tau prediction; all ten checks match.
- `fluid_reduction_parity.py` compares tensions, tail integrability, numeric
  moments, verdicts and the Markdown report; all 23 checks match.
- `fluid_variational_width_parity.py` compares actions, derivatives, extrema,
  Ermakov cross-check and the full scales bundle; all 13 checks match.

## Still to port

the remaining fluid-universe/obezite/PNN modules and the Python CLI text
renderer. These remain served by their Python entry points; the SQLite graph
is shared throughout.
