# M5 migration dry-run evidence

Run on 2026-11-07 from `projects/research-engine` against the committed source HEADs.
Every command is read-only on the source; no source file is written.

## 1. Read-only source manifests

```text
python -c "from engine.migrations import inspect_lattice, inspect_n1, inspect_obezite, inspect_tree; ..."
```

| Source | Evidence | Result |
|---|---|---|
| lattice | `lattice.db` SHA-256 `ebc2a94c…f613a5` | 3 papers, 5 claims, 2 questions, 11 edges |
| N1-Engine | `main.db` SHA-256 `089e8378…26831` | 1 intervention, 0 definitions, 0 metrics, 0 events |
| obezite | `02_LITERATUR/iddia-defteri.md` SHA-256 `f3269f3e…4db6` | 1,908 claim rows: 1,794 verified, 114 backfill |
| PNN output | `PNN/output` SHA-256 `bce1add0…cf90` | 236 files: 114 CSV, 105 JSON, 14 MD, 1 HTML, 2 SVG |
| PNN tmp_out | `PNN/tmp_out` | empty directory, recorded as 0 files |
| Atlas demo | `Atlas/demo/real_analyses` SHA-256 `0b5ebd6c…1ddc` | 50 files: 11 JSON, 16 MD, 12 SVG, 6 TSV, 5 OBJ |
| fluid results | `fluid-universe/results` SHA-256 `1b8afb04…c1f4` | 171 files: 82 JSON, 89 MD |
| host database | existing `research.db` SHA-256 `4a02efd9…005f` | schema v11: 5 programs, 5 sources, 5 questions, 25 claims, 5 hypotheses, 5 kill tests, 18 runs, 15 verdicts, 2 events |

The existing host database predates schema v14. `initialize` would migrate v11 -> v14 on open;
the inspection above is read-only and does not open it for writing.

## 2. Golden host dry-run, real sources

```text
python -c "from engine.migrations import migrate_lattice, migrate_n1; ... dry_run=True"
```

```json
{
  "lattice": {
    "source_digest": "ebc2a94cc4db760de96ba237a47fafbc326f07b7e74ddfe6112a0f9cfcf613a5",
    "tables": {"papers": 3, "claims": 5, "questions": 2, "edges": 11, "screening": 0},
    "inserted": {},
    "dry_run": true
  },
  "n1": {
    "source_digest": "089e837806f35af13ac1c045c264ea2d5ba61f026c13e4d4c609b9672df26831",
    "tables": {"interventions": 1, "metric_definitions": 0, "metrics": 0, "events": 0},
    "inserted": {},
    "dry_run": true
  },
  "host_rows_after_dry_run": {
    "source": 0,
    "claim": 0,
    "experiment_intervention": 0,
    "experiment_metric": 0,
    "migration_run": 0
  }
}
```

The dry-run writes nothing: no source, claim, experiment or migration row exists afterwards.

## 3. Existing host database, read-only

```text
python -c "from engine.migrations import inspect_research; ..."
```

```json
{
  "source_digest": "4a02efd9824af71c810d622906a1df422b3035c8eb3d6d0ae8a12d76ee56005f",
  "tables": {
    "research": 5, "source": 5, "question": 5, "claim": 25,
    "hypothesis": 5, "killtest": 5, "test_run": 18, "verdict": 15,
    "event": 2, "schema_version": 11
  },
  "dry_run": true
}
```

The inspection reports v14-only tables as 0 because they do not exist in the v11 file. No
migration was applied to the user's database; the v14 migration is exercised by the fixture
tests and the temporary target in section 2.

## 4. Golden apply on fixtures

`tests/test_migration_harness.py::test_golden_both_sources_share_one_program` applies a
two-paper lattice fixture and an N1 fixture to one program and asserts:

```text
source=2  claim=1  metric=2
```

The same test proves the second apply of one snapshot is refused by the
`(source, source_digest)` unique key.

## 5. Obezite operator tools against the pinned archive

All six tools read the pinned archive `18b5d4d8…` and write only to a temporary output root:

```text
python -m domains.obezite.dedup --root <pinned> --output-dir <tmp>/dedup
Found 0 duplicate claim IDs

python -m domains.obezite.claim_index --root <pinned> --output <tmp>/claim-index.md
Total unique claims: 995

python -m domains.obezite.backfill --root <pinned> --output <tmp>/backfilled.md --start 482 --end 597
Tur referansi: 79
Eksik: 116
[OK] 116 iskelet giris yazildi

python -m domains.obezite.cokus --ledger <pinned>/02_LITERATUR/iddia-defteri.md
iddia 1890 · gecersiz 36 · onlari anan 60 satir
TEMIZ: gecersiz iddia anan her satir serh tasiyor

python -m domains.obezite.split_range --source <pinned>/02_LITERATUR/iddia-defteri.md --output-dir <tmp>/range
Chunk 1 (1-500): 500 claims
Chunk 2 (501-1000): 97 claims

python -m domains.obezite.split --source <pinned>/02_LITERATUR/iddia-defteri.md --active <tmp>/active.md --quarantine <tmp>/quarantine.md
Total lines: 2435
Active claims/lines: 2396
Quarantined claims/lines: 584
```

No command writes into the pinned archive. The unit contracts in
`tests/test_obezite_ledger.py::LedgerOperatorTests` assert the source bytes are unchanged for
dedup and backfill.

## 6. Source integrity

The reads above use SQLite `mode=ro` or `Path.read_bytes()`. The source files are not opened
for writing and their committed SHAs are unchanged. See `READINESS.md` section 5.
