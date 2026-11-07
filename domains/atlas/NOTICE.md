# Ported Atlas pack notice

- Source: `projects/Atlas`, committed HEAD `f3cd7470e99683bc95b05f49e404bb00bffa2663`.
- License: Aegean License 1.1 (`LicenseRef-AL-1.1`). The host ASL-1.1 is based on AL-1.1 and
  the licensor is the same person, so the copy is a relicensing by the licensor, not a
  third-party sublicense. See `docs/merge/SOURCE-INVENTORY.md`.
- Ported: `atlas/*.py`, `atlas/static`, brand assets, and the two small demo modules
  `basal_ganglia_fixture.py` / `basal_ganglia_demo.py`. Uploaded media and the real-analysis
  corpus stay external; the pack stores references.
- Modifications: package path changed to `domains.atlas`; the static root points inside the
  pack; demo imports rewritten. The `atlas.visual-knowledge/v1` schema id is preserved.
- The source repository is read-only and is never modified.
