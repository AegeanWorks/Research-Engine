#!/usr/bin/env python3
"""Deduplicate obezite ledger claims across chunk files and the retracted ledger.

First occurrence in the chunk files wins. Later occurrences are described in an archive file and
removed from a *copy* of the retracted ledger. The source checkout is never written.
"""

from __future__ import annotations

import argparse
import re
from datetime import date
from pathlib import Path
from typing import Iterable, Sequence

CLAIM = re.compile(r"^\|\s*\*\*(\d+)\*\*\s*\|")


def parse_claims_from_file(filepath: Path) -> list[tuple[int, str, int]]:
    """Return ``(claim_id, line, line_index)`` for every claim row in one file."""
    if not filepath.is_file():
        return []
    lines = filepath.read_text(encoding="utf-8").splitlines(keepends=True)
    claims: list[tuple[int, str, int]] = []
    for index, line in enumerate(lines):
        match = CLAIM.match(line)
        if match:
            claims.append((int(match.group(1)), line, index))
    return claims


def get_all_lines(filepath: Path) -> list[str]:
    if not filepath.is_file():
        return []
    return filepath.read_text(encoding="utf-8").splitlines(keepends=True)


def write_lines(filepath: Path, lines: Sequence[str]) -> None:
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text("".join(lines), encoding="utf-8")


def find_duplicates(
    chunk_files: Sequence[Path], retracted_file: Path
) -> list[tuple[int, tuple[Path, str, int], tuple[Path, str, int]]]:
    """Return duplicate claims as ``(id, chunk_row, retracted_row)``."""
    first: dict[int, tuple[Path, str, int]] = {}
    for chunk in chunk_files:
        for claim_id, line, index in parse_claims_from_file(chunk):
            first.setdefault(claim_id, (chunk, line, index))
    duplicates = []
    for claim_id, line, index in parse_claims_from_file(retracted_file):
        if claim_id in first:
            duplicates.append((claim_id, first[claim_id], (retracted_file, line, index)))
    return duplicates


def deduplicate(
    chunk_files: Sequence[Path],
    retracted_file: Path,
    archive_file: Path,
    updated_retracted_file: Path,
    stamp: str | None = None,
) -> dict:
    """Write the duplicate archive and a retracted-ledger copy; return counts."""
    day = stamp or date.today().isoformat()
    duplicates = find_duplicates(chunk_files, retracted_file)
    archive_lines = [
        f"# İDDİA DEFTERİ — MÜKERRER KAYITLAR (Arşiv: {day})\n\n",
        "> Bu dosya `deduplicate_defter.py` tarafından otomatik oluşturuldu.\n",
        "> **Kural:** İlk oluşum (chunk dosyalarında) korunur, ikinci oluşum buraya taşınır.\n",
        "> Orijinal satır numaraları ve dosya kaynakları not edilmiştir.\n\n",
        "## Mükerrer İddialar\n\n",
        "| İddia | Chunk Dosyası | Chunk Satır | CURUTULMUS Satır | Not |\n",
        "|-------|---------------|-------------|------------------|-----|\n",
    ]
    remove: set[int] = set()
    for claim_id, (chunk_file, _chunk_line, chunk_index), (_cur_file, cur_line, cur_index) in duplicates:
        remove.add(cur_index)
        archive_lines.append(
            f"| {claim_id} | {chunk_file.name} | {chunk_index + 1} | {cur_index + 1} | "
            "İlk oluşum chunk dosyasında; CURUTULMUS'tan taşındı |\n"
        )
        archive_lines.append(f"\n### İddia {claim_id} (CURUTULMUS'tan taşınan satır)\n\n")
        archive_lines.append("```markdown\n")
        archive_lines.append(cur_line.rstrip() + "\n")
        archive_lines.append("```\n\n")
    archive_file.parent.mkdir(parents=True, exist_ok=True)
    archive_file.write_text("".join(archive_lines), encoding="utf-8")
    retracted_lines = get_all_lines(retracted_file)
    updated = [line for index, line in enumerate(retracted_lines) if index not in remove]
    write_lines(updated_retracted_file, updated)
    return {
        "duplicates": len(duplicates),
        "archive": str(archive_file),
        "updated": str(updated_retracted_file),
        "remaining": len(updated),
    }


def _paths(root: Path, output_dir: Path) -> tuple[list[Path], Path, Path]:
    literature = root / "02_LITERATUR"
    chunks = [
        literature / "iddia-defteri-0001-0500.md",
        literature / "iddia-defteri-0501-1000.md",
    ]
    retracted = literature / "iddia-defteri-CURUTULMUS.md"
    archive = output_dir / f"iddia-duplicates-{date.today().isoformat()}.md"
    return chunks, retracted, archive


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, help="external obezite checkout")
    parser.add_argument("--output-dir", required=True, help="host output directory")
    args = parser.parse_args(argv)
    root = Path(args.root)
    output = Path(args.output_dir)
    chunks, retracted, archive = _paths(root, output)
    result = deduplicate(
        chunks,
        retracted,
        archive,
        output / "iddia-defteri-CURUTULMUS.md",
    )
    print(f"Found {result['duplicates']} duplicate claim IDs")
    print(f"Created duplicate archive: {result['archive']}")
    print(f"Updated retracted copy: {result['updated']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
