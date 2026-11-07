# Merge parity matrix

Every row names the source capability, the host destination, the port mode and the gate that
proves it. `copy` means the committed source file was copied and only imports/roots changed;
`reimplement` means the behaviour was rebuilt on the host standard-library core; `external`
means the source data stays outside the host and is referenced by path plus SHA-256.

Status on 2026-11-07: all rows below are `ported` unless the status column says otherwise.

## lattice (M1 schema, M3 surfaces)

| ID | Capability | Host destination | Mode | Status | Acceptance gate |
|---|---|---|---|---|---|
| L-01 | Paper model: DOI/arXiv/venue/abstract/tags/study type | `engine/models.py`, `engine/sources.py` | additive schema v14 | ported | `tests/test_schema_v14.py` |
| L-02 | Bibliography parsing: BibTeX, RIS, CSV, CSL-JSON, Markdown | `adapters/lattice/ingest.py` | copy | ported | `tests/lattice/test_ingest.py` |
| L-03 | Discovery: offline, arXiv, Crossref, OpenAlex, EuropePMC, registry | `adapters/lattice/discovery.py` | copy; network opt-in | ported | `tests/lattice/test_discovery.py` |
| L-04 | Extraction: sentences, stance, confidence, quote+locator | `adapters/lattice/extraction.py` | copy | ported | `tests/lattice/test_extraction.py` |
| L-05 | Claim/question/typed-edge graph | `adapters/lattice/repository.py`, host `engine/claims.py` | copy + host bridge | ported | `tests/lattice/test_repository.py`, `tests/lattice/test_analysis.py` |
| L-06 | Contradictions, related findings, keystone rank, matrix | `adapters/lattice/analysis.py` | copy | ported | `tests/lattice/test_analysis.py` |
| L-07 | Inquiry: ask, brief, review | `adapters/lattice/inquiry.py` | copy | ported | `tests/lattice/test_inquiry.py` |
| L-08 | Token-budgeted context views | `adapters/lattice/context.py` | copy | ported | `tests/lattice/test_context.py` |
| L-09 | Synthesis: consensus, clusters, gaps, Markdown/BibTeX | `adapters/lattice/synthesis.py` | copy | ported | `tests/lattice/test_synthesis.py` |
| L-10 | Meta-analysis: fixed/random effects, Q, I-squared, forest | `adapters/lattice/meta.py` | copy | ported | `tests/lattice/test_meta.py` |
| L-11 | PRISMA 2020 screening | `adapters/lattice/screening.py` | copy | ported | `tests/lattice/test_screening.py` |
| L-12 | Snapshots, GraphML, Cytoscape, BibTeX, diff | `adapters/lattice/snapshots.py`, `diff.py` | copy | ported | `tests/lattice/test_snapshots.py`, `test_diff.py` |
| L-13 | Web Research Studio | `studio/web.py` | copy | ported | `tests/lattice/test_web.py` |
| L-14 | MCP stdio server | `studio/mcp.py` | copy | ported | `tests/lattice/test_mcp.py` |
| L-15 | Python API and client facade | `studio/api.py`, `studio/client.py` | copy | ported | `tests/lattice/test_api.py`, `test_client.py` |
| L-16 | CLI surface and launcher | `adapters/lattice/cli.py`, `start.py` | copy | ported | `tests/lattice/test_cli.py` |
| L-17 | UI inventory proof | `adapters/lattice/ui_inventory.py` | copy | ported | `tests/lattice/test_ui_inventory.py` |
| L-18 | Dogfood runner: real CLI + live studio + chaos | `adapters/lattice/dogfood.py` | copy + host paths | ported | `python -m adapters.lattice.dogfood` (25/25) |

## N1-Engine (M1 schema, M4 experiments)

| ID | Capability | Host destination | Mode | Status | Acceptance gate |
|---|---|---|---|---|---|
| N-01 | Intervention record | `experiments/models.py` | reimplement | ported | `tests/test_experiments.py` |
| N-02 | MetricDefinition record | `experiments/models.py` | reimplement | ported | `tests/test_experiments.py` |
| N-03 | MetricEntry with intervention FK | `experiments/models.py` | reimplement | ported | `tests/test_experiments.py` |
| N-04 | EventEntry with 1..5 severity | `experiments/models.py` | reimplement | ported | `tests/test_experiments.py` |
| N-05 | Baseline/intervention windows and counts | `experiments/analysis.py` | reimplement on `engine/stats.py` | ported | `tests/test_experiments.py` |
| N-06 | Trend slope and p-value | `experiments/analysis.py` | reimplement | ported | `tests/test_experiments.py` |
| N-07 | Seeded bootstrap CI | `experiments/analysis.py` | reimplement | ported | `tests/test_experiments.py` |
| N-08 | Cohen's d, Welch t, Mann-Whitney U | `experiments/analysis.py` | reimplement | ported | `tests/test_experiments.py` |
| N-09 | Multiple-comparison warning | `experiments/analysis.py` | reimplement | ported | `tests/test_experiments.py` |
| N-10 | CSV import and export for metrics, interventions, events | `experiments/importer.py`, `experiments/exporter.py` | reimplement | ported | `tests/test_n1_surfaces.py` |
| N-11 | Database schema migration and golden import, including legacy N1 schemas | `engine/migrations.py` | reimplement | ported | `tests/test_migration_harness.py` |
| N-12 | Correlation matrix aligned by date | `experiments/analysis.py:correlation_matrix` | reimplement on `engine/stats.py` | ported | `tests/test_n1_surfaces.py` |
| N-13 | HTML analysis report | `experiments/reporting.py:generate_html_report` | reimplement | ported | `tests/test_n1_surfaces.py` |
| N-14 | Analysis settings manager | `experiments/settings.py:SettingsManager` | reimplement | ported | `tests/test_n1_surfaces.py` |
| N-15 | Source-compatible class names (`AnalysisEngine`, `DataManager`, `ReportGenerator`) | `experiments/compat.py` | reimplement | ported | `tests/test_n1_surfaces.py` |
| N-16 | Intervention edit, close and status display | `experiments/models.py` (`update_intervention`, `close_intervention`, `intervention_status`) | reimplement | ported | `tests/test_n1_surfaces.py` |
| N-17 | Metric-definition rename and delete, including entry rename | `experiments/models.py` (`update_metric_definition`, `delete_metric_definition`) | reimplement | ported | `tests/test_n1_surfaces.py` |
| N-18 | Period/intervention summary and HTML rendering | `experiments/summary.py` | reimplement | ported | `tests/test_n1_surfaces.py` |
| N-19 | JSON report save | `experiments/reporting.py:save_report_json` | reimplement | ported | `tests/test_n1_surfaces.py` |
| N-20 | PyQt desktop GUI | not ported | surface not ported | deliberate | source suite stays green; host is CLI/API/MCP |
| N-21 | SQLAlchemy/PyQt dependency footprint | not copied | dependency boundary | deliberate | host import scan has neither |

## fluid-universe (M2 rigor, M4 pack)

| ID | Capability | Host destination | Mode | Status | Acceptance gate |
|---|---|---|---|---|---|
| F-01 | Two-run audit | `domains/fluid_universe/verification/audit.py` | copy | ported | `tests/test_fluid_rigor.py`, `tests/test_fluid_audit.py` |
| F-02 | Source/results fingerprints | `domains/fluid_universe/verification/fingerprint.py` | copy | ported | `tests/test_fluid_rigor.py` |
| F-03 | Compare, stale-run refusal | `domains/fluid_universe/verification/compare.py` | copy | ported | `tests/test_fluid_rigor.py` |
| F-04 | Claims and scorecard compatibility | `domains/fluid_universe/claims.py` | reimplement parser | ported | `tests/test_fluid_rigor.py` |
| F-05 | Physics theory, phenomenology, sims | `domains/fluid_universe/{theory,phenomenology,sims}/` | copy | ported | `python -c "from domains.fluid_universe.theory.circulant import q_from_ac"` |
| F-06 | Physics results and run history | external `results/` | reference + SHA-256 | external | `docs/merge/MIGRATION-DRYRUN.md` |

## PNN (M4 pack)

| ID | Capability | Host destination | Mode | Status | Acceptance gate |
|---|---|---|---|---|---|
| P-01 | End-to-end runner and selection | `domains/pnn/runner.py`, `selection.py` | copy | ported | `tests/pnn/test_run.py`, `test_pipeline.py` |
| P-02 | Evidence gates G-001..G-003 | `domains/pnn/selection.py`, `rules.py` | copy | ported | `tests/pnn/test_pipeline.py`, `test_rules.py` |
| P-03 | Markdown reports | `domains/pnn/reports.py` | copy | ported | `tests/pnn/test_pipeline.py` |
| P-04 | Studio dashboard | `domains/pnn/studio.py` | copy | ported | `tests/pnn/test_studio.py` |
| P-05 | Screening, MPO, property rules | `domains/pnn/screen.py`, `mpo.py`, `rules.py` | copy | ported | `tests/pnn/test_screen.py`, `test_mpo.py` |
| P-06 | Docking consensus | `domains/pnn/docking.py` | copy | ported | `tests/pnn/test_docking.py` |
| P-07 | Assay qualification | `domains/pnn/assay.py` | copy | ported | `tests/pnn/test_assay.py` |
| P-08 | Preclinical PK/PD | `domains/pnn/preclinical.py` | copy | ported | `tests/pnn/test_preclinical.py` |
| P-09 | SAR, bioisostere, ranking | `domains/pnn/sar.py`, `bioisostere.py`, `rank.py` | copy | ported | `tests/pnn/test_sar.py`, `test_bioisostere.py`, `test_rank.py` |
| P-10 | Curation and dedupe | `domains/pnn/curation.py`, `curate.py` | copy | ported | `tests/pnn/test_curation.py` |
| P-11 | IND dossier projection | `domains/pnn/ind.py` | copy | ported | `tests/pnn/test_ind.py` |
| P-12 | Pathway simulation and dynamics | `domains/pnn/pathway.py`, `dynamics.py` | copy | ported | `tests/pnn/test_pathway.py`, `test_dynamics.py` |
| P-13 | Curated CSV fixtures and run outputs | small `domains/pnn/data/`; real `output/` external | copy + reference | external | `tests/pnn/`, `docs/merge/MIGRATION-DRYRUN.md` |

## obezite-mekanizma-projesi (M4 pack)

| ID | Capability | Host destination | Mode | Status | Acceptance gate |
|---|---|---|---|---|---|
| O-01 | Canonical claim-ledger parsing | `domains/obezite/sentez.py` | copy with injected root | ported | `tests/test_obezite_ledger.py` |
| O-02 | Lossless chunking and claim index | `domains/obezite/uret.py` | copy with host-generated output | ported | `tests/test_obezite_ledger.py` |
| O-03 | Citation extraction | `domains/obezite/atif.py` | copy | ported | imported by `uret.py`; `tests/test_obezite_ledger.py` |
| O-04 | Dedupe, claim-index and split tools | `domains/obezite/dedup.py`, `claim_index.py`, `split*.py`, `cokus.py`, `backfill.py` | copy + explicit root/output | ported | `tests/test_obezite_ledger.py` (all write only caller paths) |
| O-05 | Register, evidence summary, inventory | `domains/obezite/sentez.py` | copy | ported | `tests/test_obezite_ledger.py` |
| O-06 | Hypothesis/observation/synthesis vocabulary | host `engine/hypotheses.py`, `engine/observations.py` | wrap host lifecycle | ported at lifecycle level | `tests/test_hypotheses.py`, `tests/test_observations.py` |
| O-07 | 6.1 GB corpus and generated tables | external `02_LITERATUR/`, `09_SENTEZ/` | reference + SHA-256 | external | `docs/merge/MIGRATION-DRYRUN.md` |

## Atlas (M4 pack; AL-1.1 compatibility checked)

| ID | Capability | Host destination | Mode | Status | Acceptance gate |
|---|---|---|---|---|---|
| A-01 | Multimodal ingestion: PDF, video, image, EPUB, text, link | `domains/atlas/ingestion.py`, `sources.py`, `doc_text.py` | copy | ported | `tests/atlas/test_ingestion.py`, `test_sources.py`; `tests/test_atlas_pack.py` |
| A-02 | Material model: diagrams, posters, podcasts, video, 3D | `domains/atlas/materials.py`, `models3d.py` | copy | ported | `tests/atlas/test_materials.py` |
| A-03 | Quoted-evidence text backend | `domains/atlas/text_backend.py`, `doc_text.py` | copy | ported | `tests/atlas/test_vendored_text.py` |
| A-04 | Knowledge-graph schema and atomic store | `domains/atlas/schema.py`, `store.py` | copy | ported | `tests/atlas/test_schema.py`; `tests/test_atlas_pack.py` |
| A-05 | Flashcards, study pack, learning modes | `domains/atlas/flashcards.py`, `summaries.py`, `learning.py` | copy | ported | `tests/atlas/test_study_pack.py`, `test_3d_flashcards.py` |
| A-06 | Quality checks | `domains/atlas/quality.py` | copy | ported | `tests/atlas/test_quality_video.py` |
| A-07 | Offline extractive fallback | `domains/atlas/offline.py` | copy | ported | `tests/atlas/test_offline_fallback.py`; `tests/test_atlas_pack.py` |
| A-08 | Standalone app/API and CLI | `domains/atlas/app.py`, `cli.py` | copy inside pack | ported | `tests/atlas/test_contract.py`, `test_cli_video.py` |
| A-09 | AL-1.1 notice and schema id | `domains/atlas/NOTICE.md`, schema id preserved | preserve | ported | notice file; `tests/atlas/test_contract.py` |
| A-10 | Uploaded media and real-analysis corpus | external `data/`, `demo/real_analyses/` | reference + SHA-256 | external | Atlas tests read the sibling checkout in place; `docs/merge/MIGRATION-DRYRUN.md` |

## Host-wide contracts

| ID | Contract | Host destination | Acceptance gate |
|---|---|---|---|
| X-01 | Pack registry: name, version, API version, data root, digest | `engine/packs.py`, `domain_pack` table | `tests/test_packs.py` |
| X-02 | Additive schema migration and dry-run harness | `engine/migrations.py` | `tests/test_migration_harness.py` |
| X-03 | External data referenced by path plus digest | `inspect_tree`, migration reports, `digest_tree` | `tests/test_migration_harness.py`, `tests/test_packs.py` |
| X-04 | NeuroCore consumes the host through API/MCP only | `studio/api.py`, `studio/mcp.py` | `tests/test_neurocore_contract.py` |
| X-05 | No cross-domain imports | repository-wide | `tests/test_domain_isolation.py` |
| X-06 | Source notices preserved | `adapters/lattice/NOTICE.md`, `studio/NOTICE.md`, `domains/*/NOTICE.md` | `docs/merge/PROVENANCE.md` |
| X-07 | Every source remains runnable and untouched | external repos | post-merge re-run in `docs/merge/READINESS.md` |
| X-08 | External pack data root fingerprinted and registered in place | `engine/artifacts.digest_tree`, `engine/packs.register_pack_from_tree` | `tests/test_packs.py` |

## Summary

| Source | Capability rows | Ported | External-only | Deliberate surface loss |
|---|---:|---:|---:|---:|
| lattice | 17 | 17 | 0 | 0 |
| N1-Engine | 13 | 11 | 0 | 1 (PyQt GUI) + 1 dependency boundary |
| fluid-universe | 6 | 5 | 1 | 0 |
| PNN | 13 | 12 | 1 | 0 |
| obezite | 7 | 6 | 1 | 0 |
| Atlas | 10 | 9 | 1 | 0 |
| Host-wide | 7 | 7 | 0 | 0 |

The only deliberate source surface loss is N1's PyQt desktop GUI. The source keeps it running;
the host exposes the same models and analysis through CLI/API/MCP.
