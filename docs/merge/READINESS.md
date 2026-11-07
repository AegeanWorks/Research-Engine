# Merge readiness report

Date: 2026-11-07  
Branch: `merge/research-functions`  
Host: `projects/research-engine` (ASL-1.1)  
Verdict: **ready for the six research functions to be exercised from the host, with the
deliberate exclusions listed in section 6.**

## 1. What was merged

| Layer | Source | Host destination | Evidence |
|---|---|---|---|
| Lifecycle core | host | `engine/` | 577 host tests before merge; schema v14 |
| Literature adapters | lattice `d3f0502b` | `adapters/lattice/` | 252 ported tests pass |
| Studio surfaces | lattice `d3f0502b` | `studio/` | web, MCP, API, client tests pass |
| Experiments | N1 `f2c48869` | `experiments/` | models, analysis, CSV import tests pass |
| Rigor | fluid-universe `7b4efe14` | `domains/fluid_universe/verification/` | fingerprint/compare/claims tests pass |
| Physics pack | fluid-universe `7b4efe14` | `domains/fluid_universe/{theory,phenomenology,sims}/` | import smoke test passes |
| Drug-discovery pack | PNN `3b6e6c27` | `domains/pnn/` | 219 ported tests pass |
| Claim-ledger pack | obezite `18b5d4d8` | `domains/obezite/` | 7 host contract tests pass |
| Learning pack | Atlas `f3cd7470` | `domains/atlas/` | 148 ported pytest tests pass, 5 skipped |

The source repositories were never stopped, finished, archived, deleted, moved, tagged or
modified. Their pins are in `SOURCE-INVENTORY.md`; copied files and modifications are listed in
`PROVENANCE.md` and each destination's `NOTICE.md`.

## 2. Baseline and post-merge test evidence

Baseline (before any host change) is in `BASELINES.md`:

| Source | Baseline |
|---|---|
| research-engine | 555 tests OK, 94.655s |
| lattice | 252 tests OK, 8.699s |
| N1-Engine | 20 passed, 18.26s |
| fluid-universe | 403 passed, 1807.74s (30:07) |
| PNN | 222 tests OK, 1.980s |
| obezite | 10 tests OK, 5.017s |
| Atlas | 152 passed, 1 skipped, 25.68s |

Post-merge host gate:

```text
python -m unittest discover -s tests -t .
Ran 1086 tests in 162.360s
OK
```

Post-merge Atlas pack gate (pytest tier, because Atlas tests are pytest functions):

```text
python -m pytest tests/atlas -q
148 passed, 5 skipped, 1 warning in 20.37s
```

The 5 skips are the external `demo/real_analyses` corpus; the pack still validates on the
committed small fixture and the source corpus is referenced by digest.

Post-merge source re-checks (sources untouched):

| Source | Current result | Notes |
|---|---|---|
| lattice | 252 tests OK, 4.467s | same SHA |
| N1-Engine | 20 passed, 7.58s | same SHA |
| PNN | 222 tests OK, 1.979s | same SHA |
| Atlas | 152 passed, 1 skipped, 20.80s | same SHA |
| obezite | 10 tests OK, 2.422s | source advanced repeatedly (latest `3ca2e0d…`, clean); host pin `18b5d4d8…` |
| fluid-universe | 403 passed, 1728.43s (28:48) | same SHA, clean |

## 3. Schema and migration

Schema v14 adds:

- `source.arxiv`, `venue`, `abstract`, `tags`, `study_type`;
- `experiment_intervention`, `experiment_metric_definition`, `experiment_metric`,
  `experiment_event`;
- `domain_pack` and `migration_run`.

`engine/migrations.py` inspects a source read-only, hashes the file/tree, and applies rows in one
transaction. A second apply of the same `(source, source_digest)` is refused. Real-source dry-run
evidence is in `MIGRATION-DRYRUN.md`:

| Source | Incoming rows | Host rows written by dry-run |
|---|---|---|
| lattice.db | 3 papers, 5 claims, 2 questions, 11 edges | 0 |
| N1 main.db | 1 intervention | 0 |
| existing `research.db` | schema v11: 5 programs, 5 sources, 5 questions, 25 claims, 5 hypotheses, 5 kill tests, 18 runs, 15 verdicts, 2 events | 0 (read-only inspection) |
| obezite ledger | 1,908 claims (1,794 verified, 114 backfill) | 0 (manifest only) |
| PNN output | 236 files: 114 CSV, 105 JSON, 14 MD, 1 HTML, 2 SVG | 0 (manifest only) |
| Atlas demo corpus | 50 files | 0 (manifest only) |
| fluid results | 171 files | 0 (manifest only) |

All six obezite operator tools were also run against the pinned archive into a temporary output
root: dedup found 0 duplicates, the claim index covered 995 claims, backfill wrote 116 skeleton
rows, the collapse audit reported `TEMIZ`, the range split produced 500/97 claim chunks, and the
quarantine split produced 2,396 active / 584 quarantined lines. No source file was written.

## 4. Exact host verification

```text
python aikit.py check research-engine
[PASS] test
[PASS] hygiene
[PASS] guidelines
[PASS] secrets
4/4 gates passed
```

`tests/test_domain_isolation.py` proves:

- no pack imports another pack;
- no pack imports `studio`, `adapters` or `experiments`;
- `engine/` imports no pack or surface.

An import sweep over all 228 copied modules under `adapters/`, `studio/`, `experiments/` and
`domains/` reports **0 failures**. The obezite split tool is import-safe and writes only to paths
passed by the caller.

`tests/test_neurocore_contract.py` exercises the documented NeuroCore consumption surface:
the `studio.api` facade (`synthesize_question`, `extract_claims_for_paper`, context pack,
evidence matrix), MCP `initialize`, `tools/list`, `resources/list`, `prompts/list`,
`resources/read`, graph writes/reads and synthesis calls. It is a contract test, not a claim
that the NeuroCore application itself was run.

## 5. Source integrity

At final capture:

```text
lattice d3f0502b99983f1436fe9466f5553935ea7be868 clean
N1-Engine f2c488695b8c00b224e851cd6aa17eaee4e6960a clean
fluid-universe 7b4efe141dfbcc267b0efceb82247f5004186c06 clean
PNN 3b6e6c277552dcb2c3604483de1277307bc18c4d clean
Atlas f3cd7470e99683bc95b05f49e404bb00bffa2663 clean
obezite-mekanizma-projesi 3ca2e0d51f5f2641ffceef9868234671acd83577 clean (latest observed)
```

obezite advanced repeatedly after the capture pin while this merge was running. The host pin
remains `18b5d4d8e2196384f4e960f01b3031beb0a6315a`; every obezite file was re-read from that
commit with `git show <pin>:08_ARACLAR/<file>` after the worktree moved, so no in-flight change
entered the host. The source suite passed 10/10 at `6776125`; the pinned archive passes 9/10
because archive extraction changes the inventory mtimes used by one freshness test.

## 6. Deliberate exclusions and residual gaps

1. **N1 PyQt GUI is not ported.** Models, metrics, events, analysis, CSV import and database
   migration are ported. The source keeps the GUI runnable.
2. **Atlas real-analysis corpus and uploaded media stay external.** 5 pytest tests that require
   `demo/real_analyses` skip in the host; the source still runs all 152.
3. **obezite's canonical corpus and generated tables stay external.** The host contracts use a
   small synthetic ledger fixture. The source advanced during the merge and its current HEAD
   (`6776125…`) passes 10/10; the host pin remains `18b5d4d8…`.
4. **fluid physics outputs stay external.** The host carries the code and verification rules; the
   generated `results/` are referenced by SHA-256, not copied. The full source suite passed 403
   tests at M0 (1807.74s) and again at M5 (1728.43s) with the same clean SHA.
5. **obezite tool CLIs still use cwd-relative ledger paths.** The library functions and
   `sentez`/`uret` are host-wired with injected roots; the remaining operator scripts are copied
   but not re-rooted.
6. **No live model calls.** Atlas Muse/SAM providers still require keys and refuse keyless calls;
   the offline fallback is the tested path.

## 7. Reproduce

```bash
cd projects/research-engine
python -m unittest discover -s tests -t .
python -m pytest tests/atlas -q
python aikit.py check research-engine
```

Source suites and their pins are in `BASELINES.md` and `SOURCE-INVENTORY.md`.
