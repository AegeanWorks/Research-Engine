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

## Verification

- `cargo test --manifest-path rust/Cargo.toml` — all engine tests pass.
- `python -m unittest discover -s tests -t .` — host compatibility suite passes.
- `research-engine run analyze --input …` — one integrated report from the facade.
