# Source inventory and immutable pins

Merge branch: `merge/research-functions`
Host baseline: `563f27a0a1fb7bbc4093a86b934e5ac66c6961dc` (`master`, before the branch)
Capture date: 2026-11-07

## Copy rule

Only committed `HEAD` is imported. A source worktree is never edited, moved, tagged, archived or
deleted. PNN and obezite-mekanizma-projesi are treated as projects with possible in-flight work, so
their working-tree files are never read into the host; the pins below are the only authority.
Every copied file records its source path and SHA in `docs/merge/PROVENANCE.md` when it lands.

## Pins

| Source | Committed HEAD | Worktree at capture | License | Python files | Python LOC | Source test command |
|---|---|---|---|---:|---:|---|
| lattice | `d3f0502b99983f1436fe9466f5553935ea7be868` | clean | AL-1.1 | 23 | 11,067 | `python -m unittest discover` |
| N1-Engine | `f2c488695b8c00b224e851cd6aa17eaee4e6960a` | clean | AL-1.1 | 21 | 2,529 | `python -m pytest tests -q` |
| fluid-universe | `7b4efe141dfbcc267b0efceb82247f5004186c06` | clean | ASL-1.1 | 137 | 26,922 | `python -m pytest -q` |
| PNN | `3b6e6c277552dcb2c3604483de1277307bc18c4d` | clean | ASL-1.1 | 27 | 9,801 | `python -m unittest discover -s tests -t .` |
| obezite-mekanizma-projesi | `18b5d4d8e2196384f4e960f01b3031beb0a6315a` | clean at capture; advanced to `6776125…` (clean) with its own work during the merge. The host pin stays `18b5d4d8…`; every copied file was re-read from that commit. | ASL-1.1 | 9 | 1,319 | `python -m unittest discover -s tests -v` |
| Atlas | `f3cd7470e99683bc95b05f49e404bb00bffa2663` | clean | AL-1.1 | 20 | 4,855 | `python -m pytest tests -q` |
| research-engine (host) | `563f27a0a1fb7bbc4093a86b934e5ac66c6961dc` | clean | ASL-1.1 | 40 | 11,088 | `python -m unittest discover -s tests -t .` |

`Python LOC` counts non-test `.py` files below the package root for the source and `engine/` for the
host; it is an inventory size, not a quality metric.

## License compatibility

All six sources are AegeanWorks licenses and the host is ASL-1.1:

- lattice, N1-Engine and Atlas carry AL-1.1 (`LicenseRef-AL-1.1`).
- fluid-universe, PNN and obezite-mekanizma-projesi carry ASL-1.1 (`LicenseRef-ASL-1.1`).
- ASL-1.1 is explicitly based on AL-1.1; the host LICENSE names AL-1.1 as its base and resolves a
  conflict in favour of the science terms for non-commercial research.
- The licensor is the same legal person for every source. Copying AL-1.1 code into the ASL-1.1 host
  is therefore a relicensing by the licensor, not a sublicense from a third party.
- Every ported file keeps a `Required Notice:` line and an entry in `REUSE.toml`; the host LICENSE is
  not replaced. Atlas is copied only after this check, and its `atlas.visual-knowledge/v1` schema id
  and source notices travel with the pack.

Evidence: `projects/*/LICENSE` first 12 lines, `projects/research-engine/LICENSE` section 1.5 and
`projects/Atlas/docs/ARCHITECTURE.md`.

## Entry points and data boundaries

| Source | Public entry points | Source data that stays external |
|---|---|---|
| lattice | `lattice.cli`, `lattice.api`, `lattice.client`, `lattice.mcp`, `lattice.web` | `lattice.db` (fixture copy only for migration tests) |
| N1-Engine | `main.core.analysis.AnalysisEngine`, `main.core.models`, `main.cli`/GUI | `main.db` (fixture copy only) |
| fluid-universe | `verification.audit`, `verification.compare`, `verification.fingerprint`, `verification.verify`, `phenomenology.run_all` | `results/`, `verification_*.json` (references/digests only) |
| PNN | `pnn.pipeline`, `pnn.cli`, `pnn.runner`, `pnn.studio` | `output/`, `data/`, `tmp_out/` (references/digests only) |
| obezite-mekanizma-projesi | `08_ARACLAR/uret.py`, `sentez_uret.py`, `atif.py`, ledger tooling | 6.1 GB corpus under `02_LITERATUR/`, `09_SENTEZ/` (references/digests only) |
| Atlas | `atlas.cli`, `atlas.app`, `atlas.ingestion`, `atlas.store`, `atlas.schema` | `data/`, `demo/`, uploaded media (references/digests only) |

## Test-file inventory

| Source | Test files | Notable suites |
|---|---:|---|
| lattice | 23 | discovery, ingest, extraction, synthesis, web, mcp, api, client, snapshots, diff, screening, meta |
| N1-Engine | 4 | baseline-vs-intervention, trends, bootstrap, multiple-comparison warning, schema migration |
| fluid-universe | 73 | verification, compare, physics theory/sims/phenomenology |
| PNN | 23 | pipeline, curation, docking, assay, preclinical, SAR, screening, safety, studio, golden |
| obezite-mekanizma-projesi | 2 | ledger projections and source health |
| Atlas | 31 | ingestion, sources, materials, offline fallback, study pack, quality, contract |

## Branch and rollback

The merge is isolated on `merge/research-functions`. `master` remains at the host baseline; rollback
is `git switch master` and no source repository is touched by that operation.
