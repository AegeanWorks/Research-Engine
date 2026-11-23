# Codebase Map & Symbol Catalog 🗺️

> **AUTO-GENERATED & VERIFIED BY `scripts/update_knowledge_base.py`**
> This document catalogues Python modules, classes, and exported functions. See Map Coverage for any stack it does not index.

---

## 📊 Codebase Metrics
- **Total Python Modules**: `200`
- **Total Classes**: `124`
- **Total Top-Level Functions**: `584`
- **Total Class Methods**: `804`
- **Total Source Lines**: `30979`

## 🧭 Map Coverage
- **Indexed**: python (`200` module(s))
- **Not indexed by this map**: rust (`49` file(s))

> Only Python symbols are catalogued. A language above is reported as not indexed, never as verified by this map.

---

## 📦 Modules & Exported Symbols

### [`engine/__init__.py`](engine/__init__.py)
> *Research Engine: provenance-backed claims, pre-registered hypotheses, executable kill tests.*

**Size**: `3` lines

---

### [`engine/__main__.py`](engine/__main__.py)
> *Entry point for `python -m engine`.*

**Size**: `6` lines

---

### [`engine/ai.py`](engine/ai.py)
> *AI provenance adapter: notarize model I/O, ingest UNVERIFIED claims, propose template tests.*

**Size**: `507` lines

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

**Size**: `100` lines

**Functions:**
- `def _to_amendment(row)`
- `def record_amendment(conn, subject_kind, subject_id, field, before, after, reason, actor)` - *Append one correction; the reason is mandatory and the past is kept.*
- `def list_amendments(conn, subject_kind, subject_id)` - *Amendments in record order, optionally filtered to one corrected record.*

---

### [`engine/analysis.py`](engine/analysis.py)
> *Discovery and ranking over the graph: contradictions, coverage, keystones.*

**Size**: `904` lines

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

**Size**: `103` lines

**Functions:**
- `def utc_now()` - *Return a second-resolution UTC timestamp in ISO-8601 form.*
- `def digest(kind, payload)` - *Domain-separated digest: the artifact kind is hashed before the payload.*
- `def sha256_text(value)` - *Hash extracted output so reproducibility is checked without storing it all.*
- `def digest_tree(root, suffixes, excluded_dirs)` - *Stream a directory into one path-and-content digest.*
- `def atomic_write_text(path, text)` - *Write UTF-8 text through a flushed temp file and an atomic replace.*

---

### [`engine/attempts.py`](engine/attempts.py)
> *Append-only attempt ledger for kill-test executions.*

**Size**: `131` lines

**Functions:**
- `def _to_attempt(row)`
- `def record(conn, test_id, run_group, outcome, reason)` - *Append one attempt; a replaceable outcome requires a recorded reason.*
- `def authoritative(conn, test_id, command_sha256, code_sha256, inputs_sha256)` - *The earliest non-replaceable attempt bound to the current command, code and inputs.*
- `def for_group(conn, test_id, run_group)` - *The attempt recorded for one run group, if any.*
- `def list_attempts(conn, test_ref, limit)` - *Attempts for one test or all tests, newest sequence first.*

---

### [`engine/bundle.py`](engine/bundle.py)
> *Portable JSONL export of the evidence graph, and a digest of its content.*

**Size**: `291` lines

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

**Size**: `184` lines

**Functions:**
- `def _clip(probability)` - *Keep log loss finite without turning a certain prediction into a free pass.*
- `def _bin_index(probability)` - *Return the fixed reliability bin for one probability, including exactly 1.0.*
- `def summary(conn, research_ref, min_resolved)` - *Compute the calibration scorecard for one program without writing anything.*
- `def score(conn, research_ref, min_resolved, actor)` - *Score one program and append the calibration run to the event log.*

---

### [`engine/cascade.py`](engine/cascade.py)
> *Transitive invalidation: when a premise collapses, everything built on it collapses too.*

**Size**: `379` lines

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

### [`engine/charts.py`](engine/charts.py)
> *Text renderers: sparklines, signed bar charts and a statistics table.*

**Size**: `250` lines

**Functions:**
- `def format_number(value)` - *A compact human label for one value, with negative zero folded to zero.*
- `def _edge_texts(low, high)` - *Labels for one bin's edges, adding digits only when six would collapse them.*
- `def resample(values, width)` - *`values` unchanged when it already fits, else `width` bucket averages.*
- `def _ratio(value, low, high)` - *Where `value` sits in [low, high], scaled when the raw span would overflow.*
- `def _level(value, low, high, levels)` - *The half-up level of `value` between `low` and `high`; a flat series sits in the middle.*
- `def sparkline(values, width, ascii_only)` - *One character per value, resampled to `width`; eight levels from lowest to highest.*
- `def _position(value, low, high, width)` - *The half-up column of `value` in a chart of `width` cells.*
- `def _bar_row(value, low, high, width, zero, block, axis)` - *One bar row with the zero axis kept visible; a tiny non-zero value keeps one block.*
- `def bar_chart(values, width, ascii_only)` - *One labelled row per value, bars growing from a shared zero axis.*
- `def stats_table(summary)` - *The human statistics block, one aligned `name  value` line per measurement.*
- `def render_histogram(histogram, width, ascii_only)` - *One row per bin: a right-open range label, a scaled bar and the count.*
- `def render_box(boxplot, width, ascii_only)` - *Render a horizontal 5-number box plot and its summary row (ADR-007).*

---

### [`engine/claims.py`](engine/claims.py)
> *Claims: the unit of knowledge, with provenance and an append-only verdict history.*

**Size**: `588` lines

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

**Size**: `1464` lines

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

**Size**: `192` lines

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

**Size**: `557` lines

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

**Size**: `153` lines

**Functions:**
- `def seed_demo(conn)` - *Create one synthetic program that exercises provenance, tests, and cascade.*

---

### [`engine/diffing.py`](engine/diffing.py)
> *Snapshot comparison: what changed between two exported graphs.*

**Size**: `123` lines

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

**Size**: `134` lines

**Functions:**
- `def normalize_doi(value)` - *Strip resolver prefixes and case-fold a DOI so two spellings compare equal.*
- `def normalize_title(value)` - *Fold accents, case and punctuation while keeping letters from every script.*
- `def _group(items, reason, key)`
- `def duplicate_sources(conn, research_ref, limit)` - *Return groups of sources that share a DOI, a normalized title/year, or a title variant.*

---

### [`engine/errors.py`](engine/errors.py)
> *Error types that carry a cause and a concrete repair step (Why/Fix triad).*

**Size**: `35` lines

**Classes:**
- `class EngineError` - *A user-facing failure with a reason and a repair step.*
  - Method `.__init__(message, why, fix)`
  - Method `.render()`
- `class NotFound` - *A referenced record does not exist.*
  - Method `.__init__(kind, ref)`

---

### [`engine/events.py`](engine/events.py)
> *Append-only event log for actions that are not verdicts.*

**Size**: `283` lines

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

**Size**: `221` lines

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

**Size**: `249` lines

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

**Size**: `62` lines

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

**Size**: `934` lines

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

**Size**: `405` lines

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

**Size**: `109` lines

**Functions:**
- `def integrity_check(conn)` - *Run SQLite's own checks plus a few facts a reviewer wants before archiving.*
- `def _refuse_if_exists(target, because)` - *Refuse to clobber an existing backup target.*
- `def backup(conn, destination)` - *Copy the live database through SQLite's backup API and verify the copy.*

---

### [`engine/manifest.py`](engine/manifest.py)
> *Generated-report manifests and drift detection.*

**Size**: `172` lines

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

**Size**: `46` lines

**Functions:**
- `def sanitize(text, width)` - *Collapse to one safe line: no control characters, no newlines, capped width.*
- `def cell(text, width)` - *A Markdown table cell: sanitized, with pipe and backtick escaped.*
- `def bullet(text, width)` - *One list or heading fragment: sanitized, with backticks escaped.*
- `def code(text, width)` - *A fenced inline code fragment safe for a single-line context.*

---

### [`engine/merging.py`](engine/merging.py)
> *Claim merging: one survivor, every edge repointed, duplicates retired.*

**Size**: `151` lines

**Functions:**
- `def merge_claims(conn, keep_ref, drop_refs, note, actor)` - *Keep one claim, repoint edges from the duplicates, and retire the duplicates.*

---

### [`engine/migrations.py`](engine/migrations.py)
> *Migration harness for lattice and N1 source databases.*

**Size**: `652` lines

**Classes:**
- `class MigrationReport` - *What one inspection or application observed and inserted.*
  - Method `.as_dict()`

**Functions:**
- `def _file_digest(path)`
- `def _read_only(path)` - *Open a source database with SQLite's read-only URI mode.*
- `def _table_count(conn, table)`
- `def _inspect(path, source, tables)`
- `def inspect_lattice(path)` - *Describe a lattice database without writing to it.*
- `def inspect_n1(path)` - *Describe an N1 database without writing to it.*
- `def inspect_research(path)` - *Describe a host research database without writing to it.*
- `def inspect_tree(path, source, suffixes, excluded_dirs)` - *Fingerprint a source tree and count files by suffix.*
- `def inspect_obezite(path)` - *Describe the obezite Markdown claim ledger without writing to it.*
- `def applied_migrations(conn)` - *List migration runs in application order.*
- `def _refuse_repeat(conn, source, digest)`
- `def _year(value)`
- `def _text(value)`
- `def _claim_kind(row)`
- `def _as_date(value)`
- `def _as_timestamp(value)`
- `def _lattice_rows(path)`
- `def _table_rows(conn, table, columns)`
- `def _n1_rows(path)`
- `def _lattice_screening(screening_rows)`
- `def _record_migration(conn, report, mapping)`
- `def migrate_lattice(conn, research_ref, path, dry_run)` - *Import a lattice snapshot into one host program without touching the source.*
- `def migrate_n1(conn, research_ref, path, dry_run)` - *Import an N1 snapshot into one host program without touching the source.*

---

### [`engine/models.py`](engine/models.py)
> *Frozen domain records and the engine's closed vocabularies.*

**Size**: `279` lines

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

**Size**: `483` lines

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

### [`engine/packs.py`](engine/packs.py)
> *Domain-pack registry: declared boundaries, never cross-domain imports.*

**Size**: `163` lines

**Classes:**
- `class Pack`

**Functions:**
- `def _to_pack(row)`
- `def register_pack(conn, name, version, api_version, data_root, manifest_sha256, status)` - *Register one domain pack; the name is the isolation boundary.*
- `def register_pack_from_tree(conn, name, version, root, suffixes, api_version)` - *Register a pack whose external data root is fingerprinted in place.*
- `def get_pack(conn, name)`
- `def list_packs(conn)`
- `def set_pack_status(conn, name, status)` - *Enable or disable a pack without deleting its registration.*

---

### [`engine/plans.py`](engine/plans.py)
> *Pre-registered analysis plans: comparisons declare their prediction first.*

**Size**: `119` lines

**Functions:**
- `def _to_plan(row)`
- `def add_plan(conn, claim_ref, baseline, treatment, prediction, actor)` - *Pre-register what a comparison is expected to show, before it runs.*
- `def get_plan(conn, ref)` - *Fetch one analysis plan by identifier.*
- `def list_plans(conn, claim_ref)` - *Plans in record order, optionally filtered to one claim.*
- `def match_plan(conn, claim_id, baseline, treatment)` - *Plans preregistered for exactly this claim and group pair.*

---

### [`engine/protocols.py`](engine/protocols.py)
> *Measurement protocol registry.*

**Size**: `188` lines

**Functions:**
- `def _to_protocol(row)`
- `def register_protocol(conn, protocol_id, measures, includes_generation, includes_judge, doc_digest, doc_path, actor)` - *Register an immutable protocol id; re-registering the same id is refused.*
- `def get_protocol(conn, ref)` - *Fetch one registered protocol by id.*
- `def amend_protocol(conn, ref, measures, reason, actor)` - *Correct a protocol's measures text; the pin and digest never move.*
- `def list_protocols(conn)` - *Every registered protocol, oldest id first.*

---

### [`engine/provenance.py`](engine/provenance.py)
> *Workspace provenance: the code and input identity a test run or report is bound to.*

**Size**: `187` lines

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

**Size**: `73` lines

**Functions:**
- `def _to_question(row)`
- `def add_question(conn, research_ref, text)` - *Add an open question to a program.*
- `def get_question(conn, ref)` - *Fetch one question by identifier.*
- `def list_questions(conn, research_ref)` - *List questions, optionally filtered by program.*
- `def close_question(conn, ref)` - *Mark a question resolved without deleting its evidence.*

---

### [`engine/researches.py`](engine/researches.py)
> *Research programs: the top-level containers the engine is asked to investigate.*

**Size**: `92` lines

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

**Size**: `114` lines

**Functions:**
- `def set_screening(conn, ref, status, reason, actor)` - *Record one screening decision; an out-status always carries a reason.*
- `def prisma_flow(conn, research_ref)` - *Counts and exclusion reasons across the review phases.*
- `def unscreened_sources(conn, research_ref)` - *Sources still in the identified state, oldest first.*

---

### [`engine/search.py`](engine/search.py)
> *Deterministic lexical search over the recorded graph.*

**Size**: `226` lines

**Functions:**
- `def _terms(query)` - *Case-folded query terms, de-duplicated and stripped of one-character noise.*
- `def _score(needle, terms, blob, primary)` - *Phrase-first relevance: exact phrase, primary field, then matched terms.*
- `def _snippet(text, needle, terms, width)` - *A one-line window around the earliest match, with visible cut marks.*
- `def _fields(kind, row)` - *Primary and supporting text for one record, in match-priority order.*
- `def _rows(conn, kind, research_id, include_superseded)` - *Program-scoped rows for one kind, in stable identifier order.*
- `def search(conn, query, research_ref, kinds, limit, include_superseded, budget)` - *Rank one query across the graph and return matches with a matched-field snippet.*

---

### [`engine/series.py`](engine/series.py)
> *Numeric input parsing, summary statistics and histogram binning for gauge.*

**Size**: `266` lines

**Classes:**
- `class Summary` - *A series' count, extrema, centre and spread, with a stable JSON shape.*
  - Method `.as_dict()` - *The `stats --json` object: stable keys and raw floating-point values.*
- `class Histogram` - *Equal-width bins: `edges` holds one more boundary than `counts` holds counts.*
- `class BoxPlot` - *The 5-number summary: minimum, lower quartile, median, upper quartile, maximum.*

**Functions:**
- `def parse_numbers(chunks, field, delimiter)` - *Every finite number in text chunks, in order.*
- `def percentile(values, fraction)` - *The nearest-rank percentile: the ceil(fraction * n)-th smallest value.*
- `def summarize(values, percentiles)` - *The summary of a non-empty finite series.*
- `def build_histogram(values, bins)` - *Equal-width bins over [min, max], right-open except the last, which is closed.*
- `def build_boxplot(values)` - *Compute the 5-number summary for a box plot (ADR-007).*

---

### [`engine/sources.py`](engine/sources.py)
> *Bibliographic sources: the only place literature text may enter the graph.*

**Size**: `173` lines

**Functions:**
- `def _to_source(row)`
- `def add_source(conn, research_ref, title, year, doi, url, authors, kind, arxiv, venue, abstract, tags, study_type)` - *Register a source; claims cannot cite it before it exists.*
- `def get_source(conn, ref)` - *Fetch one source by identifier.*
- `def list_sources(conn, research_ref)` - *List sources, optionally filtered by program.*
- `def set_source_status(conn, ref, status, note, actor)` - *Change a source's evidence status without deleting the record.*

---

### [`engine/stats.py`](engine/stats.py)
> *Deterministic statistics for recorded observations.*

**Size**: `358` lines

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

**Size**: `479` lines

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

### [`experiments/__init__.py`](experiments/__init__.py)
> *N1 experiment records and baseline-vs-intervention analysis.*

**Size**: `64` lines

---

### [`experiments/analysis.py`](experiments/analysis.py)
> *Baseline-vs-intervention analysis for N1 experiment records.*

**Size**: `356` lines

**Functions:**
- `def _start_date(value)`
- `def _days(value, field)`
- `def _summary(rows)`
- `def _trend(rows)`
- `def calculate_trend(values, dates)` - *Linear trend for a value series, matching the source ``calculate_trend`` result.*
- `def bootstrap_ci(baseline, treatment, seed, resamples)` - *Percentile bootstrap interval with both host and source key names.*
- `def _window_warnings(baseline, intervention, baseline_days, intervention_days, min_baseline_days, min_intervention_days)`
- `def analyze_baseline_vs_intervention(conn, research_ref, metric_name, start_date, baseline_days, intervention_days, settings)` - *Compare one metric before and after the declared intervention start.*
- `def correlation_matrix(conn, research_ref, metric_names)` - *Pairwise Pearson correlation for metrics observed on the same dates.*
- `def analyze_multiple_metrics(conn, research_ref, metric_names, start_date, baseline_days, intervention_days, settings)` - *Analyze several metrics and report the multiple-comparison risk as a global warning.*

---

### [`experiments/compat.py`](experiments/compat.py)
> *Compatibility names for code that imported the N1-Engine classes directly.*

**Size**: `39` lines

**Classes:**
- `class AnalysisEngine` - *Static subset of the source AnalysisEngine that does not need a DataFrame.*
- `class DataManager` - *Bind the source CSV import/export methods to one host connection and program.*
  - Method `.__init__(conn, research_ref)`
  - Method `.import_from_csv(filepath, data_type)`
  - Method `.export_to_csv(filepath, data_type)`
- `class ReportGenerator` - *Source-compatible static report entry point.*

---

### [`experiments/exporter.py`](experiments/exporter.py)
> *CSV export for N1 experiment rows, mirroring the import headers.*

**Size**: `103` lines

**Functions:**
- `def _write(path, fields, rows)`
- `def export_metrics_csv(conn, research_ref, path)`
- `def export_interventions_csv(conn, research_ref, path)`
- `def export_events_csv(conn, research_ref, path)`
- `def export_csv(conn, research_ref, path, data_type)` - *Dispatch the source ``DataManager.export_to_csv`` data types.*

---

### [`experiments/importer.py`](experiments/importer.py)
> *CSV import for N1 experiment rows, using the host experiment model.*

**Size**: `160` lines

**Functions:**
- `def _rows(path, required)`
- `def _result(imported, skipped, reasons)`
- `def import_metrics_csv(conn, research_ref, path, intervention_ref)` - *Import ``date,metric_name,value[,note]`` rows; bad rows are counted, not fatal.*
- `def import_interventions_csv(conn, research_ref, path)` - *Import ``name,start_date[,projected_end_date,end_date,dosage,notes]`` rows.*
- `def import_events_csv(conn, research_ref, path)` - *Import ``timestamp,event_name[,severity,notes,intervention_ref]`` rows.*
- `def import_csv(conn, research_ref, path, data_type)` - *Dispatch the source ``DataManager.import_from_csv`` data types.*

---

### [`experiments/models.py`](experiments/models.py)
> *Experiment records: N1 interventions, metric definitions, measurements and events.*

**Size**: `579` lines

**Classes:**
- `class Intervention`
- `class MetricDefinition`
- `class MetricEntry`
- `class EventEntry`

**Functions:**
- `def _date(value, field)`
- `def _timestamp(value)`
- `def _finite(value)`
- `def _intervention(conn, research_id, ref)`
- `def add_intervention(conn, research_ref, name, start_date, projected_end_date, end_date, dosage, notes)`
- `def add_metric_definition(conn, research_ref, name, description, unit)`
- `def add_metric(conn, research_ref, metric_name, date_value, value, intervention_ref, note)`
- `def add_event(conn, research_ref, event_name, timestamp, severity, notes, intervention_ref)`
- `def _rows(conn, sql, params)`
- `def list_interventions(conn, research_ref)`
- `def list_metric_definitions(conn, research_ref)`
- `def list_metrics(conn, research_ref, metric_name, intervention_ref)`
- `def list_events(conn, research_ref)`
- `def get_intervention(conn, ref)`
- `def get_metric_definition(conn, ref)`
- `def update_intervention(conn, research_ref, ref, name, start_date, projected_end_date, end_date, dosage, notes)` - *Replace an intervention's editable fields; the source dialog's edit path.*
- `def close_intervention(conn, ref, end_date)` - *Close an open intervention, defaulting to today like the source GUI.*
- `def intervention_status(record, today)` - *Return the source GUI's display status for one intervention.*
- `def update_metric_definition(conn, research_ref, ref, name, description, unit)` - *Edit a metric definition and rename its existing entries in one transaction.*
- `def delete_metric_definition(conn, ref)` - *Delete a metric definition; recorded metric entries keep their name.*

---

### [`experiments/reporting.py`](experiments/reporting.py)
> *HTML report generation for N1 baseline-vs-intervention results.*

**Size**: `102` lines

**Functions:**
- `def save_report_json(results, filepath)` - *Save the raw analysis result as JSON, matching the source save_report action.*
- `def _number(value, digits)`
- `def generate_html_report(results, filepath, intervention_name, metric_name)` - *Write the source-style HTML report and return whether it was written.*

---

### [`experiments/settings.py`](experiments/settings.py)
> *Analysis settings for N1 experiments, mirroring the source SettingsManager.*

**Size**: `66` lines

**Classes:**
- `class SettingsManager` - *Load, save and expose the four analysis thresholds.*
  - Method `.__init__(settings_file)`
  - Method `.load_settings()`
  - Method `.save_settings()`
  - Method `.get(key, default)`
  - Method `.set(key, value)`

---

### [`experiments/summary.py`](experiments/summary.py)
> *Daily/weekly N1 summary, extracted from the source SummarizerWidget.*

**Size**: `160` lines

**Functions:**
- `def _date(value, field)`
- `def summarize_period(conn, research_ref, start_date, end_date, intervention_ref)` - *Collect interventions, metrics and events for a date range or one intervention.*
- `def render_summary_html(summary)` - *Format a summary the way the source widget displayed it, with escaping.*

---

### [`rust/ai_parity.py`](rust/ai_parity.py)
**Size**: `81` lines

**Functions:**
- `def run(cmd, cwd)`
- `def compare(label, args, ignore)`

---

### [`rust/analysis_extra_parity.py`](rust/analysis_extra_parity.py)
**Size**: `36` lines

**Functions:**
- `def run(cmd, cwd)`
- `def compare(label, args)`

---

### [`rust/analysis_parity.py`](rust/analysis_parity.py)
**Size**: `22` lines

**Functions:**
- `def run(cmd, cwd)`

---

### [`rust/atlas_expected.py`](rust/atlas_expected.py)
> *Python reference for the Rust `atlas` CLI commands.*

**Size**: `35` lines

---

### [`rust/atlas_parity.py`](rust/atlas_parity.py)
**Size**: `56` lines

**Functions:**
- `def run(cmd, cwd)`
- `def compare(label, args)`

---

### [`rust/born_cavity_parity.py`](rust/born_cavity_parity.py)
**Size**: `43` lines

**Functions:**
- `def run(*args)`
- `def close(a, b)`
- `def check(label, rust, py)`

---

### [`rust/client_expected.py`](rust/client_expected.py)
> *Python reference for the Rust `client` CLI commands.*

**Size**: `38` lines

---

### [`rust/client_parity.py`](rust/client_parity.py)
**Size**: `44` lines

**Functions:**
- `def run(cmd, cwd)`
- `def compare(label, args, db_rust, db_py, py_args)`

---

### [`rust/discovery_expected.py`](rust/discovery_expected.py)
> *Python reference for the Rust `discovery` CLI commands.*

**Size**: `49` lines

---

### [`rust/discovery_parity.py`](rust/discovery_parity.py)
**Size**: `38` lines

**Functions:**
- `def run(cmd, cwd)`
- `def compare(label, args, db_rust, db_py)`

---

### [`rust/excited_fluid_parity.py`](rust/excited_fluid_parity.py)
**Size**: `58` lines

**Functions:**
- `def run(*args)`
- `def close(a, b)`
- `def check(label, rust, py)`

---

### [`rust/experiments_expected.py`](rust/experiments_expected.py)
> *Python reference implementation of the Rust `experiment` CLI commands.*

**Size**: `54` lines

---

### [`rust/experiments_parity.py`](rust/experiments_parity.py)
**Size**: `90` lines

**Functions:**
- `def run(cmd, cwd)`
- `def close(a, b, tol)`
- `def compare(label, args, rust_args, ignore)`

---

### [`rust/fix_literals.py`](rust/fix_literals.py)
**Size**: `10` lines

---

### [`rust/fluid_bridge_expected.py`](rust/fluid_bridge_expected.py)
> *Python reference for the Rust `fluid-bridge` CLI commands.*

**Size**: `39` lines

---

### [`rust/fluid_bridge_parity.py`](rust/fluid_bridge_parity.py)
**Size**: `38` lines

**Functions:**
- `def run(cmd, cwd)`
- `def close(a, b, tol)`
- `def compare(label, args)`

---

### [`rust/fluid_circulant_parity.py`](rust/fluid_circulant_parity.py)
**Size**: `63` lines

**Functions:**
- `def run(*args)`
- `def complex_json(matrix)`
- `def close(a, b)`
- `def check(label, rust, py)`

---

### [`rust/fluid_convergence_parity.py`](rust/fluid_convergence_parity.py)
**Size**: `67` lines

**Functions:**
- `def run(*args)`
- `def close(a, b)`
- `def check(label, rust, py)`
- `def payload(n, steps, dt, h, h_up, z3, force, bond, status)`

---

### [`rust/fluid_frank_oseen_parity.py`](rust/fluid_frank_oseen_parity.py)
**Size**: `57` lines

**Functions:**
- `def run(*args)`
- `def close(a, b)`
- `def check(label, rust, py)`

---

### [`rust/fluid_nelson_closure_parity.py`](rust/fluid_nelson_closure_parity.py)
**Size**: `51` lines

**Functions:**
- `def run(*args)`
- `def close(a, b, key)`
- `def check(label, rust, py)`

---

### [`rust/fluid_reduction_parity.py`](rust/fluid_reduction_parity.py)
**Size**: `57` lines

**Functions:**
- `def run(*args)`
- `def close(a, b)`
- `def check(label, rust, py)`

---

### [`rust/fluid_topology_parity.py`](rust/fluid_topology_parity.py)
**Size**: `39` lines

**Functions:**
- `def run(*args)`
- `def check(label, rust, py)`

---

### [`rust/fluid_variational_width_parity.py`](rust/fluid_variational_width_parity.py)
**Size**: `51` lines

**Functions:**
- `def run(*args)`
- `def close(a, b)`
- `def check(label, rust, py)`

---

### [`rust/fluid_vortex_core_parity.py`](rust/fluid_vortex_core_parity.py)
**Size**: `63` lines

**Functions:**
- `def run(*args)`
- `def close(a, b)`
- `def check(label, rust, py)`

---

### [`rust/hydrogen_radial_parity.py`](rust/hydrogen_radial_parity.py)
**Size**: `61` lines

**Functions:**
- `def run(*args)`
- `def close(a, b)`
- `def check(label, rust, py)`

---

### [`rust/hydrogen_vortex_parity.py`](rust/hydrogen_vortex_parity.py)
**Size**: `48` lines

**Functions:**
- `def run(*args)`
- `def close(a, b)`
- `def check(label, rust, py)`

---

### [`rust/lattice_expected.py`](rust/lattice_expected.py)
> *Python reference for the Rust `lattice` pure-function CLI.*

**Size**: `37` lines

---

### [`rust/lattice_parity.py`](rust/lattice_parity.py)
**Size**: `70` lines

**Functions:**
- `def run(cmd, cwd)`
- `def compare(label, args, py_args)`

---

### [`rust/lattice_query_expected.py`](rust/lattice_query_expected.py)
> *Python reference for the Rust `lattice-query` CLI commands.*

**Size**: `47` lines

---

### [`rust/lattice_query_parity.py`](rust/lattice_query_parity.py)
**Size**: `53` lines

**Functions:**
- `def run(cmd, cwd)`

---

### [`rust/lattice_repo_expected.py`](rust/lattice_repo_expected.py)
> *Python reference for the Rust `lattice-repo` CLI commands.*

**Size**: `73` lines

---

### [`rust/lattice_repo_parity.py`](rust/lattice_repo_parity.py)
**Size**: `50` lines

**Functions:**
- `def run(cmd, cwd)`
- `def strip_volatile(value)`
- `def compare(label, args, write)`

---

### [`rust/lattice_snapshots_expected.py`](rust/lattice_snapshots_expected.py)
> *Python reference for the Rust `lattice-snap` CLI commands.*

**Size**: `30` lines

---

### [`rust/lattice_snapshots_parity.py`](rust/lattice_snapshots_parity.py)
**Size**: `41` lines

**Functions:**
- `def run(cmd, cwd)`

---

### [`rust/lead_selection_parity.py`](rust/lead_selection_parity.py)
**Size**: `68` lines

**Functions:**
- `def run(*args)`
- `def make_csv(path, fields, rows)`

---

### [`rust/mcp_expected.py`](rust/mcp_expected.py)
> *Python reference for the Rust `mcp` CLI command.*

**Size**: `19` lines

---

### [`rust/mcp_parity.py`](rust/mcp_parity.py)
**Size**: `49` lines

**Functions:**
- `def normalize(value)`
- `def run(cmd, cwd)`
- `def compare(label, message, db_rust, db_py)`

---

### [`rust/meta_expected.py`](rust/meta_expected.py)
> *Python reference for the Rust `meta` CLI commands.*

**Size**: `53` lines

---

### [`rust/meta_parity.py`](rust/meta_parity.py)
**Size**: `30` lines

**Functions:**
- `def run(cmd)`
- `def compare(label, args)`

---

### [`rust/node_defect_parity.py`](rust/node_defect_parity.py)
**Size**: `52` lines

**Functions:**
- `def run(*args)`
- `def close(a, b)`
- `def check(label, rust, py)`

---

### [`rust/obezite_expected.py`](rust/obezite_expected.py)
> *Python reference for the Rust `obezite` CLI commands.*

**Size**: `29` lines

---

### [`rust/obezite_parity.py`](rust/obezite_parity.py)
**Size**: `54` lines

**Functions:**
- `def run(cmd, cwd)`
- `def check(label, rust, py)`

---

### [`rust/observed_shape_parity.py`](rust/observed_shape_parity.py)
**Size**: `30` lines

**Functions:**
- `def run(*args)`
- `def check(label, rust, py)`

---

### [`rust/parity_check.py`](rust/parity_check.py)
**Size**: `36` lines

**Functions:**
- `def run(cmd, cwd)`

---

### [`rust/pnn_assay_parity.py`](rust/pnn_assay_parity.py)
**Size**: `63` lines

**Functions:**
- `def run(*args)`
- `def check(label, rust, py)`
- `def as_json_map(items)`

---

### [`rust/pnn_compounds_parity.py`](rust/pnn_compounds_parity.py)
**Size**: `55` lines

**Functions:**
- `def run(*args)`
- `def check(label, rust, py)`

---

### [`rust/pnn_curate_parity.py`](rust/pnn_curate_parity.py)
**Size**: `69` lines

**Functions:**
- `def run(*args)`
- `def make_csv(path, rows)`

---

### [`rust/pnn_curation_parity.py`](rust/pnn_curation_parity.py)
**Size**: `106` lines

**Functions:**
- `def run(*args)`
- `def strip(result)`
- `def normalize_candidate(candidate)`
- `def normalize(payload)`
- `def eq(a, b)`
- `def check(label, rust, py)`
- `def compound(cid, mw, logp, tpsa, hbd, hba, rot, smiles, name, **extra)`

---

### [`rust/pnn_docking_expected.py`](rust/pnn_docking_expected.py)
> *Python reference for the Rust `pnn-docking` CLI commands.*

**Size**: `32` lines

---

### [`rust/pnn_docking_parity.py`](rust/pnn_docking_parity.py)
**Size**: `48` lines

**Functions:**
- `def run(cmd, cwd)`

---

### [`rust/pnn_dynamics_parity.py`](rust/pnn_dynamics_parity.py)
**Size**: `58` lines

**Functions:**
- `def run(*args)`
- `def close(a, b)`
- `def check(label, rust, py)`
- `def point(t, lig, prot, contacts, dg, residues)`

---

### [`rust/pnn_ind_parity.py`](rust/pnn_ind_parity.py)
**Size**: `57` lines

**Functions:**
- `def run(*args)`
- `def close(a, b)`
- `def check(label, rust, py)`

---

### [`rust/pnn_mpo_parity.py`](rust/pnn_mpo_parity.py)
**Size**: `54` lines

**Functions:**
- `def run(*args)`
- `def check(label, rust, py)`

---

### [`rust/pnn_pathway_parity.py`](rust/pnn_pathway_parity.py)
**Size**: `44` lines

**Functions:**
- `def run(*args)`
- `def close(a, b)`
- `def check(label, rust, py)`

---

### [`rust/pnn_preclinical_parity.py`](rust/pnn_preclinical_parity.py)
**Size**: `63` lines

**Functions:**
- `def run(*args)`
- `def close(a, b)`
- `def check(label, rust, py)`

---

### [`rust/pnn_rank_parity.py`](rust/pnn_rank_parity.py)
**Size**: `50` lines

**Functions:**
- `def run(*args)`
- `def check(label, rust, py)`

---

### [`rust/pnn_reports_parity.py`](rust/pnn_reports_parity.py)
**Size**: `52` lines

**Functions:**
- `def check(label, rust, py)`

---

### [`rust/pnn_rules_expected.py`](rust/pnn_rules_expected.py)
> *Python reference for the Rust `pnn-rules` CLI commands.*

**Size**: `17` lines

---

### [`rust/pnn_rules_parity.py`](rust/pnn_rules_parity.py)
**Size**: `38` lines

**Functions:**
- `def run(cmd, cwd)`

---

### [`rust/pnn_safety_expected.py`](rust/pnn_safety_expected.py)
> *Python reference for the Rust `pnn-safety` CLI command.*

**Size**: `19` lines

---

### [`rust/pnn_safety_parity.py`](rust/pnn_safety_parity.py)
**Size**: `54` lines

---

### [`rust/pnn_sar_parity.py`](rust/pnn_sar_parity.py)
**Size**: `61` lines

**Functions:**
- `def run(*args)`
- `def check(label, rust, py)`

---

### [`rust/pnn_screen_parity.py`](rust/pnn_screen_parity.py)
**Size**: `69` lines

**Functions:**
- `def run(*args)`
- `def close(a, b)`
- `def check(label, rust, py)`
- `def compound(cid, mw, logp, tpsa, hbd, hba, rot, **extra)`

---

### [`rust/pnn_tables_parity.py`](rust/pnn_tables_parity.py)
**Size**: `75` lines

**Functions:**
- `def run(*args)`
- `def check(label, rust, py)`
- `def compound(cid, mw, logp, tpsa, hbd, hba, rot, **extra)`

---

### [`rust/pnn_target_parity.py`](rust/pnn_target_parity.py)
**Size**: `39` lines

**Functions:**
- `def run(*args)`
- `def check(label, rust, py)`

---

### [`rust/predictions_parity.py`](rust/predictions_parity.py)
**Size**: `31` lines

**Functions:**
- `def run(*args)`
- `def check(label, rust, py)`

---

### [`rust/providers_expected.py`](rust/providers_expected.py)
> *Python reference for the Rust `providers` CLI commands.*

**Size**: `24` lines

**Functions:**
- `def fetcher(url, timeout)`

---

### [`rust/providers_parity.py`](rust/providers_parity.py)
**Size**: `65` lines

**Functions:**
- `def run(cmd, cwd)`

---

### [`rust/source_duplicates_parity.py`](rust/source_duplicates_parity.py)
**Size**: `43` lines

**Functions:**
- `def run(*args)`
- `def check(label, rust, py)`

---

### [`rust/studio_api_expected.py`](rust/studio_api_expected.py)
> *Python reference for the Rust `studio` CLI commands.*

**Size**: `30` lines

---

### [`rust/studio_api_parity.py`](rust/studio_api_parity.py)
**Size**: `44` lines

**Functions:**
- `def run(cmd, cwd)`

---

### [`rust/two_state_marcus_parity.py`](rust/two_state_marcus_parity.py)
**Size**: `49` lines

**Functions:**
- `def run(*args)`
- `def close(a, b)`
- `def check(label, rust, py)`

---

### [`rust/views_parity.py`](rust/views_parity.py)
**Size**: `46` lines

**Functions:**
- `def run(cmd, cwd)`
- `def compare(label, args)`

---

### [`rust/vortex_cascade_parity.py`](rust/vortex_cascade_parity.py)
**Size**: `48` lines

**Functions:**
- `def run(*args)`
- `def close(a, b)`
- `def check(label, rust, py)`

---

### [`rust/vortex_particles_parity.py`](rust/vortex_particles_parity.py)
**Size**: `49` lines

**Functions:**
- `def run(*args)`
- `def close(a, b)`
- `def check(label, rust, py)`

---

### [`rust/water_analogue_parity.py`](rust/water_analogue_parity.py)
**Size**: `50` lines

**Functions:**
- `def run(*args)`
- `def close(a, b)`
- `def check(label, rust, py)`

---

### [`rust/water_dispersive_parity.py`](rust/water_dispersive_parity.py)
**Size**: `44` lines

**Functions:**
- `def run(*args)`
- `def close(a, b)`
- `def check(label, rust, py)`

---

### [`rust/water_electron_parity.py`](rust/water_electron_parity.py)
**Size**: `47` lines

**Functions:**
- `def run(*args)`
- `def close(a, b)`
- `def check(label, rust, py)`

---

### [`rust/water_lineshape_parity.py`](rust/water_lineshape_parity.py)
**Size**: `38` lines

**Functions:**
- `def run(*args)`
- `def close(a, b)`
- `def check(label, rust, py)`

---

### [`rust/water_marcus_parity.py`](rust/water_marcus_parity.py)
**Size**: `41` lines

**Functions:**
- `def run(*args)`
- `def close(a, b)`
- `def check(label, rust, py)`

---

### [`rust/water_pressure_parity.py`](rust/water_pressure_parity.py)
**Size**: `52` lines

**Functions:**
- `def run(*args)`
- `def close(a, b)`
- `def check(label, rust, py)`

---

### [`rust/water_rays_parity.py`](rust/water_rays_parity.py)
**Size**: `50` lines

**Functions:**
- `def run(*args)`
- `def close(a, b)`
- `def check(label, rust, py)`

---

### [`rust/water_reorganization_parity.py`](rust/water_reorganization_parity.py)
**Size**: `45` lines

**Functions:**
- `def run(*args)`
- `def close(a, b)`
- `def check(label, rust, py)`

---

### [`rust/water_temperature_parity.py`](rust/water_temperature_parity.py)
**Size**: `42` lines

**Functions:**
- `def run(*args)`
- `def close(a, b)`
- `def check(label, rust, py)`

---

### [`rust/water_vde_parity.py`](rust/water_vde_parity.py)
**Size**: `45` lines

**Functions:**
- `def run(*args)`
- `def close(a, b)`
- `def check(label, rust, py)`

---

### [`rust/water_well_parity.py`](rust/water_well_parity.py)
**Size**: `54` lines

**Functions:**
- `def run(*args)`
- `def close(a, b)`
- `def check(label, rust, py)`

---

### [`rust/web_expected.py`](rust/web_expected.py)
> *Python reference for the Rust `web` CLI command.*

**Size**: `22` lines

---

### [`rust/web_parity.py`](rust/web_parity.py)
**Size**: `69` lines

**Functions:**
- `def run(cmd, cwd)`
- `def compare(label, method, path, body)`

---

### [`studio/__init__.py`](studio/__init__.py)
> *Studio surfaces: web, MCP and HTTP API.*

**Size**: `1` lines

---

### [`studio/api.py`](studio/api.py)
> *Stable public Python surface for host integrations such as neurocore.*

**Size**: `361` lines

**Functions:**
- `def _question_key(value)` - *Normalize `question:q_000001` or `q_000001` to the bare identifier.*
- `def get_evidence_matrix(repository, question_ids)` - *The Paper x Question matrix, optionally narrowed to selected research questions.*
- `def get_hypothesis_evidence(repository, question_id)` - *Evidence grouped by role (supports, contradicts, answers, other) for one question.*

---

### [`studio/client.py`](studio/client.py)
> *Turnkey client facade for AI hosts: own one connection, call MCP-parity tools.*

**Size**: `400` lines

**Classes:**
- `class LatticeClient` - *A synchronous, context-managed graph client with MCP tool parity.*
  - Method `.__init__(db_path, read_only)`
  - Property `.repository` - *The underlying repository for advanced writable callers.*
  - Method `.__enter__()`
  - Method `.__exit__(exc_type, exc, traceback)`
  - Method `.close()` - *Close the owned connection; safe to call more than once.*
  - Method `._ensure_open()`
  - Method `.tool_schemas()` - *The MCP tool declarations, filtered to the read-only set when requested.*
  - Method `.resource_schemas()` - *A deep copy of the advertised MCP resource declarations.*
  - Method `.prompt_schemas()` - *A deep copy of the advertised MCP prompt declarations.*
  - Method `.read_resource(uri)` - *Read one advertised resource such as `lattice://stats`.*
  - Method `.get_prompt(name, arguments)` - *Render one advertised prompt with its arguments.*
  - Method `.call_tool(name, arguments, **kwargs)` - *Run one MCP tool by name; arguments may be a mapping plus keyword overrides.*
  - Method `.search(query, limit, stance, min_confidence, year, tokens)`
  - Method `.discover_papers(query, source, limit, ingest)`
  - Method `.extract_claims(paper, question)`
  - Method `.get_entity(ref)`
  - Method `.neighbors(ref, kind)`
  - Method `.subgraph(ref, depth, tokens)`
  - Method `.related_findings(target, limit, tokens)`
  - Method `.outline(tokens)`
  - Method `.add_paper(metadata)`
  - Method `.add_claim(paper, text, quote, locator, stance, confidence)`
  - Method `.add_question(text)`
  - Method `.set_question_status(question, status)`
  - Method `.add_edge(src, dst, kind, note)`
  - Method `.ask(target, limit)` - *Evidence-first question answering, including search mode outside MCP.*
  - Method `.brief(target, tokens)`
  - Method `.review(target)`
  - Method `.synthesize(target, tokens)`
  - Method `.analyze_graph(auto_link, limit)`
  - Method `.detect_contradictions(auto_link)`
  - Method `.export_snapshot(path)`
  - Method `.export_graphml(path)` - *Export the evidence graph in standard GraphML XML format.*
  - Method `.export_cytoscape(path)` - *Export the evidence graph in Cytoscape.js JSON format.*
  - Method `.sync_article(article_data, auto_extract)` - *Sync a NeuroCore or external article dict into the evidence graph.*
  - Method `.import_snapshot(path)`
  - Method `.diff_snapshot(old_path, new_path)` - *Diff a baseline snapshot against another snapshot or the live graph.*
  - Method `.find_path(src, dst, max_depth, directed, edge_kinds)` - *Find the shortest chain of relations connecting two entities via BFS.*
  - Method `.propose_hypotheses(question, limit)` - *Formulate testable hypotheses from evidence gaps and contradiction clusters.*
  - Method `.screen_paper(paper_id, status, reason, notes)` - *Record an auditable PRISMA 2020 screening decision for a paper.*
  - Method `.get_prisma_flow(format)` - *Get PRISMA 2020 review attrition metrics and flow diagram.*
  - Method `.get_context_pack(targets, max_tokens, format)` - *Generate a token-bounded GraphRAG context pack for LLM reasoning.*
  - Method `.compute_meta_analysis(studies, question, model, format)` - *Execute quantitative meta-analysis and generate forest plot.*
  - Method `.stats()`
- `class AsyncLatticeClient` - *An asyncio facade that serializes the sync client on one dedicated thread.*
  - Method `.__init__(db_path, read_only)`
  - Method `async def .__aenter__()`
  - Method `async def .__aexit__(exc_type, exc, traceback)`
  - Method `async def .close()` - *Close the owned connection and stop the worker thread.*
  - Method `._ensure_open()`
  - Property `.repository` - *The repository is sync-only; exposing it would cross the worker thread.*
  - Method `async def ._run(func, *args, **kwargs)`
  - Method `async def .tool_schemas()`
  - Method `async def .resource_schemas()`
  - Method `async def .prompt_schemas()`
  - Method `async def .read_resource(uri)`
  - Method `async def .get_prompt(name, arguments)`
  - Method `async def .call_tool(name, arguments, **kwargs)`
  - Method `.__getattr__(name)`

---

### [`studio/mcp.py`](studio/mcp.py)
> *A dependency-free MCP stdio server exposing the graph as JSON-RPC tools.*

**Size**: `540` lines

**Functions:**
- `def _tool(name, description, properties, required)` - *An MCP tool declaration with a JSON Schema for its arguments.*
- `def handle_message(repository, message)` - *Dispatch one JSON-RPC message; notifications return None.*
- `def _call_tool(repository, request_id, params)` - *Run one MCP tool call and wrap the result as text content.*
- `def read_resource(repository, uri)` - *Return the payload for one advertised resource URI.*
- `def get_prompt(repository, name, arguments)` - *Render one advertised prompt into MCP message content.*
- `def _read_resource(repository, request_id, params)` - *Return an MCP resource payload by URI.*
- `def _get_prompt(repository, request_id, params)` - *Render a structured scientific synthesis prompt for an AI agent.*
- `def dispatch_tool(repository, name, arguments)` - *Map a tool name to its repository, discovery, extraction or synthesis operation.*
- `def _text(arguments, name)` - *A required string argument.*
- `def _int(arguments, name, default)` - *An optional integer argument that fails with the Error/Why/Fix triad.*
- `def _result(request_id, result)` - *A JSON-RPC success response.*
- `def _error(request_id, code, message)` - *A JSON-RPC error response.*
- `def serve(repository, stdin, stdout)` - *Serve newline-delimited JSON-RPC until the input stream closes.*

---

### [`studio/web.py`](studio/web.py)
> *Zero-dependency web server and human-friendly Research Studio UI for Lattice.*

**Size**: `2438` lines

**Classes:**
- `class WebResponse` - *Immutable HTTP response returned by `dispatch_web_request`.*

**Functions:**
- `def dispatch_web_request(repository, method, path, body)` - *Route an HTTP method and path to the UI or JSON API without network sockets.*
- `def _dispatch_post(repository, route, payload)` - *Handle JSON POST routes for mutations, discovery, extraction, and demo seeding.*
- `def _build_overview(repository)` - *Assemble full workspace state for the Human UI dashboard.*
- `def _handle_search(repository, query)` - *Run filtered search from query parameters.*
- `def _handle_literature(repository, query)` - *Search the literature by tags, words, sentences, study type and year.*
- `def _handle_subgraph(repository, query)` - *Run multi-hop subgraph traversal from query parameters.*
- `def _handle_path(repository, query)` - *Run relation path search between two entities from query parameters.*
- `def _handle_hypothesize(repository, query)` - *Propose structured testable hypotheses from query parameters.*
- `def _handle_synthesize(repository, query)` - *Run scientific literature synthesis from query parameters.*
- `def _handle_export_bibtex(repository, query)` - *Export papers matching query parameters as BibTeX.*
- `def _build_matrix_bundle(repository)` - *Assemble the Paper x Question evidence matrix, contradictions, and keystone ranking.*
- `def _handle_ingest_text(repository, payload)` - *Parse raw bibliography or note text (BibTeX, RIS, CSV, Markdown, text) and ingest into the graph.*
- `def _export_jsonl_string(repository)` - *Serialize all graph entities and edges as portable JSONL text.*
- `def _seed_demo(repository)` - *Populate the built-in seed corpus, create research questions, and extract claims.*
- `def _first(query, key)` - *First query parameter value or empty string.*
- `def _parse_json_body(body)` - *Parse an optional JSON request body into a dictionary.*
- `def _json_response(status, payload)` - *Serialize a dictionary as an application/json `WebResponse`.*
- `def serve_web(db_path, host, port, open_browser, once)` - *Run the local HTTP server for the Lattice Research Studio UI.*

---

### [`tests/__init__.py`](tests/__init__.py)
> *Regression shield for the research engine.*

**Size**: `1` lines

---

### [`tests/support.py`](tests/support.py)
> *Shared fixtures: a fresh in-memory database per test.*

**Size**: `64` lines

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

**Size**: `417` lines

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

**Size**: `185` lines

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

**Size**: `218` lines

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

**Size**: `126` lines

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

**Size**: `193` lines

**Classes:**
- `class BundleTests`
  - Method `.setUp()`
  - Method `.test_export_writes_meta_first_and_every_record()`
  - Method `.test_export_declares_the_supported_bridge()`
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

**Size**: `121` lines

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

**Size**: `155` lines

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

### [`tests/test_charts.py`](tests/test_charts.py)
> *Unit tests for gauge's deterministic text renderers.*

**Size**: `208` lines

**Classes:**
- `class SparklineTests` - *Eight fixed levels, a flat middle and proportional resampling.*
  - Method `.test_a_rising_series_uses_every_level()`
  - Method `.test_a_flat_series_sits_in_the_middle_level()`
  - Method `.test_the_ascii_twin_uses_its_own_middle_level()`
  - Method `.test_a_short_series_is_not_padded_or_upsampled()`
  - Method `.test_a_long_series_resamples_to_exactly_the_width()`
  - Method `.test_extreme_opposite_signs_render_without_overflow()`
  - Method `.test_an_empty_series_is_refused()`
- `class ResampleTests` - *Proportional buckets keep the shape of the original series.*
  - Method `.test_five_values_become_two_bucket_averages()`
  - Method `.test_a_series_within_the_width_is_unchanged()`
  - Method `.test_bucket_averages_of_extreme_values_do_not_overflow()`
  - Method `.test_a_zero_width_is_refused()`
- `class BarChartTests` - *Rows share a zero axis and keep a visible block for tiny values.*
  - Method `.test_positive_bars_grow_from_the_left_axis()`
  - Method `.test_signed_bars_grow_outward_from_the_center()`
  - Method `.test_all_zero_values_show_a_centered_axis()`
  - Method `.test_an_empty_series_or_narrow_width_is_refused()`
- `class StatsTableTests` - *The five-line table is a stable, aligned surface.*
  - Method `.test_the_table_matches_the_documented_example()`
  - Method `.test_numbers_stay_compact_and_negative_zero_folds()`
  - Method `.test_table_shows_custom_percentiles_aligned()`
  - Method `.test_empty_percentiles_table_keeps_p90()`
- `class HistogramRenderTests` - *Bars scale to the largest count and every bin keeps a row.*
  - Method `.test_bars_scale_to_the_largest_count()`
  - Method `.test_a_flat_series_uses_one_compact_label()`
  - Method `.test_empty_bins_stay_visible()`
  - Method `.test_the_unicode_block_is_the_default()`
  - Method `.test_a_narrow_width_is_refused()`
  - Method `.test_edges_that_share_six_digits_stay_distinguishable()`
- `class BoxPlotRenderTests` - *The box plot renders whiskers, quartiles, median and extrema (ADR-007).*
  - Method `.test_render_box_ascii()`
  - Method `.test_render_box_unicode()`
  - Method `.test_render_box_flat_series()`
  - Method `.test_a_collapsed_box_still_shows_both_brackets()`
  - Method `.test_a_box_whose_median_is_the_maximum_keeps_its_right_bracket()`
  - Method `.test_narrow_width_refused()`

---

### [`tests/test_claims.py`](tests/test_claims.py)
> *Provenance requirements and the append-only verdict lifecycle.*

**Size**: `226` lines

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

**Size**: `628` lines

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

**Size**: `87` lines

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

**Size**: `167` lines

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

**Size**: `119` lines

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

**Size**: `107` lines

**Classes:**
- `class DocsTests`
  - Method `.test_readme_has_the_cold_start_contract()`
  - Method `.test_architecture_and_mechanics_documents_exist()`
  - Method `.test_project_memory_declares_the_test_command()`
  - Method `.test_readme_tree_names_real_modules()`
  - Method `.test_readme_documents_the_current_schema_and_gates()`
  - Method `.test_architecture_documents_binding_and_digests()`

---

### [`tests/test_domain_isolation.py`](tests/test_domain_isolation.py)
> *Domain packs stay isolated: no pack imports another pack or a studio surface.*

**Size**: `54` lines

**Classes:**
- `class DomainIsolationTests`
  - Method `.test_no_pack_imports_another_pack()`
  - Method `.test_no_pack_imports_a_surface_or_adapter()`
  - Method `.test_engine_does_not_import_a_pack_or_surface()`

**Functions:**
- `def _imports(path)`

---

### [`tests/test_duplicates.py`](tests/test_duplicates.py)
> *Duplicate sources: DOI and title normalization, scope, and the integrity warning.*

**Size**: `93` lines

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

**Size**: `33` lines

**Classes:**
- `class NotFoundTests`
  - Method `.test_fix_points_at_a_real_cli_verb()`

---

### [`tests/test_events.py`](tests/test_events.py)
> *Event log: append-only record of actions that are not verdicts.*

**Size**: `190` lines

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

### [`tests/test_experiments.py`](tests/test_experiments.py)
> *N1 experiment records and baseline-vs-intervention analysis on the host core.*

**Size**: `186` lines

**Classes:**
- `class ExperimentModelTests`
  - Method `.test_intervention_round_trip()`
  - Method `.test_metric_definition_is_unique_per_program()`
  - Method `.test_metric_entry_links_intervention_and_validates_finite_value()`
  - Method `.test_event_severity_is_bounded()`
  - Method `.test_intervention_from_another_program_is_refused()`
  - Method `.test_csv_import_counts_good_and_bad_rows()`
- `class ExperimentAnalysisTests`
  - Method `._rows(research, values, start_day, metric)`
  - Method `.test_baseline_and_intervention_windows()`
  - Method `.test_insufficient_data_returns_counts_not_an_exception()`
  - Method `.test_multiple_metric_warning_above_three()`

---

### [`tests/test_golden.py`](tests/test_golden.py)
> *Golden run: the whole command surface, end to end, in a fresh database.*

**Size**: `205` lines

**Classes:**
- `class GoldenRunTests`
  - Method `.setUp()`
  - Method `.run_cli(*args)`
  - Method `.must(*args)`
  - Method `.test_every_command_composes()`

---

### [`tests/test_hypotheses.py`](tests/test_hypotheses.py)
> *Pre-registration precedes outcomes and cards carry the falsification criterion.*

**Size**: `83` lines

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

**Size**: `57` lines

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

**Size**: `70` lines

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

**Size**: `462` lines

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

**Size**: `168` lines

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

### [`tests/test_license_notices.py`](tests/test_license_notices.py)
> *Ported packages keep their source notice, SHA and license text.*

**Size**: `27` lines

**Classes:**
- `class LicenseNoticeTests`
  - Method `.test_every_ported_package_has_a_notice_with_its_pin()`
  - Method `.test_al_and_asl_license_texts_are_present()`

---

### [`tests/test_maintenance.py`](tests/test_maintenance.py)
> *Database maintenance: integrity verification and verified backups.*

**Size**: `166` lines

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

**Size**: `190` lines

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

**Size**: `50` lines

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

**Size**: `253` lines

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

**Size**: `139` lines

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

**Size**: `275` lines

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

### [`tests/test_migration_harness.py`](tests/test_migration_harness.py)
> *Migration harness: inspect first, then apply a source fixture without losing provenance.*

**Size**: `268` lines

**Classes:**
- `class MigrationHarnessTests`
  - Method `._lattice()`
  - Method `._n1()`
  - Method `._legacy_n1()`
  - Method `.test_lattice_inspect_is_read_only_and_counts_rows()`
  - Method `.test_lattice_dry_run_writes_nothing()`
  - Method `.test_lattice_apply_preserves_paper_fields_provenance_and_screening()`
  - Method `.test_lattice_apply_is_recorded_once()`
  - Method `.test_n1_manifest_and_apply_link_metrics_to_interventions()`
  - Method `.test_legacy_n1_schema_without_link_columns_migrates()`
  - Method `.test_golden_both_sources_share_one_program()`
  - Method `.test_inspect_tree_counts_and_fingerprints_files()`
  - Method `.test_inspect_obezite_counts_verified_and_backfill()`
  - Method `.test_inspect_research_reads_a_host_database()`

**Functions:**
- `def _fixture(sql, name)`

---

### [`tests/test_models.py`](tests/test_models.py)
> *Vocabularies are closed and records are immutable.*

**Size**: `53` lines

**Classes:**
- `class ModelTests`
  - Method `.test_status_vocabulary_is_closed()`
  - Method `.test_dependency_relations_are_explicit()`
  - Method `.test_claim_is_frozen()`

---

### [`tests/test_n1_ports.py`](tests/test_n1_ports.py)
> *N1 suitable ports: provenance-gated correlation, batch stats-all, CSV import.*

**Size**: `327` lines

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

### [`tests/test_n1_surfaces.py`](tests/test_n1_surfaces.py)
> *N1 surfaces that were missing after the first merge: correlation, CSV, report.*

**Size**: `284` lines

**Classes:**
- `class ExperimentSurfaceTests`
  - Method `.setUp()`
  - Method `.test_correlation_matrix_aligns_pairs_by_date()`
  - Method `.test_correlation_refuses_unknown_metric()`
  - Method `.test_csv_import_and_export_round_trip_all_three_types()`
  - Method `.test_unknown_csv_type_is_refused()`
  - Method `.test_out_of_range_severity_is_coerced_not_fatal()`
  - Method `.test_all_bad_rows_report_failure()`
  - Method `.test_settings_round_trip_and_custom_minimum()`
  - Method `.test_compatibility_names_cover_trend_bootstrap_and_data_manager()`
  - Method `.test_intervention_edit_close_and_status()`
  - Method `.test_metric_definition_rename_updates_entries_and_delete()`
  - Method `.test_summary_period_and_html()`
  - Method `.test_report_json_save()`
  - Method `.test_html_report_writes_escape_safe_summary()`

---

### [`tests/test_observations.py`](tests/test_observations.py)
> *Observations: raw values, their voiding, and the statistics projection over them.*

**Size**: `244` lines

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

### [`tests/test_packs.py`](tests/test_packs.py)
> *Domain-pack registry: an isolated pack is declared, not imported across domains.*

**Size**: `84` lines

**Classes:**
- `class PackRegistryTests`
  - Method `.test_register_and_read_a_pack()`
  - Method `.test_duplicate_pack_is_refused()`
  - Method `.test_invalid_api_version_is_refused()`
  - Method `.test_invalid_manifest_digest_is_refused()`
  - Method `.test_pack_data_root_is_a_reference_not_a_copy()`
  - Method `.test_register_pack_from_tree_fingerprints_external_data()`
  - Method `.test_register_pack_from_empty_tree_is_refused()`

---

### [`tests/test_plans.py`](tests/test_plans.py)
> *Analysis plans are preregistered; unmatched comparisons read as exploratory.*

**Size**: `101` lines

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

### [`tests/test_projects_scan.py`](tests/test_projects_scan.py)
> *Every directory under projects/ is named in the project scan.*

**Size**: `32` lines

**Classes:**
- `class ProjectsScanCoverageTests`
  - Method `.test_every_top_level_and_archived_project_is_listed()`

---

### [`tests/test_promotion.py`](tests/test_promotion.py)
> *Promotion gate: a NUMERIC verdict must cite a current, verified run group.*

**Size**: `94` lines

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

**Size**: `91` lines

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

**Size**: `45` lines

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

**Size**: `171` lines

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

### [`tests/test_schema_v14.py`](tests/test_schema_v14.py)
> *Schema 14: lattice paper fields, N1 experiment tables and the pack registry.*

**Size**: `107` lines

**Classes:**
- `class Schema14MigrationTests`
  - Method `._v13()`
  - Method `.test_version_13_source_gains_paper_columns_and_keeps_rows()`
  - Method `.test_version_14_creates_experiment_and_pack_tables()`
- `class PaperFieldTests`
  - Method `.test_source_round_trips_paper_metadata()`

---

### [`tests/test_screening.py`](tests/test_screening.py)
> *Screening decisions and the PRISMA flow.*

**Size**: `85` lines

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

**Size**: `129` lines

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

### [`tests/test_series.py`](tests/test_series.py)
> *Unit tests for gauge's input parsing and summary statistics.*

**Size**: `240` lines

**Classes:**
- `class ParseNumbersTests` - *One strict reader for positional arguments, files and pipes.*
  - Method `.test_whitespace_commas_and_lines_split_the_same_way()`
  - Method `.test_decimal_exponent_and_signed_forms_are_accepted()`
  - Method `.test_a_generator_is_consumed_once()`
  - Method `.test_a_non_numeric_token_is_named()`
  - Method `.test_non_finite_values_are_refused()`
  - Method `.test_empty_input_is_refused()`
- `class PercentileTests` - *The nearest-rank definition recorded in ADR-002.*
  - Method `.test_p90_is_the_ninth_of_ten_values()`
  - Method `.test_a_single_value_is_its_own_percentile()`
  - Method `.test_an_out_of_range_fraction_is_refused()`
  - Method `.test_an_empty_series_is_refused()`
- `class SummaryTests` - *Central values, spread and the stable JSON object.*
  - Method `.test_odd_series_has_its_middle_value_as_median()`
  - Method `.test_even_series_averages_the_middle_pair()`
  - Method `.test_stdev_is_the_population_form()`
  - Method `.test_a_flat_series_has_zero_stdev()`
  - Method `.test_extreme_opposite_signs_stay_finite()`
  - Method `.test_even_median_of_extreme_values_does_not_overflow()`
  - Method `.test_an_unrepresentable_sum_is_refused()`
  - Method `.test_json_object_has_the_documented_keys()`
  - Method `.test_custom_percentiles_computed_and_included_in_dict()`
  - Method `.test_invalid_custom_percentiles_refused()`
  - Method `.test_empty_percentiles_list_behaves_like_none()`
  - Method `.test_an_empty_or_non_finite_series_is_refused()`
- `class HistogramTests` - *The equal-width bin contract recorded in ADR-004.*
  - Method `.test_ten_values_split_evenly_across_five_bins()`
  - Method `.test_the_maximum_belongs_to_the_closed_last_bin()`
  - Method `.test_an_inner_edge_belongs_to_the_upper_bin()`
  - Method `.test_a_flat_series_is_one_bin()`
  - Method `.test_negative_ranges_bin_without_special_cases()`
  - Method `.test_extreme_opposite_signs_do_not_overflow()`
  - Method `.test_bin_counts_outside_the_bounds_are_refused()`
  - Method `.test_an_empty_or_non_finite_series_is_refused()`
- `class FieldAndDelimiterTests` - *Field and delimiter extraction rules (ADR-005).*
  - Method `.test_field_extracts_column_from_lines()`
  - Method `.test_delimiter_splits_custom_separator()`
  - Method `.test_field_with_custom_delimiter_csv()`
  - Method `.test_field_out_of_bounds_raises()`
  - Method `.test_invalid_field_raises()`
  - Method `.test_empty_delimiter_raises()`
  - Method `.test_field_with_empty_delimiter_is_refused()`
- `class BoxPlotTests` - *The 5-number summary computation (ADR-007).*
  - Method `.test_boxplot_computes_five_number_summary()`
  - Method `.test_boxplot_flat_series()`
  - Method `.test_boxplot_empty_or_non_finite_raises()`

---

### [`tests/test_sources_questions.py`](tests/test_sources_questions.py)
> *Source identifiers and question lifecycle.*

**Size**: `63` lines

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

**Size**: `257` lines

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

**Size**: `162` lines

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

**Size**: `202` lines

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
