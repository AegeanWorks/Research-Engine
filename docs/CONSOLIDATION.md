# Consolidation: one cohesive research engine

## Why

The merge of six source projects added their entire Python surfaces under
`adapters/` and `domains/`. Porting every function one-for-one into Rust made the
runtime a collection of independent namespaces rather than one engine. This
document records the deliberate narrowing.

## Important parts kept

The cohesive engine is the schema-14 evidence graph and its lifecycle rules:

- provenance-backed claims, pre-registered hypotheses and executable kill tests;
- append-only verdicts, cascades and hash-chained events;
- bounded views, reports and manifests;
- offline literature discovery plus the shared lattice graph;
- one facade (`rust/src/engine.rs`, CLI `research-engine run analyze`) that composes
  the domain capabilities that answer research questions: design-rule screening,
  safety qualification and the fluid/Gaussian bridge primitives.

The facade is intentionally small: it selects capabilities by the question they
answer, not by the source project they came from.

## Not kept as a separate engine

The standalone `fluid-universe` checkout was merged completely: the source audit
(`docs/merge/OTHER-PROJECTS-ANALYSIS.md`) records 681 source public definitions
and 0 missing host definitions. Its results remain reachable as an external data
root through the pack registry; the data itself was never copied into the host.
Keeping a second copy of the same project alongside the host is the duplication
this consolidation removes.

## Deletion record

`projects/fluid-universe` was removed from the workspace on 2026-11-23 after the
parity evidence was committed. The removal is recoverable from
`C:\Users\Yunus-Emre\AppData\Local\Temp\opencode\removed-projects\fluid-universe-20261123-221119`.
No host test imports the standalone checkout: the only references are string
fixtures and an optional external data-root reference.

The wholesale copies inside the host were removed in the same step:
`domains/{pnn,fluid_universe,obezite,atlas}`, `adapters/lattice` and the test
directories that only exercised those copies. Their capabilities remain in the
canonical Rust engine, exposed through the single `research-engine run` entry
point; 50 per-module CLI namespaces were retired from `Commands`, leaving the
lifecycle commands and `run analyze` / `run execute`.

The remaining imported-surface CLI namespaces (`lattice`, `lattice-repo`,
`lattice-snap`, `lattice-query`, `meta`, `discovery`, `studio`, `atlas`,
`pnn-safety`, `mcp`, `web`, `client`) were retired in the same way. `run` now
carries eight capabilities grouped into four subsystems: `catalog.*` (literature
identity), `candidate.*` (design, screen, safety), `bridge.primitives` and
`corpus.citations`. The standalone `obezite-mekanizma-projesi` checkout was
removed from the workspace; it was fully merged and referenced only by string
fixtures.

The Rust implementation was collapsed to match: 47 unreachable `domains_*`
modules and their tests were deleted, and the five retained ones became
`engine_bridge`, `engine_corpus`, `engine_rules`, `engine_safety` and
`engine_screen`. With `lattice.rs` (catalog), they are the only domain
implementation behind `run execute`.

The removed test directories, Python trees and obezite checkout are preserved
under `C:\Users\Yunus-Emre\AppData\Local\Temp\opencode\removed-from-host-20261123`.

## Verification

- `cargo test --manifest-path rust/Cargo.toml` — all engine tests pass.
- `python -m unittest discover -s tests -t .` — host compatibility suite passes.
- `research-engine run analyze --input …` — one integrated report from the facade.

## Full Rust conversion (ADR-064)

The last Python runtime was removed after every remaining CLI behaviour was
ported: `claim revise` and `claim merge` (`runtime_claims.rs`), `hypothesis card`
and `hypothesis amend` (`runtime_hypotheses.rs`), `analysis plan`
(`runtime_plans.rs`), `source duplicates` (`runtime_sources.rs`) and
`analysis stats-all` (`runtime_analysis.rs`). Each was checked against the Python
implementation before its Python source was archived.

`engine/`, `studio/`, `experiments/`, the Python test suite and the dev-only parity
scripts are preserved under
`C:\Users\Yunus-Emre\AppData\Local\Temp\opencode\removed-python-runtime-20261124`.
Only `tests/test_projects_scan.py` remains in Python because it validates the
project-scan document rather than the runtime. The project gate now runs the Rust
suite followed by that single test.

## Integrity parity (ADR-065)

A follow-up audit found that the Rust `check` command was still missing eleven
finding codes from the Python integrity audit. All are now implemented in
`rust/src/integrity.rs`: duplicate claim text and source identity, empty
programs, hypothesis chronology, cross-program edges, a test created after a
failure, information-poor quotes, stale numeric evidence and missing evidence
volumes, and AI provenance. Rust and Python now emit the same 41-code vocabulary.
