# Project Guidelines

Rules for this project only, written by people or AI agents. They add to AIKit's principles and
rank below them: a guideline never overrides a principle (PRINCIPLE-000 R6, PRINCIPLE-001 R4).
Add one with `python aikit.py guideline <name> "<rule>" --source <user|ADR-NNN|person>`, or by
hand as one line below in the form `- **G-NNN** (source): rule`; IDs are never reused.

Persisted state carries a format version. A loader refuses a version it does not support,
without modifying or quarantining that file; older versions migrate when a migration exists.

## Rules
- **G-001** (user): Every empirical claim carries a registered source, an exact quote and a locator; no quote, no claim.
- **G-002** (user): Every claim names the test most likely to kill it before any promotion.
- **G-003** (user): A NUMERIC verdict requires two separate runs that agree on exit code and output hashes; one run is evidence, not proof.
- **G-004** (user): Negative results are kept: corrections are new verdicts, never silent edits or deletions.
- **G-005** (user): Dependency edges (derived_from, depends_on) drive cascade invalidation; evidence edges do not.
- **G-006** (user): Reports, scorecards and consensus values are generated from the graph; never hand-write their numbers.
