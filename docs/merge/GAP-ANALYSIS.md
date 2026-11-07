# Function gap analysis (second pass)

Date: 2026-11-07  
Method: AST inventory of public top-level functions/classes in each source package, compared with
the host destination by module and by basename where the host adds a package level.

## Results

| Project | Source modules | Source public defs | Host modules | Host public defs | Missing public names |
|---|---:|---:|---:|---:|---:|
| lattice | 22 | 121 | 24 | 128 | 0 |
| PNN | 26 | 171 | 26 | 171 | 0 |
| Atlas | 19 | 94 | 21 | 97 | 0 |
| fluid-universe | 133 | 681 | 134 | 690 | 0 after basename matching |
| N1-Engine | 16 (incl. GUI) | 26 | 5 (experiments) | 24 | GUI + SettingsManager only |
| obezite `08_ARACLAR` | 9 | 50 | 9 | 50 | 0 after renaming/re-rooting |

The first raw comparison showed false gaps where the host adds a directory level
(`domains/fluid_universe/verification/audit.py` vs `verification/audit.py`) or replaces classes
with functions. Matching by basename and checking the semantic surface removed those false
positives.

## N1 gaps found and implemented

The source exposed these reusable functions that the host did not yet have:

| Source | Host function | Status |
|---|---|---|
| `AnalysisEngine.correlation_matrix` | `experiments/analysis.py:correlation_matrix` | implemented |
| `DataManager.import_from_csv(..., "metrics"\|"interventions"\|"events")` | `experiments/importer.py:import_csv` + three importers | implemented |
| `DataManager.export_to_csv(...)` | `experiments/exporter.py:export_csv` + three exporters | implemented |
| `ReportGenerator.generate_html_report` | `experiments/reporting.py:generate_html_report` | implemented |

Tests: `tests/test_n1_surfaces.py` (5 tests): date-aligned Pearson matrix, unknown-metric refusal,
three-type CSV import/export round trip, unknown-type refusal, escaped HTML report.

## Deliberate non-ports

- **N1 GUI and `SettingsManager`**: PyQt desktop widgets and app-settings storage; the host is
  CLI/API/MCP and keeps the underlying records and analysis.
- **N1 SQLAlchemy session helpers** (`get_db`, `ensure_schema`): replaced by
  `engine/database.py` transactions and schema migration.
- **obezite `07_ANALIZ` (137 scripts) and `06_MAKALELER` (3 scripts)**: one-off NHANES/VA data
  pulls, cohort-specific regressions and document builders. They depend on the external corpus
  and are not reusable host functions. The reusable ledger tooling in `08_ARACLAR` is ported and
  tested.
- **Atlas uploaded media and fluid/PNN outputs**: data, not functions; referenced by SHA-256.

## Evidence

```text
python C:\Users\Yunus-Emre\AppData\Local\Temp\refined_gap.py
fluid: 133 source modules, 134 host modules, 0 missing names
N1 source: AnalysisEngine, DataManager, ReportGenerator, models, SettingsManager
N1 host: analysis.py (3), importer.py (4), exporter.py (4), reporting.py (1), models.py (12)
obezite: 9 tool files in 08_ARACLAR; 137 one-off scripts in 07_ANALIZ; 3 in 06_MAKALELER

python -m unittest tests.test_n1_surfaces -v
Ran 5 tests in 0.180s
OK
```
