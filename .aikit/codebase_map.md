# Codebase Map & Symbol Catalog 🗺️

> **AUTO-GENERATED & VERIFIED BY `scripts/update_knowledge_base.py`**
> This document provides an automated, up-to-date registry of all modules, classes, and exported functions across this repository.

---

## 📊 Codebase Metrics
- **Total Python Modules**: `64`
- **Total Classes**: `56`
- **Total Top-Level Functions**: `189`
- **Total Class Methods**: `341`
- **Total Source Lines**: `9877`

---

## 📦 Modules & Exported Symbols

### [`engine/__init__.py`](engine/__init__.py)
> *Research Engine: provenance-backed claims, pre-registered hypotheses, executable kill tests.*

**Size**: `3` lines (`122` bytes)

---

### [`engine/__main__.py`](engine/__main__.py)
> *Entry point for `python -m engine`.*

**Size**: `5` lines (`97` bytes)

---

### [`engine/analysis.py`](engine/analysis.py)
> *Discovery and ranking over the graph: contradictions, coverage, keystones.*

**Size**: `349` lines (`13422` bytes)

**Functions:**
- `def keywords(text)` - *Content words of an assertion, lowercased and de-duplicated.*
- `def overlap(left, right)` - *Jaccard overlap of two keyword sets, 0.0 when either is empty.*
- `def _pair_score(first, second)`
- `def contradictions(conn, research_ref, min_score)` - *Pairs of supporting and contradicting claims attached to the same question.*
- `def unlinked_contradictions(conn, research_ref, min_score)` - *Claims that contradict each other by keyword overlap but have no `contradicts` edge.*
- `def evidence_matrix(conn, research_ref)` - *Sources x questions: how many claims each source contributes to each question.*
- `def keystone_claims(conn, research_ref, limit)` - *Claims that the rest of the graph leans on, by transitive dependents and inbound edges.*
- `def expose(conn, claim_ref)` - *What a claim would take down with it, plus what cites it.*
- `def claim_statistics(conn, claim_ref, baseline, treatment, seed, resamples, actor)` - *Compare two observation groups of a claim and record that the comparison happened.*
- `def observation_summary(conn, claim_ref)` - *Per-group counts and basic summaries for one claim.*
- `def claim_trend(conn, claim_ref, group, actor)` - *Fit a least-squares trend over a group's observations in recording order.*

---

### [`engine/artifacts.py`](engine/artifacts.py)
> *Artifact I/O: timestamps, output digests and atomic file replacement.*

**Size**: `51` lines (`1755` bytes)

**Functions:**
- `def utc_now()` - *Return a second-resolution UTC timestamp in ISO-8601 form.*
- `def digest(kind, payload)` - *Domain-separated digest: the artifact kind is hashed before the payload.*
- `def sha256_text(value)` - *Hash extracted output so reproducibility is checked without storing it all.*
- `def atomic_write_text(path, text)` - *Write UTF-8 text through a flushed temp file and an atomic replace.*

---

### [`engine/bundle.py`](engine/bundle.py)
> *Portable JSONL export of the evidence graph, and a digest of its content.*

**Size**: `259` lines (`9394` bytes)

**Functions:**
- `def _rows(conn, table, research_id)`
- `def export_records(conn, research_ref)` - *Return the ordered graph records and their per-table counts.*
- `def evidence_records(records)` - *Drop the audit log from the digest input.*
- `def content_records(records)` - *Semantic projection of a record set: run allocation artefacts are dropped.*
- `def _digest(records, kind)`
- `def graph_sha256(conn, research_ref)` - *Exact digest of every evidence record, including run bookkeeping; excludes the audit log.*
- `def content_sha256(conn, research_ref)` - *Digest of the graph's content, stable across a pure re-verification.*
- `def export_jsonl(conn, path, research_ref)` - *Write the graph as deterministic JSONL lines, atomically.*
- `def verify_export(path)` - *Check a snapshot against the digest it carries in its own meta line.*

---

### [`engine/cascade.py`](engine/cascade.py)
> *Transitive invalidation: when a premise collapses, everything built on it collapses too.*

**Size**: `169` lines (`6012` bytes)

**Functions:**
- `def dependents(conn, claim_id)` - *Return every claim that structurally depends on this claim, by depth.*
- `def preview(conn, claim_ref)` - *Show what a collapse would invalidate without writing anything.*
- `def invalidate(conn, claim_ref, status, reason, evidence, actor)` - *Record a failed root claim, then invalidate every dependent in one transaction.*
- `def retract_source(conn, ref, reason, evidence, actor)` - *Retract a source and retire every empirical claim that cites it.*

---

### [`engine/claims.py`](engine/claims.py)
> *Claims: the unit of knowledge, with provenance and an append-only verdict history.*

**Size**: `380` lines (`14665` bytes)

**Functions:**
- `def _to_claim(row)`
- `def _validate_confidence(value)`
- `def add_claim(conn, research_ref, text, kind, source_ref, quote, locator, confidence, kill_test, basis, prerequisites)` - *Record a claim; empirical claims must carry a verbatim quote and a locator.*
- `def get_claim(conn, ref)` - *Fetch one claim by identifier.*
- `def list_claims(conn, research_ref, status)` - *List claims, optionally filtered by program and verdict.*
- `def current_groups_for_claim(conn, claim_id)` - *Verified run groups, bound to the current code and inputs, for a claim's tests.*
- `def set_verdict(conn, claim_ref, status, evidence, note, actor, evidence_group)` - *Append a verdict; promotion needs a kill test, evidence, and current numeric proof.*
- `def prerequisites(conn, claim_id)` - *Return the claims this claim structurally depends on.*
- `def link_claims(conn, src_ref, dst_ref, rel)` - *Add a typed claim-to-claim edge; dependency edges make invalidation transitive.*
- `def record_edge(conn, src_kind, src_id, dst_kind, dst_id, rel)` - *Insert one typed edge, returning the existing id when the edge is already present.*
- `def list_edges(conn, subject_ref)` - *Return every edge touching a claim, in either direction.*
- `def link_to_question(conn, claim_ref, question_ref, stance)` - *Attach a claim to a question with a stance used by the consensus score.*
- `def iter_edges(conn)` - *Yield every edge for audits that need the whole graph.*

---

### [`engine/cli.py`](engine/cli.py)
> *Command-line surface: one entry point for every engine mechanic.*

**Size**: `745` lines (`37306` bytes)

**Functions:**
- `def _build_parser()`
- `def _emit(payload, as_json, text)`
- `def _records_payload(rows)`
- `def _cmd_research(conn, args)`
- `def _cmd_question(conn, args)`
- `def _cmd_source(conn, args)`
- `def _cmd_observation(conn, args)`
- `def _cmd_claim(conn, args)`
- `def _cmd_hypothesis(conn, args)`
- `def _cmd_test(conn, args)`
- `def main(argv)` - *Parse one command, open the database, and dispatch it.*

---

### [`engine/context.py`](engine/context.py)
> *Token-budgeted views: the same graph, measured in tokens for an agent reader.*

**Size**: `191` lines (`7481` bytes)

**Classes:**
- `class View` - *A rendered, bounded view of one program.*
  - Method `.to_dict()`

**Functions:**
- `def estimate_tokens(text)` - *A stable, provider-agnostic estimate: roughly four characters per token.*
- `def _clip(text, width)` - *Shorten one safe line without exceeding the width.*
- `def pack(lines, budget)` - *Fit lines into a budget, always keeping the first, and count what was dropped.*
- `def _render(lines, budget)`
- `def _status_counts(conn, research_id)`
- `def outline(conn, research_ref, budget)` - *One line per question, hypothesis and test, with counts instead of text.*
- `def brief(conn, research_ref, budget)` - *Per question: consensus, the strongest support, and the strongest contradiction.*
- `def claim_brief(conn, claim_ref, budget)` - *One claim, its provenance, its premises and its verdicts, bounded.*

---

### [`engine/database.py`](engine/database.py)
> *SQLite connection, schema versioning and atomic transactions.*

**Size**: `322` lines (`11990` bytes)

**Functions:**
- `def connect(path)` - *Open a database with durability pragmas suitable for a state file.*
- `def _ensure_indexes(conn)` - *Create indexes that depend on migrated columns; safe to run after every migration.*
- `def _add_missing_columns(conn, version)` - *Apply the additive column migrations for one older schema version.*
- `def initialize(conn)` - *Create the schema, migrate an older one, and refuse a future version.*
- `def _count_unbound_numeric(conn)` - *Numeric claims whose promotion verdict predates evidence binding.*
- `def transaction(conn)` - *Run a write atomically; nested calls join the outer transaction.*
- `def next_id(conn, prefix)` - *Allocate a readable, gap-free identifier inside the current transaction.*

---

### [`engine/demo.py`](engine/demo.py)
> *A self-contained demonstration of every engine mechanic in under ten seconds.*

**Size**: `148` lines (`5231` bytes)

**Functions:**
- `def seed_demo(conn)` - *Create one synthetic program that exercises provenance, tests, and cascade.*

---

### [`engine/diffing.py`](engine/diffing.py)
> *Snapshot comparison: what changed between two exported graphs.*

**Size**: `117` lines (`4444` bytes)

**Functions:**
- `def load_jsonl(path)` - *Read an export, dropping its meta line; a malformed file is refused.*
- `def _key(record)` - *Identity of a record: its id, or a digest of a projection that has no id.*
- `def _strip(record)`
- `def _index(records, semantic)` - *Index records by type and identity, optionally collapsing run churn.*
- `def diff_records(old, new, semantic)` - *Compare two record sets and classify added, removed and changed records.*
- `def diff_files(old, new, semantic)` - *Compare two exported snapshots.*
- `def render(result)` - *Render a diff as a compact, deterministic report.*

---

### [`engine/errors.py`](engine/errors.py)
> *Error types that carry a cause and a concrete repair step (Why/Fix triad).*

**Size**: `26` lines (`822` bytes)

**Classes:**
- `class EngineError` - *A user-facing failure with a reason and a repair step.*
  - Method `.__init__(message, why, fix)`
  - Method `.render()`
- `class NotFound` - *A referenced record does not exist.*
  - Method `.__init__(kind, ref)`

---

### [`engine/events.py`](engine/events.py)
> *Append-only event log for actions that are not verdicts.*

**Size**: `97` lines (`2843` bytes)

**Classes:**
- `class Event`

**Functions:**
- `def _to_event(row)`
- `def record(conn, kind, subject, detail, research_id, actor)` - *Append one event. Callers run inside their own write transaction.*
- `def list_events(conn, research_ref, kind, limit)` - *Recent events, newest first, optionally filtered by program and kind.*
- `def count(conn)` - *Total recorded events.*

---

### [`engine/evidence.py`](engine/evidence.py)
> *Evidence identity: which verified run groups are valid for a test right now.*

**Size**: `140` lines (`5331` bytes)

**Functions:**
- `def test_inputs(test)` - *The canonical declared input names of a test.*
- `def binding(test)` - *The identity a run must carry to count as evidence now.*
- `def _groups(conn, test_id, exact)` - *Verified main-role groups for one test, newest first, optionally binding-filtered.*
- `def verified_groups(conn, test_id)` - *Every historical main-role group that passed twice with identical output.*
- `def current_verified_groups(conn, test)` - *Every main-role group valid for the current code, inputs and command, newest first.*
- `def current_verified_group(conn, test)` - *The newest group valid for the current binding, if any.*
- `def control_state(conn, test, group)` - *Whether the declared control was falsified in one run group.*
- `def _claim_tests(conn, claim_id)`
- `def claim_groups(conn, claim_id)` - *Current verified groups across every test bound to a claim.*
- `def claim_has_historical_evidence(conn, claim_id)` - *Whether any test bound to a claim ever produced a verified group.*
- `def claim_tests(conn, claim_id)` - *Every test bound to a claim.*

---

### [`engine/hypotheses.py`](engine/hypotheses.py)
> *Pre-registered hypotheses and their outcomes (the K13 discipline).*

**Size**: `174` lines (`6438` bytes)

**Functions:**
- `def _to_hypothesis(row)`
- `def add_hypothesis(conn, research_ref, statement, criterion, confidence, question_ref)` - *Pre-register a prediction before any outcome is known.*
- `def get_hypothesis(conn, ref)` - *Fetch one hypothesis by identifier.*
- `def list_hypotheses(conn, research_ref)` - *List hypotheses, optionally filtered by program.*
- `def record_outcome(conn, hypothesis_ref, outcome, evidence, note, actor)` - *Close a pre-registered hypothesis with an evidence-backed outcome.*
- `def preregistration_card(conn, hypothesis_ref)` - *Render the pre-registration card an agent writes before searching.*

---

### [`engine/integrity.py`](engine/integrity.py)
> *Graph integrity: provenance, evidence paths, dependency acyclicity and stale dependents.*

**Size**: `574` lines (`21725` bytes)

**Functions:**
- `def _finding(code, severity, subject, message, fix)`
- `def _entity(conn, kind, ref)`
- `def _cycles(conn)`
- `def check(conn)` - *Return every integrity finding; an empty list means the graph is coherent.*
- `def has_errors(findings)` - *Return True when at least one finding blocks a verdict.*
- `def render_markdown(findings)` - *Render findings as a compact audit table.*
- `def render_json(findings)` - *Render findings as stable machine-readable JSON.*
- `def findings_for_research(conn, research_id)` - *Findings attributable to one program: its own records, edges and the program itself.*

---

### [`engine/killtests.py`](engine/killtests.py)
> *Executable kill tests: two agreeing runs, bound to code, inputs and command.*

**Size**: `352` lines (`12867` bytes)

**Functions:**
- `def _to_test(row)`
- `def _to_run(row)`
- `def add_test(conn, research_ref, name, command, claim_ref, hypothesis_ref, expect_exit, timeout_seconds, inputs, control_command)` - *Register an executable test bound to a claim, a hypothesis, its inputs and a control.*
- `def get_test(conn, ref)` - *Fetch one test by identifier.*
- `def list_tests(conn, research_ref)` - *List tests, optionally filtered by program.*
- `def _terminate_tree(process)` - *Kill the process and its children without leaking a detached tree.*
- `def _run_once(command, timeout_seconds)` - *Run one command in the project root and capture a deterministic fingerprint.*
- `def run_test(conn, test_ref, runs)` - *Run a test one or more times, plus its negative control, recording each run's identity.*
- `def _execute(conn, test, command, group, runs, role, tag_prefix, current)` - *Execute one command `runs` times and persist every run under its role.*
- `def _summarise_control(results, expect_exit)` - *A control is falsified when every repetition fails the expectation identically.*
- `def verify_test(conn, test_ref)` - *Run a test twice in separate processes; disagreement or drift is a failure.*
- `def list_runs(conn, test_ref, limit)` - *List recent runs, optionally for one test.*

---

### [`engine/maintenance.py`](engine/maintenance.py)
> *Database maintenance: integrity verification and a crash-safe backup.*

**Size**: `86` lines (`3212` bytes)

**Functions:**
- `def integrity_check(conn)` - *Run SQLite's own checks plus a few facts a reviewer wants before archiving.*
- `def backup(conn, destination)` - *Copy the live database through SQLite's backup API and verify the copy.*

---

### [`engine/manifest.py`](engine/manifest.py)
> *Generated-report manifests and drift detection.*

**Size**: `161` lines (`6250` bytes)

**Functions:**
- `def license_block()` - *Identify the terms the generated artifact is offered under, by id and text digest.*
- `def manifest_path(report_path)` - *The sidecar path for a report, accepting a report or a manifest path.*
- `def build_manifest(conn, research_ref, text)` - *Describe one generated report: schema, digests, counts, findings and limits.*
- `def write_report(conn, research_ref, path)` - *Write the report and its manifest atomically; return both paths and the digests.*
- `def _load_manifest(sidecar)` - *Read a manifest and refuse an unknown schema.*
- `def check_report(conn, research_ref, path, strict)` - *Compare a committed report and its manifest with the current graph.*

---

### [`engine/markdown.py`](engine/markdown.py)
> *Markdown-safe rendering of untrusted text.*

**Size**: `46` lines (`1727` bytes)

**Functions:**
- `def sanitize(text, width)` - *Collapse to one safe line: no control characters, no newlines, capped width.*
- `def cell(text, width)` - *A Markdown table cell: sanitized, with pipe and backtick escaped.*
- `def bullet(text, width)` - *One list or heading fragment: sanitized, with backticks escaped.*
- `def code(text, width)` - *A fenced inline code fragment safe for a single-line context.*

---

### [`engine/merging.py`](engine/merging.py)
> *Claim merging: one survivor, every edge repointed, duplicates retired.*

**Size**: `117` lines (`4332` bytes)

**Functions:**
- `def merge_claims(conn, keep_ref, drop_refs, note, actor)` - *Keep one claim, repoint edges from the duplicates, and retire the duplicates.*

---

### [`engine/models.py`](engine/models.py)
> *Frozen domain records and the engine's closed vocabularies.*

**Size**: `177` lines (`3632` bytes)

**Classes:**
- `class Research`
- `class Source`
- `class Question`
- `class Claim`
- `class Hypothesis`
- `class KillTest`
- `class TestRun`
- `class Observation`
- `class Finding`

---

### [`engine/observations.py`](engine/observations.py)
> *Recorded observations: the raw measurements a numeric claim is computed from.*

**Size**: `153` lines (`5354` bytes)

**Functions:**
- `def _to_observation(row)`
- `def add_observation(conn, claim_ref, group_label, value, note, at)` - *Record one measurement in a named group; non-finite values are refused.*
- `def get_observation(conn, ref)` - *Fetch one observation by identifier.*
- `def list_observations(conn, claim_ref, group_label, include_voided)` - *Observations of a claim, oldest first, excluding voided rows by default.*
- `def void_observation(conn, ref, reason, actor)` - *Retire a measurement without deleting it; the reason stays in the record.*
- `def group_values(conn, claim_ref)` - *Non-voided values per group, in insertion order.*

---

### [`engine/provenance.py`](engine/provenance.py)
> *Workspace provenance: the code and input identity a test run or report is bound to.*

**Size**: `187` lines (`6107` bytes)

**Classes:**
- `class Fingerprint` - *Identity of the engine code and the declared inputs.*
  - Method `.to_dict()`

**Functions:**
- `def _digest(entries)` - *Hash `(name, kind, content)` triples with length prefixes.*
- `def code_sha256()` - *Hash the engine package; the test harness and prose are deliberately excluded.*
- `def _inside(path)`
- `def _name_for(path, raw)` - *A stable name: project-relative when possible, otherwise the raw declaration.*
- `def _expand(raw)` - *Expand one declaration into canonical names, deterministically.*
- `def resolve_inputs(paths)` - *Canonical, sorted, de-duplicated input names for a declaration list.*
- `def inputs_sha256(paths)` - *Hash declared inputs; an absent declaration hashes as a distinct typed marker.*
- `def fingerprint(inputs)` - *Compute the current code and input fingerprint.*
- `def git_state()` - *Return `(commit, dirty)`; a missing repository reports `no-git` and dirty.*
- `def environment()` - *Runtime identity recorded for diagnosis, not used for binding.*
- `def provenance(inputs)` - *One block combining binding data with diagnostic metadata.*

---

### [`engine/questions.py`](engine/questions.py)
> *Research questions that collect supporting and contradicting claims.*

**Size**: `67` lines (`2440` bytes)

**Functions:**
- `def _to_question(row)`
- `def add_question(conn, research_ref, text)` - *Add an open question to a program.*
- `def get_question(conn, ref)` - *Fetch one question by identifier.*
- `def list_questions(conn, research_ref)` - *List questions, optionally filtered by program.*
- `def close_question(conn, ref)` - *Mark a question resolved without deleting its evidence.*

---

### [`engine/researches.py`](engine/researches.py)
> *Research programs: the top-level containers the engine is asked to investigate.*

**Size**: `91` lines (`3450` bytes)

**Functions:**
- `def _slugify(conn, title)`
- `def _to_research(row)`
- `def create_research(conn, title, scope, slug)` - *Create a research program with a stable, unique slug.*
- `def get_research(conn, ref)` - *Resolve a program by identifier or slug.*
- `def list_researches(conn)` - *List programs in creation order.*
- `def research_counts(conn, research_id)` - *Return the record counts that summarise a program.*

---

### [`engine/screening.py`](engine/screening.py)
> *Source screening and the PRISMA flow.*

**Size**: `114` lines (`4319` bytes)

**Functions:**
- `def set_screening(conn, ref, status, reason, actor)` - *Record one screening decision; an out-status always carries a reason.*
- `def prisma_flow(conn, research_ref)` - *Counts and exclusion reasons across the review phases.*
- `def unscreened_sources(conn, research_ref)` - *Sources still in the identified state, oldest first.*

---

### [`engine/sources.py`](engine/sources.py)
> *Bibliographic sources: the only place literature text may enter the graph.*

**Size**: `145` lines (`4989` bytes)

**Functions:**
- `def _to_source(row)`
- `def add_source(conn, research_ref, title, year, doi, url, authors, kind)` - *Register a source; claims cannot cite it before it exists.*
- `def get_source(conn, ref)` - *Fetch one source by identifier.*
- `def list_sources(conn, research_ref)` - *List sources, optionally filtered by program.*
- `def set_source_status(conn, ref, status, note, actor)` - *Change a source's evidence status without deleting the record.*

---

### [`engine/stats.py`](engine/stats.py)
> *Deterministic statistics for recorded observations.*

**Size**: `309` lines (`11549` bytes)

**Functions:**
- `def sample_sd(values)` - *Sample standard deviation; zero for fewer than two values.*
- `def cohens_d(baseline, treatment)` - *Standardized mean difference using the pooled standard deviation.*
- `def _betacf(a, b, x)` - *Continued fraction for the incomplete beta function (modified Lentz).*
- `def _betai(a, b, x)` - *Regularized incomplete beta I_x(a, b).*
- `def t_two_sided_p(t, df)` - *Two-sided p-value for a t statistic with the given degrees of freedom.*
- `def welch_t(baseline, treatment)` - *Welch's unequal-variance t test, with the zero-variance case handled explicitly.*
- `def _ranks(values)` - *Average ranks for ties, returning the ranks and the tie-group sizes.*
- `def _u_distribution(n1, n2)` - *Counts of the U statistic under the null, by dynamic programming.*
- `def _exact_u_two_sided_p(u1, n1, n2)` - *Exact two-sided p for the U statistic when the sample is small and untied.*
- `def mann_whitney(baseline, treatment)` - *Mann-Whitney U: exact for small untied samples, continuity-corrected asymptotic otherwise.*
- `def bootstrap_ci(baseline, treatment, seed, resamples)` - *Percentile bootstrap interval for the difference in means, reproducibly seeded.*
- `def linregress(xs, ys)` - *Least-squares slope, intercept, correlation and two-sided p for paired points.*
- `def compare_groups(baseline, treatment, seed, resamples)` - *Compare two recorded groups and state the result, the agreement and the caveats.*

---

### [`engine/synthesis.py`](engine/synthesis.py)
> *Evidence synthesis: weighted consensus, contradiction pairs, and generated reports.*

**Size**: `348` lines (`13919` bytes)

**Functions:**
- `def stance_claims(conn, question_id)`
- `def consensus(conn, question_ref)` - *Confidence-weighted support minus contradiction in [-1, 1].*
- `def _contradictions(conn, question_id)`
- `def _provenance_cell(conn, row)`
- `def report(conn, research_ref)` - *Render a full, reproducible research report from the graph.*
- `def scorecard(conn, research_ref)` - *Render one line per claim, ordered by status then identifier.*
- `def claim_detail(conn, claim_ref)` - *Render one claim with provenance, dependencies, verdicts and linked tests.*
- `def inventory(conn)` - *Return engine-wide counts used by the CLI overview.*

---

### [`tests/__init__.py`](tests/__init__.py)
> *Regression shield for the research engine.*

**Size**: `1` lines (`49` bytes)

---

### [`tests/support.py`](tests/support.py)
> *Shared fixtures: a fresh in-memory database per test.*

**Size**: `64` lines (`2181` bytes)

**Classes:**
- `class DatabaseCase` - *Give each test an isolated schema and connection.*
  - Method `.setUp()`
  - Method `.add_research(title)`
  - Method `.add_source(research, title)`
  - Method `.add_empirical(research, text)`

**Functions:**
- `def memory_connection()` - *Return an initialized in-memory connection for direct module tests.*
- `def force_numeric(conn, claim_id, group)` - *Write a NUMERIC state directly, simulating a record that predates the promotion gate.*

---

### [`tests/test_analysis.py`](tests/test_analysis.py)
> *Discovery: contradictions, coverage matrix, keystone ranking, exposure.*

**Size**: `102` lines (`4618` bytes)

**Classes:**
- `class KeywordTests`
  - Method `.test_stopwords_are_removed()`
  - Method `.test_overlap_is_jaccard()`
- `class AnalysisTests`
  - Method `.setUp()`
  - Method `.test_contradictions_pair_within_a_question()`
  - Method `.test_contradictions_are_ranked_by_score()`
  - Method `.test_min_score_filters()`
  - Method `.test_claims_on_different_questions_are_not_paired()`
  - Method `.test_unlinked_contradictions_skip_recorded_edges()`
  - Method `.test_matrix_counts_claims_per_source_and_question()`
  - Method `.test_matrix_ignores_assumed_claims()`
  - Method `.test_keystone_ranks_by_downstream_and_inbound()`
  - Method `.test_expose_lists_dependents_and_inbound()`

---

### [`tests/test_audit_fixes.py`](tests/test_audit_fixes.py)
> *Regression tests for defects found in the T-004 audit.*

**Size**: `126` lines (`5788` bytes)

**Classes:**
- `class RunIdentityTests`
  - Method `.test_projected_runs_carry_distinct_stable_ids()`
  - Method `.test_semantic_index_does_not_collapse_runs()`
  - Method `.test_a_changed_run_is_reported_by_identity()`
- `class ContradictionScopeTests`
  - Method `.test_the_same_pair_on_two_questions_is_reported_twice()`
- `class MergeFollowThroughTests`
  - Method `.setUp()`
  - Method `.test_tests_follow_the_survivor()`
  - Method `.test_merging_into_a_retired_survivor_is_refused()`
  - Method `.test_a_test_left_on_a_retired_claim_warns()`
- `class ScopedAuditTests`
  - Method `.test_outline_counts_only_its_own_program()`

---

### [`tests/test_bundle.py`](tests/test_bundle.py)
> *JSONL export is complete, scoped and deterministic in order.*

**Size**: `163` lines (`6841` bytes)

**Classes:**
- `class BundleTests`
  - Method `.setUp()`
  - Method `.test_export_writes_meta_first_and_every_record()`
  - Method `.test_scoped_export_excludes_other_programs()`
  - Method `.test_export_replaces_the_file_atomically()`
  - Method `.test_export_includes_observations_and_events()`
  - Method `.test_observation_changes_the_digests()`
  - Method `.test_generation_events_do_not_change_the_digests()`
  - Method `.test_export_verifies_its_own_digest()`
  - Method `.test_a_tampered_record_is_detected()`
  - Method `.test_a_legacy_export_without_a_digest_is_refused()`
  - Method `.test_a_count_mismatch_is_reported()`
  - Method `.test_an_unsupported_schema_is_reported_not_trusted()`
  - Method `.test_a_non_numeric_record_count_is_handled()`

---

### [`tests/test_cascade.py`](tests/test_cascade.py)
> *A collapsed premise invalidates every dependent transitively.*

**Size**: `68` lines (`2995` bytes)

**Classes:**
- `class CascadeTests`
  - Method `._chain()`
  - Method `.test_dependents_are_transitive_and_ordered_by_depth()`
  - Method `.test_preview_writes_nothing()`
  - Method `.test_collapse_invalidates_every_dependent()`
  - Method `.test_retracted_dependent_is_not_rewritten()`
  - Method `.test_collapse_requires_reason_and_failed_status()`

---

### [`tests/test_claims.py`](tests/test_claims.py)
> *Provenance requirements and the append-only verdict lifecycle.*

**Size**: `139` lines (`5802` bytes)

**Classes:**
- `class ClaimTests`
  - Method `.test_empirical_claim_needs_source_quote_and_locator()`
  - Method `.test_derived_claim_needs_a_basis_or_premise()`
  - Method `.test_quote_is_refused_for_non_empirical_claims()`
  - Method `.test_confidence_bounds_are_enforced()`
  - Method `.test_source_must_share_the_program()`
  - Method `.test_prerequisites_create_dependency_edges()`
  - Method `.test_verdict_requires_evidence()`
  - Method `.test_promotion_requires_a_kill_test()`
  - Method `.test_verdict_history_preserves_previous_status()`
  - Method `.test_same_status_is_refused()`
  - Method `.test_promotion_blocked_by_failed_premise()`
  - Method `.test_links_are_typed_and_directional()`
  - Method `.test_list_filters_by_status()`

---

### [`tests/test_cli.py`](tests/test_cli.py)
> *The CLI surface: JSON output, exit codes and the error triad.*

**Size**: `335` lines (`13462` bytes)

**Classes:**
- `class CliTests`
  - Method `.setUp()`
  - Method `.run_cli(*args)`
  - Method `.test_init_and_demo()`
  - Method `.test_demo_passes_integrity_gate()`
  - Method `.test_error_triad_on_missing_quote()`
  - Method `.test_report_and_scorecard()`
  - Method `.test_kill_test_verify_exit_code()`
  - Method `.test_export_writes_a_file()`
  - Method `.test_missing_database_record_exits_one()`
  - Method `.test_report_check_ignores_reverification()`
  - Method `.test_source_status_and_retraction_from_the_cli()`
  - Method `.test_inventory_reports_provenance()`
  - Method `.test_verdict_group_flag_is_accepted()`
  - Method `.test_outline_and_brief_respect_the_budget()`
  - Method `.test_analysis_commands()`
  - Method `.test_diff_command_exit_codes()`
  - Method `.test_claim_merge_and_context()`
  - Method `.test_screening_and_prisma()`
  - Method `.test_events_are_listed()`
  - Method `.test_db_integrity_and_backup()`
  - Method `.test_negative_control_through_the_cli()`
  - Method `.test_observations_and_statistics()`
  - Method `.test_observation_errors_use_the_triad()`
  - Method `.test_analysis_trend()`
  - Method `.test_export_check_detects_tampering()`
  - Method `.test_export_check_refuses_a_research_filter()`
  - Method `.test_export_check_fails_on_an_unsupported_schema()`

---

### [`tests/test_context.py`](tests/test_context.py)
> *Token-budgeted views: estimation, packing and omission accounting.*

**Size**: `87` lines (`3067` bytes)

**Classes:**
- `class TokenTests`
  - Method `.test_estimate_is_character_quarters()`
  - Method `.test_pack_keeps_the_first_line_even_when_over_budget()`
  - Method `.test_pack_keeps_everything_that_fits()`
  - Method `.test_pack_rejects_a_non_positive_budget()`
- `class ViewTests`
  - Method `.setUp()`
  - Method `.test_outline_lists_questions_hypotheses_tests_and_audit()`
  - Method `.test_outline_reports_omissions()`
  - Method `.test_brief_shows_support_and_contradiction()`
  - Method `.test_views_are_deterministic()`
  - Method `.test_default_budget_is_positive()`
  - Method `.test_claim_view_carries_provenance_and_verdicts()`
  - Method `.test_budget_is_respected()`

---

### [`tests/test_controls.py`](tests/test_controls.py)
> *Negative controls: a test must be able to fail before its pass is evidence.*

**Size**: `125` lines (`5231` bytes)

**Classes:**
- `class ControlTests`
  - Method `.setUp()`
  - Method `._script(name, code)`
  - Method `._test(control)`
  - Method `.test_control_runs_are_stored_with_their_role()`
  - Method `.test_a_control_that_passes_blocks_verification()`
  - Method `.test_an_irreproducible_control_blocks_verification()`
  - Method `.test_absence_of_a_control_is_reported_but_not_blocking()`
  - Method `.test_editing_the_control_retires_the_evidence()`
  - Method `.test_control_state_reports_absence_explicitly()`
  - Method `.test_outline_counts_the_program_screening()`
  - Method `.test_adding_a_control_later_clears_the_error()`

---

### [`tests/test_diffing.py`](tests/test_diffing.py)
> *Snapshot diff: semantic by default, exact on request.*

**Size**: `113` lines (`4477` bytes)

**Classes:**
- `class DiffTests`
  - Method `.setUp()`
  - Method `.test_identical_exports_have_no_differences()`
  - Method `.test_a_new_claim_is_added()`
  - Method `.test_semantic_mode_ignores_run_churn()`
  - Method `.test_a_changed_status_is_reported()`
  - Method `.test_missing_snapshot_is_reported()`
  - Method `.test_malformed_snapshot_is_reported()`
  - Method `.test_render_lists_each_change()`
  - Method `.test_a_second_run_with_the_same_identity_cannot_mask_a_change()`

---

### [`tests/test_docs.py`](tests/test_docs.py)
> *Documentation and project memory stay discoverable and within budget.*

**Size**: `85` lines (`3321` bytes)

**Classes:**
- `class DocsTests`
  - Method `.test_readme_has_the_cold_start_contract()`
  - Method `.test_architecture_and_mechanics_documents_exist()`
  - Method `.test_project_memory_declares_the_test_command()`
  - Method `.test_readme_tree_names_real_modules()`
  - Method `.test_readme_documents_the_current_schema_and_gates()`
  - Method `.test_architecture_documents_binding_and_digests()`

---

### [`tests/test_events.py`](tests/test_events.py)
> *Event log: append-only record of actions that are not verdicts.*

**Size**: `97` lines (`4089` bytes)

**Classes:**
- `class EventTests`
  - Method `.test_record_and_list_newest_first()`
  - Method `.test_filters_by_kind_and_research()`
  - Method `.test_detail_is_flattened()`
  - Method `.test_source_status_is_recorded()`
  - Method `.test_screening_is_recorded()`
  - Method `.test_merge_is_recorded_once()`
  - Method `.test_report_generation_is_recorded()`
  - Method `.test_migration_records_an_event()`

---

### [`tests/test_golden.py`](tests/test_golden.py)
> *Golden run: the whole command surface, end to end, in a fresh database.*

**Size**: `164` lines (`8063` bytes)

**Classes:**
- `class GoldenRunTests`
  - Method `.setUp()`
  - Method `.run_cli(*args)`
  - Method `.must(*args)`
  - Method `.test_every_command_composes()`

---

### [`tests/test_hypotheses.py`](tests/test_hypotheses.py)
> *Pre-registration precedes outcomes and cards carry the falsification criterion.*

**Size**: `57` lines (`2368` bytes)

**Classes:**
- `class HypothesisTests`
  - Method `.test_criterion_is_required()`
  - Method `.test_registration_is_immediate_and_card_is_rendered()`
  - Method `.test_outcome_requires_evidence_and_closes_once()`
  - Method `.test_unknown_outcome_is_refused()`

---

### [`tests/test_inputs.py`](tests/test_inputs.py)
> *Declared inputs: glob expansion, directory refusal, absence and collision safety.*

**Size**: `70` lines (`2844` bytes)

**Classes:**
- `class InputTests`
  - Method `.setUp()`
  - Method `.test_glob_expands_to_each_matching_file()`
  - Method `.test_glob_result_tracks_content()`
  - Method `.test_a_new_file_matching_the_glob_changes_the_digest()`
  - Method `.test_unmatched_glob_is_recorded_and_changes_when_files_appear()`
  - Method `.test_directory_input_is_refused()`
  - Method `.test_absent_file_does_not_collide_with_the_word_missing()`
  - Method `.test_declarations_are_deduplicated_and_sorted()`
  - Method `.test_directory_contents_are_not_silently_ignored()`

---

### [`tests/test_integrity.py`](tests/test_integrity.py)
> *Every integrity rule must detect the corruption it names.*

**Size**: `265` lines (`11975` bytes)

**Classes:**
- `class IntegrityTests`
  - Method `._clean_program()`
  - Method `.test_clean_program_has_no_errors()`
  - Method `.test_missing_provenance_is_detected()`
  - Method `.test_source_without_identifier_is_detected()`
  - Method `.test_promoted_claim_needs_kill_test()`
  - Method `.test_numeric_claim_needs_two_run_test()`
  - Method `.test_failed_status_needs_evidence()`
  - Method `.test_hypothesis_outcome_needs_verdict()`
  - Method `.test_dependency_cycle_is_detected()`
  - Method `.test_dangling_and_self_edges_are_detected()`
  - Method `.test_cross_program_edge_is_detected()`
  - Method `.test_stale_dependent_is_detected()`
  - Method `.test_gaps_and_duplicates_are_warnings()`
  - Method `.test_empty_program_warns()`
  - Method `.test_renderers_are_stable()`
  - Method `.test_stale_numeric_evidence_is_detected()`
  - Method `.test_retracted_source_blocks_a_live_claim()`
  - Method `.test_expression_of_concern_is_a_warning()`
  - Method `.test_unknown_is_recorded_with_a_reason()`
  - Method `.test_unknown_without_a_reason_warns()`
  - Method `.test_unknown_is_not_a_failure_state()`
  - Method `.test_promotion_is_blocked_by_an_unknown_premise()`
  - Method `.test_out_of_order_hypothesis_outcome_is_scoped_to_its_hypothesis()`

**Functions:**
- `def codes(findings)`

---

### [`tests/test_killtests.py`](tests/test_killtests.py)
> *Kill tests: binding, two-run agreement, expected exits and bounded teardown.*

**Size**: `144` lines (`6210` bytes)

**Classes:**
- `class KillTestTests`
  - Method `.setUp()`
  - Method `._script(name, body)`
  - Method `.test_test_must_be_bound_to_a_target()`
  - Method `.test_two_runs_agree_and_record_a_verified_group()`
  - Method `.test_disagreeing_runs_fail_reproducibility()`
  - Method `.test_expected_exit_code_is_honoured()`
  - Method `.test_ordinary_failure_is_reported()`
  - Method `.test_timeout_kills_the_command_and_fails()`
  - Method `.test_binding_matches_after_verification()`
  - Method `.test_editing_the_command_invalidates_the_binding()`
  - Method `.test_changing_a_declared_input_invalidates_the_binding()`
  - Method `.test_run_records_the_binding_and_git_state()`

---

### [`tests/test_maintenance.py`](tests/test_maintenance.py)
> *Database maintenance: integrity verification and verified backups.*

**Size**: `81` lines (`3291` bytes)

**Classes:**
- `class MaintenanceTests`
  - Method `.setUp()`
  - Method `.test_integrity_reports_ok_and_counts()`
  - Method `.test_integrity_detects_a_foreign_key_violation()`
  - Method `.test_backup_produces_a_readable_copy()`
  - Method `.test_backup_refuses_to_overwrite()`
  - Method `.test_backup_leaves_no_temporary_file()`
  - Method `.test_backup_of_a_database_with_events_copies_them()`

---

### [`tests/test_manifest.py`](tests/test_manifest.py)
> *Generated report manifests and drift detection.*

**Size**: `171` lines (`7216` bytes)

**Classes:**
- `class ManifestTests`
  - Method `.setUp()`
  - Method `.test_write_report_creates_report_and_manifest()`
  - Method `.test_check_passes_on_an_unchanged_graph()`
  - Method `.test_graph_change_is_reported_as_drift()`
  - Method `.test_missing_manifest_is_an_error()`
  - Method `.test_unknown_manifest_schema_is_refused()`
  - Method `.test_manifest_identifies_the_license()`
  - Method `.test_license_change_is_reported_as_drift()`
  - Method `.test_report_prints_its_limits()`
  - Method `.test_reverification_does_not_report_content_drift()`
  - Method `.test_strict_check_reports_record_churn()`
  - Method `.test_tampered_counts_are_reported()`
  - Method `.test_another_program_does_not_dirty_a_committed_report()`
  - Method `.test_strict_check_passes_right_after_generation()`

---

### [`tests/test_markdown.py`](tests/test_markdown.py)
> *Untrusted text: control characters, newlines and table syntax must not escape a cell.*

**Size**: `50` lines (`1645` bytes)

**Classes:**
- `class SanitizeTests`
  - Method `.test_newlines_collapse()`
  - Method `.test_control_characters_are_removed()`
  - Method `.test_heading_injection_cannot_survive()`
  - Method `.test_width_is_respected_and_marked()`
  - Method `.test_zero_width_means_no_cap()`
- `class CellTests`
  - Method `.test_pipe_is_escaped()`
  - Method `.test_backtick_is_escaped()`
  - Method `.test_backslash_is_escaped_first()`
  - Method `.test_cell_is_a_single_line()`
  - Method `.test_bullet_and_code_are_single_line()`

---

### [`tests/test_merging.py`](tests/test_merging.py)
> *Merging duplicates: survivor, repointed edges, retired duplicates, history kept.*

**Size**: `93` lines (`4146` bytes)

**Classes:**
- `class MergeTests`
  - Method `.setUp()`
  - Method `.test_merge_retires_the_duplicate_and_keeps_history()`
  - Method `.test_edges_are_repointed_to_the_survivor()`
  - Method `.test_dependency_edges_survive_and_feed_the_survivor()`
  - Method `.test_merge_clears_the_duplicate_warning()`
  - Method `.test_self_merge_is_refused()`
  - Method `.test_empty_duplicate_list_is_refused()`
  - Method `.test_retired_duplicate_is_refused()`
  - Method `.test_cross_program_merge_is_refused()`
  - Method `.test_linking_two_merged_claims_does_not_leave_a_self_edge()`

---

### [`tests/test_migration.py`](tests/test_migration.py)
> *Schema migration: an older database is repaired, not rejected or wiped.*

**Size**: `196` lines (`8522` bytes)

**Classes:**
- `class MigrationTests`
  - Method `._old_database()`
  - Method `.test_version_one_database_is_migrated_in_place()`
  - Method `.test_existing_rows_are_preserved()`
  - Method `.test_migration_is_idempotent()`
  - Method `.test_future_version_is_refused_without_changes()`
  - Method `.test_fresh_database_declares_the_current_version()`
  - Method `.test_verdict_gains_the_evidence_group_column()`
  - Method `.test_migration_reports_the_unbound_numeric_claims()`
  - Method `.test_version_two_database_gains_only_the_verdict_column()`
  - Method `.test_observation_table_exists_after_migration()`
  - Method `.test_version_four_database_gains_the_observation_table()`

---

### [`tests/test_models.py`](tests/test_models.py)
> *Vocabularies are closed and records are immutable.*

**Size**: `53` lines (`1607` bytes)

**Classes:**
- `class ModelTests`
  - Method `.test_status_vocabulary_is_closed()`
  - Method `.test_dependency_relations_are_explicit()`
  - Method `.test_claim_is_frozen()`

---

### [`tests/test_observations.py`](tests/test_observations.py)
> *Observations: raw values, their voiding, and the statistics projection over them.*

**Size**: `201` lines (`9695` bytes)

**Classes:**
- `class ObservationTests`
  - Method `.setUp()`
  - Method `.test_values_are_recorded_in_order()`
  - Method `.test_non_finite_values_are_refused()`
  - Method `.test_invalid_group_is_refused()`
  - Method `.test_groups_are_lowercased()`
  - Method `.test_void_retires_without_deleting()`
  - Method `.test_void_requires_a_reason_and_happens_once()`
  - Method `.test_void_is_logged()`
  - Method `.test_statistics_compare_the_groups()`
  - Method `.test_missing_group_lists_available_groups()`
  - Method `.test_statistics_are_logged_and_clear_the_warning()`
  - Method `.test_summary_and_detail()`
  - Method `.test_voided_values_are_excluded_from_statistics()`
  - Method `.test_trend_is_fitted_over_recording_order()`
  - Method `.test_trend_needs_a_group()`
  - Method `.test_short_series_warns_instead_of_pretending()`
  - Method `.test_more_than_two_groups_warns_about_uncorrected_comparison()`
  - Method `.test_group_labels_are_case_insensitive()`
  - Method `.test_a_group_cannot_be_compared_with_itself()`
  - Method `.test_too_few_resamples_are_refused()`
  - Method `.test_trend_labels_are_case_insensitive()`
  - Method `.test_new_observations_after_a_run_warn_again()`
  - Method `.test_a_void_after_a_run_warns_again()`
  - Method `.test_a_short_trend_says_it_is_insufficient()`
  - Method `.test_a_claim_whose_observations_were_all_voided_does_not_warn()`

---

### [`tests/test_promotion.py`](tests/test_promotion.py)
> *Promotion gate: a NUMERIC verdict must cite a current, verified run group.*

**Size**: `94` lines (`4148` bytes)

**Classes:**
- `class PromotionTests`
  - Method `.setUp()`
  - Method `._verified_test()`
  - Method `.test_numeric_without_a_test_is_refused()`
  - Method `.test_numeric_derives_the_current_group()`
  - Method `.test_explicit_group_is_recorded()`
  - Method `.test_unknown_group_is_refused()`
  - Method `.test_promotion_on_a_changed_command_is_detected()`
  - Method `.test_proven_promotion_needs_no_group()`

---

### [`tests/test_provenance.py`](tests/test_provenance.py)
> *Workspace provenance: code and input identity used to bind evidence.*

**Size**: `91` lines (`3447` bytes)

**Classes:**
- `class ProvenanceTests`
  - Method `.test_code_digest_is_stable_and_shaped()`
  - Method `.test_inputs_digest_tracks_content()`
  - Method `.test_missing_input_hashes_distinctly()`
  - Method `.test_input_order_does_not_matter()`
  - Method `.test_fingerprint_combines_code_and_inputs()`
  - Method `.test_git_state_reports_a_pair()`
  - Method `.test_environment_names_runtime()`
  - Method `.test_provenance_block_has_binding_and_diagnostics()`

---

### [`tests/test_research.py`](tests/test_research.py)
> *Program creation, slug resolution and counts.*

**Size**: `40` lines (`1581` bytes)

**Classes:**
- `class ResearchTests`
  - Method `.test_create_and_resolve_by_slug()`
  - Method `.test_duplicate_slug_is_suffixed()`
  - Method `.test_invalid_slug_is_refused()`
  - Method `.test_missing_program_is_reported()`
  - Method `.test_counts_include_open_questions()`

---

### [`tests/test_screening.py`](tests/test_screening.py)
> *Screening decisions and the PRISMA flow.*

**Size**: `85` lines (`3747` bytes)

**Classes:**
- `class ScreeningTests`
  - Method `.setUp()`
  - Method `.test_new_sources_are_identified()`
  - Method `.test_vocabularies_are_closed()`
  - Method `.test_out_status_defaults_to_other_reason()`
  - Method `.test_reason_is_required_to_be_known()`
  - Method `.test_reason_is_cleared_for_an_in_status()`
  - Method `.test_unknown_status_and_repeat_are_refused()`
  - Method `.test_prisma_counts_and_fraction()`
  - Method `.test_excluded_source_citing_claim_warns()`
  - Method `.test_included_source_does_not_warn()`

---

### [`tests/test_sources_questions.py`](tests/test_sources_questions.py)
> *Source identifiers and question lifecycle.*

**Size**: `48` lines (`1949` bytes)

**Classes:**
- `class SourceQuestionTests`
  - Method `.test_source_requires_an_identifier()`
  - Method `.test_source_accepts_doi_or_url()`
  - Method `.test_source_rejects_bad_kind_and_year()`
  - Method `.test_question_closes_without_deleting()`
  - Method `.test_empty_question_is_refused()`

---

### [`tests/test_sources_retraction.py`](tests/test_sources_retraction.py)
> *Source status and retraction cascade.*

**Size**: `118` lines (`5098` bytes)

**Classes:**
- `class SourceStatusTests`
  - Method `.test_downgrade_requires_a_note()`
  - Method `.test_unknown_status_and_repeat_are_refused()`
  - Method `.test_retraction_requires_a_reason()`
  - Method `.test_retraction_retires_claims_and_dependents()`
  - Method `.test_retracting_twice_is_refused()`
  - Method `.test_claims_are_left_alone_when_already_failed()`
  - Method `.test_retracted_source_is_clean_after_cascade()`
  - Method `.test_reinstatement_requires_a_note_and_keeps_claim_verdicts()`

---

### [`tests/test_stats.py`](tests/test_stats.py)
> *Statistics: values checked against an independent implementation, behaviour checked here.*

**Size**: `132` lines (`5151` bytes)

**Classes:**
- `class DistributionTests`
  - Method `.test_sample_sd()`
  - Method `.test_t_p_value_matches_reference()`
  - Method `.test_t_p_value_edges()`
- `class TestTests`
  - Method `.test_welch_matches_reference()`
  - Method `.test_welch_degenerate_group()`
  - Method `.test_welch_zero_variance()`
  - Method `.test_mann_whitney_exact_matches_reference()`
  - Method `.test_mann_whitney_uses_asymptotic_with_ties()`
  - Method `.test_mann_whitney_empty()`
  - Method `.test_effect_size_matches_reference()`
  - Method `.test_effect_size_needs_two_values_per_group()`
- `class IntervalTests`
  - Method `.test_bootstrap_is_seeded_and_reproducible()`
  - Method `.test_bootstrap_brackets_the_difference()`
  - Method `.test_bootstrap_empty()`
- `class RegressionTests`
  - Method `.test_linregress_matches_reference()`
  - Method `.test_linregress_too_few_points()`
  - Method `.test_linregress_flat_line()`
- `class CompareTests`
  - Method `.test_significant_difference_with_agreeing_tests()`
  - Method `.test_small_groups_warn()`
  - Method `.test_zero_variance_warns()`
  - Method `.test_ties_are_disclosed()`

---

### [`tests/test_synthesis.py`](tests/test_synthesis.py)
> *Consensus weighting and generated reports.*

**Size**: `116` lines (`5273` bytes)

**Classes:**
- `class SynthesisTests`
  - Method `._question_with_opposition()`
  - Method `.test_consensus_weights_status_and_confidence()`
  - Method `.test_report_contains_evidence_and_contradictions()`
  - Method `.test_scorecard_orders_failed_claims_first()`
  - Method `.test_claim_detail_shows_verdict_history()`
  - Method `.test_untrusted_text_cannot_break_a_table()`
  - Method `.test_inventory_counts_every_table()`
  - Method `.test_report_excludes_another_programs_findings()`
  - Method `.test_report_lists_measurements_and_the_last_run()`

---
