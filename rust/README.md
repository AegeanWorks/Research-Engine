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
| Domains: osmotic closure | Fokker-Planck residual with conservative flux, Gaussian/bimodal probes, residual scaling, frozen-drift sigma map and claim-48 scales (`fluid-nelson-closure` CLI) |
| Domains: convergence | Resolution/temporal convergence diagnostics and linear trend projections for the claim-15 scan (`fluid-convergence` CLI) |
| Domains: water analogue | Shallow-water acoustic horizon: sound speed, radial flow, horizon radius, surface gravity, analogue temperature, metric and validity scales (`water-analogue` CLI) |
| Domains: water well | Finite spherical well for the hydrated electron: Born depth, 1s/1p matching roots, transition gaps, inverse depth and full scales bundle (`water-well` CLI) |
| Domains: water electron | Hydrated-electron cavity scale: screened Bohr radius/energy, capillary cavity radius/energy, infinite-well gap and inverse radius (`water-electron` CLI) |
| Domains: water VDE | Two-observable inversion: well depth for VDE binding, cavity radius for the 1.7 eV gap and capillary comparison (`water-vde` CLI) |
| Domains: dispersive water | Full capillary-gravity dispersion, group velocity, horizon wavenumber, dispersive horizon radius and capillary frequency (`water-dispersive` CLI) |
| Domains: two-state Marcus | Classical Marcus FWHM, shared-λ two-state width prediction, observed component ratio and frozen kill thresholds (`two-state-marcus` CLI) |
| Domains: excited fluid | First-excited HO density/wavefunction/quantum pressure, π phase slip at the node, phase-gradient divergence and log-log scaling (`excited-fluid` CLI) |
| Domains: acoustic rays | Outgoing/ingoing radial speeds, horizon separatrix, peeling rate, analytic ray time and RK4 integration (`water-rays` CLI) |
| Domains: vortex hierarchy | Koide Q, geometric/power-law mass spectra, Koide-power bisection and one-parameter hierarchy falsification (`vortex-cascade` CLI) |
| Domains: vortex particles | T(2,n) torus-knot filaments, chord tangents, length, regularized Biot–Savart energy and knot-mass falsification (`vortex-particles` CLI) |
| Domains: observed shape | Citable band-shape comparator data: width-change slopes, Jou–Freeman components/tail and temperature side half-widths (`observed-shape` CLI) |
| Domains: hydrogen vortex | Hydrogen 2p radial function/probability, most-probable radius, azimuthal velocity, circulation, loop integral and angular momentum (`hydrogen-vortex` CLI) |
| Domains: nodal defect | Exact two-branch split of the excited state, phase slip, branch-wise pressure, gradient scaling and the frozen 2p vortex gate (`node-defect` CLI) |
| Domains: water pressure | Surface energy, finite-well total energy, golden-section equilibrium radius, VDE-matched depth and pressure scales (`water-pressure` CLI) |
| Domains: obezite | Citation-number extraction with bibliography-noise stripping and claim-row de-duplication (`obezite` CLI) |
| Domains: PNN rules | CNS/property design-rule evaluation and criterion weighting (`pnn-rules` CLI) |
| Domains: PNN docking | Docking-score alias parsing, RMSD/Vina filtering, weighted consensus normalization and per-compound best-target aggregation (`pnn-docking` CLI) |
| Domains: PNN compounds | Compound CSV header aliasing, numeric validation, charge normalization and duplicate handling (`pnn-compounds` CLI) |
| Domains: PNN screen | Weighted-criterion scoring, A/B/C/Reject tiering, compound ranking and screen summary (`pnn-screen` CLI) |
| Domains: PNN tables | Curated/screen CSV row contracts, optional-field coercion and six-property binning (`pnn-tables` CLI) |
| Domains: PNN curation | Candidate preparation, ID/SMILES deduplication, tier filtering, per-bin caps and global size limits (`pnn-curation` CLI) |
| Domains: PNN reports | Atomic CSV (Python QUOTE_MINIMAL/CRLF), sorted pretty JSON and text report writers (`pnn-reports` CLI) |
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
- `pnn_compounds_parity.py` compares header aliasing, record parsing and
  duplicate rejection; all eleven checks match.
- `pnn_screen_parity.py` compares single-compound evaluation, tier ranking and
  the screen summary; all three checks match.
- `pnn_tables_parity.py` compares property bins, both CSV row contracts and
  the field manifests; all seven checks match.
- `pnn_curation_parity.py` compares candidate preparation, deduplication and
  both curation configurations; all four checks match.
- `pnn_reports_parity.py` compares CSV, JSON and text report bytes plus nested
  directory creation; all four checks match.
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
- `fluid_nelson_closure_parity.py` compares osmotic velocity, FP residual,
  scaling, sigma map, OU/free probes and the scales bundle; all six checks match
  (the log-fit over ~1e-16 error floors uses a documented wider tolerance).
- `fluid_convergence_parity.py` compares scan, temporal and trend diagnostics;
  all four checks match.
- `water_analogue_parity.py` compares horizon scalars, acoustic metric, lab
  scales and validity bundle; all eleven checks match.
- `water_well_parity.py` compares Born depths, well roots, inverse depths,
  minimum depth and the full scales bundle; all seventeen checks match.
- `water_electron_parity.py` compares screened scales, cavity radius/energy,
  well gaps, inverse radii and the scales bundle; all thirteen checks match.
- `water_vde_parity.py` compares binding-depth inversion, cavity solutions and
  the capillary comparison; all seven checks match.
- `water_dispersive_parity.py` compares dispersion, group velocities, horizon
  wavenumbers/radii and capillary frequency; all fifteen checks match.
- `two_state_marcus_parity.py` compares Marcus widths, shared-λ predictions,
  the observed ratio, thresholds and scales; all nine checks match.
- `excited_fluid_parity.py` compares density, wavefunction, regular pressure,
  phase slip/gradient and scaling slope; all seven checks match.
- `water_rays_parity.py` compares ray speeds, peeling rate, analytic time and
  RK4 integration; all nine checks match.
- `vortex_cascade_parity.py` compares Koide Q, both spectra, the power solver
  and the hierarchy verdict; all nine checks match.
- `vortex_particles_parity.py` compares Koide Q, knot lengths, Biot–Savart
  energies and the full mass hypothesis; all six checks match.
- `observed_shape_parity.py` compares width changes, shape evidence, scales and
  side half-width fits; all seven checks match.
- `hydrogen_vortex_parity.py` compares the 2p radial curve, vortex velocities,
  circulation, loop integral and radial norm; all eight checks match.
- `node_defect_parity.py` compares the branch split, pressure match, gradient
  scaling, vortex gate and scales bundle; all five checks match.
- `water_pressure_parity.py` compares surface/total energies, equilibrium
  radii, the VDE-matched depth and scales; all eight checks match (optimizer
  results use a documented 1e-3 relative tolerance vs scipy).

## Still to port

the remaining fluid-universe/obezite/PNN modules and the Python CLI text
renderer. These remain served by their Python entry points; the SQLite graph
is shared throughout.
