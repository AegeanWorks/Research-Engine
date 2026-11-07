#!/usr/bin/env python3
"""Build skeleton backfill rows for missing obezite claims.

The source operator script wrote into ``02_LITERATUR/iddia-defteri.md`` after a prompt. This port
separates discovery, row construction and insertion, and writes only to a caller-provided output
file. The external ledger is never modified.
"""

from __future__ import annotations

import argparse
import re
from datetime import date
from pathlib import Path
from typing import Iterable

CLAIM = re.compile(r"^\|\s*\*\*(\d+)\*\*")
REFERENCE = re.compile(r"[İI]ddia\s+(\d+)")
DEFAULT_TOURS = range(85, 118)


def existing_ids(ledger_file: Path) -> set[int]:
    if not ledger_file.is_file():
        return set()
    return {
        int(match.group(1))
        for match in CLAIM.finditer(ledger_file.read_text(encoding="utf-8"))
        if match
    }


def _tour_file(questions_dir: Path, tour_no: int) -> Path | None:
    candidates = sorted(questions_dir.glob(f"tur-{tour_no}-*.md"))
    if not candidates:
        candidates = sorted((questions_dir / "KARANTINA").glob(f"tur-{tour_no}-*.md"))
    return candidates[0] if candidates else None


def claims_from_tour(questions_dir: Path, tour_no: int) -> list[int]:
    path = _tour_file(questions_dir, tour_no)
    if path is None:
        return []
    text = path.read_text(encoding="utf-8")
    return sorted({int(value) for value in REFERENCE.findall(text)})


def collect_references(questions_dir: Path, tours: Iterable[int] = DEFAULT_TOURS) -> dict[int, int]:
    references: dict[int, int] = {}
    for tour_no in tours:
        for claim_id in claims_from_tour(questions_dir, tour_no):
            references.setdefault(claim_id, tour_no)
    return references


def skeleton_row(claim_id: int, tour_no: int | None) -> str:
    return (
        f"| **{claim_id}** | **BACKFILL GEREKTIRIR** -- Tur {tour_no or '?'}-den "
        f"'İddia {claim_id}' referansi bulundu; icerik henuz dogrulanmadi, deftere islenmedi. | "
        "L? | **D?/E?** -- backfill-gerektirir | ? | K5 aleyhte arama yapilmamis | "
        f"**backfill-bekliyor** | T{tour_no or '?'} |"
    )


def insert_rows(ledger_text: str, rows: Iterable[str]) -> str:
    """Insert rows at the end of the active table, before any retracted section."""
    new_rows = list(rows)
    if not new_rows:
        return ledger_text
    lines = ledger_text.splitlines()
    cut = len(lines)
    for index, line in enumerate(lines):
        if "ÇÜRÜTÜLMÜŞ" in line.upper() or "CURUTULMUS" in line.upper():
            cut = index
            break
    insert_at = cut
    for index in range(cut - 1, -1, -1):
        stripped = lines[index].strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            insert_at = index + 1
            break
    result = lines[:insert_at] + new_rows + lines[insert_at:]
    return "\n".join(result) + ("\n" if ledger_text.endswith("\n") else "")


def backfill(
    ledger_file: Path,
    questions_dir: Path,
    output_file: Path,
    start: int = 482,
    end: int = 597,
    tours: Iterable[int] = DEFAULT_TOURS,
    stamp: str | None = None,
) -> dict:
    """Write a backfilled ledger copy and return the missing/reference counts."""
    references = collect_references(questions_dir, tours)
    present = existing_ids(ledger_file)
    missing = sorted(set(range(start, end + 1)) - present)
    rows = [skeleton_row(claim_id, references.get(claim_id)) for claim_id in missing]
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(
        insert_rows(ledger_file.read_text(encoding="utf-8"), rows), encoding="utf-8"
    )
    return {
        "existing": len(present),
        "references": len(references),
        "missing": missing,
        "inserted": len(rows),
        "output": str(output_file),
        "stamp": stamp or date.today().isoformat(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, help="external obezite checkout")
    parser.add_argument("--output", required=True, help="host output ledger copy")
    parser.add_argument("--start", type=int, default=482)
    parser.add_argument("--end", type=int, default=597)
    args = parser.parse_args(argv)
    root = Path(args.root)
    result = backfill(
        root / "02_LITERATUR" / "iddia-defteri.md",
        root / "01_SORULAR",
        Path(args.output),
        start=args.start,
        end=args.end,
    )
    print(f"Mevcut iddia sayisi: {result['existing']}")
    print(f"Tur referansi: {result['references']}")
    print(f"Eksik: {len(result['missing'])}")
    print(f"[OK] {result['inserted']} iskelet giris yazildi: {result['output']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
