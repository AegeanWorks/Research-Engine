#!/usr/bin/env python3
"""Audit collapse annotations: every row citing an invalidated claim needs a marker.

The source script read a fixed working-directory ledger. This port takes an explicit ledger path
and returns the same analysis; it never writes the ledger.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from domains.obezite.atif import atiflar

CLAIM = re.compile(r"^\| \*\*(\d+)\*\*")
INVALID = re.compile(
    r"çürütüldü|GERİ ALINDI|geri alındı|DÜŞÜRÜLDÜ|düşürüldü|geçersiz|falsified|ÇÖKTÜ|çöktü",
    re.I,
)
MARKER = re.compile(r"~~|⛔|◐|⚠")


def ledger_lines(ledger_file: Path) -> list[str]:
    return ledger_file.read_text(encoding="utf-8").split("\n")


def marker_present(line: str) -> bool:
    """A marker counts only in the status or opposing-data column."""
    columns = line.split("|")
    if len(columns) < 9:
        return MARKER.search(line) is not None
    return (MARKER.search(columns[-3]) or MARKER.search(columns[-4])) is not None


def analyze(ledger_file: Path) -> dict:
    claims: dict[int, str] = {}
    for line in ledger_lines(ledger_file):
        match = CLAIM.match(line)
        if match:
            claims[int(match.group(1))] = line
    invalid: set[int] = set()
    for claim_id, line in claims.items():
        columns = line.split("|")
        if len(columns) >= 9 and INVALID.search(columns[-3]):
            invalid.add(claim_id)
    citing: dict[int, list[int]] = {}
    for claim_id, line in claims.items():
        columns = line.split("|")
        if len(columns) < 3:
            continue
        for reference in atiflar(columns[-2]):
            citing.setdefault(reference, []).append(claim_id)
    dependents = sorted(
        {dependent for claim_id in invalid for dependent in citing.get(claim_id, []) if dependent != claim_id}
    )
    missing = [
        (claim_id, dependent)
        for claim_id in sorted(invalid)
        for dependent in sorted(citing.get(claim_id, []))
        if dependent != claim_id and not marker_present(claims[dependent])
    ]
    baseline = sum(1 for line in claims.values() if marker_present(line))
    return {
        "claims": len(claims),
        "invalid": sorted(invalid),
        "dependents": dependents,
        "missing": missing,
        "baseline_marked": baseline,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", required=True)
    parser.add_argument("--details", action="store_true")
    args = parser.parse_args(argv)
    result = analyze(Path(args.ledger))
    total = result["claims"]
    dependents = result["dependents"]
    marked = len(dependents) - len({dependent for _, dependent in result["missing"]})
    print(
        "iddia %d · gecersiz %d · onlari anan %d satir"
        % (total, len(result["invalid"]), len(dependents))
    )
    print(
        "serh taban orani %d/%d (%.0f%%) · bagimli kumede %d/%d (%.0f%%)"
        % (
            result["baseline_marked"],
            total,
            100.0 * result["baseline_marked"] / total if total else 0.0,
            marked,
            len(dependents),
            100.0 * marked / len(dependents) if dependents else 100.0,
        )
    )
    if args.details:
        for invalid in result["invalid"]:
            print(f"  {invalid}: {sorted({d for g, d in result['missing'] if g == invalid})}")
    if result["missing"]:
        print(f"SERHSIZ BAGIMLI: {len(result['missing'])}")
        return 1
    print("TEMIZ: gecersiz iddia anan her satir serh tasiyor")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
