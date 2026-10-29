# Mechanics and Their Sources

This project is a clean-room composition of four mechanics observed in four separate research
codebases. No source code was copied. The goal is to keep the transferable discipline and drop the
domain content and pipeline weight.

## 1. Provenance-first claims (`lattice`)

**Mechanic.** A claim is the unit of knowledge. It cannot exist without a source, an exact quote and
a locator. Questions collect claims with a stance (`supports`, `contradicts`, `answers`, `mentions`).

**Rule here.** `kind=empirical` refuses to save without `source_ref`, `quote` and `locator`. Quotes
are refused on derived or assumed claims, so an argument cannot masquerade as a quotation.

**Deliberately not copied.** Literature discovery, full-text extraction, web studio, MCP server.
The engine is a ledger, not a crawler.

## 2. Falsification-first ledger (`fluid-universe`)

**Mechanic.** Every claim has a status, an evidence path, and the test most likely to kill it.
Negative results are first-class. A correction is a new record, never a silent edit.

**Rule here.** The vocabulary is closed: `UNVERIFIED`, `PROVEN`, `NUMERIC`, `FALSIFIED`,
`RETRACTED`, `INVALIDATED`. Promotion requires a kill test and evidence. Failed states require
evidence. `verdict` rows preserve `previous -> new`, evidence, note, actor and time.

**Deliberately not copied.** The physics content, the claim ledger as prose, and the Make targets
for that project's simulations.

## 3. Two-run independent verification (`fluid-universe`)

**Mechanic.** A numerical claim is not accepted from a single run. Two separate processes must
agree.

**Rule here.** `test verify` runs a command twice, each in its own process, and compares exit code
and stdout/stderr hashes. `NUMERIC` integrity requires a run group with at least two passing runs
and one distinct fingerprint. A single run is evidence; it is not numeric proof.

**Deliberately not copied.** The project-specific audit harness and its claim list.

## 3b. Evidence binding (extension of the same mechanic)

**Gap found.** Two agreeing runs can pass before and after the tested code changes, because the
hashes cover only stdout and stderr. A command edited in the database keeps its old verified group.
Probes confirmed both: a NUMERIC claim survived a changed input file and a rewritten command.

**Rule here.** A run records `command_sha256`, `code_sha256` over `engine/**.py` and
`inputs_sha256` over the test's declared `--input` paths. `current_verified_group` matches the
current binding, and integrity reports `EVID-005` when a numeric claim has no matching group.
Git commit, dirty flag, Python and platform are recorded but excluded from the binding, so an
unrelated worktree edit does not invalidate a durable measurement.

**Scope limit.** Code outside `engine/` and undeclared input files are not hashed. Declaring inputs
is the researcher's obligation; the README states this.

## 3c. Attempt authority (extension of the same mechanic)

**Gap found.** A current group can be any verified group, so a researcher can keep re-running a
failing test until a later run passes and promote that group. The earlier subject failure stays in
the log but does not constrain the verdict.

**Rule here.** Every execution records an attempt with a monotonic sequence and one outcome:
`completed`, `subject_failed`, `infra_failed` or `indeterminate`. Only `infra_failed` and
`indeterminate` are replaceable, and each needs a recorded reason. The earliest non-replaceable
attempt bound to the current command, code and inputs is authoritative. A later `completed`
attempt cannot displace an earlier `subject_failed` attempt, and `set_verdict` refuses a NUMERIC
promotion that cites anything else. Legacy run groups without an attempt row keep the old
any-current-group behaviour until they are re-run.

**Deliberately not copied.** A separate hash-chained attempt file; SQLite's append-only rows and
the existing run binding are the ledger.

## 4. Pre-registration (`obezite-mekanizma-projesi`)

**Mechanic.** A prediction is written, with its confidence and its falsification criterion, before
the search or experiment. This prevents post-hoc storytelling.

**Rule here.** `hypothesis add` stores the statement, confidence, criterion and registration time.
`hypothesis outcome` can close it once, with evidence. Integrity checks that the outcome is not
dated before registration. `hypothesis card` renders the K13-style card.

**Deliberately not copied.** Turkish-language domain files, the chunked claim register, and the
project's intervention boundaries. Only the pre-registration discipline moved.

## 4b. Claim revisions (extension of the same discipline)

**Gap found.** Claim text was immutable. Refining an assertion forced either a second, silently
contradicting claim or a stale statement that no longer matched the evidence.

**Rule here.** `claim revise` appends a new claim row, sets `revision_of` on the new row and
`superseded_by` on the old one, and moves the old claim's edges to the new head. The new claim
starts `UNVERIFIED`; verdicts are never inherited. Tests stay on the old claim and integrity
reports `REV-002` until they are deliberately rebound; `REV-001` catches a dependency edge that
still points at a superseded claim. `claim history` renders the chain. An empirical revision still
needs a source, quote and locator, and every revision needs a reason.

**Deliberately not copied.** Editing a claim row in place or carrying the old verdict forward.

## 5. Transitive cascade invalidation (`obezite-mekanizma-projesi`)

**Mechanic.** When an invalid claim is cited without qualification, everything built on it is
suspect. The collapse must propagate rather than leave a silent stale claim.

**Rule here.** Dependency edges (`derived_from`, `depends_on`) define the propagation graph.
`claim invalidate` records the root as `FALSIFIED` or `RETRACTED`, then marks every transitive
dependent `INVALIDATED` in the same transaction, with a reason and a link to the root. A dependent
that was deliberately retracted is left as retracted.

**Deliberately not copied.** The prose ledger and its manual audit scripts.

## 5c. Explicit UNKNOWN (`PNN`)

**Mechanic.** A screening stage distinguishes PASS, FAIL and UNKNOWN, and UNKNOWN never counts
as a pass. Missing data is a state, not an absence.

**Rule here.** `claim verdict --status UNKNOWN --evidence ...` records that the evidence does
not exist and why. UNKNOWN carries zero consensus weight, blocks the promotion of a dependent
(`NON_SUPPORTING_STATUSES`, alongside the failure states), and does **not** cascade: an absent
measurement is not a refutation. `EVID-007` warns when the reason was never recorded.

**Deliberately not copied.** The domain screening tiers and their threshold rules.

## 5b. Source retraction (`obezite-mekanizma-projesi` + `lattice` screening)

**Mechanic.** A cited source can be withdrawn or placed under an expression of concern. The
reference project verifies PMIDs and retractions before a source stays usable; lattice records
screening decisions with explicit exclusion reasons.

**Rule here.** `source status` records `active`, `expression_of_concern` or `retracted`, with a
mandatory note for either downgrade. `source retract` runs inside one transaction: it marks the
source, retires every empirical claim citing it as `RETRACTED`, and cascades to their dependents as
`INVALIDATED`. A claim already failed is left untouched. Integrity reports `PROV-003` for a live
claim on a retracted source and a warning (`PROV-004`) for one under concern.

**Deliberately not copied.** PMID lookup and the prose audit tables; the engine has no network
access, so the retraction notice is recorded by the researcher.

## 6. Gate and golden path (`PNN`)

**Mechanic.** A delivery gate runs the real pipeline and refuses a broken state; a golden run makes
the baseline checkable. Generated artifacts carry a manifest so a later reader can tell whether
they still match the state that produced them.

**Rule here.** `check` is the gate: provenance, evidence, binding freshness, graph structure, scope,
cascade freshness, source status and pre-registration order. `demo` is the golden path: a synthetic
program that exercises every writer and is expected to pass `check` with zero findings.
`report --out` writes a manifest with a schema id, graph and report digests, counts, findings and an
explicit limits block; `report --check` exits 1 on drift.

**Deliberately not copied.** The drug-discovery phases and their CSV contracts.

## 6b. Deterministic projections (`obezite-mekanizma-projesi`)

**Mechanic.** Derived files are projections of one canonical source, and a `--check` mode fails
when the projection drifted. The reference project learned this the hard way: hand-maintained
derived files silently dropped high-value records.

**Rule here.** `report`, `scorecard` and `export` are pure functions over the database; nothing is
maintained by hand. The manifest digests make drift detectable, and `report --check` is the
projection gate.

## Why not use one project wholesale?

- `lattice` has the right storage model but no verdict lifecycle, executable tests, pre-registration
  or cascade.
- `fluid-universe` has the right epistemic vocabulary but is inseparable from a specific physics
  program.
- `obezite-mekanizma-projesi` has the right cascade and pre-registration discipline but is a
  large domain archive.
- `PNN` has the right gate discipline but its phases are domain-specific.

Composing the mechanics on a small standard-library graph avoids four forks, four schemas, and four
divergent definitions of "verified".

## 6c. Declared-input integrity (`fluid-universe` fingerprints)

**Mechanic.** A run is bound to the code and inputs it actually consumed, not to whatever exists
when someone later reads the result.

**Gap found.** The first binding implementation hashed declared input paths literally. A directory
declaration hashed nothing, a glob was hashed as a missing filename, and an absent file used the
same marker bytes as a file containing the word `missing`.

**Rule here.** `resolve_inputs` expands globs deterministically and refuses directories; the digest
is length-prefixed with a typed `file`/`missing` tag, so absence and content cannot collide. A
declaration that matches nothing is still recorded, so creating the file later invalidates the old
evidence instead of leaving it silently valid.

**Scope limit.** Only declared inputs and `engine/**.py` are bound. Undeclared reads remain the
researcher's risk, stated in the README.

## 7. Agent-facing views (`lattice`)

**Mechanic.** A graph is only usable by an agent if it can be read under a token budget, and a
truncated read must say so.

**Rule here.** `estimate_tokens` uses `(chars + 3) / 4`; `pack` keeps the first line as an anchor,
reserves 40 tokens, and reports the number of omitted lines, which every view appends as
`OMITTED: n`. `outline`, `brief` and `claim context` cover the three reading depths.

**Deliberately not copied.** The search/expand MCP surface and the web studio; this is a CLI
over the same store.

## 8. Contradiction and coverage analysis (`lattice`)

**Mechanic.** Opposing claims should be discoverable, not only recorded, and coverage gaps should
be visible per source and question.

**Rule here.** `contradictions` pairs stances inside one question and ranks by confidence and
keyword overlap; the same claim pair attached to two questions is reported once per question; `unlinked_contradictions` proposes pairs that lack an edge; `evidence_matrix`
counts claims per source and question; `keystone_claims` ranks claims by transitive dependents
and inbound edges. All four are read-only; only `claim link` records a relation.

**Deliberately not copied.** Global stance pairing (lattice's model stores stance on the claim,
so it can pair across questions) and its auto-link flag default.

## 9. Non-vacuity of a gate (`obezite-mekanizma-projesi`)

**Mechanic.** The reference project measured the base rate of its annotation marker (60%) against
the dependent set (100%) before trusting the gate, because "the discipline holds" and "the test
tests nothing" produce the same passing output.

**Rule here.** A kill test declares a negative control: a command that must fail. `test verify`
runs the control twice and requires an identical failure. A test with verified evidence and no
control is a warning (`EVID-008`); a declared control that passes is an error (`EVID-009`). The
control is part of the command binding, so editing it retires the evidence.

**Deliberately not copied.** The Turkish prose ledger, the annotation-marker convention and its
per-row audit script.

## 10. Screening and PRISMA (`lattice`)

**Mechanic.** A source is not simply present or absent: it is identified, screened against stated
criteria, then included or excluded for a recorded reason, and the flow is reported.

**Rule here.** `source screen` uses the five-state lattice vocabulary and a closed reason taxonomy;
`source prisma` and the report show counts, reasons and the included fraction. A claim citing an
excluded source warns (`SCREEN-001`).

**Deliberately not copied.** Database search, deduplication against external indexes and the web
screening UI.

## 11. Domain-separated digests and pinned licence identity (`aegean-licensing`)

**Mechanic.** Canonical JSON is hashed with a domain prefix so a certificate digest and a signature
can never collide; the licence text is normalized and pinned by SHA-256.

**Rule here.** `artifacts.digest(kind, payload)` prefixes every digest with its artifact kind
(`export/1`, `graph/1`, `content/1`, `report/1`, `license/1`). An export carries its own digest,
record count and schema, so `export --check` proves the file intact without a sidecar and refuses
a schema this build does not read. Manifest schema 3 records the license id and the
digest of the normalized `LICENSE` file, and `report --check` treats a terms change as drift.

**Deliberately not copied.** The certificate schema, HMAC signing and the revocation register;
those belong to licence issuance, not to evidence.

## 12. Verified backup and event trail (`aegean-licensing-ops`)

**Mechanic.** State is copied through the storage engine's own backup path, verified, and moved
into place atomically; every mutation leaves an audit trail.

**Rule here.** `db backup` uses `sqlite3.Connection.backup`, verifies the copy, fsyncs and renames;
an existing target is refused. `event` records source status, screening, merges, revisions, report
generation and migrations, inside the writer's transaction. Each event also carries a per-program
sequence and an optional parent; `events --tree` and `events --path` render the causal chain.

**Deliberately not copied.** The commercial key store, issuance workflow and web console.

## 13. Deterministic comparison of repeated measurements (`N1-Engine`)

**Mechanic.** The reference project turns repeated numeric series into a result envelope: means,
standard deviations, effect size, a parametric test, a non-parametric cross-check, and a confidence
interval, with per-item errors isolated so one bad metric does not abort the batch. It also guards
against testing many metrics at once.

**Rule here.** `observation add` records each value in a named group; `analysis stats` compares two
groups with `engine/stats.py`: Cohen's d, Welch t with a beta-function p-value, Mann-Whitney U
(exact for untied small samples, tie-corrected normal otherwise), and a seeded percentile bootstrap.
The result states whether the two tests agree and carries explicit warnings for small groups,
degenerate variance, the approximation, disagreement, and an uncorrected pairwise test among more
than two groups. Labels are case-insensitive, a self-comparison is refused, and so is a bootstrap
with fewer than ten resamples. `analysis trend` fits a least-squares slope over a group's recording order, and
refuses to pretend when there are fewer than three points. Every run is logged as `claim.stats`
or `claim.trend`, and `OBS-001` warns when observations exist without a statistics run.

**Extension: measurement provenance.** An observation may carry the instrument (kind, id,
digest), rater (kind, id, version), protocol id, sample size, aggregation and unit. The protocol is
an immutable registry entry. `analysis stats` refuses to compare different protocols,
instruments, raters or units unless `--allow-incomparable` is explicit; a legacy row without
provenance warns `OBS-002`. This makes "the metric improved" a claim about a named procedure, not
a bare number.

**Deliberately not copied.** The intervention/baseline domain model, the medical metrics, pandas,
scipy, SQLAlchemy and PyQt. The port is stdlib-only and deterministic; the reference bootstrap is
unseeded, which this project does not reproduce.
