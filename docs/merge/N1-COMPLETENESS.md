# N1-Engine completeness audit

Date: 2026-11-07  
Purpose: decide whether N1-Engine can be archived after the merge. Every public module and
function in the pinned source (`f2c488695b8c00b224e851cd6aa17eaee4e6960a`) is mapped below.

## Public surface mapping

| Source module | Public functions/classes | Host destination | Status |
|---|---|---|---|
| `core/analysis.py` | `AnalysisEngine.calculate_trend`, `bootstrap_ci`, `correlation_matrix`, `calculate_baseline_vs_intervention`, `analyze_multiple_metrics` | `experiments/analysis.py` (`calculate_trend`, `bootstrap_ci`, `correlation_matrix`, `analyze_baseline_vs_intervention`, `analyze_multiple_metrics`); `experiments/compat.py:AnalysisEngine` | **ported** |
| `core/data_manager.py` | `DataManager.import_from_csv`, `export_to_csv` | `experiments/importer.py`, `experiments/exporter.py`, `experiments/compat.py:DataManager` | **ported** |
| `core/database.py` | `ensure_schema`, `get_db` | `engine/database.py` (`connect`, `initialize`, `transaction`); `engine/migrations.py:migrate_n1` also reads legacy N1 schemas | **replaced** |
| `core/models.py` | `Intervention`, `MetricDefinition`, `MetricEntry`, `EventEntry` | `experiments/models.py` (frozen dataclasses + CRUD) | **ported** |
| `core/reporting.py` | `ReportGenerator.generate_html_report` | `experiments/reporting.py`; `experiments/compat.py:ReportGenerator` | **ported** |
| `core/settings_manager.py` | `SettingsManager.load_settings`, `save_settings`, `get`, `set` | `experiments/settings.py:SettingsManager` (atomic save) | **ported** |
| GUI `InterventionsWidget` backend | add, edit, close and status display | `experiments/models.py` (`add_intervention`, `update_intervention`, `close_intervention`, `intervention_status`) | **ported** |
| GUI `MetricDefinitionWidget` backend | add, rename (and rewrite entries), delete | `experiments/models.py` (`add_metric_definition`, `update_metric_definition`, `delete_metric_definition`) | **ported** |
| GUI `SummarizerWidget` backend | intervention/date-range summary and HTML rendering | `experiments/summary.py` (`summarize_period`, `render_summary_html`) | **ported** |
| GUI `AnalysisWidget` backend | JSON report save, HTML report export | `experiments/reporting.py` (`save_report_json`, `generate_html_report`) | **ported** |
| `config.py` | `MIN_BASELINE_DAYS`, `MIN_INTERVENTION_DAYS`, `MIN_DATA_POINTS`, `MAX_SAFE_METRICS` | `experiments/models.py`, `experiments/settings.py:DEFAULTS` | **ported** |
| `config.py` | `DATABASE_URL` | host database path (`engine/database.py`) | **replaced** |
| `gui/analysis.py` | `AnalysisWidget.*` | not ported | **GUI only** |
| `gui/data_management.py` | `DataManagementWidget.*` | not ported | **GUI only** |
| `gui/dialogs.py` | `show_error`, `show_warning`, `show_info` | not ported | **GUI only** |
| `gui/events.py` | `EventsWidget.*` | not ported | **GUI only** |
| `gui/interventions.py` | `DateTableWidgetItem`, `InterventionDialog`, `InterventionsWidget` | not ported | **GUI only** |
| `gui/main_window.py` | `WorkspaceWidget`, `MainWindow` | not ported | **GUI only** |
| `gui/metrics.py` | `LoggingWidget`, `MetricDefinitionDialog`, `MetricDefinitionWidget` | not ported | **GUI only** |
| `gui/settings.py` | `SettingsWidget` | not ported | **GUI only** |
| `gui/summarizer.py` | `SummarizerWidget` | not ported | **GUI only** |
| `run_gui.py` | launcher | not ported | **GUI only** |

## What is actually left

Only **presentation code** remains:

- the PyQt widget/dialog classes under `main/gui/`;
- `run_gui.py`;
- the SQLAlchemy `get_db` session generator and `ensure_schema` in-place upgrade, which the host
  replaces with `engine/database.py` and the read-only `migrate_n1` harness.

The operational logic those widgets contained has been extracted: intervention edit/close/status,
metric-definition rename/delete, period summarization, JSON report saving and HTML export are host
functions now. No analysis, data, settings, reporting or model function remains unported.

## Gaps closed in this audit

- Added `calculate_trend` and `bootstrap_ci` public functions plus source-compatible
  `AnalysisEngine` names.
- Added `SettingsManager` with load/save/get/set and atomic file replacement.
- Added `DataManager` and `ReportGenerator` compatibility classes for source-style callers.
- Extracted intervention edit/close/status and metric-definition rename/delete from the GUI.
- Extracted the daily/weekly summarizer into `experiments/summary.py`.
- Added JSON report saving alongside HTML export.
- Added CSV export/import of intervention links, `success` flags, and out-of-range severity
  coercion to `None`.
- `migrate_n1` now reads legacy N1 databases that lack `projected_end_date` and
  `intervention_id` columns.
- Added analysis result aliases: `t_test.statistic`, `mann_whitney_u.statistic`,
  `bootstrap_ci.lower`, `bootstrap_ci.upper`.

## Evidence

```text
python -m unittest tests.test_n1_surfaces tests.test_migration_harness -q
Ran 23 tests in 2.421s
OK

python C:\Users\Yunus-Emre\AppData\Local\Temp\n1_inventory.py
core/analysis.py      AnalysisEngine(calculate_trend, bootstrap_ci, correlation_matrix,
                                     calculate_baseline_vs_intervention, analyze_multiple_metrics)
core/data_manager.py  DataManager(import_from_csv, export_to_csv)
core/database.py      ensure_schema, get_db
core/models.py        Intervention, MetricDefinition, MetricEntry, EventEntry
core/reporting.py     ReportGenerator(generate_html_report)
core/settings_manager.py SettingsManager(load_settings, save_settings, get, set)
gui/*                 12 widget/dialog classes
```

The source test `test_gui_logic.py` is the only N1 test with no host counterpart; it exercises
PyQt widget formatting. All non-GUI source behaviours are covered by the host tests.

**Archive verdict:** N1-Engine can be archived for non-GUI use. If the desktop GUI itself is still
required, keep the source until a replacement GUI exists.
