# Ported fluid-universe pack notice

- Source: `projects/fluid-universe`, committed HEAD `7b4efe141dfbcc267b0efceb82247f5004186c06`.
- License: Aegean Source License 1.1 (`LicenseRef-ASL-1.1`), same as the host.
- Ported: `verification/*.py`, `theory/*.py`, `phenomenology/*.py` and `sims/*.py` into
  `domains.fluid_universe`. Physics outputs under `results/`, and every generated report,
  stay external and are referenced by fingerprint.
- Modifications: package paths changed; the verification root points at the sibling
  checkout; no claim status or audit rule is changed.
- The source repository is read-only and is never modified.
