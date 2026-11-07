"""Split the obezite claim ledger into active and quarantined projections.

The source script ran at import time against a fixed working-directory path. This port keeps the
same keyword rule but exposes it as a function with explicit paths; importing the module touches
no file.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Iterable

from domains.obezite.sentez import split_fields

QUARANTINE_KEYWORDS = (
    "falsified",
    "GERİ ÇEKİLDİ",
    "geçersiz",
    "çürütüldü",
    "yanlışlandı",
    "replike edilemedi",
)

CLAIM_PATTERN = re.compile(r"^\|\s*\*\*\d+\*\*\s*\|")


def split_lines(lines: Iterable[str]) -> tuple[list[str], list[str]]:
    """Return active and quarantined lines using the source's verdict-column rule."""
    active: list[str] = []
    quarantine: list[str] = []
    for line in lines:
        if CLAIM_PATTERN.match(line):
            columns = split_fields(line)
            if len(columns) >= 7:
                verdict = columns[6].lower()
                direction = columns[4].lower()
                hit = any(keyword.lower() in verdict for keyword in QUARANTINE_KEYWORDS)
                hit = hit or any(keyword.lower() in direction for keyword in QUARANTINE_KEYWORDS)
                (quarantine if hit else active).append(line)
            else:
                active.append(line)
        else:
            active.append(line)
            quarantine.append(line)
    return active, quarantine


def split_ledger(
    source_file: Path | str,
    active_file: Path | str,
    quarantine_file: Path | str,
) -> dict:
    """Write the two projections and return their line counts."""
    lines = Path(source_file).read_text(encoding="utf-8").splitlines(keepends=True)
    active, quarantine = split_lines(lines)
    Path(active_file).write_text("".join(active), encoding="utf-8")
    Path(quarantine_file).write_text("".join(quarantine), encoding="utf-8")
    return {
        "total": len(lines),
        "active": len(active),
        "quarantined": len(quarantine),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--active", required=True)
    parser.add_argument("--quarantine", required=True)
    args = parser.parse_args(argv)
    counts = split_ledger(args.source, args.active, args.quarantine)
    print(f"Total lines: {counts['total']}")
    print(f"Active claims/lines: {counts['active']}")
    print(f"Quarantined claims/lines: {counts['quarantined']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
