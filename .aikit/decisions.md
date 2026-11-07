# Decisions

Why this project is built the way it is, oldest first. One entry per decision that changes a
contract, a dependency, a data format or the architecture; IDs are consecutive and never reused.

### ADR-001: Compose mechanics, do not fork the reference projects
- **Date**: 2026-10-27
- **Status**: Accepted
- **Context**: Four existing projects each solve one part of research discipline. Forking all four
  would duplicate schemas and mix domain content into a general engine.
- **Decision**: Build one standard-library SQLite graph and implement six transferable mechanics:
  provenance-first claims, a falsification-first verdict vocabulary, executable kill tests, two-run
  verification, pre-registration, and transitive cascade invalidation.
- **Consequences**: The engine has no literature crawler and no domain pipeline. Domain work is
  hosted as research programs. Mechanics are clean-room implementations, not code copies.

### ADR-002: Closed verdict vocabulary with INVALIDATED
- **Date**: 2026-10-27
- **Status**: Accepted
- **Context**: Reference ledgers distinguish proven, numeric, unverified, falsified and retracted
  claims. None has a state for "a premise collapsed, so this claim is no longer established".
- **Decision**: Add `INVALIDATED` as a distinct status written only by cascade or an explicit
  evidence-backed verdict. Keep `RETRACTED` for deliberate withdrawal.
- **Consequences**: Reports can separate author withdrawal from premise collapse. Integrity can
  detect a dependent left standing after its premise failed.

### ADR-003: Numeric claims require two agreeing process runs
- **Date**: 2026-10-27
- **Status**: Accepted
- **Context**: A single run cannot distinguish a measurement from a one-off artifact.
- **Decision**: `test verify` runs a command twice in separate processes and compares exit code plus
  stdout/stderr hashes. `NUMERIC` integrity requires a run group with two passing, identical runs.
- **Consequences**: Tests with timings or randomness fail verification by design. The recorded
  output tail is for diagnosis; the hashes are the audit evidence.

### ADR-004: Dependency edges drive invalidation, evidence edges do not
- **Date**: 2026-10-27
- **Status**: Accepted
- **Context**: A supporting citation is not always a premise. Collapsing everything that cites a
  failed claim would over-invalidate.
- **Decision**: Only `derived_from` and `depends_on` propagate invalidation. `supports`,
  `contradicts`, `replicates`, `extends`, `uses_method`, `measures` and `related` remain evidence
  relations.
- **Consequences**: Authors must declare structural dependence explicitly. Cascade preview shows the
  exact transitive closure before a collapse is recorded.

### ADR-005: Keep the command surface in one adapter module
- **Date**: 2026-10-27
- **Status**: Accepted
- **Context**: The domain modules need one stable entry point, but a CLI that owns business rules
  would duplicate validation.
- **Decision**: `engine/cli.py` only parses arguments and renders results. Every rule lives in a
  domain module and raises `EngineError` with a Why/Fix explanation.
- **Consequences**: Tests can call domain functions without a subprocess. The CLI stays replaceable
  by another adapter.

### ADR-006: Schema v2 with additive in-place migration
- **Date**: 2026-10-27
- **Status**: Accepted
- **Context**: Evidence binding and source status need new columns. `CREATE TABLE IF NOT EXISTS`
  never adds a column to an existing table, and the previous `initialize` rejected any version
  other than its own, so an existing database could not be upgraded.
- **Decision**: Bump the schema to 2 and add `_add_missing_columns`, an additive `ALTER TABLE`
  migration keyed by the old version. Migration runs inside one transaction, preserves every row,
  is idempotent, and still refuses a version newer than the build without modification.
- **Consequences**: Version-1 databases open and upgrade on first use. Destructive migrations are
  out of scope; a future one needs a documented backup step first.

### ADR-007: Bind evidence to code, declared inputs and command
- **Date**: 2026-10-27
- **Status**: Accepted
- **Context**: Verification probes showed that two agreeing runs still pass after the tested input
  file changes and after the stored command is rewritten. Integrity could not see either.
- **Decision**: Record `command_sha256`, `code_sha256` (engine package only) and `inputs_sha256`
  (declared `--input` paths) per run. A NUMERIC claim is current only while a verified group
  matches all three; otherwise integrity reports `EVID-005`.
- **Consequences**: Editing the engine, the command or a declared input retires numeric evidence
  until it is re-verified. Git commit, dirty flag, Python and platform are metadata, not binding,
  so unrelated worktree edits do not invalidate durable measurements. Undeclared inputs stay
  invisible; the README states this limit. Runs written before schema 2 carry an empty binding and
  therefore count as stale until `test verify` runs again.

### ADR-008: Source status and retraction cascade
- **Date**: 2026-10-27
- **Status**: Accepted
- **Context**: A retracted paper invalidates the claims that cite it, but the engine had no source
  state, so the cascade had to be started by hand claim by claim.
- **Decision**: Sources carry `active`, `expression_of_concern` or `retracted` plus a required
  note. `source retract` marks the source, retires its live claims as `RETRACTED`, and cascades to
  dependents in one transaction. Integrity adds `PROV-003` (error) and `PROV-004` (warning).
- **Consequences**: A source status change always needs a note. Reinstating a retracted source is
  recorded but never restores claim verdicts; the claims must re-establish their evidence with a
  fresh verdict and test run.

### ADR-009: Report manifests and drift checks
- **Date**: 2026-10-27
- **Status**: Accepted
- **Context**: Reports were deterministic but unverifiable: nothing recorded which graph state a
  committed report described, and the report had no stated limits.
- **Decision**: `report --out` writes a sidecar manifest with a schema id, engine version, research
  id, `report_sha256`, `graph_sha256` (over the deterministic JSONL record set), counts, finding
  totals and a shared `LIMITS` block. `report --check` recomputes both digests and exits 1 on drift.
- **Consequences**: A committed report is only valid with its manifest. Generation time stays out
  of the digests, so re-running an unchanged graph produces an identical manifest body.

### ADR-010: Typed, glob-aware input binding
- **Date**: 2026-10-27
- **Status**: Accepted
- **Context**: Probes showed that `--input data/` hashed nothing, `--input data/*.csv` was hashed as
  a literal filename, and an absent file collided with a file whose content was the text `missing`.
  Each of those makes a declaration silently useless, which is worse than refusing it.
- **Decision**: `resolve_inputs` expands globs deterministically, de-duplicates and sorts names, and
  refuses a directory with an Error/Why/Fix triad. The digest is length-prefixed with a typed
  `file`/`missing` tag, so absence, content and boundaries cannot collide. A declaration that
  matches nothing is kept as written so later creation changes the digest.
- **Consequences**: Declarations are canonical from the moment a test is created. Unmatched globs
  are intentional and observable. Directories are rejected rather than approximated.

### ADR-011: Two report digests, semantic by default
- **Date**: 2026-10-27
- **Status**: Accepted
- **Context**: `report --check` compared an exact record digest. Re-verifying an unchanged test
  allocates new run ids, a new group and new timings, so every re-verification reported drift for a
  report that was still true. A gate that fires on correct behaviour gets ignored.
- **Decision**: Store `content_sha256` (a projection: run allocation fields dropped, identical runs
  de-duplicated) and `graph_sha256` (exact). `--check` compares content, rendered text and counts;
  `--strict` also compares the exact records. Both digests live in manifest schema
  `research-engine.report/2`.
- **Consequences**: Routine re-verification stays clean; release checks can demand exactness.
  Counts are now compared too, so a tampered manifest is detected rather than only a stale graph.

### ADR-012: Promotion cites a run group, and the gate is at write time
- **Date**: 2026-10-27
- **Status**: Accepted
- **Context**: A claim could be promoted to `NUMERIC` with no registered test, and later could keep
  `NUMERIC` while its supporting command changed and a fresh run was recorded. The gate only asked
  whether *some* historical group existed.
- **Decision**: `verdict.evidence_group` records the group a numeric promotion cites. `set_verdict`
  refuses `NUMERIC` when no current group exists, and rejects a group that is not current. Integrity
  adds `EVID-006` for a promotion whose group is no longer current. Any current group is accepted,
  not only the newest, so a pure re-verification does not invalidate the promotion.
- **Consequences**: Numeric promotion is impossible without reproducible, current evidence. Legacy
  numeric claims from schema 1 or 2 have no group and are reported until they are re-verified and
  re-recorded; the migration notice states how many.

### ADR-013: UNKNOWN is a state, not a failure
- **Date**: 2026-10-27
- **Status**: Accepted
- **Context**: The verdict vocabulary could say a claim was unverified or refuted, but not that the
  evidence does not exist. Missing data therefore looked like weak support and counted 0.4 in
  consensus.
- **Decision**: Add `UNKNOWN` to the claim vocabulary with zero consensus weight, a required
  evidence note, and a place in `NON_SUPPORTING_STATUSES` so it blocks promotion of dependents.
  It is deliberately not a `FAILED_STATUSES` member, so it never cascades an invalidation.
- **Consequences**: `EVID-007` warns when the reason is absent. A dependency on missing evidence
  blocks promotion without destroying the graph beneath it.

### ADR-014: Views are budgeted and self-reporting
- **Date**: 2026-10-27
- **Status**: Accepted
- **Context**: Reports are complete documents; an agent reading the graph needs a bounded view and
  must know when it is seeing a clipped one.
- **Decision**: `engine/context.py` estimates tokens with `(chars + 3) / 4`, packs lines with a
  40-token reserve, always keeps the anchor line, and appends `OMITTED: n` on truncation.
  `outline`, `brief` and `claim context` are read-only and deterministic.
- **Consequences**: A view at a small budget is still meaningful and never silently incomplete.
  The estimate is a heuristic, not a tokenizer, and is documented as such.

### ADR-015: Discovery is advisory, merging is recorded
- **Date**: 2026-10-27
- **Status**: Accepted
- **Context**: Contradiction discovery can produce false positives; automatically writing edges
  would corrupt the graph. Duplicate claims, by contrast, need an operation that removes the noise
  without deleting history.
- **Decision**: `analysis` only reads and proposes; a human records a link. Pairing is scoped to a
  single question so unrelated claims are never called contradictory. `claim merge` repoints edges
  to a survivor and retires duplicates as `RETRACTED` with the survivor as evidence.
- **Consequences**: `DUP-001` ignores retired claims. Merging never removes a verdict, and a merge
  that would create a self-edge drops that edge instead.

### ADR-016: Audit fixes after the T-004 review
- **Date**: 2026-10-27
- **Status**: Accepted
- **Context**: A review of the new analysis surface found four defects. Semantic diff keyed every
  projected run as the empty string, so distinct runs collapsed and a changed run could hide. The
  contradiction dedupe key omitted the question, silently dropping a pair attached to a second
  question. `merge_claims` imported the private `_insert_edge` and left kill tests pointing at the
  retired duplicate. `outline` counted every program's audit findings as its own.
- **Decision**: Projected runs carry `run:<test>:<run_tag>`. The contradiction key includes the
  question. `_insert_edge` is public as `record_edge`; merge repoints tests, refuses a retired
  survivor, and integrity reports `TEST-001` for a test left on a retired claim. Findings gain
  `findings_for_research`, and `DUP-001` is attributed to its program.
- **Consequences**: A changed run is reported by identity rather than as an anonymous record. A
  contradiction visible under two questions is visible twice. Merging keeps the evidence chain
  attached. `outline` is honest about its own program's gate state.

### ADR-017: Negative control in the kill test
- **Date**: 2026-10-27
- **Status**: Accepted
- **Context**: `test verify` accepted a command that cannot fail, so a permanently green test was
  indistinguishable from a real one. The reference project solved the same problem by measuring a
  gate's base rate before trusting it.
- **Decision**: `killtest.control_command` declares a negative control that must fail reproducibly.
  Control runs are stored with `role='control'` in the same group; `verification_complete` requires
  both sides. The control is part of the command binding. `EVID-008` warns when evidence-bearing
  tests lack one; `EVID-009` is an error when a declared control never failed.
- **Consequences**: `test verify` runs the command twice per side. Existing tests keep verifying but
  warn until a control is added. A control proves falsifiability, not correctness, and the limits
  block says so.

### ADR-018: Screening states and a PRISMA projection
- **Date**: 2026-10-27
- **Status**: Accepted
- **Context**: Sources had an evidence status but no record of whether they were ever screened, or
  why they were left out.
- **Decision**: Add `source.screening`, `screening_reason` and `screening_at` with the five lattice
  states and a closed reason taxonomy. `source prisma` and the report compute counts, reasons and
  the included fraction. A live claim citing an excluded source warns (`SCREEN-001`).
- **Consequences**: New sources start as `identified`, which is accurate. An out-status always
  records a reason (`other` by default) so an exclusion cannot look like an oversight.

### ADR-019: Append-only event log for non-verdict actions
- **Date**: 2026-10-27
- **Status**: Accepted
- **Context**: Verdicts and invalidations recorded themselves, but a source losing its status, a
  merge, or a report generation left no ordered trail.
- **Decision**: Add an `event` table and `engine/events.py`. Writers append inside their own
  transaction; `db.migrate` is inserted inline during migration to avoid an import cycle. `events`
  lists newest first with program and kind filters.
- **Consequences**: The log cannot contain an event for a rolled-back action. It is append-only, so
  correcting an earlier action means appending a new event, not editing one.

### ADR-020: Verified backup, integrity gate, domain-separated digests and safe text
- **Date**: 2026-10-27
- **Status**: Accepted
- **Context**: The engine could not verify or copy its own state, its digests shared one domain, and
  untrusted claim text could break a Markdown table or inject a heading.
- **Decision**: Add `db integrity` and `db backup` (backup API, verify, fsync, atomic rename, refuse
  overwrite). Prefix every digest with its artifact kind and record the licence id and digest in
  the manifest (schema 3). Render all untrusted text through `engine/markdown.py`.
- **Consequences**: A report digest cannot collide with a graph digest, a licence change is drift,
  and a claim can no longer alter document structure. Backup files are copies, not incrementals.

### ADR-021: Observations and deterministic statistics
- **Date**: 2026-10-27
- **Status**: Accepted
- **Context**: The engine could run a command and compare its output, but could not hold repeated
  measurements or report an effect size. N1-Engine's statistics were the strongest unported
  mechanic, but its implementation depends on pandas/scipy and has an unseeded bootstrap.
- **Decision**: Add an append-only `observation` table (claim, group, finite value, note, void flag)
  and a pure `engine/stats.py`. The statistics use only the standard library: regularized incomplete
  beta for t p-values, dynamic-programming exact Mann-Whitney for untied samples up to 400
  comparisons, tie-corrected normal otherwise, and a seeded bootstrap. `analysis stats` logs a
  `claim.stats` event; `OBS-001` warns when observations lack one.
- **Consequences**: Results are reproducible across machines for a fixed seed. A measurement is
  retired by voiding, never by editing. The tests disclose their own assumptions instead of
  presenting one p-value as the truth.

### ADR-022: Scoped reports, complete exports, and a golden run
- **Date**: 2026-10-27
- **Status**: Accepted
- **Context**: Review found three composition defects. A report included every program's findings,
  so an unrelated program could dirty a committed report and its digest. Snapshots and manifest
  digests silently omitted observations and events. No test exercised the command surface as a
  sequence.
- **Decision**: Reports and manifests compute findings with `findings_for_research`. `export`
  includes `observation` and `event`, and their rows participate in drift: a new observation changes
  both digests. The audit log is excluded from the digests because events follow hashed state and
  `report.write` is created during manifest generation; including it would make the manifest
  self-referential. `tests/test_golden.py` drives every command in one sequence and asserts state.
- **Consequences**: A report is true for its own program only. Adding a measurement invalidates a
  committed report until it is regenerated; writing a report does not. The golden run is the gate
  that catches interface drift between otherwise passing modules.

### ADR-023: Self-verifying exports and reported measurements
- **Date**: 2026-10-27
- **Status**: Accepted
- **Context**: Snapshots could be compared but not verified: nothing in the file said whether it had
  been altered, and a legacy snapshot was indistinguishable from an intact one. The report also
  omitted the measurements that `observation` now stores.
- **Decision**: Export meta carries `export_digest` over every record (including the audit log) and
  a record count; `export --check` recomputes both and exits 1 on mismatch, while a digest-less
  export is refused. This digest is separate from the manifest's, which excludes the log and tracks
  evidence drift. The report gains a measurements table and the last statistics or trend run per
  claim.
- **Consequences**: An export is self-describing and tamper-evident. A file edited with a text
  editor fails verification; a legacy file must be re-exported before it can be trusted. The report
  now shows the numbers a claim rests on, not just its verdict.

### ADR-024: Review fixes for evidence selection and label handling
- **Date**: 2026-10-27
- **Status**: Accepted
- **Context**: A review of the last three pushes found three defects. `EVID-009` inspected the
  oldest verified run group instead of the newest, so adding a control after an early run produced
  a false error. Group labels were compared verbatim while observations store them lowercased, so
  `--baseline Baseline` failed. A group could be compared with itself, producing a meaningless
  zero-difference result. `OBS-001` also cleared forever after the first statistics run, even when
  new measurements arrived.
- **Decision**: Control checks and default promotion binding use the newest verified group. Labels
  are normalised in the analysis layer, self-comparison is refused, and a bootstrap with fewer than
  ten resamples is refused. `OBS-001` compares the latest observation or void timestamp with the
  latest `claim.stats`/`claim.trend` event and warns when data is newer. `export --check` refuses a
  `--research` filter, and an insufficient trend records that fact instead of printing a slope of 0.
- **Consequences**: A late-added control no longer breaks the gate. Label case never matters.
  Comparisons must be between two distinct groups. Analysis is flagged as stale when data changes,
  with a documented one-second resolution limit.

### ADR-025: Review fixes for diff identity, export trust and finding scope
- **Date**: 2026-10-27
- **Status**: Accepted
- **Context**: A review of six pushes found three defects. Semantic diff keyed projected runs by
  `(test, run_tag)`, so several run groups shared a key and the index overwrote all but one; a
  changed run could be masked. `export --check` ignored the meta schema and raised `ValueError` on a
  non-numeric record count instead of reporting it. `PRE-001` used the verdict id as its subject, so
  a program-scoped report never showed it.
- **Decision**: `_index` keeps colliding semantic records as a sorted list, so any change in any
  group is visible. Export verification reports `schema`/`schema_supported`, handles an unparsable
  count as a mismatch, and the CLI exits 1 for an unsupported schema. `PRE-001` is attributed to its
  hypothesis and names the verdict in the message.
- **Consequences**: A snapshot diff cannot hide a group's change behind another group's identical
  run. A snapshot from another schema is refused rather than trusted by accident. Scoped reports
  now include pre-registration ordering violations.

### ADR-026: Information-poor quote warning
- **Date**: 2026-10-29
- **Status**: Accepted
- **Context**: The engine stores a quote and a locator, not the source body. A quote can restate a
  linked question, duplicate another claim's quote, or contain only stopwords and still satisfy the
  presence-only provenance rule. The full frequency/entropy weight model needs a corpus the engine
  does not store, so it cannot be implemented as written.
- **Decision**: Add `engine/information.py` with normalization, question-restatement,
  duplicate-quote and stopword-only checks. `integrity.check` emits `EVID-010` as a warning for
  live claims with quotes. The check is text-only, runs on stored data, does not gate promotion and
  does not add a numeric weight.
- **Consequences**: Obvious echo and duplicate quotes are visible in `check` and reports as
  warnings, never errors. A legitimate repeated quote needs a recorded reason but is not blocked.
  The weight threshold remains deferred until a source-body store exists.

### ADR-027: Earliest-valid attempt authority
- **Date**: 2026-10-29
- **Status**: Accepted
- **Context**: `set_verdict` accepted any current verified group, so a researcher could re-run a
  failing kill test until a later group passed and promote that group. The earlier subject failure
  remained in `test_run` but did not constrain the verdict. Without an attempt outcome, the engine
  could not distinguish a legitimate retry after an infrastructure failure from a retry after a
  subject failure.
- **Decision**: Bump the schema to 6 and add the append-only `test_attempt` table. Each execution
  records a monotonic attempt number, its run group, one outcome from `completed`,
  `subject_failed`, `infra_failed` or `indeterminate`, and a reason for replaceable outcomes. The
  earliest non-replaceable attempt bound to the current command, code and inputs is authoritative;
  only its group may be used for a `NUMERIC` promotion. `test attempts` lists the ledger and
  `test runs` shows the attempt beside each run. Legacy run groups without an attempt row keep the
  old any-current-group behaviour until they are re-run.
- **Consequences**: Retry-until-pass is blocked for new runs, including a later pass after an
  earlier subject failure. An infrastructure failure, timeout, workspace drift, non-reproducible
  run or a control that does not fail is replaceable only with a recorded reason. Existing
  databases migrate without a backfill; their historical runs remain readable and keep the legacy
  promotion path.

### ADR-028: Claim revisions without inherited evidence
- **Date**: 2026-10-29
- **Status**: Accepted
- **Context**: `claim.text` was immutable. Refining a claim forced a second, silently contradicting
  claim or left a stale statement in the graph. The OpenSpec-style delta chain was the candidate
  mechanic, but its blueprint proposed lowercase `superseded`/`active` statuses that would break
  the closed uppercase `CLAIM_STATUSES` vocabulary used by consensus, integrity and cascade.
- **Decision**: Bump the schema to 7 and add `revision_of`, `superseded_by` and `revision_reason`
  to `claim`. `claim revise` inserts a new claim through the normal provenance rules, sets the
  links, and moves edges from the old claim to the new head in one transaction. The new claim
  starts `UNVERIFIED`; old verdicts are never copied. Tests stay on the old claim and raise
  `REV-002`; `REV-001` catches a dependency edge still pointing at a superseded claim. `claim list`
  hides superseded rows unless `--history` is passed, and `claim history` renders the chain.
- **Consequences**: A refinement keeps the old text, provenance and verdict history auditable while
  the graph uses one head. The status machine is unchanged. A superseded claim cannot be revised
  again or merged; the head is the only live target. Existing claims migrate as heads with empty
  links.

### ADR-029: Measurement provenance and protocol comparability
- **Date**: 2026-10-29
- **Status**: Accepted
- **Context**: `observation` stored a value and a group label, so a number could not be traced to
  the instrument, rater or procedure that produced it. Two numbers called "accuracy" could be
  compared even when one measured top-1 accuracy and the other an end-to-end judge score. The
  source idea's separate `measurement` table would have duplicated the observation value.
- **Decision**: Bump the schema to 8 and add the immutable `protocol` table plus observation
  provenance columns: instrument kind/id/digest, rater kind/id/version, protocol id, sample size,
  aggregation and unit. Provenance is all-or-nothing on insert; an unprovenanced record is legacy
  and warns `OBS-002`. `analysis stats` refuses to compare groups with different protocols,
  instruments, raters or units unless `--allow-incomparable` is explicit, and records the caveat
  in the result. The report prints protocol, unit and instrument beside each measurement.
- **Consequences**: A numeric comparison now names the procedure it compares. The protocol id is
  immutable, so changing a procedure requires a new id. Legacy observations remain readable but
  are visibly unverified; comparisons involving them warn rather than silently passing.

### ADR-030: Nested event provenance
- **Date**: 2026-10-29
- **Status**: Accepted
- **Context**: The event log was flat, so a reviewer could see that a merge, cascade or report
  write happened but not which action caused it. The source mechanic used a per-program sequence
  plus root and parent ids to turn the log into a causal tree.
- **Decision**: Bump the schema to 9 and add `seq`, `root_id` and `parent_id` to `event`. `record`
  allocates the next per-program sequence inside the writer transaction; a parent must already
  exist in the same program, and the child inherits its root. A root event points at itself.
  `events --tree ROOT` renders the descendants breadth-first and `events --path EVENT` renders the
  root-to-event chain. Legacy events keep `seq` 0 and no root.
- **Consequences**: New events can be audited as a cause tree without a second store. A parent
  that crosses a program boundary or does not exist is refused. The flat `events` listing remains
  the default, so existing scripts are unaffected.

### ADR-031: Self-produced metric quarantine
- **Date**: 2026-10-29
- **Status**: Accepted
- **Context**: A measurement produced by the system under study could enter the evidence base and
  be compared with an independent measurement as if they were the same kind of observation. The
  source idea classified a producer by module path; the engine has no module-under-study registry,
  so that automatic classification would have been guesswork.
- **Decision**: Bump the schema to 10 and add `provenance_class`, `producer_path` and
  `producer_digest` to `observation`. The class is `independent`, `self_reported` or
  `unclassified`; a self-reported value must name its producer path, and a producer digest is
  validated when supplied. `analysis stats` refuses a comparison involving a self-reported group
  unless `--allow-self-reported` is explicit, and refuses a group that mixes self-reported and
  independent rows. The report prints self-reported measurements in a separate table. `OBS-003`
  warns on unclassified rows and `OBS-004` on self-reported rows.
- **Consequences**: Self-reported numbers stay available for diagnosis but cannot silently support
  an independent comparison. The operator must state the class; the engine does not infer it from
  a path. Legacy observations are unclassified and warn rather than being retroactively labelled.

### ADR-032: Failed Claims Are Revived Only by Revision
- **Date**: 2026-10-29
- **Status**: Accepted
- **Context**: `set_verdict` allowed a claim to move from `FALSIFIED`, `RETRACTED` or `INVALIDATED`
  back to `PROVEN` or `NUMERIC`. The verdict history kept the failure, but the latest status won,
  so a negative result could be overwritten in place.
- **Decision**: Refuse any transition from a failed status (`FALSIFIED`, `RETRACTED`,
  `INVALIDATED`) to a non-failed status. A failed claim may still move to another failed status to
  correct the label. Reviving the assertion requires `claim revise`, which creates a new head that
  starts `UNVERIFIED`.
- **Consequences**: A failure stays a failure in the live graph; the new attempt is a new claim
  with its own evidence and verdict history. The status vocabulary is unchanged, and deliberate
  corrections remain possible through a revision.

### ADR-033: New Test After a Sibling Failure Is Visible
- **Date**: 2026-10-29
- **Status**: Accepted
- **Context**: Attempt authority is per test. Creating a new test after a failed attempt on the
  same claim is a new evidence path, but it can also be a way to bypass the authoritative failure
  without recording why the new test is independent.
- **Decision**: Add `TEST-002` as a warning when a test's `created_at` is later than a
  `subject_failed` attempt of another test on the same claim. The warning names both tests; it does
  not block the new test or promotion.
- **Consequences**: The bypass is visible in `check` and reports, while legitimate new tests remain
  possible. A future rule could require a recorded independence reason; that would be a new
  contract and is not part of this change.

### ADR-034: Superseded Claims Are Read-Only
- **Date**: 2026-10-30
- **Status**: Accepted
- **Context**: Revisions moved edges to the head but left the old claim addressable. A verdict,
  observation, test, edge or prerequisite could still be attached to the superseded row, creating
  evidence that looks live but is not on the current assertion.
- **Decision**: Refuse a new verdict, observation, test, outgoing or incoming edge, or prerequisite
  link on a claim with `superseded_by` set. The head is the only live target; history remains
  readable through `claim history` and the old verdict trail.
- **Consequences**: The live graph has one target per assertion. A caller that names the old id
  gets the Error/Why/Fix triad naming the head. No schema change is needed.

### ADR-035: Deterministic Lexical Search Without an Index
- **Date**: 2026-10-30
- **Status**: Accepted
- **Context**: The graph could only be read through lists and budgeted views. Finding a phrase
  across claims, sources, questions and hypotheses required opening each table, and the reference
  research graph already ranks a phrase before scattered terms.
- **Decision**: Add `engine/search.py` and `search QUERY`. It scans program-scoped rows in
  identifier order, scores an exact phrase before matched terms, returns the matched field and a
  centred snippet, hides superseded claim revisions by default, and packs text output through the
  existing budget. No persistent index and no FTS5 dependency.
- **Consequences**: A result cannot be stale and the standard-library-only contract holds on every
  Python 3.10 build. Search is lexical, not semantic; a future embedding index would be a new
  adapter, not a change to this ranking rule.

### ADR-036: Split Sources Are Detected, Not Merged Automatically
- **Date**: 2026-10-30
- **Status**: Accepted
- **Context**: A source registered twice splits its provenance and doubles its apparent evidence.
  The reference graph normalizes DOIs and titles before ingest, and the duplicate-file tool groups
  exact identities before reporting.
- **Decision**: Add `engine/duplicates.py`, `source duplicates` and the `DUP-002` warning. DOIs are
  stripped of resolver prefixes and case-folded; titles are accent-, case- and punctuation-folded;
  sources group by DOI, then normalized title/year, then title alone. Only DOI and title/year groups
  warn; a title-only match is a variant. The lowest identifier is the suggested survivor.
- **Consequences**: Hard duplicates become visible in `check` without deleting history or crossing
  a program boundary. A source merge would change provenance, so it stays a deliberate human action
  rather than an automatic repair.

### ADR-037: Calibration Scores Recorded Confidence
- **Date**: 2026-10-30
- **Status**: Accepted
- **Context**: Every hypothesis stores the confidence recorded before its outcome, but nothing
  compared that probability with what happened. The reference research archive keeps a calibration
  log, and the N=1 engine warns when a small sample cannot support a confident reading.
- **Decision**: Add `engine/calibration.py` and `analysis calibration`. `SUPPORTED` scores 1,
  `REFUTED` 0, and `INCONCLUSIVE` is excluded from the score but counted in coverage. Report the
  Brier score, clipped log loss, base-rate baseline, skill score and fixed reliability bins; label
  a resolved set below `--min-n` descriptive and a one-sided set non-discriminating. The CLI appends
  one `hypothesis.calibration` event; the report calls the pure summary.
- **Consequences**: A program can see whether its probabilities were calibrated without changing a
  hypothesis. Calibration is a scoring rule, not a posterior, and it does not touch verdicts.

### ADR-038: AI output enters as UNVERIFIED with hash-only provenance
- **Date**: 2026-11-02
- **Status**: Accepted
- **Context**: Automating sweeps, idea generation and drafting needs the engine as skeptic:
  AI text is a hypothesis source, never evidence. Stage-2 verification found three bypasses
  in a naive design: `PROVEN` needs only a free-text kill-test name and evidence string
  (presence, never validity), `invalidate`/`retract`/`merge` destroy with free-text reasons,
  and the CLI verdict path never records an actor, so AI and human verdicts were
  indistinguishable. It also found that quote text is unverifiable by construction (the
  engine stores no body), that model-supplied shell would execute via `shell=True` in test
  runs, and that no network import exists in the engine to guard.
- **Decision**: Add `engine/ai.py` plus a schema-11 `ai_artifact` table (kind, model id,
  prompt/output SHA-256, cited source ids, optional claim/hypothesis/test links). Raw
  prompt/output bytes are never stored. Ingest creates `UNVERIFIED`/`PREREGISTERED` rows
  linked to the artifact or refuses (`ai.reject` event keeps the failed run flagged). The
  adapter never calls `set_verdict`, `invalidate`, `retract`, `merge` or `record_outcome`;
  CLI `verdict`/`outcome` gain `--actor` (default `agent`, adapter stamps `model:<id>`).
  Test proposals come only from fixed deterministic templates; free-form model shell and
  the external API are refused in code. Integrity adds `AI-001` (unresolvable AI citation),
  `AI-002` (AI-origin `PROVEN` with no twice-passing test) and `AI-003` (AI test off its
  template). The event-log-only alternative was rejected because the claim-to-artifact
  join needed for `AI-002` is not queryable from free-text event detail. Draft assembly
  reuses `report` digests, refuses on error-level findings, withholds non-surviving claims
  with their status, and never writes a verdict.
- **Consequences**: A fabricated source id fails closed at ingest; a fake quote against a
  real source stays `UNVERIFIED` until a kill test it cannot pass. Per-claim kill tests
  with real discriminating power remain researcher-authored; template probes prove the
  plumbing, not the science. The external adapter is a later ADR, not this change.

### ADR-039: Diff refuses non-object snapshot lines
- **Date**: 2026-11-03
- **Status**: Accepted
- **Context**: `export --check` reports a tampered snapshot whose JSONL line is valid JSON
  but not an object (for example `[1, 2]`) as a digest mismatch, while `diff` crashed on
  the same file with `AttributeError` in `load_jsonl`. The first-30 audit reproduced the
  crash against the current head; the export-side guard from the earlier malformed-snapshot
  fix did not cover the diff path.
- **Decision**: `engine/diffing.py load_jsonl` refuses any non-dict record with an
  `EngineError` Error/Why/Fix triad naming the line number, matching the existing
  malformed-JSON refusal. `verify_export` keeps its pinned behaviour of reporting
  `ok=False` with a count mismatch for the same input.
- **Consequences**: A tampered snapshot fails closed in both commands with no traceback.
  `diff_records` keeps its `List[dict]` contract; file-level refusal is the boundary.

### ADR-040: Harden AI ingest citations, actor default and file boundary
- **Date**: 2026-11-03
- **Status**: Accepted
- **Context**: Stage-2 verification of the AI integration found three gaps around a
  sufficient core: a claim with a valid `source_ref` but one fake `cited_json` entry
  entered as `UNVERIFIED` with only an async `AI-001` flag (promotion not blocked in
  code); AI-proximate ingest/test events defaulted to `agent`, so AI/human actions were
  indistinguishable without operator discipline; `--prompt-file/--output-file` inside the
  checkout would commit raw payloads despite the hashes-only DB invariant.
- **Decision**: Validate cited existence in-program at ingest time (`sweep` stays outside
  the gate as pre-source notarization) and require an empirical `source_ref` to appear in
  the cited list; both refuse with `ai.reject`, closing the divergence without a schema
  change. Default AI-proximate ingest/test actors to the artifact's `model:` identity
  unless `--actor` is explicit. Refuse model I/O paths resolving inside the project
  checkout in `engine/cli.py`. No new loop engine code: the automation is the documented
  gated operator sequence `sweep -> extract/idea -> propose-test -> verify -> verdict ->
  draft`. `fetch_external` stays a refusing stub; no new templates.
- **Consequences**: A fabricated cited entry dies at entry with a flagged run; copy-paste
  around `ai ingest` remains operator malfeasance, not a code path, and stays visible via
  the artifact join and `AI-002`. Raw payloads cannot enter the repo through the CLI.
  `AI-001` remains as the backstop for legacy rows and direct DB edits.

### ADR-041: Test identity binds the expected exit and the timeout
- **Date**: 2026-11-04
- **Status**: Accepted
- **Context**: IDEA-979: `evidence.binding()` covered the command, the negative control,
  the engine code and the declared inputs, but not `expect_exit` or `timeout_seconds`.
  A pass is `exit_code == expect_exit` inside a bounded run, so editing either after a
  twice-passing verification silently redefined what the recorded evidence proved.
- **Decision**: Fold `expect_exit` and `timeout_seconds` into the command-identity hash
  in `evidence.binding()`; no schema change. Groups verified under the weaker identity
  read as stale (`EVID-005`) until re-verified, exactly like a command edit today.
- **Consequences**: Post-verdict edits to the expected exit or the timeout retire the
  group instead of redefining the pass. One upgrade cost: pre-existing verified groups
  need one fresh `test verify` to rebind under the stronger identity.

### ADR-042: Retraction covers every row of the retracted work
- **Date**: 2026-11-04
- **Status**: Accepted
- **Context**: IDEA-980. `retract_source` retired only the single cited row: a twin row
  sharing the normalized DOI stayed `active`, so the retraction was bypassed without
  touching the retracted record. `DUP-002` already detects the split, and ADR-036 keeps
  detection advisory, but nothing closed the bypass at retraction time.
- **Decision**: `retract_source` resolves the work identity via `normalize_doi` and
  retracts every same-program sibling row with its claims in one transaction; the CLI
  names the covered twins. No schema change, no insert-time refusal: `DUP-002` stays the
  detection path and the advisory-merge workflow is untouched. Full terminality
  (refusing `retracted -> active`) is deliberately not added: reinstatement after a
  withdrawn retraction is pinned behavior
  (`test_reinstatement_requires_a_note_and_keeps_claim_verdicts`) and stays a per-row
  operator action with its claim verdicts preserved.
- **Consequences**: A twin row can no longer shelter live claims past a retraction;
  `PROV-003` stays clean without a second pass. Cross-program rows are out of scope:
  programs are separate boundaries and retract in their own scope.

### ADR-043: Collapse bulk tripwire and missing-volume finding
- **Date**: 2026-11-04
- **Status**: Accepted
- **Context**: IDEA-982 and IDEA-974. `invalidate`/`retract_source` retired unbounded
  record sets in one command; and a moved evidence folder turned every `NUMERIC` claim
  stale at once, burying the single root cause under N `EVID-005` errors.
- **Decision**: `CASCADE_BULK_LIMIT = 10` tripwire in `engine/cascade.py`: collapses
  retiring more than 10 records refuse unless `allow_bulk` (`--allow-bulk` on
  `claim invalidate` and `source retract`); the refusal names `cascade preview` for
  inspection. When 3 or more stale `NUMERIC` claims in one program share a missing
  ancestor folder, `check` reports one `EVID-011` volume error instead of per-claim
  `EVID-005`s; smaller or heterogeneous stale sets keep per-claim findings.
- **Consequences**: Fat-fingered program-wide collapses need an explicit opt-in; a
  moved folder reads as one error naming the volume and the count. Ten and three are
  tripwires in the MIN_GROUP tradition, not safety proofs; the limits registry
  (IDEA-1613, Proposed) stays the follow-up.

### ADR-044: Anchored event ledger (schema v12)
- **Date**: 2026-11-04
- **Status**: Accepted
- **Context**: IDEA-981. The event log had no tamper evidence: deleting the newest
  rows was invisible. `event` gains `prev_hash`/`event_hash` (schema v12 with an
  additive 11 -> 12 migration); every new row chains to its program predecessor.
- **Decision**: `record()` recomputes the tip digest and refuses to extend a broken
  chain; `verify_ledger()` replays each program and `check` reports every break as
  `LEDGER-001`; `events --verify` exposes the same replay on demand. Rows written
  before v12 carry no digest and are grandfathered: the chain restarts at the first
  hashed row instead of condemning the archive.
- **Consequences**: Silent log edits surface as errors naming the row; legacy
  databases keep a clean gate after migration. Cross-program chains stay separate:
  the hash restarts per program, matching the causal-tree boundary.

### ADR-045: Preregistered analysis plans and the amendment ledger (schema v13)
- **Date**: 2026-11-04
- **Status**: Accepted
- **Context**: IDEA-986 and IDEA-993. Comparisons ran without declared predictions,
  so unmatched runs could not be told apart from planned ones; and hypothesis or
  protocol text had no correction path, forcing direct database surgery for typos.
- **Decision**: New `analysis_plan` table (`analysis plan` preregisters a claim's
  baseline/treatment pair with a prediction before data is seen);
  `claim_statistics` accepts `--plan`, cites it in the result, and warns
  `exploratory` when plans exist for the pair but none is cited. New `amendment`
  table: `hypothesis amend` and `protocol amend` correct live records with a
  mandatory reason, keep the original registration timestamp and digest, and append
  the before/after to the ledger plus a causal event. Closed hypotheses are frozen
  (register a new one); protocols stay immutable except for measures text.
  `plan-list` is deliberately omitted: plan ids print at creation and surface in
  `events --kind analysis.plan`, which is enough discovery until a registry pass.
- **Consequences**: Planned vs exploratory comparisons are explicit in the result;
  typo corrections no longer bypass the record. No integrity finding is attached to
  exploratory runs yet: verdict-time linkage of evidence groups to plans is the
  follow-up, not this milestone.

### ADR-046: Coverage-gated consensus display
- **Date**: 2026-11-04
- **Status**: Accepted
- **Context**: IDEA-978. The consensus number weighted status by confidence with no
  coverage fraction: one untested stance, or a single cited source, could crown a
  claim with a confident-looking score.
- **Decision**: New `coverage()` (tested fraction over `PROVEN`/`NUMERIC`/
  `FALSIFIED` stances plus distinct cited sources) and `consensus_display()`: a
  number prints only with at least half the stances tested and never from exactly
  one source (unsourced questions judge on tests alone). `consensus()` stays a pure
  number for composition; the report, outline and brief views print the display
  string, which names the shortfall when it refuses.
- **Consequences**: Thin or single-sourced questions read as `insufficient coverage`
  instead of a score; well-tested questions are unchanged. The half-coverage bar
  and the source rule are tripwires, not proofs; tuning them is a calibration
  follow-up, not this milestone.

### ADR-047: Preview-bound collapse and retraction
- **Date**: 2026-11-04
- **Status**: Accepted
- **Context**: IDEA-975. `cascade preview` described the blast radius but the
  action never verified it: a status, edge or claim change between preview and
  action silently redefined what fell.
- **Decision**: `preview()` carries a digest over exactly the rows the action
  re-reads (claim id/status/supersession plus source id/status, canonical sorted
  form). `invalidate` and `retract_source` accept an optional `preview_digest`
  and refuse on mismatch, naming a fresh preview in the fix. The digest is opt-in
  so existing flows keep working; `cascade preview` also accepts a source ref and
  previews the retraction across twin rows. Single-writer scope means no lock is
  needed between a verified preview and its transaction.
- **Consequences**: Bound actions fail closed on drift instead of retiring a
  changed graph. Operators who skip the digest keep today's behavior with today's
  risk, stated in the refusal text.

### ADR-048: Reports refuse verdict-less programs
- **Date**: 2026-11-04
- **Status**: Accepted
- **Context**: IDEA-1103. `report()` rendered even with zero answered items: a
  program of bare claims produced a trustworthy-looking document with no
  adjudication behind it.
- **Decision**: `report()` refuses when the program holds claims but no verdict
  adjudicates any claim or hypothesis, naming `claim verdict` /
  `hypothesis outcome` and the WIP views (`brief`, `outline`, `scorecard`) in the
  fix. Empty programs still render scaffolding; `scorecard`, `brief` and
  `outline` are untouched.
- **Consequences**: Unadjudicated work can no longer ship as a report; WIP reading
  moves to the summary views. Three report fixtures gained a `FALSIFIED` verdict
  to keep exercising the rendered sections.

### ADR-049: Robust summaries and the polarity bit
- **Date**: 2026-11-04
- **Status**: Accepted
- **Context**: IDEA-988 and IDEA-989. `observation_summary` reported only the
  mean, so one extreme observation silently dragged the location; and keyword
  overlap dropped negations with the stopwords, so "S rises" vs "S does not rise"
  scored as near-identical while true paraphrases ranked lower.
- **Decision**: Summaries now carry median and MAD beside the mean; when they
  disagree the group deserves a second look before comparison (no auto-trim: the
  engine never rewrites data). Contradiction pairs and unlinked proposals carry
  an advisory-only `polarity_mismatch` bit plus a text marker; scores and ranking
  are untouched.
- **Consequences**: Skewed groups are visible in the summary dicts; negated
  opposition is flagged instead of outranked. No new gate, no refusals: both
  changes inform, they do not block.

### ADR-050: Audit wave 1 - total blast radius, thin consensus, Holm boundary
- **Date**: 2026-11-05
- **Status**: Accepted
- **Context**: Wave 1 audit of the pushed history found three verified gaps: (1)
  `retract_source` counted only direct citing claims for the bulk tripwire, so
  six direct claims with two dependents each retired 18 records without
  `--allow-bulk`; (2) `coverage()` allowed a single tested stance with no source
  to display `+1.0000` as consensus; (3) `holm_adjust` rejected only when
  adjusted `< ALPHA`, so an adjusted `p == 0.05` did not reject, against the
  standard Holm rule. The canonical gate also took 513s on Windows, and the
  README/Data Model omitted the v13 `analysis_plan`/`amendment` tables.
- **Decision**: (1) The retraction tripwire counts every `would_retire` entry
  from `_retraction_plan` (direct plus transitive), matching the preview digest;
  (2) `coverage()` requires at least two linked claims (`total >= 2`), so lone
  stances read as insufficient however tested; (3) Holm rejects when adjusted
  `<= ALPHA`. `run_test()` captures git/environment once per verification group
  instead of once per role, halving process spawns; README and ARCHITECTURE now
  list the v13 tables, with the README tightened to stay inside the 22_500-char
  cold-start budget.
- **Consequences**: Sharded retractions trip correctly; thin questions refuse;
  boundary families reject per standard; the demo runs in ~1s warm and the full
  suite drops proportionally. No binding change: git identity stays diagnostic.

### ADR-051: N1 suitable ports - correlation, batch stats-all, CSV import
- **Date**: 2026-11-05
- **Status**: Accepted
- **Context**: N1-Engine holds deterministic comparison mechanics plus CSV/GUI/domain
  models. Only stdlib-compatible advisory patterns fit the provenance/digest
  constraints; pandas, scipy, SQLAlchemy and PyQt are excluded by the
  standard-library-only non-negotiable.
- **Decision**: (1) `stats.pearson` plus `analysis correlation` computes advisory
  pairwise Pearson r paired by recording order, provenance-gated, read-only, never
  a `claim.stats` event so `OBS-001` still requires a real run; (2)
  `analysis stats-all` batches one baseline/treatment pair across every claim in a
  program with per-claim `EngineError` isolation and a multiple-comparison warning
  beyond `MAX_SAFE_CLAIMS=3`; (3) `observation import-csv` bulk-records
  `group_label,value` plus optional provenance columns through `add_observation`
  validation with per-row skip reasons; no CSV export, JSONL digests stay canonical.
- **Consequences**: Discovery gains a correlation view without a new gate;
  batch runs cannot be aborted by one bad group; N1 legacy values migrate without
  breaking digests. GUI, date windows, HTML reports, SQLAlchemy models and
  mutable settings remain deliberately unported.

### ADR-052: Golden coverage plus CSV template
- **Date**: 2026-11-05
- **Status**: Accepted
- **Context**: T-020 shipped three CLI paths with unit tests but no end-to-end
  composition proof; the CSV header contract lived in docs only.
- **Decision**: (1) `test_golden` drives `import-csv --template`, bulk import to a
  fresh claim, `analysis correlation` and `analysis stats-all` before `report --out`
  so the manifest stays clean; (2) `observation import-csv --template` prints the
  canonical header with no DB write (CLAIM/PATH optional when flagged).
- **Consequences**: Full surface stays composable; template removes guesswork with
  zero digest impact; default report bytes unchanged.

### ADR-053: Time windows, import dry-run, cross-claim Holm
- **Date**: 2026-11-05
- **Status**: Accepted
- **Context**: Stats could not slice by record time; CSV imports wrote before the
  user saw skip reasons; `stats-all` warned about multiplicity without adjusting it.
- **Decision**: (1) `--since/--until` on `stats`, `stats-all` and `correlation`
  bound the read to record time `at` (bare date = start/end of day, naive = UTC),
  stored in the result and event detail; (2) `import-csv --dry-run` reuses
  `add_observation` validation inside a rolled-back transaction; (3)
  `stats-all --holm` reuses `holm_adjust` for a display-only cross-claim table.
- **Consequences**: Temporal slicing without a domain model; safe migration preview;
  rigorous family view with no verdict change and unchanged default output.

### ADR-054: Trend time window
- **Date**: 2026-11-05
- **Status**: Accepted
- **Context**: T-022 gave windows to `stats`, `stats-all` and `correlation` but left
  `trend` full-range, so paired analyses disagreed on `n`.
- **Decision**: `trend --since/--until` bounds the fit to record time `at` with the
  same parser, re-indexing recording positions inside the window; window stored in
  the result and the `claim.trend` event detail.
- **Consequences**: Consistent windowing across all analysis reads; report totals
  stay all-time by design.

### ADR-055: Audit fixes for time windows
- **Date**: 2026-11-05
- **Status**: Accepted
- **Context**: Audit of T-021..T-023 found non-UTC `--since/--until` offsets compared
  as raw strings against `+00:00` record times, and `stats-all` folded invalid
  bounds into per-claim errors instead of refusing loudly.
- **Decision**: Normalize every bound with `astimezone(UTC)` before comparison;
  `batch_statistics` validates bounds once up front; flag hint names the offending
  flag (`--since` vs `--until`).
- **Consequences**: Correct cross-timezone windows; invalid batch flags exit loudly;
  no schema or default-output change.

### ADR-056: Merge six research projects into one host without forking them
- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: lattice, N1-Engine, fluid-universe, PNN, obezite-mekanizma-projesi and
  Atlas each hold research mechanics that the lifecycle host lacks, while the host
  already owns programs, sources, claims, hypotheses, kill tests, verdicts,
  observations, reports and audit. Forking or moving the sources would freeze six
  running projects and lose their history. The host is ASL-1.1; the sources are
  AL-1.1 or ASL-1.1 and all name the same licensor.
- **Decision**: Grow this repository in place as the host and copy committed source
  code into five explicit layers: `engine/` (stdlib-only lifecycle), `adapters/`
  (lattice discovery, ingest, extraction, analysis, synthesis, inquiry, meta and
  snapshots), `studio/` (lattice web, MCP, API and CLI surfaces), `experiments/`
  (N1 models, analysis, importer) and `domains/` (isolated PNN, fluid_universe,
  obezite and atlas packs). Packs use only the public engine API and may not import
  another domain. External data (obezite corpus, PNN outputs, fluid results, Atlas
  media, source databases) stays outside the host and is referenced by path plus
  digest. Every source stays runnable; only committed `HEAD` is copied, pinned in
  `docs/merge/SOURCE-INVENTORY.md`, and every copied file keeps its notice.
- **Consequences**: One lifecycle graph can cite domain evidence without importing
  domain data; the four domain packs remain independently removable. The host keeps
  its standard-library-only core, while a pack's optional scientific dependencies are
  declared and confined to that pack. N1's PyQt GUI is the only deliberately
  unported surface. The source repositories are read-only inputs whose SHAs and
  suites are re-checked after the merge. Rollback is the pre-merge branch point
  `563f27a` on `master`.

### ADR-057: Schema 14 carries portable papers, experiments and pack boundaries
- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: The merge must absorb lattice paper metadata, N1 experiment
  records and isolated domain packs without forcing source databases into the
  host. Existing graph columns cannot model paper venue/arXiv/tags, repeated
  intervention metrics, or a pack's external data root.
- **Decision**: Raise the host schema to 14. Add `source.arxiv`, `venue`,
  `abstract`, `tags`, `study_type`; add `experiment_intervention`,
  `experiment_metric_definition`, `experiment_metric` and `experiment_event`;
  add `domain_pack` and `migration_run`. Inspect a source database read-only,
  hash the file, then apply rows in one transaction and record
  `(source, source_digest)` once. Source data stays external.
- **Consequences**: A lattice or N1 snapshot imports without modifying its
  origin; a repeated snapshot is refused; packs declare a version, API version,
  data root and manifest digest instead of importing another domain. Migration
  drops lattice edge kinds the host ontology cannot express and reports the
  count, rather than inventing a relation.

### ADR-058: Ported packages keep their source namespaces and external roots
- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: M2-M4 copied the lattice modules, the PNN pipeline, the
  fluid-universe verification and physics packages, the obezite ledger tools
  and the Atlas pack. Importing them as flat host modules would collide with
  the host's own `models`, `analysis` and `web` names; copying their data would
  freeze six running projects.
- **Decision**: Use `adapters.lattice`, `studio`, `experiments`, `domains.pnn`,
  `domains.fluid_universe`, `domains.obezite` and `domains.atlas`. Rewrite only
  import paths and root resolution. Sources of truth stay external: fluid
  `results/`, PNN `output/`, the obezite ledger/corpus and Atlas uploaded media
  are referenced by path and digest. Each pack carries a `NOTICE.md` naming the
  source SHA, license and modifications. `tests/test_domain_isolation.py`
  fails on a cross-pack, adapter, studio or experiment import.
- **Consequences**: 1,060+ host unittest contracts and 148 Atlas pytest
  contracts run against the copied code. The only unported surface remains
  N1's PyQt GUI; N1 models, analysis, CSV import and database migration are
  ported. Packs remain independently removable.


### ADR-059: Port gauge series and terminal chart primitives
- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: The 50-project scan found one reusable primitive missing from the
  lifecycle host: gauge's numeric series parsing, summaries, percentiles,
  histograms, box plots and terminal charts. The host has statistical tests but
  no compact display primitives for reports and experiment summaries.
- **Decision**: Copy gauge's series.py and 
ender.py into engine/series.py
  and engine/charts.py, preserving the source contracts and tests. Keep gauge
  active; store its SHA and notice in engine/NOTICE-gauge.md.
- **Consequences**: Reports and experiment summaries can use one stdlib-only
  series vocabulary. No third-party dependency is added. Other scanned projects
  (games, compilers, chains, model harnesses) are not lifted into the core.
