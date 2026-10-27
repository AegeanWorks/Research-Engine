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
