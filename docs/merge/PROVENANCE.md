# Ported-code provenance

All copies are from committed `HEAD`; no source worktree was read for PNN/obezite in-flight
changes beyond the pinned commit. Every destination keeps a `NOTICE.md` naming the source,
SHA, license and modifications.

| Host destination | Source | Source SHA | Files | Lines | Modifications |
|---|---|---|---:|---:|---|
| `adapters/lattice/` | `lattice/lattice/*.py`, `tools/ui_inventory.py`, `tools/dogfood.py`, `start.py` | `d3f0502b…e868` | 22 | 6,894 | package path, imports, host roots and dogfood command |
| `studio/` | `lattice/lattice/{web,mcp,api,client}.py` | `d3f0502b…e868` | 5 | 3,472 | package path, imports |
| `experiments/` | N1 `main/core/*` and GUI backend behaviour | `f2c48869…960a` | 9 | 1,478 | reimplemented on stdlib + SQLite, including compatibility and summary surfaces |
| `domains/pnn/` | `PNN/pnn/*.py` + small `data/` fixtures | `3b6e6c27…8c4d` | 27 | 8,580 | package path, pack-local data root |
| `domains/fluid_universe/` | `fluid-universe/{verification,theory,phenomenology,sims}/*.py` | `7b4efe14…6c06` | 139 | 24,142 | package paths, external verification root |
| `domains/obezite/` | `obezite-mekanizma-projesi/08_ARACLAR/*.py` | `18b5d4d8…315a` | 9 | 1,093 | package path, explicit external roots and host output paths, import-safe operator tools |
| `domains/atlas/` | `Atlas/atlas/*.py`, `static/`, `assets/`, two demo modules | `f3cd7470…2663` | 23 | 4,546 | package path, pack-local static root |

## What stayed external

- lattice `lattice.db`: read-only migration source; no copy in the host.
- N1 `main.db`: read-only migration source; no copy in the host.
- fluid `results/`, `verification_*.json`: referenced by SHA-256; no copy.
- PNN `output/`, `tmp_out/`: referenced; only the small `data/` CSV fixtures are copied.
- obezite 6.1 GB corpus and `09_SENTEZ/`: referenced; only the tooling is copied.
- Atlas uploaded media and `demo/real_analyses/`: referenced; the host tests read the sibling
  checkout in place and skip only when it is absent.

## Test provenance

- lattice: all 23 source test modules copied to `tests/lattice/`; 252 tests pass.
- PNN: 21 of 23 source test modules copied to `tests/pnn/` (docs and golden-run suites target
  the source workspace); 219 tests pass.
- fluid: the source suite stays in place (403 tests); the host adds 9 contract tests for
  fingerprint/compare/claims.
- Atlas: all 31 source test modules copied to `tests/atlas/`; 153 pass against the external
  real-analysis corpus and demo videos, with 0 skips; a 4-test unittest contract covers the
  canonical gate.
- N1: PyQt GUI tests stay in the source; host contracts cover models, analysis and migration.
- obezite: source data-dependent projections stay in the source; host contracts use a small
  synthetic ledger fixture.
