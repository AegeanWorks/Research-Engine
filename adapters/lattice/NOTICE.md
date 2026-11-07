# Ported lattice notice

- Source: `projects/lattice`, committed HEAD `d3f0502b99983f1436fe9466f5553935ea7be868`.
- License: Aegean License 1.1 (`LicenseRef-AL-1.1`), compatible with the host ASL-1.1 as
  described in `docs/merge/SOURCE-INVENTORY.md`.
- Ported: `lattice/*.py` except `web.py`, `mcp.py`, `api.py` and `client.py`, plus
  `tools/ui_inventory.py`, `tools/dogfood.py` and a host-adapted `start.py`.
- Modifications: package path changed to `adapters.lattice`; imports rewritten; the four
  studio modules moved to `studio/`; the launcher defaults to the host project database; the
  dogfood server command uses `python -m adapters.lattice`.
- The source repository and its `lattice.db` are read-only inputs and are never modified.
