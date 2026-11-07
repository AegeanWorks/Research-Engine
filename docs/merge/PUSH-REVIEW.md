# Push-window review

Date: 2026-11-08  
Branch: `merge/research-functions`  
Base: `563f27a` (host before the merge)

The 22 branch commits were reviewed in cumulative windows: 1→3, 1→6, 1→9, 1→12, 1→15, 1→18,
1→21 and 1→22. Each window was checked for defects, gaps and missing implementations; fixes found
in a window are named in the last column.

| Window | Commits included | Review result | Fix made |
|---|---|---|---|
| 1→3 | `34fd2f7` schema/migration, `925a16f` big port, `ec23f6a` README tree | schema, ports and tests green; no defect at this depth | README tree entry corrected in the window |
| 1→6 | + `12d73cf`, `52fa913`, `c2cee82` docs/fluid rerun | source evidence and fluid rerun recorded | none |
| 1→9 | + `0bcd715`, `f130a1a`, `6b60671` ledger, split fix, obezite note | `split.py` executed file I/O at import and used cwd paths | import-safe function + CLI, `f130a1a` |
| 1→12 | + `6f40dad`, `b295c6b`, `c155e48` tools, neurocore, Atlas/fluid/license tests | re-rooted tools and added MCP/API contract | none after the window |
| 1→15 | + `de3b8ac`, `d178a3f`, `771fb05` N1 surfaces | N1 GUI contained real backend operations not in the host | extracted edit/close/status, metric rename/delete, summary, JSON report |
| 1→18 | + `47f9861`, `5b6036e`, `1abd70c` lattice dogfood | dogfood gate was the one unported lattice tool | ported dogfood; excluded tooling from API facade |
| 1→21 | + `9287770`, `fdb5de2`, `07669ed` pack trees, gauge, README | `digest_tree` loaded each whole file into memory; unsafe for large external data | streamed in 1 MiB chunks |
| 1→22 | + `729ea0f` project scan | coverage test broke when transient worktrees appeared; archive gained `iris` | ignore `*-baseline*`; record `archive/iris` |

## Final fixes in this review

- `engine/artifacts.digest_tree` now streams file bytes instead of `read_bytes()`, so a large
  external file cannot exhaust memory.
- `experiments/summary.summarize_period(intervention_ref=...)` now keeps the source contract:
  an intervention-scoped summary includes every event linked to that intervention, even outside
  the display window, while metrics remain the intervention's full series.
- The project-coverage test ignores transient `*-baseline*` copies and the scan table records
  `archive/iris`.

## Verification

```text
python -m unittest tests.test_n1_surfaces tests.test_packs -q
Ran 20 tests in 0.615s
OK
```

The full suite and strict gate are run before the push; the push is recorded separately in the
session report.
