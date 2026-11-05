# Codebase Map & Symbol Catalog 🗺️

> **AUTO-GENERATED & VERIFIED BY `scripts/update_knowledge_base.py`**
> This document provides an automated, up-to-date registry of all modules, classes, and exported functions across this repository.

---

## 📊 Codebase Metrics
- **Total Python Modules**: `84`
- **Total Classes**: `86`
- **Total Top-Level Functions**: `280`
- **Total Class Methods**: `610`
- **Total Source Lines**: `18352`

---

## 📦 Modules & Exported Symbols

### [`engine/__init__.py`](engine/__init__.py)
> *Research Engine: provenance-backed claims, pre-registered hypotheses, executable kill tests.*

**Size**: `3` lines (`122` bytes)

---

### [`engine/__main__.py`](engine/__main__.py)
> *Entry point for `python -m engine`.*

**Size**: `6` lines (`128` bytes)

---

### [`engine/ai.py`](engine/ai.py)
> *AI provenance adapter: notarize model I/O, ingest UNVERIFIED claims, propose template tests.*

**Size**: `507` lines (`19242` bytes)

**Functions:**
- `def actor_for(model_id)` - *Attribution for AI-proximate actions: the model, not the default agent.*
- `def _to_artifact(row)`
- `def _validate_cited(cited)` - *Check citation shape only; existence is enforced at ingest and by AI-001.*
- `def _cited_entries(artifact)` - *Parse the stored cited payload; shape was checked at record time.*
- `def _ensure_cited_resolve(conn, artifact, source_ref)` - *Fail closed when a cited source cannot be resolved in-program.*
- `def _resolve_actor(artifact, actor)` - *Default AI-proximate actions to the model identity.*
- `def record_artifact(conn, research_ref, kind, model_id, prompt_text, output_text, cited)` - *Notarize one model invocation: hashes in, raw text never stored.*
- `def get_artifact(conn, ref)` - *Fetch one AI artifact by identifier.*
- `def list_artifacts(conn, research_ref)` - *List AI artifacts, optionally filtered by program.*
- `def ingest_claim(conn, artifact_ref, text, kind, source_ref, quote, locator, confidence, kill_test, basis, prerequisites, question_ref, stance, actor)` - *Enter one AI-proposed claim as UNVERIFIED, or refuse it loudly.*
- `def ingest_hypothesis(conn, artifact_ref, statement, criterion, confidence, question_ref, actor)` - *Pre-register one AI-proposed hypothesis from an idea artifact.*
- `def propose_test(conn, artifact_ref, template, name, claim_ref, hypothesis_ref, actor)` - *Bind a fixed-template kill test to a claim or hypothesis.*
- `def fetch_external(*args, **kwargs)` - *Refusing stub for the external-API adapter: this build is local-only.*
- `def render_draft(conn, research_ref)` - *Assemble an article draft from surviving claims only. Never upgrades a verdict.*

---

### [`engine/amendments.py`](engine/amendments.py)
> *Append-only amendment ledger: every correction keeps its before and after.*

**Size**: `100` lines (`3118` bytes)

**Functions:**
- `def _to_amendment(row)`
- `def record_amendment(conn, subject_kind, subject_id, field, before, after, reason, actor)` - *Append one correction; the reason is mandatory and the past is kept.*
- `def list_amendments(conn, subject_kind, subject_id)` - *Amendments in record order, optionally filtered to one corrected record.*

---

### [`engine/analysis.py`](engine/analysis.py)
> *Discovery and ranking over the graph: contradictions, coverage, keystones.*

**Size**: `904` lines (`37096` bytes)

**Functions:**
- `def _negated(text)` - *Whether an assertion carries an explicit negation marker.*
- `def polarity_mismatch(left, right)` - *Exactly one of two assertions is negated: an advisory-only polarity bit.*
- `def keywords(text)` - *Content words of an assertion, lowercased and de-duplicated.*
- `def overlap(left, right)` - *Jaccard overlap of two keyword sets, 0.0 when either is empty.*
- `def _pair_score(first, second)`
- `def contradictions(conn, research_ref, min_score)` - *Pairs of supporting and contradicting claims attached to the same question.*
- `def unlinked_contradictions(conn, research_ref, min_score)` - *Claims that contradict each other by keyword overlap but have no `contradicts` edge.*
- `def evidence_matrix(conn, research_ref)` - *Sources x questions: how many claims each source contributes to each question.*
- `def keystone_claims(conn, research_ref, limit)` - *Claims that the rest of the graph leans on, by transitive dependents and inbound edges.*
- `def expose(conn, claim_ref)` - *What a claim would take down with it, plus what cites it.*
- `def _parse_time_bound(value, name)` - *Validate a `--since`/`--until` bound and normalize it to second-resolution UTC ISO.*
- `def _group_provenance(conn, claim_id, label, since, until)` - *Protocols, instruments and units recorded for one observation group.*
- `def _comparability(baseline, treatment, allow_incomparable, allow_self_reported)` - *Whether two groups measure the same quantity under the same procedure.*
- `def claim_statistics(conn, claim_ref, baseline, treatment, seed, resamples, allow_incomparable, allow_self_reported, actor, plan_ref, since, until)` - *Compare two observation groups of a claim and record that the comparison happened.*
- `def observation_summary(conn, claim_ref)` - *Per-group counts and basic summaries for one claim.*
- `def claim_trend(conn, claim_ref, group, actor, since, until)` - *Fit a least-squares trend over a group's observations in recording order.*
- `def group_correlations(conn, claim_ref, groups, allow_incomparable, allow_self_reported, since, until)` - *Advisory pairwise Pearson correlations between a claim's observation groups.*
- `def batch_statistics(conn, research_ref, baseline, treatment, seed, resamples, allow_incomparable, allow_self_reported, actor, since, until, holm)` - *Compare one baseline/treatment pair across every claim in a program.*

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

### [`engine/attempts.py`](engine/attempts.py)
> *Append-only attempt ledger for kill-test executions.*

**Size**: `131` lines (`4781` bytes)

**Functions:**
- `def _to_attempt(row)`
- `def record(conn, test_id, run_group, outcome, reason)` - *Append one attempt; a replaceable outcome requires a recorded reason.*
- `def authoritative(conn, test_id, command_sha256, code_sha256, inputs_sha256)` - *The earliest non-replaceable attempt bound to the current command, code and inputs.*
- `def for_group(conn, test_id, run_group)` - *The attempt recorded for one run group, if any.*
- `def list_attempts(conn, test_ref, limit)` - *Attempts for one test or all tests, newest sequence first.*

---

### [`engine/bundle.py`](engine/bundle.py)
> *Portable JSONL export of the evidence graph, and a digest of its content.*

**Size**: `285` lines (`10458` bytes)

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

### [`engine/calibration.py`](engine/calibration.py)
> *Hypothesis calibration: score preregistered confidence against recorded outcomes.*

**Size**: `184` lines (`7018` bytes)

**Functions:**
- `def _clip(probability)` - *Keep log loss finite without turning a certain prediction into a free pass.*
- `def _bin_index(probability)` - *Return the fixed reliability bin for one probability, including exactly 1.0.*
- `def summary(conn, research_ref, min_resolved)` - *Compute the calibration scorecard for one program without writing anything.*
- `def score(conn, research_ref, min_resolved, actor)` - *Score one program and append the calibration run to the event log.*

---

### [`engine/cascade.py`](engine/cascade.py)
> *Transitive invalidation: when a premise collapses, everything built on it collapses too.*

**Size**: `379` lines (`14497` bytes)

**Functions:**
- `def _plan_digest(conn, claim_ids, source_ids)` - *Bind exactly the rows an action will retire: any change breaks the digest.*
- `def _retraction_targets(conn, source)` - *The source plus every live twin row sharing its normalized DOI work.*
- `def dependents(conn, claim_id)` - *Return every claim that structurally depends on this claim, by depth.*
- `def preview(conn, ref)` - *Show what a collapse or retraction would retire without writing anything.*
- `def _preview_retraction(conn, ref)`
- `def _retraction_plan(conn, targets)` - *Claim ids plus display entries a retraction would read.*
- `def invalidate(conn, claim_ref, status, reason, evidence, actor, allow_bulk, preview_digest)` - *Record a failed root claim, then invalidate every dependent in one transaction.*
- `def retract_source(conn, ref, reason, evidence, actor, allow_bulk, preview_digest)` - *Retract a source and retire every empirical claim that cites it.*

---

### [`engine/claims.py`](engine/claims.py)
> *Claims: the unit of knowledge, with provenance and an append-only verdict history.*

**Size**: `588` lines (`23083` bytes)

**Functions:**
- `def _to_claim(row)`
- `def _validate_confidence(value)`
- `def add_claim(conn, research_ref, text, kind, source_ref, quote, locator, confidence, kill_test, basis, prerequisites, revision_of, revision_reason)` - *Record a claim; empirical claims must carry a verbatim quote and a locator.*
- `def get_claim(conn, ref)` - *Fetch one claim by identifier.*
- `def list_claims(conn, research_ref, status, include_superseded)` - *List claims, optionally filtered by program and verdict; hide superseded heads by default.*
- `def revision_chain(conn, ref)` - *The full revision chain, oldest first, with a cycle guard.*
- `def revise_claim(conn, ref, text, reason, source_ref, quote, locator, confidence, kill_test, basis, prerequisites, actor)` - *Append a revised claim, mark the old one superseded, and move its edges to the head.*
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

**Size**: `1464` lines (`72945` bytes)

**Functions:**
- `def _build_parser()`
- `def _emit(payload, as_json, text)`
- `def _records_payload(rows)`
- `def _need_budget(value, command)`
- `def _cmd_research(conn, args)`
- `def _cmd_question(conn, args)`
- `def _cmd_source(conn, args)`
- `def _cmd_protocol(conn, args)`
- `def _cmd_observation(conn, args)`
- `def _cmd_claim(conn, args)`
- `def _cmd_hypothesis(conn, args)`
- `def _cmd_test(conn, args)`
- `def _ensure_outside_repo(path_str)` - *Refuse model I/O files that live inside the project checkout.*
- `def _cmd_ai(conn, args)`
- `def main(argv)` - *Parse one command, open the database, and dispatch it.*

---

### [`engine/context.py`](engine/context.py)
> *Token-budgeted views: the same graph, measured in tokens for an agent reader.*

**Size**: `192` lines (`7536` bytes)

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

**Size**: `467` lines (`18053` bytes)

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

**Size**: `153` lines (`5481` bytes)

**Functions:**
- `def seed_demo(conn)` - *Create one synthetic program that exercises provenance, tests, and cascade.*

---

### [`engine/diffing.py`](engine/diffing.py)
> *Snapshot comparison: what changed between two exported graphs.*

**Size**: `123` lines (`4746` bytes)

**Functions:**
- `def load_jsonl(path)` - *Read an export, dropping its meta line; a malformed file is refused.*
- `def _key(record)` - *Identity of a record: its id, or a digest of a projection that has no id.*
- `def _strip(record)`
- `def _index(records, semantic)` - *Index records by type and identity, optionally collapsing run churn.*
- `def diff_records(old, new, semantic)` - *Compare two record sets and classify added, removed and changed records.*
- `def diff_files(old, new, semantic)` - *Compare two exported snapshots.*
- `def render(result)` - *Render a diff as a compact, deterministic report.*

---

### [`engine/duplicates.py`](engine/duplicates.py)
> *Duplicate-source detection by normalized DOI and title.*

**Size**: `134` lines (`4517` bytes)

**Functions:**
- `def normalize_doi(value)` - *Strip resolver prefixes and case-fold a DOI so two spellings compare equal.*
- `def normalize_title(value)` - *Fold accents, case and punctuation while keeping letters from every script.*
- `def _group(items, reason, key)`
- `def duplicate_sources(conn, research_ref, limit)` - *Return groups of sources that share a DOI, a normalized title/year, or a title variant.*

---

### [`engine/errors.py`](engine/errors.py)
> *Error types that carry a cause and a concrete repair step (Why/Fix triad).*

**Size**: `35` lines (`1015` bytes)

**Classes:**
- `class EngineError` - *A user-facing failure with a reason and a repair step.*
  - Method `.__init__(message, why, fix)`
  - Method `.render()`
- `class NotFound` - *A referenced record does not exist.*
  - Method `.__init__(kind, ref)`

---

### [`engine/events.py`](engine/events.py)
> *Append-only event log for actions that are not verdicts.*

**Size**: `283` lines (`9637` bytes)

**Classes:**
- `class Event`

**Functions:**
- `def event_hash_for(event)` - *The tamper-evident digest of one event, chained to its predecessor.*
- `def _stored_tip(conn, research_id)`
- `def verify_ledger(conn, research_id)` - *Replay one program's event chain; every break is an (event id, reason) pair.*
- `def _to_event(row)`
- `def record(conn, kind, subject, detail, research_id, actor, parent_id)` - *Append one event. Callers run inside their own write transaction.*
- `def list_events(conn, research_ref, kind, limit)` - *Recent events, newest first, optionally filtered by program and kind.*
- `def count(conn)` - *Total recorded events.*
- `def _one_event(conn, ref)`
- `def event_path(conn, ref)` - *The causal chain from the root event to one event, root first.*
- `def event_tree(conn, ref)` - *A root event and its descendants, breadth-first with a depth per event.*

---

### [`engine/evidence.py`](engine/evidence.py)
> *Evidence identity: which verified run groups are valid for a test right now.*

**Size**: `221` lines (`8354` bytes)

**Functions:**
- `def test_inputs(test)` - *The canonical declared input names of a test.*
- `def binding(test)` - *The identity a run must carry to count as evidence now.*
- `def _groups(conn, test_id, exact, current)` - *Verified main-role groups for one test, newest first, optionally binding-filtered.*
- `def verified_groups(conn, test_id)` - *Every historical main-role group that passed twice with identical output.*
- `def current_verified_groups(conn, test, current)` - *Every main-role group valid for the current code, inputs and command, newest first.*
- `def current_verified_group(conn, test)` - *The newest group valid for the current binding, if any.*
- `def control_state(conn, test, group)` - *Whether the declared control was falsified in one run group.*
- `def authoritative_attempt(conn, test)` - *The earliest non-replaceable attempt bound to the test's current identity.*
- `def authoritative_group(conn, test)` - *The authoritative group when that attempt is also a currently verified group.*
- `def authority_blocked(conn, test)` - *The reason a later pass cannot be promoted, when the authority is a subject failure.*
- `def _claim_tests(conn, claim_id)`
- `def claim_groups(conn, claim_id)` - *Current verified groups across every test bound to a claim.*
- `def claim_authority_blocked(conn, claim_id)` - *The first subject-failure authority across a claim's tests, if any.*
- `def claim_has_historical_evidence(conn, claim_id)` - *Whether any test bound to a claim ever produced a verified group.*
- `def claim_tests(conn, claim_id)` - *Every test bound to a claim.*

---

### [`engine/hypotheses.py`](engine/hypotheses.py)
> *Pre-registered hypotheses and their outcomes (the K13 discipline).*

**Size**: `249` lines (`9334` bytes)

**Functions:**
- `def _to_hypothesis(row)`
- `def add_hypothesis(conn, research_ref, statement, criterion, confidence, question_ref)` - *Pre-register a prediction before any outcome is known.*
- `def get_hypothesis(conn, ref)` - *Fetch one hypothesis by identifier.*
- `def list_hypotheses(conn, research_ref)` - *List hypotheses, optionally filtered by program.*
- `def record_outcome(conn, hypothesis_ref, outcome, evidence, note, actor)` - *Close a pre-registered hypothesis with an evidence-backed outcome.*
- `def amend_hypothesis(conn, hypothesis_ref, reason, statement, criterion, actor)` - *Correct a pre-registered hypothesis; the original registration is kept.*
- `def preregistration_card(conn, hypothesis_ref)` - *Render the pre-registration card an agent writes before searching.*

---

### [`engine/information.py`](engine/information.py)
> *Cheap information-quality checks over stored claim quotes.*

**Size**: `62` lines (`2271` bytes)

**Functions:**
- `def normalize(text)` - *Fold case and punctuation so two quotes compare on their words.*
- `def content_terms(text)` - *Words that carry information, excluding the small English stopword set.*
- `def restates_question(quote, questions)` - *Whether the quote is a substring of a question it is supposed to answer.*
- `def duplicate_quote(quote, other_quotes)` - *Whether the same quote already supports another claim in the same program.*
- `def stopword_only(quote)` - *Whether the quote has no content terms at all.*
- `def quote_classes(quote, questions, other_quotes)` - *Return the stable, additive information classes of one quote.*

---

### [`engine/integrity.py`](engine/integrity.py)
> *Graph integrity: provenance, evidence paths, dependency acyclicity and stale dependents.*

**Size**: `934` lines (`35534` bytes)

**Functions:**
- `def _finding(code, severity, subject, message, fix)`
- `def _entity(conn, kind, ref)`
- `def _cycles(conn, relations)`
- `def _missing_inputs(tests)` - *Declared input files that no longer exist, resolved exactly like the fingerprint.*
- `def _quote_quality(conn)` - *Warn when a live quote restates a question, duplicates another quote, or is empty.*
- `def check(conn)` - *Return every integrity finding; an empty list means the graph is coherent.*
- `def has_errors(findings)` - *Return True when at least one finding blocks a verdict.*
- `def render_markdown(findings)` - *Render findings as a compact audit table.*
- `def render_json(findings)` - *Render findings as stable machine-readable JSON.*
- `def findings_for_research(conn, research_id)` - *Findings attributable to one program: its own records, edges and the program itself.*

---

### [`engine/killtests.py`](engine/killtests.py)
> *Executable kill tests: two agreeing runs, bound to code, inputs and command.*

**Size**: `405` lines (`14976` bytes)

**Functions:**
- `def _to_test(row)`
- `def _to_run(row)`
- `def add_test(conn, research_ref, name, command, claim_ref, hypothesis_ref, expect_exit, timeout_seconds, inputs, control_command)` - *Register an executable test bound to a claim, a hypothesis, its inputs and a control.*
- `def get_test(conn, ref)` - *Fetch one test by identifier.*
- `def list_tests(conn, research_ref)` - *List tests, optionally filtered by program.*
- `def _terminate_tree(process)` - *Kill the process and its children without leaking a detached tree.*
- `def _run_once(command, timeout_seconds)` - *Run one command in the project root and capture a deterministic fingerprint.*
- `def _classify_attempt(results, control, runs, before, after)` - *Classify one execution into the attempt vocabulary, conservatively.*
- `def run_test(conn, test_ref, runs)` - *Run a test one or more times, plus its negative control, recording each run's identity.*
- `def _execute(conn, test, command, group, runs, role, tag_prefix, current, commit, dirty, runtime)` - *Execute one command `runs` times and persist every run under its role.*
- `def _summarise_control(results, expect_exit)` - *A control is falsified when every repetition fails the expectation identically.*
- `def verify_test(conn, test_ref)` - *Run a test twice in separate processes; disagreement or drift is a failure.*
- `def list_runs(conn, test_ref, limit)` - *List recent runs, optionally for one test.*

---

### [`engine/maintenance.py`](engine/maintenance.py)
> *Database maintenance: integrity verification and a crash-safe backup.*

**Size**: `109` lines (`4245` bytes)

**Functions:**
- `def integrity_check(conn)` - *Run SQLite's own checks plus a few facts a reviewer wants before archiving.*
- `def _refuse_if_exists(target, because)` - *Refuse to clobber an existing backup target.*
- `def backup(conn, destination)` - *Copy the live database through SQLite's backup API and verify the copy.*

---

### [`engine/manifest.py`](engine/manifest.py)
> *Generated-report manifests and drift detection.*

**Size**: `172` lines (`6698` bytes)

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

**Size**: `151` lines (`5780` bytes)

**Functions:**
- `def merge_claims(conn, keep_ref, drop_refs, note, actor)` - *Keep one claim, repoint edges from the duplicates, and retire the duplicates.*

---

### [`engine/models.py`](engine/models.py)
> *Frozen domain records and the engine's closed vocabularies.*

**Size**: `274` lines (`6000` bytes)

**Classes:**
- `class Research`
- `class Source`
- `class Question`
- `class Claim`
- `class Hypothesis`
- `class KillTest`
- `class TestRun`
- `class Attempt`
  - Method `.to_dict()`
- `class AIArtifact`
- `class Observation`
- `class Protocol`
- `class Finding`
- `class AnalysisPlan`
- `class Amendment`

---

### [`engine/observations.py`](engine/observations.py)
> *Recorded observations: the raw measurements a numeric claim is computed from.*

**Size**: `483` lines (`18632` bytes)

**Classes:**
- `class _DryRunComplete` - *Carry validated counts out of a rolled-back dry-run transaction.*
  - Method `.__init__(imported, skipped)`

**Functions:**
- `def _to_observation(row)`
- `def add_observation(conn, claim_ref, group_label, value, note, at, instrument_kind, instrument_id, instrument_digest, rater_kind, rater_id, rater_version, protocol_id, sample_size, aggregation, unit, provenance_class, producer_path, producer_digest)` - *Record one measurement in a named group; non-finite values are refused.*
- `def get_observation(conn, ref)` - *Fetch one observation by identifier.*
- `def list_observations(conn, claim_ref, group_label, include_voided)` - *Observations of a claim, oldest first, excluding voided rows by default.*
- `def void_observation(conn, ref, reason, actor)` - *Retire a measurement without deleting it; the reason stays in the record.*
- `def group_values(conn, claim_ref)` - *Non-voided values per group, in insertion order.*
- `def group_values_window(conn, claim_ref, since, until)` - *Non-voided values per group in insertion order, optionally bounded by record time.*
- `def import_observations_csv(conn, claim_ref, path, actor, dry_run)` - *Bulk-record measurements from a CSV file with per-row error isolation.*

---

### [`engine/plans.py`](engine/plans.py)
> *Pre-registered analysis plans: comparisons declare their prediction first.*

**Size**: `119` lines (`4189` bytes)

**Functions:**
- `def _to_plan(row)`
- `def add_plan(conn, claim_ref, baseline, treatment, prediction, actor)` - *Pre-register what a comparison is expected to show, before it runs.*
- `def get_plan(conn, ref)` - *Fetch one analysis plan by identifier.*
- `def list_plans(conn, claim_ref)` - *Plans in record order, optionally filtered to one claim.*
- `def match_plan(conn, claim_id, baseline, treatment)` - *Plans preregistered for exactly this claim and group pair.*

---

### [`engine/protocols.py`](engine/protocols.py)
> *Measurement protocol registry.*

**Size**: `188` lines (`6814` bytes)

**Functions:**
- `def _to_protocol(row)`
- `def register_protocol(conn, protocol_id, measures, includes_generation, includes_judge, doc_digest, doc_path, actor)` - *Register an immutable protocol id; re-registering the same id is refused.*
- `def get_protocol(conn, ref)` - *Fetch one registered protocol by id.*
- `def amend_protocol(conn, ref, measures, reason, actor)` - *Correct a protocol's measures text; the pin and digest never move.*
- `def list_protocols(conn)` - *Every registered protocol, oldest id first.*

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

**Size**: `73` lines (`2726` bytes)

**Functions:**
- `def _to_question(row)`
- `def add_question(conn, research_ref, text)` - *Add an open question to a program.*
- `def get_question(conn, ref)` - *Fetch one question by identifier.*
- `def list_questions(conn, research_ref)` - *List questions, optionally filtered by program.*
- `def close_question(conn, ref)` - *Mark a question resolved without deleting its evidence.*

---

### [`engine/researches.py`](engine/researches.py)
> *Research programs: the top-level containers the engine is asked to investigate.*

**Size**: `92` lines (`3486` bytes)

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

### [`engine/search.py`](engine/search.py)
> *Deterministic lexical search over the recorded graph.*

**Size**: `226` lines (`8252` bytes)

**Functions:**
- `def _terms(query)` - *Case-folded query terms, de-duplicated and stripped of one-character noise.*
- `def _score(needle, terms, blob, primary)` - *Phrase-first relevance: exact phrase, primary field, then matched terms.*
- `def _snippet(text, needle, terms, width)` - *A one-line window around the earliest match, with visible cut marks.*
- `def _fields(kind, row)` - *Primary and supporting text for one record, in match-priority order.*
- `def _rows(conn, kind, research_id, include_superseded)` - *Program-scoped rows for one kind, in stable identifier order.*
- `def search(conn, query, research_ref, kinds, limit, include_superseded, budget)` - *Rank one query across the graph and return matches with a matched-field snippet.*

---

### [`engine/sources.py`](engine/sources.py)
> *Bibliographic sources: the only place literature text may enter the graph.*

**Size**: `157` lines (`5570` bytes)

**Functions:**
- `def _to_source(row)`
- `def add_source(conn, research_ref, title, year, doi, url, authors, kind)` - *Register a source; claims cannot cite it before it exists.*
- `def get_source(conn, ref)` - *Fetch one source by identifier.*
- `def list_sources(conn, research_ref)` - *List sources, optionally filtered by program.*
- `def set_source_status(conn, ref, status, note, actor)` - *Change a source's evidence status without deleting the record.*

---

### [`engine/stats.py`](engine/stats.py)
> *Deterministic statistics for recorded observations.*

**Size**: `358` lines (`13460` bytes)

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
- `def holm_adjust(p_values)` - *Holm step-down adjustment for a family of p-values, in standard-library code.*
- `def bootstrap_ci(baseline, treatment, seed, resamples)` - *Percentile bootstrap interval for the difference in means, reproducibly seeded.*
- `def pearson(xs, ys)` - *Pearson product-moment correlation for paired samples, stdlib-only.*
- `def linregress(xs, ys)` - *Least-squares slope, intercept, correlation and two-sided p for paired points.*
- `def compare_groups(baseline, treatment, seed, resamples)` - *Compare two recorded groups and state the result, the agreement and the caveats.*

---

### [`engine/synthesis.py`](engine/synthesis.py)
> *Evidence synthesis: weighted consensus, contradiction pairs, and generated reports.*

**Size**: `479` lines (`19723` bytes)

**Functions:**
- `def stance_claims(conn, question_id)`
- `def consensus(conn, question_ref)` - *Confidence-weighted support minus contradiction in [-1, 1].*
- `def coverage(conn, question_ref)` - *Tested fraction and source breadth behind a question's stances.*
- `def consensus_display(conn, question_ref)` - *The reportable consensus: a number with coverage, or an explicit refusal.*
- `def _contradictions(conn, question_id)`
- `def _provenance_cell(conn, row)`
- `def _verdict_count(conn, research_id)` - *Verdicts adjudicating this program's claims or hypotheses.*
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

### [`tests/test_ai.py`](tests/test_ai.py)
> *AI integration: provenance at birth, fabricated citations die, novelty can survive.*

**Size**: `417` lines (`16243` bytes)

**Classes:**
- `class ArtifactTests`
  - Method `.test_schema_carries_ai_artifact_table()`
  - Method `.test_record_hashes_only_never_raw_text()`
  - Method `.test_record_refuses_empty_model_or_payload()`
  - Method `.test_external_fetch_always_refuses()`
- `class IngestTests`
  - Method `._extraction(research, cited)`
  - Method `.test_extract_enters_unverified_with_link()`
  - Method `.test_fabricated_source_is_refused_and_flagged()`
  - Method `.test_cited_divergence_is_refused_and_flagged()`
  - Method `.test_source_outside_cited_list_is_refused()`
  - Method `.test_ingest_defaults_actor_to_model()`
  - Method `.test_wrong_kind_from_wrong_artifact_is_refused()`
  - Method `.test_idea_preregisters_hypothesis()`
- `class KillTestAdapterTests`
  - Method `.test_free_form_template_is_refused()`
  - Method `.test_template_probe_verifies_like_a_human_test()`
  - Method `.test_tampered_template_command_trips_ai003()`
  - Method `.test_ai_proven_without_a_run_trips_ai002()`
- `class BoundaryTests`
  - Method `.test_no_network_imports_anywhere_in_the_engine()`
  - Method `.test_ai_module_never_calls_verdict_paths()`
  - Method `.test_model_io_inside_repo_is_refused()`
  - Method `.test_model_io_outside_repo_is_allowed()`
- `class DraftTests`
  - Method `._surviving_claim(research)`
  - Method `.test_draft_carries_kill_test_receipts()`
  - Method `.test_draft_withholds_unverified_claims()`
  - Method `.test_draft_refuses_a_failing_gate()`

---

### [`tests/test_analysis.py`](tests/test_analysis.py)
> *Discovery: contradictions, coverage matrix, keystone ranking, exposure.*

**Size**: `185` lines (`8910` bytes)

**Classes:**
- `class KeywordTests`
  - Method `.test_stopwords_are_removed()`
  - Method `.test_overlap_is_jaccard()`
  - Method `.test_negation_is_visible_despite_stopwords()`
- `class AnalysisTests`
  - Method `.setUp()`
  - Method `.test_contradictions_pair_within_a_question()`
  - Method `.test_contradictions_are_ranked_by_score()`
  - Method `.test_min_score_filters()`
  - Method `.test_contradiction_pairs_carry_the_polarity_bit()`
  - Method `.test_unlinked_proposals_carry_the_polarity_bit()`
  - Method `.test_pairings_ignore_withdrawn_and_superseded_claims()`
  - Method `.test_claims_on_different_questions_are_not_paired()`
  - Method `.test_unlinked_score_uses_both_confidences()`
  - Method `.test_unlinked_contradictions_skip_recorded_edges()`
  - Method `.test_matrix_counts_claims_per_source_and_question()`
  - Method `.test_matrix_ignores_assumed_claims()`
  - Method `.test_keystone_ranks_by_downstream_and_inbound()`
  - Method `.test_expose_lists_dependents_and_inbound()`

---

### [`tests/test_attempts.py`](tests/test_attempts.py)
> *Attempt authority: the earliest non-replaceable attempt wins.*

**Size**: `218` lines (`8803` bytes)

**Classes:**
- `class AttemptAuthorityTests`
  - Method `.setUp()`
  - Method `.test_duplicate_attempt_is_an_engine_error()`
  - Method `.test_attempt_for_a_missing_test_is_not_found()`
  - Method `._insert_group(group, passed, values, outputs)`
  - Method `._record(group, outcome, reason)`
  - Method `.test_earliest_completed_attempt_wins()`
  - Method `.test_infra_failure_is_replaceable()`
  - Method `.test_subject_failure_blocks_a_later_pass()`
  - Method `.test_indeterminate_is_replaceable()`
  - Method `.test_stale_binding_is_ignored()`
  - Method `.test_legacy_group_without_an_attempt_still_counts()`
  - Method `.test_replaceable_outcome_requires_a_reason()`
  - Method `.test_attempts_are_sequenced_and_listed()`
  - Method `.test_completed_attempt_promotes()`
  - Method `.test_real_subject_failure_records_an_attempt_and_blocks()`
  - Method `.test_single_run_is_indeterminate()`
  - Method `.test_control_that_does_not_fail_is_indeterminate()`
  - Method `.test_a_new_test_after_a_subject_failure_warns()`

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

**Size**: `185` lines (`7822` bytes)

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
  - Method `.test_a_non_ascii_digest_is_reported_not_crashed()`
  - Method `.test_a_non_object_line_is_reported_not_crashed()`
  - Method `.test_an_unsupported_schema_is_reported_not_trusted()`
  - Method `.test_a_non_numeric_record_count_is_handled()`

---

### [`tests/test_calibration.py`](tests/test_calibration.py)
> *Hypothesis calibration: recorded confidence is scored against recorded outcomes.*

**Size**: `121` lines (`5590` bytes)

**Classes:**
- `class CalibrationTests`
  - Method `.add_outcome(research, confidence, status, text)`
  - Method `.test_min_resolved_must_be_a_positive_integer()`
  - Method `.test_brier_log_loss_and_coverage()`
  - Method `.test_reliability_bins_separate_direction()`
  - Method `.test_empty_program_is_undefined_not_zero()`
  - Method `.test_small_resolved_set_is_flagged()`
  - Method `.test_one_sided_outcomes_cannot_measure_discrimination()`
  - Method `.test_score_appends_an_event_and_report_shows_the_score()`
  - Method `.test_minimum_resolved_set_must_be_positive()`

---

### [`tests/test_cascade.py`](tests/test_cascade.py)
> *A collapsed premise invalidates every dependent transitively.*

**Size**: `155` lines (`7049` bytes)

**Classes:**
- `class CascadeTests`
  - Method `._chain()`
  - Method `.test_collapse_traverses_depends_on_edges()`
  - Method `.test_dependents_are_transitive_and_ordered_by_depth()`
  - Method `.test_preview_writes_nothing()`
  - Method `.test_collapse_invalidates_every_dependent()`
  - Method `.test_retracted_dependent_is_not_rewritten()`
  - Method `.test_falsified_dependent_keeps_its_primary_failure()`
  - Method `.test_bulk_collapse_is_refused_without_override()`
  - Method `.test_collapse_requires_evidence()`
  - Method `.test_collapse_requires_reason_and_failed_status()`
  - Method `.test_stale_preview_digest_is_refused()`
  - Method `.test_current_preview_digest_allows_collapse()`
  - Method `.test_preview_digest_binds_new_dependents()`

---

### [`tests/test_claims.py`](tests/test_claims.py)
> *Provenance requirements and the append-only verdict lifecycle.*

**Size**: `226` lines (`9687` bytes)

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
  - Method `.test_failed_claim_cannot_be_promoted_in_place()`
  - Method `.test_failed_claim_can_move_to_another_failed_status()`
  - Method `.test_revision_of_must_exist_in_the_same_program()`
  - Method `.test_revise_refuses_itself_as_a_prerequisite()`
  - Method `.test_record_edge_validates_its_endpoints()`
  - Method `.test_record_edge_validates_the_relation()`

---

### [`tests/test_cli.py`](tests/test_cli.py)
> *The CLI surface: JSON output, exit codes and the error triad.*

**Size**: `628` lines (`25692` bytes)

**Classes:**
- `class CliTests`
  - Method `.setUp()`
  - Method `.run_cli(*args)`
  - Method `.test_init_and_demo()`
  - Method `.test_demo_passes_integrity_gate()`
  - Method `.test_error_triad_on_missing_quote()`
  - Method `.test_report_and_scorecard()`
  - Method `.test_search_command()`
  - Method `.test_source_duplicates_command()`
  - Method `.test_calibration_command()`
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
  - Method `.test_claim_revision_commands()`
  - Method `.test_screening_and_prisma()`
  - Method `.test_events_are_listed()`
  - Method `.test_event_tree_and_path()`
  - Method `.test_db_integrity_and_backup()`
  - Method `.test_negative_control_through_the_cli()`
  - Method `.test_observations_and_statistics()`
  - Method `.test_observation_errors_use_the_triad()`
  - Method `.test_analysis_trend()`
  - Method `.test_export_check_detects_tampering()`
  - Method `.test_export_check_refuses_a_research_filter()`
  - Method `.test_export_check_fails_on_an_unsupported_schema()`
  - Method `.test_closed_vocabularies_are_rejected_by_the_parser()`
  - Method `.test_retracted_status_points_at_retract()`
  - Method `.test_non_positive_budgets_are_refused()`
  - Method `.test_demo_failure_reports_the_error_triad()`
  - Method `.test_events_tree_refuses_list_filters()`
  - Method `.test_strict_needs_check()`
  - Method `.test_check_json_is_stable_machine_output()`
  - Method `.test_report_scorecard_card_evaluate_once()`
  - Method `.test_protocol_add_doc_path_mismatch_is_refused()`
  - Method `.test_bulk_invalidate_needs_allow_bulk()`
  - Method `.test_events_verify_reports_a_healthy_ledger()`
  - Method `.test_analysis_plan_is_cited_by_stats()`
  - Method `.test_amend_commands_correct_live_records()`
  - Method `.test_stale_preview_digest_is_refused()`
  - Method `.test_main_module_import_has_no_side_effects()`

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

**Size**: `167` lines (`7133` bytes)

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
  - Method `.test_single_control_run_is_not_falsified_or_reproducible()`
  - Method `.test_control_state_single_run_is_not_reproducible()`
  - Method `.test_binding_runs_single_source_of_truth()`

---

### [`tests/test_diffing.py`](tests/test_diffing.py)
> *Snapshot diff: semantic by default, exact on request.*

**Size**: `119` lines (`4724` bytes)

**Classes:**
- `class DiffTests`
  - Method `.setUp()`
  - Method `.test_identical_exports_have_no_differences()`
  - Method `.test_a_new_claim_is_added()`
  - Method `.test_semantic_mode_ignores_run_churn()`
  - Method `.test_a_changed_status_is_reported()`
  - Method `.test_missing_snapshot_is_reported()`
  - Method `.test_malformed_snapshot_is_reported()`
  - Method `.test_non_object_snapshot_line_is_reported()`
  - Method `.test_render_lists_each_change()`
  - Method `.test_a_second_run_with_the_same_identity_cannot_mask_a_change()`

---

### [`tests/test_docs.py`](tests/test_docs.py)
> *Documentation and project memory stay discoverable and within budget.*

**Size**: `107` lines (`3880` bytes)

**Classes:**
- `class DocsTests`
  - Method `.test_readme_has_the_cold_start_contract()`
  - Method `.test_architecture_and_mechanics_documents_exist()`
  - Method `.test_project_memory_declares_the_test_command()`
  - Method `.test_readme_tree_names_real_modules()`
  - Method `.test_readme_documents_the_current_schema_and_gates()`
  - Method `.test_architecture_documents_binding_and_digests()`

---

### [`tests/test_duplicates.py`](tests/test_duplicates.py)
> *Duplicate sources: DOI and title normalization, scope, and the integrity warning.*

**Size**: `93` lines (`4413` bytes)

**Classes:**
- `class NormalizationTests`
  - Method `.test_doi_resolver_prefix_and_case_are_folded()`
  - Method `.test_title_folds_accents_case_and_punctuation()`
- `class DuplicateSourceTests`
  - Method `.test_doi_duplicates_are_grouped_with_the_lowest_id_kept()`
  - Method `.test_title_year_duplicates_are_grouped()`
  - Method `.test_same_title_different_year_is_only_a_variant()`
  - Method `.test_programs_are_never_grouped_together()`
  - Method `.test_limit_keeps_the_total_visible()`
  - Method `.test_integrity_warns_on_doi_title_year_and_variants()`

---

### [`tests/test_errors.py`](tests/test_errors.py)
> *NotFound fixes must point at real CLI verbs.*

**Size**: `33` lines (`1023` bytes)

**Classes:**
- `class NotFoundTests`
  - Method `.test_fix_points_at_a_real_cli_verb()`

---

### [`tests/test_events.py`](tests/test_events.py)
> *Event log: append-only record of actions that are not verdicts.*

**Size**: `190` lines (`8353` bytes)

**Classes:**
- `class EventTests`
  - Method `.test_record_and_list_newest_first()`
  - Method `.test_filters_by_kind_and_research()`
  - Method `.test_detail_is_flattened()`
  - Method `.test_nested_events_form_a_tree_and_path()`
  - Method `.test_orphan_parent_is_refused()`
  - Method `.test_cross_program_parent_is_refused()`
  - Method `.test_tree_rejects_a_non_root()`
  - Method `.test_source_status_is_recorded()`
  - Method `.test_screening_is_recorded()`
  - Method `.test_merge_is_recorded_once()`
  - Method `.test_report_generation_is_recorded()`
  - Method `.test_migration_records_an_event()`
  - Method `.test_chain_links_each_event_to_its_predecessor()`
  - Method `.test_tampered_middle_row_breaks_the_chain()`
  - Method `.test_extending_a_broken_tip_is_refused()`
  - Method `.test_legacy_unhashed_rows_are_grandfathered()`

---

### [`tests/test_golden.py`](tests/test_golden.py)
> *Golden run: the whole command surface, end to end, in a fresh database.*

**Size**: `205` lines (`9926` bytes)

**Classes:**
- `class GoldenRunTests`
  - Method `.setUp()`
  - Method `.run_cli(*args)`
  - Method `.must(*args)`
  - Method `.test_every_command_composes()`

---

### [`tests/test_hypotheses.py`](tests/test_hypotheses.py)
> *Pre-registration precedes outcomes and cards carry the falsification criterion.*

**Size**: `83` lines (`3827` bytes)

**Classes:**
- `class HypothesisTests`
  - Method `.test_criterion_is_required()`
  - Method `.test_registration_is_immediate_and_card_is_rendered()`
  - Method `.test_outcome_requires_evidence_and_closes_once()`
  - Method `.test_unknown_outcome_is_refused()`
  - Method `.test_statement_correction_keeps_registration_and_logs()`
  - Method `.test_amendment_needs_a_reason_and_a_live_record()`

---

### [`tests/test_information.py`](tests/test_information.py)
> *Cheap information-quality checks over stored claim quotes.*

**Size**: `57` lines (`2046` bytes)

**Classes:**
- `class InformationTests`
  - Method `.test_normalize_folds_case_and_punctuation()`
  - Method `.test_restates_question_exact_and_substring()`
  - Method `.test_restates_question_needs_two_content_terms()`
  - Method `.test_duplicate_quote_is_case_and_punctuation_insensitive()`
  - Method `.test_stopword_only_quote_has_no_content_terms()`
  - Method `.test_quote_classes_are_stable_and_additive()`
  - Method `.test_distinct_quote_has_no_classes()`

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

**Size**: `462` lines (`21009` bytes)

**Classes:**
- `class IntegrityTests`
  - Method `._clean_program()`
  - Method `.test_clean_program_has_no_errors()`
  - Method `.test_missing_provenance_is_detected()`
  - Method `.test_quote_restating_a_question_warns()`
  - Method `.test_duplicate_quote_warns()`
  - Method `.test_stopword_only_quote_warns()`
  - Method `.test_distinct_quote_does_not_warn()`
  - Method `.test_source_without_identifier_is_detected()`
  - Method `.test_promoted_claim_needs_kill_test()`
  - Method `.test_numeric_claim_needs_two_run_test()`
  - Method `.test_failed_status_needs_evidence()`
  - Method `.test_hypothesis_outcome_needs_verdict()`
  - Method `.test_dependency_cycle_is_detected()`
  - Method `.test_mutual_support_cycle_is_flagged()`
  - Method `.test_support_ring_is_flagged()`
  - Method `.test_one_way_support_is_not_a_cycle()`
  - Method `.test_dangling_and_self_edges_are_detected()`
  - Method `.test_cross_program_edge_is_detected()`
  - Method `.test_stale_dependent_is_detected()`
  - Method `.test_both_failed_is_not_a_stale_dependent()`
  - Method `.test_title_variant_duplicate_warns()`
  - Method `.test_corrupt_schema_ledger_is_an_error()`
  - Method `.test_rendered_table_escapes_untrusted_text()`
  - Method `.test_gaps_and_duplicates_are_warnings()`
  - Method `.test_empty_program_warns()`
  - Method `.test_renderers_are_stable()`
  - Method `.test_stale_numeric_evidence_is_detected()`
  - Method `.test_missing_evidence_volume_reports_once()`
  - Method `.test_small_stale_set_keeps_per_claim_findings()`
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

**Size**: `168` lines (`7490` bytes)

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
  - Method `.test_editing_expect_exit_invalidates_the_binding()`
  - Method `.test_editing_timeout_invalidates_the_binding()`
  - Method `.test_changing_a_declared_input_invalidates_the_binding()`
  - Method `.test_run_records_the_binding_and_git_state()`

---

### [`tests/test_maintenance.py`](tests/test_maintenance.py)
> *Database maintenance: integrity verification and verified backups.*

**Size**: `166` lines (`7202` bytes)

**Classes:**
- `class MaintenanceTests`
  - Method `.setUp()`
  - Method `.test_integrity_reports_ok_and_counts()`
  - Method `.test_integrity_detects_a_foreign_key_violation()`
  - Method `.test_backup_produces_a_readable_copy()`
  - Method `.test_backup_refuses_to_overwrite()`
  - Method `.test_backup_leaves_no_temporary_file()`
  - Method `.test_connect_uses_a_lock_wait_timeout()`
  - Method `.test_locked_database_reports_an_engine_error()`
  - Method `.test_backup_preserves_the_journal_mode()`
  - Method `.test_backup_refuses_an_open_write_transaction()`
  - Method `.test_counts_cover_edges_and_ai_artifacts()`
  - Method `.test_version_skew_fails_the_gate()`
  - Method `.test_corrupt_version_fails_closed()`
  - Method `.test_backup_target_guard_refuses_existing_paths()`
  - Method `.test_backup_of_a_database_with_events_copies_them()`

---

### [`tests/test_manifest.py`](tests/test_manifest.py)
> *Generated report manifests and drift detection.*

**Size**: `190` lines (`8101` bytes)

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
  - Method `.test_tampered_report_body_is_drift()`
  - Method `.test_missing_report_file_is_drift()`

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

### [`tests/test_measurements.py`](tests/test_measurements.py)
> *Measurement provenance and protocol comparability.*

**Size**: `253` lines (`11173` bytes)

**Classes:**
- `class MeasurementTests`
  - Method `.setUp()`
  - Method `._kwargs(protocol, instrument, digest, unit)`
  - Method `._add(group, value, **overrides)`
  - Method `.test_protocol_registration_is_immutable()`
  - Method `.test_doc_path_digest_mismatch_is_refused()`
  - Method `.test_doc_path_only_pins_computed_digest()`
  - Method `.test_missing_doc_path_is_refused()`
  - Method `.test_measures_correction_preserves_digest_and_logs()`
  - Method `.test_protocol_amendment_needs_a_reason()`
  - Method `.test_observation_round_trips_provenance()`
  - Method `.test_incomplete_provenance_is_refused()`
  - Method `.test_unknown_protocol_is_refused()`
  - Method `.test_unknown_aggregation_is_refused()`
  - Method `.test_legacy_observation_warns()`
  - Method `.test_same_protocol_is_comparable()`
  - Method `.test_different_protocols_are_refused()`
  - Method `.test_incomparable_can_be_allowed_with_a_warning()`
  - Method `.test_different_instruments_are_refused()`
  - Method `.test_different_units_are_refused()`
  - Method `.test_mixed_provenance_in_one_group_is_refused()`
  - Method `.test_self_reported_requires_a_producer_path()`
  - Method `.test_unknown_provenance_class_is_refused()`
  - Method `.test_self_reported_comparison_is_refused()`
  - Method `.test_mixed_self_reported_group_is_refused()`
  - Method `.test_self_reported_measurements_are_separated_in_the_report()`
  - Method `.test_integrity_flags_unclassified_and_self_reported()`

---

### [`tests/test_merging.py`](tests/test_merging.py)
> *Merging duplicates: survivor, repointed edges, retired duplicates, history kept.*

**Size**: `139` lines (`6172` bytes)

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
  - Method `.test_falsified_survivor_and_duplicate_are_refused()`
  - Method `.test_observations_and_artifacts_follow_the_survivor()`
  - Method `.test_already_repointed_edges_are_not_double_counted()`
  - Method `.test_linking_two_merged_claims_does_not_leave_a_self_edge()`

---

### [`tests/test_migration.py`](tests/test_migration.py)
> *Schema migration: an older database is repaired, not rejected or wiped.*

**Size**: `275` lines (`11484` bytes)

**Classes:**
- `class MigrationTests`
  - Method `._old_database()`
  - Method `.test_version_one_database_is_migrated_in_place()`
  - Method `.test_existing_rows_are_preserved()`
  - Method `.test_migration_creates_the_attempt_table()`
  - Method `.test_migration_adds_the_claim_revision_columns()`
  - Method `.test_migration_adds_observation_provenance_columns()`
  - Method `.test_migration_creates_the_protocol_table()`
  - Method `.test_migration_adds_event_nesting_columns()`
  - Method `.test_migration_is_idempotent()`
  - Method `.test_future_version_is_refused_without_changes()`
  - Method `.test_future_version_is_refused_before_creating_tables()`
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

### [`tests/test_n1_ports.py`](tests/test_n1_ports.py)
> *N1 suitable ports: provenance-gated correlation, batch stats-all, CSV import.*

**Size**: `327` lines (`14588` bytes)

**Classes:**
- `class PearsonTests`
  - Method `.test_perfect_correlation()`
  - Method `.test_anticorrelation()`
  - Method `.test_degenerate_variance_yields_zero()`
  - Method `.test_fewer_than_three_pairs_yields_zero()`
- `class CorrelationTests`
  - Method `._claim_with_groups()`
  - Method `.test_correlated_groups_rank_first()`
  - Method `.test_truncation_is_reported()`
  - Method `.test_incomparable_protocols_are_recorded_not_raised()`
  - Method `.test_fewer_than_two_groups_refused()`
- `class BatchStatisticsTests`
  - Method `._claim(research, baseline, treatment)`
  - Method `.test_errors_are_isolated_per_claim()`
  - Method `.test_many_claims_warn()`
- `class CsvImportTests`
  - Method `._write_csv(rows)`
  - Method `.test_valid_rows_import_and_bad_rows_skip()`
  - Method `.test_missing_header_refused()`
  - Method `.test_alternate_group_header_accepted()`
- `class TemplateTests`
  - Method `.test_header_names_required_columns_first()`
- `class WindowTests`
  - Method `._window_claim()`
  - Method `.test_window_filters_by_record_time()`
  - Method `.test_invalid_bound_refused()`
  - Method `.test_non_utc_offset_normalized_to_utc()`
  - Method `.test_batch_rejects_bad_bounds_loudly()`
  - Method `.test_correlation_respects_window()`
  - Method `.test_trend_respects_window()`
- `class DryRunTests`
  - Method `.test_dry_run_writes_nothing()`
- `class HolmTests`
  - Method `.test_holm_table_opt_in()`

---

### [`tests/test_observations.py`](tests/test_observations.py)
> *Observations: raw values, their voiding, and the statistics projection over them.*

**Size**: `244` lines (`11825` bytes)

**Classes:**
- `class ObservationTests`
  - Method `.setUp()`
  - Method `.test_values_are_recorded_in_order()`
  - Method `.test_non_finite_values_are_refused()`
  - Method `.test_non_numeric_values_are_refused()`
  - Method `.test_sample_size_must_be_a_positive_integer()`
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
  - Method `.test_summary_reports_median_and_mad()`
  - Method `.test_more_than_two_groups_warns_about_uncorrected_comparison()`
  - Method `.test_more_than_two_groups_reports_a_holm_family()`
  - Method `.test_group_labels_are_case_insensitive()`
  - Method `.test_a_group_cannot_be_compared_with_itself()`
  - Method `.test_too_few_resamples_are_refused()`
  - Method `.test_trend_labels_are_case_insensitive()`
  - Method `.test_new_observations_after_a_run_warn_again()`
  - Method `.test_a_void_after_a_run_warns_again()`
  - Method `.test_a_short_trend_says_it_is_insufficient()`
  - Method `.test_a_claim_whose_observations_were_all_voided_does_not_warn()`

---

### [`tests/test_plans.py`](tests/test_plans.py)
> *Analysis plans are preregistered; unmatched comparisons read as exploratory.*

**Size**: `101` lines (`3941` bytes)

**Classes:**
- `class PlanTests`
  - Method `._planned_claim()`
  - Method `.test_plan_registers_before_data_is_seen()`
  - Method `.test_plan_needs_a_prediction_and_two_groups()`
  - Method `.test_cited_plan_is_recorded_on_the_comparison()`
  - Method `.test_uncited_comparison_with_plans_is_exploratory()`
  - Method `.test_plan_must_match_the_compared_pair()`
  - Method `.test_plan_belongs_to_one_claim()`

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

**Size**: `45` lines (`1739` bytes)

**Classes:**
- `class ResearchTests`
  - Method `.test_create_and_resolve_by_slug()`
  - Method `.test_duplicate_slug_is_suffixed()`
  - Method `.test_invalid_slug_is_refused()`
  - Method `.test_missing_program_is_reported()`
  - Method `.test_counts_include_open_questions()`
  - Method `.test_counts_require_an_existing_program()`

---

### [`tests/test_revisions.py`](tests/test_revisions.py)
> *Claim revisions: the head carries the edges, the old claim stays as history.*

**Size**: `171` lines (`6027` bytes)

**Classes:**
- `class RevisionTests`
  - Method `.setUp()`
  - Method `._revise(**overrides)`
  - Method `.test_revision_marks_the_old_claim_and_starts_unverified()`
  - Method `.test_default_list_hides_superseded_and_history_includes_it()`
  - Method `.test_revision_chain_is_oldest_first()`
  - Method `.test_edges_move_to_the_head()`
  - Method `.test_an_empirical_revision_still_needs_a_quote()`
  - Method `.test_a_revision_needs_a_reason()`
  - Method `.test_a_superseded_claim_cannot_be_revised_again()`
  - Method `.test_a_test_on_a_superseded_claim_warns()`
  - Method `.test_a_superseded_claim_refuses_a_new_verdict()`
  - Method `.test_a_superseded_claim_refuses_a_new_observation()`
  - Method `.test_a_superseded_claim_refuses_a_new_test()`
  - Method `.test_a_superseded_claim_refuses_a_new_prerequisite()`
  - Method `.test_a_superseded_claim_refuses_new_links()`

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

### [`tests/test_search.py`](tests/test_search.py)
> *Deterministic lexical search: phrase ranking, snippets, scope and budget.*

**Size**: `129` lines (`5971` bytes)

**Classes:**
- `class SearchTests`
  - Method `.add_assumption(research, text, basis)`
  - Method `.test_phrase_beats_scattered_terms()`
  - Method `.test_case_and_punctuation_are_folded()`
  - Method `.test_all_four_kinds_are_searched()`
  - Method `.test_research_filter_excludes_other_programs()`
  - Method `.test_superseded_claims_are_hidden_unless_requested()`
  - Method `.test_snippet_reports_the_matching_field()`
  - Method `.test_budget_reports_omitted_lines()`
  - Method `.test_result_limit_is_per_kind()`
  - Method `.test_repeat_is_deterministic()`
  - Method `.test_invalid_inputs_are_refused()`

---

### [`tests/test_sources_questions.py`](tests/test_sources_questions.py)
> *Source identifiers and question lifecycle.*

**Size**: `63` lines (`2639` bytes)

**Classes:**
- `class SourceQuestionTests`
  - Method `.test_source_requires_an_identifier()`
  - Method `.test_source_accepts_doi_or_url()`
  - Method `.test_source_rejects_bad_kind_and_year()`
  - Method `.test_question_closes_without_deleting()`
  - Method `.test_source_year_must_be_an_integer()`
  - Method `.test_double_close_is_refused()`
  - Method `.test_empty_question_is_refused()`

---

### [`tests/test_sources_retraction.py`](tests/test_sources_retraction.py)
> *Source status and retraction cascade.*

**Size**: `257` lines (`11450` bytes)

**Classes:**
- `class SourceStatusTests`
  - Method `.test_downgrade_requires_a_note()`
  - Method `.test_unknown_status_and_repeat_are_refused()`
  - Method `.test_direct_retracted_status_routes_through_retraction()`
  - Method `.test_retraction_path_retires_and_refuses_repeats()`
  - Method `.test_retraction_requires_a_reason()`
  - Method `.test_retraction_requires_evidence()`
  - Method `.test_retraction_ignores_superseded_claims()`
  - Method `.test_retraction_retires_claims_and_dependents()`
  - Method `.test_retracting_twice_is_refused()`
  - Method `.test_claims_are_left_alone_when_already_failed()`
  - Method `.test_retracted_source_is_clean_after_cascade()`
  - Method `.test_retraction_covers_twin_doi_rows()`
  - Method `.test_bulk_retraction_is_refused_without_override()`
  - Method `.test_bulk_retraction_counts_transitive_dependents()`
  - Method `.test_stale_retract_preview_is_refused()`
  - Method `.test_reinstatement_requires_a_note_and_keeps_claim_verdicts()`

---

### [`tests/test_stats.py`](tests/test_stats.py)
> *Statistics: values checked against an independent implementation, behaviour checked here.*

**Size**: `162` lines (`6501` bytes)

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
  - Method `.test_linregress_ignores_non_finite_points()`
  - Method `.test_linregress_too_few_points()`
  - Method `.test_linregress_flat_line()`
- `class HolmTests`
  - Method `.test_holm_adjusts_step_down()`
  - Method `.test_holm_enforces_monotonicity()`
  - Method `.test_holm_empty()`
  - Method `.test_holm_rejects_at_the_boundary()`
- `class CompareTests`
  - Method `.test_significant_difference_with_agreeing_tests()`
  - Method `.test_small_groups_warn()`
  - Method `.test_zero_variance_warns()`
  - Method `.test_ties_are_disclosed()`

---

### [`tests/test_synthesis.py`](tests/test_synthesis.py)
> *Consensus weighting and generated reports.*

**Size**: `202` lines (`9381` bytes)

**Classes:**
- `class SynthesisTests`
  - Method `._question_with_opposition()`
  - Method `.test_consensus_weights_status_and_confidence()`
  - Method `.test_uncovered_question_reports_insufficient_instead_of_a_number()`
  - Method `.test_single_tested_stance_cannot_crown_a_claim()`
  - Method `.test_single_source_cannot_crown_a_claim()`
  - Method `.test_covered_question_displays_its_consensus()`
  - Method `.test_report_contains_evidence_and_contradictions()`
  - Method `.test_report_without_any_verdict_is_refused()`
  - Method `.test_empty_program_still_renders_scaffolding()`
  - Method `.test_report_pairs_answers_with_contradictions()`
  - Method `.test_scorecard_orders_failed_claims_first()`
  - Method `.test_claim_detail_shows_verdict_history()`
  - Method `.test_untrusted_text_cannot_break_a_table()`
  - Method `.test_inventory_counts_every_table()`
  - Method `.test_report_excludes_another_programs_findings()`
  - Method `.test_report_lists_measurements_and_the_last_run()`

---
