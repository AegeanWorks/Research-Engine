# Research Engine — Rust implementation

This crate is the complete Research Engine. The Python runtime and its parity scripts were
removed under ADR-064; every command and capability is implemented here. The engine writes a
schema-14 SQLite graph and exposes one CLI.

## Build and test

The crate pins the GNU toolchain because this workspace has no MSVC linker:

```bash
cd rust
cargo build
cargo test
```

`rust-toolchain.toml` and `.cargo/config.toml` select `stable-x86_64-pc-windows-gnu` and `gcc`;
`Cargo.lock` pins every dependency. Declared dependencies: `rusqlite` (bundled SQLite), `clap`,
`chrono`, `serde_json`, `regex`, `sha1`, `sha2`, `unicode-normalization` (NFKD title folding).

Run the binary through the project launchers (`research-engine` / `research-engine.cmd`) or
directly:

```bash
target/x86_64-pc-windows-gnu/debug/research-engine.exe --db research.db init
target/x86_64-pc-windows-gnu/debug/research-engine.exe --db research.db demo
target/x86_64-pc-windows-gnu/debug/research-engine.exe --db research.db check
```

`--json` is a global flag and must precede the subcommand.

## Command surface

The lifecycle is one CLI: `research`, `question`, `source` (including `prisma` and `duplicates`),
`protocol`, `observation`, `claim` (including `revise` and `merge`), `hypothesis` (including `card`
and `amend`), `test`, `cascade`, `analysis` (including `plan` and `stats-all`), `db`, `events`,
`diff`, `scorecard`, `ai`, `experiment`, `search`, `report`, `outline`, `brief`, `export`, `init`,
`demo`, `check` and `inventory`.

`run` is the unified capability surface:

```bash
research-engine run analyze --input graph.json
research-engine run execute <capability> --input '{"text": "..."}'
```

### `run execute` capabilities

`CAPABILITIES` in `src/engine.rs` is the closed vocabulary:

| Subsystem | Capabilities | Source |
|---|---|---|
| `catalog` | `catalog.normalize`, `catalog.study-type`, `catalog.paper-id`, `catalog.normalize-doi`, `catalog.normalize-title` | `lattice.rs`, `runtime_sources.rs` |
| `candidate` | `candidate.rules`, `candidate.screen`, `candidate.noael-hed` | `engine_rules.rs`, `engine_screen.rs`, `engine_safety.rs` |
| `bridge` | `bridge.primitives` | `engine_bridge.rs` |
| `corpus` | `corpus.citations`, `corpus.duplicates` | `engine_corpus.rs`, `runtime_sources.rs` |

Old capability names (`pnn-rules`, `fluid-bridge`, `obezite-atiflar`) remain aliases.

## Subsystem layout

- `core.rs`, `db.rs`, `migrations.rs` — schema, transactions and the shared graph.
- `integrity.rs` — the `check` audit and its finding codes.
- `analysis.rs`, `stats.rs`, `calibration.rs`, `cascade.rs`, `discovery.rs`, `search.rs`,
  `synthesis.rs`, `killtest.rs` — the research mechanics.
- `runtime_claims.rs`, `runtime_hypotheses.rs`, `runtime_plans.rs`, `runtime_screening.rs`,
  `runtime_sources.rs`, `runtime_analysis.rs` — the consolidated runtime behaviours formerly in
  `engine/`.
- `lattice*.rs` — the literature catalog, parsers and discovery providers.
- `engine_*.rs` — the five cohesive domain subsystems behind `run`.
- `ai.rs`, `experiments.rs`, `studio_*.rs` — AI provenance, N1 experiments and studio adapters.

## Verification

`cargo test` builds fresh graphs and checks provenance refusal, append-only verdicts, a verifiable
event ledger, integrity findings and cross-subsystem behaviour. The integration suite in
`tests/parity.rs` also pins the event hash and the schema version. The project gate runs
`cargo test --manifest-path rust/Cargo.toml` followed by the project-scan test.
