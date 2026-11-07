#!/usr/bin/env python3
"""Create the claim cross-reference index from the obezite chunk files.

The source script wrote into a fixed ``02_LITERATUR`` path. This port returns the Markdown and
writes only to a caller-provided output file.
"""

from __future__ import annotations

import argparse
import re
from collections import defaultdict
from pathlib import Path
from typing import Iterable

CLAIM = re.compile(r"^\|\s*\*\*(\d+)\*\*\s*\|(.+)\|$")


def parse_claims_from_file(filepath: Path) -> list[tuple[int, str]]:
    """Return ``(claim_id, linked_column)`` for each claim row."""
    if not filepath.is_file():
        return []
    claims: list[tuple[int, str]] = []
    for line in filepath.read_text(encoding="utf-8").splitlines():
        match = CLAIM.match(line)
        if not match:
            continue
        columns = match.group(2).split("|")
        if len(columns) >= 7:
            claims.append((int(match.group(1)), columns[6].strip()))
    return claims


def categorize_reference(ref: str) -> list[tuple[str, str]]:
    """Categorize the free-text linked column into stable reference kinds."""
    text = ref.strip()
    if not text or text == "—":
        return []
    refs: list[tuple[str, str]] = []
    for part in re.split(r"[,\s]+", text):
        token = part.strip()
        if not token:
            continue
        if token.startswith(("VA-", "va-")):
            refs.append(("VA", token.upper()))
        elif token.startswith("S") and token[1:].replace(".", "").isdigit():
            refs.append(("SORU", token))
        elif token.startswith(("Ç-", "C-")):
            refs.append(("ÇELİŞKİ", token))
        elif token.startswith("H") and token[1:].isdigit():
            refs.append(("HIPOTEZ", token))
        elif token.startswith("T") and token[1:].isdigit():
            refs.append(("TUR", token))
        elif token.startswith("G") and token[1:].isdigit():
            refs.append(("GÖZLEM", token))
        elif token.startswith(("K", "R")) and token[1:].isdigit():
            refs.append(("KURAL", token))
        elif token.startswith("Z") and token[1:].isdigit():
            refs.append(("Z-SKOR", token))
        elif token.startswith("M-") or (token.startswith("M") and token[1:].isdigit()):
            refs.append(("MODEL", token))
        elif token.startswith(("D", "E")) and token[1:].isdigit():
            refs.append(("DERECE", token))
    return refs


def build_index(
    chunk_files: Iterable[Path],
    retracted_file: Path,
    output_file: Path,
) -> dict:
    """Build and write the cross-reference index; return the counts."""
    all_claims: dict[int, str] = {}
    for chunk in chunk_files:
        for claim_id, linked in parse_claims_from_file(chunk):
            all_claims[claim_id] = linked
    if retracted_file.is_file():
        for claim_id, linked in parse_claims_from_file(retracted_file):
            all_claims.setdefault(claim_id, linked)

    buckets: dict[str, dict[str, list[int]]] = {
        key: defaultdict(list)
        for key in (
            "VA", "HIPOTEZ", "TUR", "SORU", "ÇELİŞKİ", "GÖZLEM", "KURAL", "MODEL",
            "DERECE", "Z-SKOR",
        )
    }
    for claim_id, linked in sorted(all_claims.items()):
        for kind, value in categorize_reference(linked):
            buckets[kind][value].append(claim_id)

    lines = [
        "# İDDİA ÇAPRAZ-ATIF İNDEKSİ\n\n",
        f"> Otomatik oluşturuldu: {len(all_claims)} benzersiz iddia\n",
        "> Kaynak: chunk dosyaları + CURUTULMUS\n\n",
        "## İstatistikler\n\n",
        f"- Toplam iddia: {len(all_claims)}\n",
        f"- VA raporu atıflı: {len(buckets['VA'])}\n",
        f"- Hipotez kartı atıflı: {len(buckets['HIPOTEZ'])}\n",
        f"- Tur atıflı: {len(buckets['TUR'])}\n",
        f"- Soru haritası atıflı: {len(buckets['SORU'])}\n",
        f"- Çelişki atıflı: {len(buckets['ÇELİŞKİ'])}\n",
        f"- Gözlem atıflı: {len(buckets['GÖZLEM'])}\n",
        f"- Kural atıflı: {len(buckets['KURAL'])}\n",
        f"- Model atıflı: {len(buckets['MODEL'])}\n",
        f"- Derece (D/E) atıflı: {len(buckets['DERECE'])}\n",
        f"- Z-skor atıflı: {len(buckets['Z-SKOR'])}\n\n",
    ]
    sections = (
        ("VA", "VA Raporlarına Göre İddialar"),
        ("HIPOTEZ", "Hipotez Kartlarına Göre İddialar"),
        ("TUR", "Turlara Göre İddialar"),
        ("SORU", "Soru Haritasına Göre İddialar"),
        ("ÇELİŞKİ", "Çelişkilerle Göre İddialar"),
    )
    for kind, heading in sections:
        lines.append(f"## {heading}\n\n")
        for value in sorted(buckets[kind], key=lambda item: (len(item), item)):
            claims = sorted(buckets[kind][value])
            links = ", ".join(f"[{claim}](#iddia-{claim})" for claim in claims)
            lines.append(f"### {value}\n\nİddialar: {links}\n\n")
    lines.append("## Tam İddia Listesi (Bağlı Sütunu)\n\n")
    lines.append("| İddia | Bağlı |\n|-------|-------|\n")
    for claim_id in sorted(all_claims):
        lines.append(f"| {claim_id} | {all_claims[claim_id]} |\n")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text("".join(lines), encoding="utf-8")
    return {"claims": len(all_claims), "output": str(output_file)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, help="external obezite checkout")
    parser.add_argument("--output", required=True, help="host output file")
    args = parser.parse_args(argv)
    literature = Path(args.root) / "02_LITERATUR"
    chunks = [
        literature / "iddia-defteri-0001-0500.md",
        literature / "iddia-defteri-0501-1000.md",
    ]
    result = build_index(chunks, literature / "iddia-defteri-CURUTULMUS.md", Path(args.output))
    print(f"Total unique claims: {result['claims']}")
    print(f"Created {result['output']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
