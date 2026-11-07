# M5 migration dry-run evidence

Run on 2026-11-07 from `projects/research-engine` against the committed source HEADs.
Every command is read-only on the source and writes only to a temporary host database.

## 1. Read-only source manifests

```text
python -c "from engine.migrations import inspect_lattice, inspect_n1, inspect_obezite, inspect_tree; ..."
```

| Source | Evidence | Result |
|---|---|---|
| lattice | `lattice.db` SHA-256 `ebc2a94c…f613a5` | 3 papers, 5 claims, 2 questions, 11 edges |
| N1-Engine | `main.db` SHA-256 `089e8378…26831` | 1 intervention, 0 definitions, 0 metrics, 0 events |
| obezite | `02_LITERATUR/iddia-defteri.md` SHA-256 `f3269f3e…4db6` | 1,908 claim rows: 1,794 verified, 114 backfill |
| PNN fixtures | `PNN/data` SHA-256 `ae3c08c1…cf7` | 200 CSV files |
| Atlas demo | `Atlas/demo/real_analyses` SHA-256 `0b5ebd6c…1ddc` | 50 files: 11 JSON, 16 MD, 12 SVG, 6 TSV, 5 OBJ |
| fluid results | `fluid-universe/results` SHA-256 `1b8afb04…c1f4` | 171 files: 82 JSON, 89 MD |
| host schema | a fresh `research.db` | all 17 host tables present, 0 rows |

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

## 3. Golden apply on fixtures

`tests/test_migration_harness.py::test_golden_both_sources_share_one_program` applies a
two-paper lattice fixture and an N1 fixture to one program and asserts:

```text
source=2  claim=1  metric=2
```

The same test proves the second apply of one snapshot is refused by the
`(source, source_digest)` unique key.

## 4. Source integrity

The reads above use SQLite `mode=ro` or `Path.read_bytes()`. The source files are not opened
for writing and their committed SHAs are unchanged. See `READINESS.md` section 5.
