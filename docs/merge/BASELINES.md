# Pre-merge baseline (M0)

All commands were run from each project root on 2026-11-07, before any host code change.
The host branch is `merge/research-functions`; every source is at the committed SHA in
`SOURCE-INVENTORY.md`.

| Project | Command | Result | Exit |
|---|---|---|---:|
| research-engine | `python -m unittest discover -s tests -t .` | `Ran 555 tests in 94.655s` — `OK` | 0 |
| lattice | `python -m unittest discover` | `Ran 252 tests in 8.699s` — `OK` | 0 |
| N1-Engine | `python -m pytest tests -q` | `20 passed in 18.26s` | 0 |
| fluid-universe | `python -m pytest -q` | `403 passed in 1807.74s (0:30:07)` | 0 |
| PNN | `python -m unittest discover -s tests -t .` | `Ran 222 tests in 1.980s` — `OK` | 0 |
| obezite-mekanizma-projesi | `python -m unittest discover -s tests -v` | `Ran 10 tests in 5.017s` — `OK` | 0 |
| Atlas | `python -m pytest tests -q` | `152 passed, 1 skipped, 1 warning in 25.68s` | 0 |

## Notes

- N1's `pytest` run is the four file suite; its GUI tests exercise the analysis and schema
  contracts without opening a window.
- fluid-universe's suite is the slow tier: 403 tests pass, dominated by the physics
  regeneration tests. The run completed in a background process with exit code 0.
- Atlas's one skip is a platform-dependent optional path; the remaining 152 tests pass.
- PNN's suite prints pipeline output between dots; the summary line is the gate.
- The host baseline is green before the branch point, so any later failure is attributable to the
  merge.

## Reproduce

```bash
cd projects/research-engine && python -m unittest discover -s tests -t .
cd projects/lattice && python -m unittest discover
cd projects/N1-Engine && python -m pytest tests -q
cd projects/fluid-universe && python -m pytest -q
cd projects/PNN && python -m unittest discover -s tests -t .
cd projects/obezite-mekanizma-projesi && python -m unittest discover -s tests -v
cd projects/Atlas && python -m pytest tests -q
```

## M5 re-check after the merge

| Source | Result | SHA |
|---|---|---|
| lattice | `Ran 252 tests in 4.467s` — `OK` | unchanged |
| N1-Engine | `20 passed in 7.58s` | unchanged |
| PNN | `Ran 222 tests in 1.979s` — `OK` | unchanged |
| Atlas | `152 passed, 1 skipped in 20.80s` | unchanged |
| obezite (pinned archive) | 9/10; only `test_generated_files_are_fresh` fails because archive extraction changes inventory mtimes | pinned `18b5d4d8…` |
| obezite (current worktree) | 8/10; the source advanced to `23f2df6…` with its own in-flight projection drift (1910 vs 1906 claims) | not imported |
| fluid-universe | M0 full run `403 passed`; M5 rerun recorded in the final report | unchanged |
