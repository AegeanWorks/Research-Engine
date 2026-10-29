# Architecture

## Shape

The engine is one process, one SQLite file, and one dependency direction:

```text
cli.py
  -> researches / questions / sources / claims / hypotheses / killtests
     -> database.py (transactions, IDs, schema)
     -> models.py (frozen records, closed vocabularies)
  -> cascade.py      (uses claims + database)
  -> integrity.py    (reads the whole graph)
  -> synthesis.py    (reads the whole graph, calls integrity)
  -> bundle.py       (reads the whole graph)
demo.py              (composes every write path for the golden path)
```

No domain module imports `cli.py`; `integrity.py` and `synthesis.py` are read-only over the graph.
`cascade.py` is the only writer that composes other writers, and it does so inside one transaction.

## Storage

SQLite with WAL, `synchronous=FULL` and `foreign_keys=ON`. The connection runs in autocommit mode
(`isolation_level=None`) and every public write uses:

```text
BEGIN IMMEDIATE -> validate -> insert/update -> COMMIT
```

`transaction()` is re-entrant: a nested call joins the outer transaction. That is what lets
`cascade.invalidate` record the root verdict, every dependent verdict, and the invalidation record
as one atomic unit. A crash leaves either the whole collapse or none of it.

Identifiers come from a `counters` table inside the transaction, so `c000001`-style references are
readable and gap-free without `AUTOINCREMENT` surprises.

## Records

| Table | Role | Mutable? |
|---|---|---|
| `research` | program boundary | title/scope by hand; never deleted by the engine |
| `source` | bibliographic provenance | metadata and evidence status (`active`, `expression_of_concern`, `retracted`) |
| `question` | collection point for evidence | status (open/closed) |
| `claim` | assertion + provenance + verdict, with revision links | status via append-only verdicts; text via a new revision row |
| `edge` | typed relation between claims/questions/hypotheses | append-only |
| `hypothesis` | pre-registered prediction | outcome once |
| `killtest` | executable command, declared inputs and target | append-only |
| `test_run` | one process execution, its output hashes, binding and role (`main`/`control`) | append-only |
| `test_attempt` | one verification invocation: sequence, run group, outcome and reason | append-only |
| `protocol` | immutable measurement procedure | append-only |
| `observation` | one measurement with instrument, rater, protocol and unit | append-only; voided, never edited |
| `event` | non-verdict action trail | append-only |
| `verdict` | `previous -> new` with evidence, actor and time | append-only |
| `invalidation` | root, reason, and the JSON list of affected dependents | append-only |

`claim.status` is a cached projection of its latest verdict. The verdict table is the source of
truth for history; the cached column makes listings and consensus cheap. Integrity checks compare
them.

## Invariants

1. Empirical claims carry a source, quote and locator.
2. A derived claim carries a basis or at least one premise edge.
3. A promoted claim has a kill test and an evidence-backed verdict.
4. A numeric claim has a run group with at least two passing runs and identical fingerprints.
5. A numeric claim is current only while a verified group matches the engine code, declared inputs
   and command hash, and its promotion verdict cites such a group.
6. Dependency edges (`derived_from`, `depends_on`) form a DAG.
7. Edges never cross program boundaries.
8. A dependent of a failed premise must be invalidated or retracted.
9. A claim does not cite a retracted source unless it is already failed.
10. Outcomes are dated after registration.
11. An UNKNOWN claim carries the reason its evidence is missing, contributes zero consensus
    weight, and blocks the promotion of anything that depends on it without cascading.
12. A test that produced verified evidence either declares a negative control that failed
    reproducibly, or is flagged as unproven-falsifiable.
13. A claim does not silently cite a source that was screened out of the review.

## Evidence Binding

Each run records four identities: `command_sha256` of the command string, `code_sha256` over
`engine/**.py`, `inputs_sha256` over the test's declared `--input` paths, and the git commit plus
runtime for diagnosis. `current_verified_groups` accepts only groups whose two runs agree and whose
three binding hashes equal the values computed now. Editing the command, the engine code or a
declared input therefore retires the evidence instead of silently reusing it. Files a test reads
without declaring them are outside the guarantee; that limit is stated in the README.

Declarations are canonicalised by `provenance.resolve_inputs`: globs are expanded and sorted, names
are de-duplicated, and a directory is refused. Hashing is injective — each entry contributes a
length-prefixed name, a typed kind tag (`file` or `missing`) and length-prefixed content — so an
absent declaration cannot collide with a file whose bytes happen to be the word `missing`, and a
new file appearing under a declared glob changes the digest.

The binding excludes `git_dirty`, the Python version and the platform: a durable result should not
die because the worktree has an unrelated edit or the reviewer upgraded Python. Those fields are
recorded so a disagreement can be diagnosed.

## Promotion

`set_verdict` refuses a `NUMERIC` verdict unless the claim has a test with an authoritative
verified group that matches the current binding, and stores that group in
`verdict.evidence_group`. `PROVEN` needs no group because it records an argument, not a
measurement. Integrity reports `EVID-005` when no group is current at all and `EVID-006` when the
promotion cites a group that is no longer authoritative — the case where a claim was promoted on
evidence that has since been superseded.

The earliest non-replaceable attempt is authoritative. Only `infra_failed` and `indeterminate`
attempts are replaceable, and each needs a recorded reason. Re-verifying unchanged code allocates
a new attempt, but a later `completed` attempt cannot displace an earlier `subject_failed` attempt.
Legacy run groups with no attempt row keep the pre-v6 any-current-group behaviour until they are
re-run.

## Revisions

`claim revise` appends a new claim row and sets `revision_of` on it and `superseded_by` on the old
row. The new row starts `UNVERIFIED`; verdicts are never copied, because old evidence supports the
old text, not the new one. Edges are repointed to the new head, tests are not: a test remains bound
to the old claim and integrity reports `REV-002` until it is deliberately rebound. `REV-001` catches
a dependency edge that still points at a superseded claim. `claim list` hides superseded rows by
default; `claim history` renders the chain oldest first.

## Schema Versions

`initialize` creates missing tables, then migrates an older `schema_meta.version` additively and
raises the version, returning a report with the starting version and how many numeric claims lost
their binding. `CREATE TABLE IF NOT EXISTS` alone would leave an older table without its new
columns, so `_add_missing_columns` inspects `PRAGMA table_info` and adds each missing column inside
the same transaction. Version 6 adds the `test_attempt` table; version 7 adds the claim revision
columns; version 8 adds the `protocol` table and the observation provenance columns. Existing run
groups are not backfilled and remain on the legacy path until they are re-run; existing claims are
revision heads with empty links; existing observations are legacy rows and warn `OBS-002`. Each version step is separate, so
a version-1 database passes through the version-2 step and then the version-3 step. A version
newer than the build is refused without modification, and the migration preserves existing rows,
including legacy runs whose binding columns are empty.

## Generated Reports

`report` is a pure function of the graph. `report --out PATH` writes the Markdown plus
`PATH.manifest.json` with a schema id, engine version, research id, `report_sha256`,
`content_sha256`, `graph_sha256`, counts, finding totals and the shared `LIMITS` block.

Two digests exist because one is not enough:

- `content_sha256` hashes a projection where `test_run` rows lose `id`, `run_group`, `started_at`,
  `duration_ms` and `output_tail`, and `test_attempt` rows keep only test, outcome and reason;
  identical records are de-duplicated. It is stable across a pure re-verification and changes when
  a claim, verdict, source or run fingerprint changes.
- `graph_sha256` hashes every exported evidence record exactly, so any recorded run changes it.
The audit log is exported but excluded from both digests: events are consequences of hashed
state, and `report.write` is created while the manifest is produced, so including it would make
the manifest reference itself.

`report --check PATH` compares content, the rendered text and the counts, and exits 1 on drift.
`--strict` additionally compares `graph_sha256`, which is the right check at release time.

## Reproducibility

`test_run` stores the exit code, duration, stdout/stderr SHA-256 hashes and a 2,000-character tail.
Two runs are comparable because the fingerprint is `(exit code, stdout hash, stderr hash)`.
Commands run in the project root with a bounded timeout; on timeout the whole process tree is
killed (`taskkill /T` on Windows, `killpg` on POSIX). A test that prints timings or random values
will fail two-run verification by design: make the evidence deterministic or do not call it
numeric.

Reports contain only values computed from the graph. `export` writes JSONL through a flushed
temporary file and `os.replace`, so a partial bundle is never visible. Report and manifest are
written through the same atomic helper, in that order; a manifest without a report is detectable
and `report --check` refuses to invent one.

## Extension Points

- **New relation:** add it to the relevant vocabulary in `models.py`, validate it in the adding
  function, and decide whether integrity should treat it as a dependency.
- **New verdict rule:** add a check to `integrity.check` with a stable code; never weaken an
  existing code silently.
- **New evidence adapter:** register sources from a new module and keep it outside `engine/cli.py`;
  the graph contract should not depend on the adapter.
- **New report:** read the graph and keep it free of hand-written numeric claims.

## Deliberate Non-Goals

- Distributed writers, CRDTs or multi-user concurrency.
- Network discovery inside the engine.
- Automatic promotion from test results.
- A formal proof checker. `PROVEN` records an evidence path, not a verified derivation.

## Falsifiability and Screening

`killtest.control_command` holds a negative control. `run_test` executes it in the same run group
but under `role='control'`; the control must fail the expectation on every repetition with identical
output. `verification_complete` requires the main command to pass twice and the control to fail
twice. The binding hashes `command + "--control--" + control`, so editing either side retires the
evidence. `EVID-008` warns when an evidence-bearing test has no control; `EVID-009` is an error when
a declared control never failed.

`source.screening` moves a source through `identified`, `screened_in`, `screened_out`, `included`
and `excluded`, with a reason drawn from a closed taxonomy and defaulted to `other` when an
out-status omits it. `prisma_flow` aggregates counts, reasons and the included fraction, and the
report renders it as a table. A live claim citing an excluded source yields `SCREEN-001` (warning);
retraction remains the hard error.

## Event Log

`event` is append-only: `id`, `at`, `research_id`, `kind`, `subject`, `detail`, `actor`. It records
the actions verdicts do not: `source.status`, `source.screening`, `claim.merge`, `report.write` and
`db.migrate`. Writers append inside their own transaction, so an event never exists for an action
that rolled back. `events` reads newest first with optional program and kind filters.

## Observations and Statistics

`observation` stores one measurement per row: claim, group label, finite numeric value, note,
timestamp, and a `voided` flag with a reason. A provenanced row also carries the instrument
(kind, id, digest), rater (kind, id, version), protocol id, sample size, aggregation and unit.
Provenance is all-or-nothing: pass the whole set or none. `protocol` is an immutable registry of
named measurement procedures; an unregistered id is refused. `analysis stats` refuses to compare
groups with different protocol ids, instruments, raters or units unless `--allow-incomparable` is
explicit, and then records the caveat. A legacy observation without provenance warns `OBS-002`.
Rows are never edited or deleted; a wrong measurement is voided so the record keeps its history.
`analysis stats` compares two groups through `engine/stats.py`, which is pure and stdlib-only:

| Quantity | Method | Notes |
|---|---|---|
| location/spread | sample mean, sample SD | – |
| effect size | Cohen's d, pooled SD | 0 when the pooled SD is 0 |
| parametric | Welch t, Satterthwaite df | zero-variance groups handled explicitly |
| p-value | regularized incomplete beta | matches reference values to 1e-10 |
| rank test | Mann-Whitney U | exact DP for untied n1·n2 ≤ 400, tie-corrected normal otherwise |
| interval | percentile bootstrap, seeded | the seed and resample count are recorded |
| trend | least squares, t-based p | needs ≥ 3 points |

`compare_groups` returns the numbers, `tests_agree`, `significant`, and warnings: fewer than three
observations, degenerate zero variance, the asymptotic rank method, and parametric/rank
disagreement at alpha 0.05. Group labels are normalised to lowercase, a group cannot be compared
with itself, and fewer than ten bootstrap resamples are refused. A run appends a `claim.stats`
or `claim.trend` event; `OBS-001` warns when no run exists **or when an observation was added or
voided after the last run**. Timestamps have second resolution, so a change inside the same
second as the run is not distinguished.

## Maintenance

`db integrity` runs `PRAGMA integrity_check` and `PRAGMA foreign_key_check`, then reports schema
version, journal mode and table counts; it exits 1 when either check fails. `db backup PATH` copies
the live database through SQLite's backup API into a temporary file in the destination directory,
verifies the copy, fsyncs it and only then renames it into place. An existing target is refused
rather than overwritten.

## Digests and Licence Identity

`artifacts.digest(kind, payload)` hashes the artifact kind before the payload: `graph/1`,
`content/1`, `report/1`, `license/1`. Two artifacts with identical bytes therefore get different
digests, so a report digest cannot be confused with a graph digest. The manifest records the
license id (`ASL-1.1`) and the digest of the normalized `LICENSE` text; `report --check` reports
drift when the terms change.

## Snapshot Integrity

An export's meta record carries `export_digest` over every record including the audit log, plus a
record count and the schema version. `export --check PATH` recomputes the digest and count; a
mismatch exits 1, a legacy export without a digest is refused rather than trusted, and a file
written by an unsupported schema is reported rather than accepted. This answers "is this file intact?"; the manifest's content
digest answers "has the evidence changed?" and deliberately excludes the log.

## Report Scope

A report is a statement about one program. `synthesis.report` and `manifest.build_manifest` use
`integrity.findings_for_research`, so another program's findings neither appear in the text nor in
the manifest counts. Before this, a clean program's committed report could be dirtied — and its
digest changed — by an unrelated program's error.

## Golden Run

`tests/test_golden.py` drives the entire CLI surface in a fresh database: program, question, source,
screening, empirical and derived claims, question links, pre-registration, observations, statistics,
trend, a controlled kill test, a numeric verdict, every view and analysis command, report plus
manifest plus drift check, two exports and a diff, integrity, backup, events, the gate, a cascade and
a merge. It asserts exit codes and the resulting state, so a command that composes badly fails
once, not only when its module is unit-tested.

## Markdown Safety

Claim text, quotes, locators and basis strings are untrusted. `engine/markdown.py` removes control
and format characters, collapses whitespace to a single line, caps width, and escapes backslashes,
pipes and backticks for table cells. Reports, scorecards, claim detail and token views all render
through it, so a newline in a claim can no longer break a table row or inject a heading.

## Agent Views

`engine/context.py` renders the graph for a bounded reader. `estimate_tokens` is the stable
`(chars + 3) / 4` heuristic; `pack` always keeps the first line as an anchor, drops from the end
when the budget is exhausted, reserves 40 tokens and returns the omitted count. Every view ends
with `OMITTED: n` when it was clipped, so a truncated view is never mistaken for a complete one.

| View | Content | Cost driver |
|---|---|---|
| `outline` | counts, one line per question/hypothesis/test, audit totals | questions + hypotheses + tests |
| `brief` | per question: consensus, strongest support, strongest contradiction | questions + 2 lines each |
| `claim context` | one claim with provenance, premises, verdict history | premises + verdicts |

The audit line in `outline` is scoped with `integrity.findings_for_research`, so a second
program's findings never inflate this program's totals. A budget smaller than the anchor line
still returns that one line: an empty view would be less useful than an honest overrun.

Views are read-only and deterministic: the same graph and budget produce the same bytes.

## Discovery

`engine/analysis.py` is advisory and never writes. `contradictions` pairs a supporting and a
contradicting claim **inside one question** — deliberately narrower than a global pairing, because
two claims about different questions are not in conflict. The score is
`0.6 * mean(confidence) + 0.4 * jaccard(keywords)`, sorted descending. `unlinked_contradictions`
proposes pairs with no `contradicts` edge at a default overlap of 0.35; a human records the edge.
`evidence_matrix` counts claims per source and question and reports uncovered questions.
`keystone_claims` ranks by transitive dependents plus inbound edges, reusing `cascade.dependents`
so the ranking matches what a collapse would actually do.

## Snapshots and Merges

`engine/diffing.py` compares two exports, which now include observations and the event log. The
default comparison is semantic: it reuses `bundle.content_records`, so re-verifying an unchanged
test is not a difference; `--exact` compares run bookkeeping too. Records are matched by `(type, id)`, so a renamed field is a change and a
reordering is not. Projected runs carry the identity `run:<test>:<run_tag>`: stable across a
re-verification, distinct across a test's two runs, and changed in place when a run's content
changes. When several run groups share that identity, their projections are compared as a
sorted list, never overwritten, so one group cannot hide another's change. The CLI exits 1 when
the snapshots differ.

`engine/merging.py` keeps one live claim, repoints every edge that touched a duplicate (dropping
edges that would become self-loops), repoints bound kill tests to the survivor, deletes the
duplicate's edges, and records the duplicate as `RETRACTED` with the survivor as its evidence.
Nothing is deleted from history: the duplicate keeps its verdict trail, and `DUP-001` ignores
retired claims. A test that still targets a retired claim through any other path is reported as
`TEST-001`.
