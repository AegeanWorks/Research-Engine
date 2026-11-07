#!/usr/bin/env python3
"""Split the obezite ledger into two range chunks plus a master index.

The source script wrote into a fixed ``02_LITERATUR`` directory. This port writes into the
directory the caller names and never touches the source ledger.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Iterable

HEADER = "| # | İddia"
CLAIM = re.compile(r"^\|\s*\*\*(\d+)\*\*\s*\|")


def parse_claims(lines: Iterable[str]) -> list[tuple[int, int, str]]:
    claims: list[tuple[int, int, str]] = []
    in_table = False
    for index, line in enumerate(lines):
        if line.strip().startswith(HEADER):
            in_table = True
            continue
        if in_table and line.strip().startswith("|---"):
            continue
        if in_table:
            match = CLAIM.match(line)
            if match:
                claims.append((int(match.group(1)), index, line))
            elif line.strip() and not line.strip().startswith("|"):
                break
    return claims


def split_ledger(source_file: Path, output_dir: Path) -> dict:
    lines = source_file.read_text(encoding="utf-8").splitlines(keepends=True)
    header_end = 0
    for index, line in enumerate(lines):
        if line.strip().startswith(HEADER):
            header_end = index
            break
    header = lines[:header_end]
    claims = parse_claims(lines)
    first = [claim for claim in claims if 1 <= claim[0] <= 500]
    second = [claim for claim in claims if 501 <= claim[0] <= 1000]
    main_table_end = len(lines)
    for index, line in enumerate(lines):
        if line.strip().startswith("### ★ YENİ ÇELİŞKİLER"):
            main_table_end = index
            break
    post_table = lines[main_table_end:]

    table_header = (
        "| # | İddia (nicel, model sistemi ile) | Katman | En güçlü kanıt (D/E) | "
        "Nedensellik (K6) | Aleyhte veri | Durum | Bağlı |\n"
        "|---|---|---|---|---|---|---|---|\n"
    )
    chunk_one = header[:]
    chunk_one.append("## A. AKTİF İDDİALAR (1-500)\n\n")
    chunk_one.append(table_header)
    chunk_one.extend(line for _claim_id, _index, line in first)
    chunk_one.append("\n> **Not:** İddialar 501-1000 için bkz. [iddia-defteri-0501-1000.md](iddia-defteri-0501-1000.md)\n")
    chunk_one.append("> **Ana indeks:** [iddia-defteri-index.md](iddia-defteri-index.md)\n")

    chunk_two = header[:]
    chunk_two.append("## A. AKTİF İDDİALAR (501-1000)\n\n")
    chunk_two.append(table_header)
    chunk_two.extend(line for _claim_id, _index, line in second)
    chunk_two.append("\n")
    chunk_two.extend(post_table)
    chunk_two.append("\n> **Not:** İddialar 1-500 için bkz. [iddia-defteri-0001-0500.md](iddia-defteri-0001-0500.md)\n")
    chunk_two.append("> **Ana indeks:** [iddia-defteri-index.md](iddia-defteri-index.md)\n")

    index_lines = [
        "# İDDİA DEFTERİ — ANA İNDEKS\n\n",
        "> Bu dosya, iddia defterinin parçalanmış dosyalarını haritalar.\n\n",
        "## Chunk Haritası\n\n",
        "| Dosya | Aralık | İddia Sayısı | Açıklama |\n",
        "|-------|--------|--------------|----------|\n",
        f"| [iddia-defteri-0001-0500.md](iddia-defteri-0001-0500.md) | 1-500 | {len(first)} | İlk 500 iddia |\n",
        f"| [iddia-defteri-0501-1000.md](iddia-defteri-0501-1000.md) | 501-1000 | {len(second)} | İddialar 501+ |\n",
    ]
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "chunk1": output_dir / "iddia-defteri-0001-0500.md",
        "chunk2": output_dir / "iddia-defteri-0501-1000.md",
        "index": output_dir / "iddia-defteri-index.md",
    }
    paths["chunk1"].write_text("".join(chunk_one), encoding="utf-8")
    paths["chunk2"].write_text("".join(chunk_two), encoding="utf-8")
    paths["index"].write_text("".join(index_lines), encoding="utf-8")
    return {
        "claims": len(claims),
        "chunk1": len(first),
        "chunk2": len(second),
        "outputs": {name: str(path) for name, path in paths.items()},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    result = split_ledger(Path(args.source), Path(args.output_dir))
    print(f"Found {result['claims']} claims")
    print(f"Chunk 1 (1-500): {result['chunk1']} claims")
    print(f"Chunk 2 (501-1000): {result['chunk2']} claims")
    for name, path in result["outputs"].items():
        print(f"Created {name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
