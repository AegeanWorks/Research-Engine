# Merge parity matrix

Every row names the source capability, the exact source evidence used to judge parity, the host
destination, the port mode, and the acceptance gate that proves the row landed. "Copy" means the
committed source file is copied and its imports are adjusted; "wrap" means a thin host adapter calls
the copied module; "reimplement" means the behaviour is rebuilt on the host standard-library core
because the source implementation depends on a package the host cannot require.

No source row is deleted. A row marked "surface not ported" is deliberately out of scope and the
source keeps that surface running.

## lattice (M1 schema, M3 surfaces)

| ID | Capability | Source evidence | Host destination | Mode | Acceptance gate |
|---|---|---|---|---|---|
| L-01 | Paper bibliographic model: DOI/arXiv/title/year/authors/venue/abstract/tags/study type | `lattice/models.py`, `lattice/repository.py`, `tests/test_models.py` | `engine/models.py` schema v14; `adapters/ingest.py` | copy + additive schema | `tests/test_schema_v14.py`, `tests/test_paper_fields.py` |
| L-02 | Bibliography parsing: BibTeX, RIS, CSV, CSL-JSON, Markdown | `lattice/ingest.py`, `tests/test_ingest.py` | `adapters/ingest.py` | copy | `tests/test_ingest_parity.py` |
| L-03 | Discovery providers: offline, arXiv, Crossref, OpenAlex, EuropePMC, federated list, dedupe, 4-layer registry | `lattice/discovery.py`, `tests/test_discovery.py` | `adapters/discovery.py` | copy; network stays opt-in | `tests/test_discovery_parity.py` |
| L-04 | Extraction: sentence segmentation, stance/confidence, quote+locator, question linking | `lattice/extraction.py`, `tests/test_extraction.py` | `adapters/extraction.py` | copy | `tests/test_extraction_parity.py` |
| L-05 | Claim/question/typed-edge graph with provenance | `lattice/repository.py`, `lattice/models.py`, host `engine/claims.py` | `engine/claims.py`, `engine/sources.py` | wrap host core; add paper FK | `tests/test_lattice_graph_compat.py` |
| L-06 | Analysis: contradictions, related findings, keystone rank, evidence matrix | `lattice/analysis.py`, `tests/test_analysis.py` | `adapters/analysis.py` | copy | `tests/test_analysis_parity.py` |
| L-07 | Inquiry: `ask`, budgeted `brief`, `review` outlines | `lattice/inquiry.py`, `tests/test_inquiry.py` | `adapters/inquiry.py` | copy on host context | `tests/test_inquiry_parity.py` |
| L-08 | Token-budgeted context views | `lattice/context.py`, `tests/test_context.py` | host `engine/context.py` | wrap existing | `tests/test_context_parity.py` |
| L-09 | Synthesis: consensus, thematic clusters, gaps, Markdown/BibTeX | `lattice/synthesis.py`, `tests/test_synthesis.py` | `adapters/synthesis.py` | copy | `tests/test_synthesis_parity.py` |
| L-10 | Meta-analysis: fixed/random effects, Cochran Q, I-squared, forest plot | `lattice/meta.py`, `tests/test_meta.py` | `adapters/meta.py` | copy | `tests/test_meta_parity.py` |
| L-11 | PRISMA 2020 screening flow | `lattice/screening.py`, `tests/test_screening.py` | host `engine/screening.py` | wrap existing | `tests/test_prisma_parity.py` |
| L-12 | Snapshots: JSONL import/export, GraphML, Cytoscape, BibTeX, diff | `lattice/snapshots.py`, `lattice/diff.py`, `tests/test_snapshots.py`, `tests/test_diff.py` | `adapters/snapshots.py` | copy | `tests/test_snapshot_parity.py` |
| L-13 | Web Research Studio | `lattice/web.py`, `tests/test_web.py` | `studio/web.py` | copy | `tests/test_studio_web.py` |
| L-14 | MCP stdio server | `lattice/mcp.py`, `tests/test_mcp.py` | `studio/mcp.py` | copy | `tests/test_mcp_parity.py` |
| L-15 | Stable Python API and client facade | `lattice/api.py`, `lattice/client.py`, `tests/test_api.py`, `tests/test_client.py` | `studio/api.py` | copy | `tests/test_api_parity.py` |
| L-16 | CLI command surface | `lattice/cli.py`, `tests/test_cli.py` | `studio/cli.py` delegating to host CLI | wrap | `tests/test_lattice_cli_parity.py` |

## N1-Engine (M1 schema, M4 experiments)

| ID | Capability | Source evidence | Host destination | Mode | Acceptance gate |
|---|---|---|---|---|---|
| N-01 | Intervention record | `main/core/models.py:Intervention`, `tests/test_phase1.py` | `experiments/models.py` | reimplement (stdlib/SQLite) | `tests/test_experiments_models.py` |
| N-02 | MetricDefinition record | `main/core/models.py:MetricDefinition` | `experiments/models.py` | reimplement | `tests/test_experiments_models.py` |
| N-03 | MetricEntry record with intervention FK | `main/core/models.py:MetricEntry` | `experiments/models.py` | reimplement | `tests/test_experiments_models.py` |
| N-04 | EventEntry record with 1..5 severity constraint | `main/core/models.py:EventEntry` | `experiments/models.py` | reimplement | `tests/test_experiments_models.py` |
| N-05 | Baseline-vs-intervention windows and counts | `main/core/analysis.py:calculate_baseline_vs_intervention` | `experiments/analysis.py` | reimplement on `engine/stats.py` | `tests/test_experiment_analysis.py` |
| N-06 | Trend slope and p-value | `main/core/analysis.py:calculate_trend`, `tests/test_new_features.py` | `experiments/analysis.py` | reimplement | `tests/test_experiment_analysis.py` |
| N-07 | Seeded bootstrap CI for mean difference | `main/core/analysis.py:bootstrap_ci` | `experiments/analysis.py` | reimplement with fixed seed | `tests/test_experiment_analysis.py` |
| N-08 | Cohen's d, Welch t, Mann-Whitney U | `main/core/analysis.py` | `experiments/analysis.py` | reimplement on `engine/stats.py` | `tests/test_experiment_analysis.py` |
| N-09 | Multiple-comparison warning above 3 metrics | `main/core/analysis.py:analyze_multiple_metrics`, `tests/test_phase1.py` | `experiments/analysis.py` | reimplement | `tests/test_experiment_analysis.py` |
| N-10 | CSV import and schema migration | `main/core/data_manager.py`, `tests/test_schema_migration.py` | `experiments/importer.py`, `engine/migrations.py` | reimplement | `tests/test_experiment_migration.py` |
| N-11 | PyQt GUI | `main/gui/`, `tests/test_gui_logic.py` | not ported | surface not ported | source suite stays green; host is CLI/API |
| N-12 | SQLAlchemy/PyQt dependency footprint | `requirements.txt` | not copied | dependency boundary | host import scan proves no SQLAlchemy/PyQt import |

## fluid-universe (M2 rigor, M4 pack)

| ID | Capability | Source evidence | Host destination | Mode | Acceptance gate |
|---|---|---|---|---|---|
| F-01 | Two-run independent audit | `verification/audit.py`, `verification/verify.py` | `engine/audit.py` | reimplement stdlib runner | `tests/test_audit.py` |
| F-02 | Source and results fingerprints | `verification/fingerprint.py` | `engine/fingerprint.py` | copy | `tests/test_fingerprint.py` |
| F-03 | Compare two runs, reject stale or disagreeing results | `verification/compare.py`, `tests/test_verify_compare.py` | `engine/compare.py` | copy | `tests/test_compare.py` |
| F-04 | Claims and scorecard compatibility | `claims.md`, `SCORECARD.md`, `phenomenology/provenance.py` | host `engine/claims.py`, `engine/analysis.py` | wrap | `tests/test_scorecard_compat.py` |
| F-05 | Physics computation pack | `theory/`, `phenomenology/`, `sims/`, `verification/` | `domains/fluid_universe/` | copy; numpy/scipy/sympy/jax stay pack-local | `domains/fluid_universe/tests/` |
| F-06 | Physics outputs and run history | `results/`, `verification_*.json` | external; digest reference only | reference | `tests/test_external_refs.py` |

## PNN (M4 pack)

| ID | Capability | Source evidence | Host destination | Mode | Acceptance gate |
|---|---|---|---|---|---|
| P-01 | End-to-end pipeline runner and selection | `pnn/pipeline.py`, `pnn/runner.py`, `pnn/selection.py`, `tests/test_pipeline.py` | `domains/pnn/pipeline.py` | copy | `domains/pnn/tests/test_pipeline.py` |
| P-02 | Evidence gates G-001..G-003 | `pnn/selection.py`, `pnn/rules.py`, `tests/test_pipeline.py` | `domains/pnn/gates.py` | copy + host claim binding | `domains/pnn/tests/test_gates.py` |
| P-03 | Markdown reports | `pnn/reports.py`, `tests/test_golden.py` | `domains/pnn/reports.py` | copy | `domains/pnn/tests/test_reports.py` |
| P-04 | Studio dashboard | `pnn/studio.py`, `tests/test_studio.py` | `domains/pnn/studio.py` | copy | `domains/pnn/tests/test_studio.py` |
| P-05 | Screening, MPO and property rules | `pnn/screen.py`, `pnn/mpo.py`, `pnn/rules.py`, `tests/test_screen.py`, `tests/test_mpo.py` | `domains/pnn/screen.py`, `mpo.py`, `rules.py` | copy | `domains/pnn/tests/` |
| P-06 | Docking consensus | `pnn/docking.py`, `tests/test_docking.py` | `domains/pnn/docking.py` | copy | `domains/pnn/tests/test_docking.py` |
| P-07 | Assay qualification | `pnn/assay.py`, `tests/test_assay.py` | `domains/pnn/assay.py` | copy | `domains/pnn/tests/test_assay.py` |
| P-08 | Preclinical PK/PD | `pnn/preclinical.py`, `tests/test_preclinical.py` | `domains/pnn/preclinical.py` | copy | `domains/pnn/tests/test_preclinical.py` |
| P-09 | SAR, bioisostere and lead ranking | `pnn/sar.py`, `pnn/bioisostere.py`, `pnn/rank.py`, `tests/test_sar.py` | `domains/pnn/sar.py`, `bioisostere.py`, `rank.py` | copy | `domains/pnn/tests/test_sar.py` |
| P-10 | Curation and dedupe | `pnn/curation.py`, `pnn/curate.py`, `tests/test_curation.py` | `domains/pnn/curation.py` | copy | `domains/pnn/tests/test_curation.py` |
| P-11 | IND dossier projection | `pnn/ind.py`, `tests/test_ind.py` | `domains/pnn/ind.py` | copy | `domains/pnn/tests/test_ind.py` |
| P-12 | Pathway simulation and dynamics | `pnn/pathway.py`, `pnn/dynamics.py`, `tests/test_pathway.py`, `tests/test_dynamics.py` | `domains/pnn/pathway.py`, `dynamics.py` | copy | `domains/pnn/tests/` |
| P-13 | Curated data and run outputs | `data/`, `output/`, `tmp_out/` | external; digest reference only | reference | `domains/pnn/tests/test_external_refs.py` |

## obezite-mekanizma-projesi (M4 pack)

| ID | Capability | Source evidence | Host destination | Mode | Acceptance gate |
|---|---|---|---|---|---|
| O-01 | Canonical claim-ledger parsing | `08_ARACLAR/uret.py`, `tests/test_project.py` | `domains/obezite/ledger.py` | copy with injected root | `domains/obezite/tests/test_ledger.py` |
| O-02 | Lossless chunking and claim index | `08_ARACLAR/uret.py`, `create_claim_index.py` | `domains/obezite/ledger.py` | copy | `domains/obezite/tests/test_ledger.py` |
| O-03 | Citation extraction with bibliographic noise removal | `08_ARACLAR/atif.py` | `domains/obezite/citations.py` | copy | `domains/obezite/tests/test_citations.py` |
| O-04 | Ledger dedupe and archive projection | `08_ARACLAR/deduplicate_defter.py` | `domains/obezite/dedup.py` | copy | `domains/obezite/tests/test_dedup.py` |
| O-05 | Synthesis register, evidence summary and file inventory | `08_ARACLAR/sentez_uret.py`, `tests/test_sentez.py` | `domains/obezite/projection.py` | copy | `domains/obezite/tests/test_projection.py` |
| O-06 | Hypothesis/observation/synthesis workflow vocabulary | `03_HIPOTEZLER/`, `04_GOZLEMLER/`, `GUIDELINE.md` | `domains/obezite/workflow.py` | reimplement as data-driven pack | `domains/obezite/tests/test_workflow.py` |
| O-07 | 6.1 GB corpus and generated tables | `02_LITERATUR/`, `09_SENTEZ/` | external; digest reference only | reference | `domains/obezite/tests/test_external_refs.py` |

## Atlas (M4 pack, AL-1.1 compatibility checked)

| ID | Capability | Source evidence | Host destination | Mode | Acceptance gate |
|---|---|---|---|---|---|
| A-01 | Multimodal ingestion: PDF, video, image, EPUB, text, link | `atlas/ingestion.py`, `atlas/sources.py`, `atlas/doc_text.py`, `tests/test_ingestion.py`, `tests/test_sources.py` | `domains/atlas/ingestion.py`, `sources.py`, `doc_text.py` | copy | `domains/atlas/tests/test_ingestion.py` |
| A-02 | Material model: diagrams, posters, podcasts, video, model3d | `atlas/materials.py`, `atlas/models3d.py`, `tests/test_materials.py` | `domains/atlas/materials.py`, `models3d.py` | copy | `domains/atlas/tests/test_materials.py` |
| A-03 | Quoted-evidence text backend | `atlas/text_backend.py`, `atlas/doc_text.py`, `docs/AI_CONTRACT.md` | `domains/atlas/text_backend.py` | copy | `domains/atlas/tests/test_text_backend.py` |
| A-04 | Knowledge graph schema and atomic store | `atlas/schema.py`, `atlas/store.py`, `tests/test_schema.py` | `domains/atlas/schema.py`, `store.py` | copy | `domains/atlas/tests/test_schema.py` |
| A-05 | Flashcards, study pack, learning modes | `atlas/flashcards.py`, `atlas/summaries.py`, `atlas/learning.py`, `tests/test_study_pack.py` | `domains/atlas/flashcards.py`, `summaries.py`, `learning.py` | copy | `domains/atlas/tests/test_study_pack.py` |
| A-06 | Quality checks | `atlas/quality.py`, `tests/test_quality_video.py` | `domains/atlas/quality.py` | copy | `domains/atlas/tests/test_quality.py` |
| A-07 | Offline extractive fallback | `atlas/offline.py`, `tests/test_offline_fallback.py` | `domains/atlas/offline.py` | copy | `domains/atlas/tests/test_offline.py` |
| A-08 | Standalone app/API | `atlas/app.py`, `atlas/cli.py`, `docs/AI_CONTRACT.md` | `domains/atlas/app.py`, `cli.py` | copy inside pack | `domains/atlas/tests/test_app_contract.py` |
| A-09 | AL-1.1 notices and schema id | `LICENSE`, `atlas/schema.py` | `LICENSES/Atlas-AL-1.1.txt`, `REUSE.toml` | preserve | `tests/test_license_notices.py` |
| A-10 | Uploaded media and analysis data | `data/`, `demo/` | external; digest reference only | reference | `domains/atlas/tests/test_external_refs.py` |

## Host-wide contracts

| ID | Contract | Evidence | Destination | Acceptance gate |
|---|---|---|---|---|
| X-01 | Domain-pack registry with name, version, public API, data root | new host contract | `engine/packs.py` | `tests/test_pack_registry.py` |
| X-02 | Additive schema migration harness with dry-run | host `engine/database.py`, ADR-006/ADR-044 | `engine/migrations.py` | `tests/test_migration_harness.py`, golden migration |
| X-03 | External data is referenced by path plus digest, never copied | new host contract | `engine/artifacts.py` | `tests/test_external_refs.py` |
| X-04 | NeuroCore consumes the host through MCP/API only | `lattice/api.py`, `lattice/mcp.py`; NeuroCore consumer docs | `studio/api.py`, `studio/mcp.py` | `tests/test_neurocore_contract.py` |
| X-05 | No cross-domain imports; packs use only public engine API | `tests/test_domain_isolation.py` (new) | repository-wide | `python -m unittest tests.test_domain_isolation` |
| X-06 | License notices preserved for every ported file | `REUSE.toml`, `LICENSES/` | repository-wide | `python scripts/check_licenses.py` (project gate) |
| X-07 | Every source remains runnable and untouched | source SHAs above | external repos | post-merge re-run of all six suites |

## Parity summary

| Source | Rows | Copy/wrap | Reimplement | Surface not ported | External-only |
|---|---:|---:|---:|---:|---:|
| lattice | 16 | 13 | 0 | 0 | 0 |
| N1-Engine | 12 | 0 | 9 | 1 | 0 |
| fluid-universe | 6 | 4 | 1 | 0 | 1 |
| PNN | 13 | 12 | 0 | 0 | 1 |
| obezite | 7 | 5 | 1 | 0 | 1 |
| Atlas | 10 | 8 | 0 | 0 | 1 |
| Host-wide | 7 | 7 | 0 | 0 | 0 |

The only deliberate surface loss is N1's PyQt desktop GUI. Its analysis, models, migration and CSV
import are ported; the source keeps the GUI running.
