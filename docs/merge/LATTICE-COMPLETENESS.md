# lattice completeness audit

Date: 2026-11-07  
Purpose: decide whether lattice can be archived after the merge. Every public module, function,
class and class method in the pinned source (`d3f0502b99983f1436fe9466f5553935ea7be868`) is
mapped below.

## Result

AST inventory including class methods:

| Measure | Source | Host |
|---|---:|---:|
| Modules | 22 | 25 (adds host start, inventory and dogfood) |
| Public functions/classes/methods | 187 | 208 |
| Missing public names | — | **0** |

## Module mapping

| Source module | Host destination | Status |
|---|---|---|
| `lattice/database.py` | `adapters/lattice/database.py` | **copied** |
| `lattice/models.py` | `adapters/lattice/models.py` | **copied** |
| `lattice/repository.py` | `adapters/lattice/repository.py` | **copied** |
| `lattice/discovery.py` | `adapters/lattice/discovery.py` | **copied** |
| `lattice/ingest.py` | `adapters/lattice/ingest.py` | **copied** |
| `lattice/extraction.py` | `adapters/lattice/extraction.py` | **copied** |
| `lattice/analysis.py` | `adapters/lattice/analysis.py` | **copied** |
| `lattice/context.py` | `adapters/lattice/context.py` | **copied** |
| `lattice/inquiry.py` | `adapters/lattice/inquiry.py` | **copied** |
| `lattice/meta.py` | `adapters/lattice/meta.py` | **copied** |
| `lattice/snapshots.py` | `adapters/lattice/snapshots.py` | **copied** |
| `lattice/diff.py` | `adapters/lattice/diff.py` | **copied** |
| `lattice/checks.py` | `adapters/lattice/checks.py` | **copied** |
| `lattice/screening.py` | `adapters/lattice/screening.py` | **copied** |
| `lattice/synthesis.py` | `adapters/lattice/synthesis.py` | **copied** |
| `lattice/cli.py` | `adapters/lattice/cli.py` | **copied** |
| `lattice/web.py` | `studio/web.py` | **copied** |
| `lattice/mcp.py` | `studio/mcp.py` | **copied** |
| `lattice/api.py` | `studio/api.py` | **copied** |
| `lattice/client.py` | `studio/client.py` | **copied** |
| `lattice/__main__.py` | `adapters/lattice/__main__.py` | **copied** |
| `lattice/__init__.py` (`__version__`) | `adapters/lattice/__init__.py` | **copied** |
| `start.py` | `adapters/lattice/start.py` | **adapted** (host root DB default) |
| `tools/ui_inventory.py` | `adapters/lattice/ui_inventory.py` | **adapted** (reads `studio/web.py`) |
| `tools/dogfood.py` | `adapters/lattice/dogfood.py` | **adapted and run** (25/25 steps) |

## Entry-point names

The code is complete, but the invocation path changed because the host separates adapters and
studio:

| Source | Host |
|---|---|
| `python -m lattice ...` | `python -m adapters.lattice ...` |
| `from lattice.api import ...` | `from studio.api import ...` |
| `from lattice.web/mcp/client import ...` | `from studio.web/mcp/client import ...` |
| `from lattice.<other> import ...` | `from adapters.lattice.<other> import ...` |
| `python tools/ui_inventory.py` | `python -m adapters.lattice.ui_inventory` |
| `python tools/dogfood.py` | `python -m adapters.lattice.dogfood` |

## What is left

No functional code. Only packaging and convenience files were not copied:

- `start.bat`, `start.sh` (the Python launcher is ported);
- `pyproject.toml`, `README.md`, `REUSE.toml`, `assets/`, source `.aikit/` memory;
- the source `lattice.db` fixture and test data.

## Evidence

```text
python C:\Users\Yunus-Emre\AppData\Local\Temp\lattice_audit.py
source_modules 22, host_modules 25, source_defs 187, host_defs 208,
modules_with_missing 0, dogfood adapters/lattice/dogfood.py

python -m unittest discover -s tests/lattice -t .
Ran 252 tests
OK

python -m adapters.lattice.dogfood
LATTICE DOGFOOD (PRINCIPLE-015): 25/25 steps passed
  full log: .aikit\dogfood_last_run.log
```

**Archive verdict:** lattice can be archived. The full public surface is present under
`adapters/lattice` and `studio`; only the command/import names changed. Keep the source only if
the original `lattice` package name or its batch launchers must remain available unchanged.
