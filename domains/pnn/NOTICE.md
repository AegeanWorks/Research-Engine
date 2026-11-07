# Ported PNN pack notice

- Source: `projects/PNN`, committed HEAD `3b6e6c277552dcb2c3604483de1277307bc18c4d`.
- License: Aegean Source License 1.1 (`LicenseRef-ASL-1.1`), same as the host.
- Ported: `pnn/*.py` into `domains.pnn`, and the small `data/` CSV fixtures used by the
  pipeline contracts. Generated `output/`, `tmp_out/` and real project data stay external.
- Modifications: package path changed to `domains.pnn`; `PROJECT_ROOT` points at the pack
  so the copied fixtures resolve without touching the source checkout.
- The source repository is read-only and is never modified.
