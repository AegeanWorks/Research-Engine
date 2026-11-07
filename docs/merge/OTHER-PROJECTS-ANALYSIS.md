# Other projects: what is worth implementing

Date: 2026-11-07  
Scope: fluid-universe, PNN, obezite-mekanizma-projesi and Atlas. Lattice and N1-Engine were
reviewed separately (`LATTICE-COMPLETENESS.md`, `N1-COMPLETENESS.md`). These four projects stay
active and are **not** being archived, so the question is what they add to the host rather than
what must be copied for shutdown.

## Source-function result

AST comparison of public functions/classes/methods (basename-normalised where the host adds a
package level):

| Project | Source modules | Source public defs | Host public defs | Missing |
|---|---:|---:|---:|---:|
| fluid-universe | 133 | 681 | 690 | 0 |
| PNN | 26 | 171 | 171 | 0 |
| Atlas | 19 | 94 | 97 | 0 |
| obezite `08_ARACLAR` | 9 | 50 | 50 | 0 |

The 137 Python files under obezite `07_ANALIZ` and 3 under `06_MAKALELER` are one-off NHANES/VA
data pulls and document builders tied to the external corpus. They are not reusable host
functions.

## Worth implementing across all four: external data-root registration

Each project keeps its data outside the host. The host had a pack registry with a `data_root` and
`manifest_sha256`, but no safe way to fingerprint a tree. Added:

- `engine/artifacts.digest_tree(root, suffixes, excluded_dirs)` — streams relative paths and
  bytes into one SHA-256, returning file count and byte count.
- `engine/packs.register_pack_from_tree(...)` — fingerprints an external tree and registers the
  pack in one call.

Tests: `tests/test_packs.py`
- registers a temp external tree and stores its digest;
- changing one file changes the digest;
- an empty tree is refused;
- the data root is stored as a reference, never copied.

Real external roots registered in a temporary host database:

| Pack | Data root | SHA-256 |
|---|---|---|
| fluid_universe | `projects/fluid-universe/results` | `1b8afb04…c1f4` |
| pnn | `projects/PNN/output` | `bce1add0…cf90` |
| atlas | `projects/Atlas/demo/real_analyses` | `0b5ebd6c…1ddc` |
| obezite | `projects/obezite-mekanizma-projesi/02_LITERATUR` | `097b722c…19db` |

## Per-project judgement

| Project | Already merged | Worth adding? | Decision |
|---|---|---|---|
| fluid-universe | audit, fingerprint, compare, theory, phenomenology, sims | generic results-root fingerprint | **yes**, via pack tree registration |
| PNN | pipeline, screening, docking, assay, PK/PD, SAR, reports, studio | output-root fingerprint | **yes**, via pack tree registration |
| obezite | ledger parsing, chunking, projections, citation and operator tools | corpus/ledger-root fingerprint | **yes**, via pack tree registration |
| Atlas | ingestion, materials, study pack, quality, offline fallback, app | media/demo-root fingerprint | **yes**, via pack tree registration |

Nothing else in these four adds a missing host-core function. PNN tier thresholds, fluid audit
checks, Atlas UI panels and obezite cohort regressions are domain-specific and already live in
their packs; lifting them into `engine/` would couple the lifecycle core to one domain.

## Evidence

```text
python C:\Users\Yunus-Emre\AppData\Local\Temp\register_packs.py
fluid_universe 1b8afb04…c1f4  registered
pnn            bce1add0…cf90  registered
atlas          0b5ebd6c…1ddc  registered
obezite        097b722c…19db  registered

python -m unittest tests.test_packs -v
Ran 7 tests
OK
```
