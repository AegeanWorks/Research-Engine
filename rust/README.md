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
`serde_json`, `sha2`.

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
| Lattice discovery | Offline seed-corpus provider, candidate de-duplication, provider registry and Crossref/OpenAlex helper parsers (`discovery` CLI) |
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

## Still to port

the network-backed lattice providers (arXiv, Crossref, OpenAlex, EuropePMC),
studio, domains and the Python CLI text renderer. These remain served by their
Python entry points until their Rust equivalents land; the SQLite graph is
shared throughout.
