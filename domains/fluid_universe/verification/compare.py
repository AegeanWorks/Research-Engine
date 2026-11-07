"""Compare two independent verification runs.

Project rule G-001: every claim in `claims.md` marked PROVEN, NUMERIC, or
VERIFIED must be re-derived in two separate runs (separate processes), never
twice in one run. The per-claim results must agree before a claim is accepted.
This rule applies to claims, not to the pytest suite.

The comparison also rejects stale runs: both runs must carry the same source
and results fingerprints, and those must match the current files.

Run:

    python -m verification.audit --tag run1
    python -m verification.audit --tag run2
    python -m verification.compare
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path

from .fingerprint import default_root, fingerprints

RESULTS = default_root() / "results"


def _load(tag: str, root: Path | None = None) -> dict:
    results = (root / "results") if root is not None else RESULTS
    path = results / f"verification_{tag}.json"
    if not path.is_file():
        raise FileNotFoundError(f"missing {path}; run the audit with --tag {tag}")
    return json.loads(path.read_text(encoding="utf-8"))


def _digest(payload: dict) -> str:
    checks = [
        {"claim": c["claim"], "passed": c["passed"], "detail": c["detail"]}
        for c in payload["checks"]
    ]
    blob = json.dumps(checks, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def compare(tags: tuple[str, str] = ("run1", "run2"), root: Path | None = None) -> dict:
    if tags[0] == tags[1]:
        raise ValueError("tags must differ (G-001: two separate processes)")
    runs = [_load(tag, root) for tag in tags]
    current = fingerprints(root) if root is not None else fingerprints()
    run_fingerprints = [run["meta"].get("fingerprints", {}) for run in runs]
    fingerprints_match = all(fp == current for fp in run_fingerprints)

    maps = [{check["claim"]: check for check in run["checks"]} for run in runs]
    all_claims = sorted(set(maps[0]) | set(maps[1]))
    per_claim = []
    for claim in all_claims:
        first = maps[0].get(claim)
        second = maps[1].get(claim)
        if first is None or second is None:
            per_claim.append(
                {
                    "claim": claim,
                    "run1": "MISSING" if first is None else ("PASS" if first["passed"] else "FAIL"),
                    "run2": "MISSING" if second is None else ("PASS" if second["passed"] else "FAIL"),
                    "agree": False,
                    "detail_match": False,
                    "detail": "claim present in only one run",
                }
            )
            continue
        per_claim.append(
            {
                "claim": claim,
                "run1": "PASS" if first["passed"] else "FAIL",
                "run2": "PASS" if second["passed"] else "FAIL",
                "agree": first["passed"] == second["passed"],
                "detail_match": first["detail"] == second["detail"],
                "detail": first["detail"],
            }
        )

    claims_agree = all(item["agree"] for item in per_claim)
    details_match = all(item["detail_match"] for item in per_claim)
    checks_match = _digest(runs[0]) == _digest(runs[1])
    totals_match = all(
        (run["total"], run["passed"], run["failed"])
        == (runs[0]["total"], runs[0]["passed"], runs[0]["failed"])
        for run in runs
    )
    all_passed = all(run["failed"] == 0 for run in runs)
    accepted = (
        claims_agree
        and details_match
        and checks_match
        and totals_match
        and fingerprints_match
        and all_passed
    )

    combined = {
        "meta": {
            "rule": "G-001: each claim is verified in two separate processes; per-claim results must agree",
            "scope": "claims.md claims, not the pytest suite",
            "current_fingerprints": current,
            "runs": [
                {
                    "tag": tag,
                    "generated_utc": run["meta"].get("generated_utc"),
                    "git_commit": run["meta"].get("git_commit"),
                    "passed": run["passed"],
                    "total": run["total"],
                    "failed": run["failed"],
                    "checks_sha256": digest,
                    "fingerprints": run["meta"].get("fingerprints", {}),
                }
                for tag, run, digest in zip(tags, runs, [_digest(r) for r in runs])
            ],
            "claims_agree": claims_agree,
            "details_match": details_match,
            "checks_match": checks_match,
            "totals_match": totals_match,
            "fingerprints_match": fingerprints_match,
            "all_passed": all_passed,
            "accepted": accepted,
        },
        "claims": per_claim,
        "checks": runs[0]["checks"],
        "total": runs[0]["total"],
        "passed": runs[0]["passed"],
        "failed": runs[0]["failed"],
        "failures": runs[0]["failures"],
    }
    _write("verification.json", json.dumps(combined, indent=2) + "\n", root)
    _write("verification.md", render(combined), root)
    return combined


def _write(name: str, text: str, root: Path | None = None) -> None:
    results = (root / "results") if root is not None else RESULTS
    path = results / name
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def render(payload: dict) -> str:
    meta = payload["meta"]
    lines = [
        "# Independent claim verification (two runs)",
        "",
        "Project rule G-001: every claim in `claims.md` marked PROVEN, NUMERIC, or VERIFIED is "
        "verified twice, in two separate processes, and the per-claim results must agree. This "
        "applies to claims, not to the pytest suite.",
        "",
        "| run | generated (UTC) | commit | passed/total | source SHA-256 | results SHA-256 |",
        "|---|---|---|---|---|---|",
    ]
    for run in meta["runs"]:
        fp = run["fingerprints"]
        lines.append(
            f"| {run['tag']} | {run['generated_utc']} | `{run['git_commit']}` | "
            f"{run['passed']}/{run['total']} | `{fp.get('source_sha256', '')[:16]}...` | "
            f"`{fp.get('results_sha256', '')[:16]}...` |"
        )
    lines += [
        "",
        f"- per-claim agreement: **{meta['claims_agree']}**",
        f"- per-claim detail equality: **{meta['details_match']}**",
        f"- fingerprints match current files: **{meta['fingerprints_match']}**",
        f"- all checks passed: **{meta['all_passed']}**",
        f"- accepted: **{meta['accepted']}**",
        "",
        "| claim | run 1 | run 2 | agree | detail match | detail |",
        "|---|---|---|---|---|---|",
    ]
    for item in payload["claims"]:
        lines.append(
            f"| {item['claim']} | {item['run1']} | {item['run2']} | "
            f"{'YES' if item['agree'] else 'NO'} | "
            f"{'YES' if item['detail_match'] else 'NO'} | {item['detail']} |"
        )
    if not meta["accepted"]:
        lines += [
            "",
            "## Rejected",
            "",
            "The two runs do not agree, a claim failed, or the fingerprints do not match the "
            "current files. Re-run both audits after any change.",
        ]
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare two verification runs.")
    parser.add_argument("--tags", nargs=2, default=("run1", "run2"))
    args = parser.parse_args()
    try:
        result = compare(tuple(args.tags))
    except FileNotFoundError as error:
        print(f"Why: {error}")
        print("Fix: run both audits first: `python -m verification.audit --tag run1` and `--tag run2`.")
        return 2
    meta = result["meta"]
    print(
        f"per-claim agree={meta['claims_agree']} details={meta['details_match']} "
        f"fingerprints={meta['fingerprints_match']} all_passed={meta['all_passed']} "
        f"accepted={meta['accepted']} ({result['passed']}/{result['total']})"
    )
    return 0 if meta["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
