#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sentez projections: the claim register and file inventory are derived from the canonical
ledger and the worktree, never hand-maintained (project rule: no second source, claim 804).

Usage:
  python 08_ARACLAR/sentez_uret.py          # regenerate 09_SENTEZ/*.csv
  python 08_ARACLAR/sentez_uret.py --check  # exit 1 when a generated file drifted
"""
from __future__ import annotations

import argparse
import csv
import io
import os
import re
import sys
import tempfile
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Dict, Iterable, List, Optional

ROOT = Path(__file__).resolve().parents[3] / "obezite-mekanizma-projesi"
LEDGER = ROOT / "02_LITERATUR" / "iddia-defteri.md"
OUT_DIR = Path(__file__).resolve().parent / "generated"
REGISTER = OUT_DIR / "iddia-register.csv"
COUNTS = OUT_DIR / "kanit-ozeti.csv"
INVENTORY = OUT_DIR / "dosya-envanteri.csv"

SKIP_DIRS = {".git", ".aikit", "__pycache__", ".pytest_cache", "node_modules", ".venv", "venv"}
RAW_DATA = Path("07_ANALIZ") / "veri"
GENERATED = {REGISTER.name, COUNTS.name, INVENTORY.name}


def split_fields(line: str) -> List[str]:
    """A markdown table row as cells; `\\|` stays inside a cell."""
    text = line.strip()
    if text.startswith("|"):
        text = text[1:]
    if text.endswith("|"):
        text = text[:-1]
    text = text.replace("\\|", "\x00")
    return [cell.strip().replace("\x00", "|") for cell in text.split("|")]


def macro_bucket(verdict: str) -> str:
    """Group the ledger's free-text verdict into six auditable buckets."""
    text = verdict.lower()
    if "backfill" in text:
        return "backfill-bekliyor"
    if "çürütüldü" in text:
        return "çürütüldü"
    if "çelişkili" in text:
        return "çelişkili"
    if any(word in text for word in
           ("olası", "spekülatif", "belirsiz", "çıkarım", "zayıf", "açık", "tutarlı (zayıf)")):
        return "olası/spekülatif"
    if "kanıtlı" in text:
        return "kanıtlı"
    return "diğer"


def grade_bucket(grade: str) -> str:
    text = re.sub(r"[*~]", "", grade).strip()
    if re.search(r"D1|E1", text):
        return "D1/E1"
    if re.search(r"D2|E2", text):
        return "D2/E2"
    if re.search(r"D3|E3", text):
        return "D3/E3"
    if "D?" in text or "E?" in text:
        return "belirsiz"
    return "diğer"


def source_identity(source: str) -> bool:
    return bool(re.search(r"PMID|DOI|PMC|https?://|VA-\d|S\d\d\.", source))


def star_count(claim: str) -> int:
    match = re.search(r"★+", claim)
    return len(match.group(0)) if match else 0


def parse_claims(text: str) -> List[Dict[str, object]]:
    claims: List[Dict[str, object]] = []
    for line_no, line in enumerate(text.splitlines(), 1):
        if not line.startswith("| **"):
            continue
        cells = split_fields(line)
        if len(cells) < 8 or not cells[0].strip("*").isdigit():
            continue
        claims.append({
            "id": int(cells[0].strip("*")),
            "line": line_no,
            "claim": cells[1],
            "class": cells[2],
            "grade": cells[3],
            "direction": cells[4],
            "linked": cells[5],
            "verdict": cells[6],
            "source": cells[7],
        })
    for claim in claims:
        claim["bucket"] = macro_bucket(str(claim["verdict"]))
        claim["grade_bucket"] = grade_bucket(str(claim["grade"]))
        claim["source_identity"] = "yes" if source_identity(str(claim["source"])) else "no"
        claim["stars"] = star_count(str(claim["claim"]))
        claim["range"] = "1-481" if claim["id"] <= 481 else "482-597" if claim["id"] <= 597 else "600-885"
    return claims


def summarize(claims: Iterable[Dict[str, object]]) -> Dict[str, object]:
    rows = list(claims)
    verified = [row for row in rows if row["bucket"] != "backfill-bekliyor"]
    ranges = Counter(str(row["range"]) for row in rows)
    summary: Dict[str, object] = {
        "rows": len(rows),
        "verified": len(verified),
        "backfill": len(rows) - len(verified),
        "range_1_481": ranges.get("1-481", 0),
        "range_482_597": ranges.get("482-597", 0),
        "range_600_885": ranges.get("600-885", 0),
        "buckets": Counter(str(row["bucket"]) for row in verified),
        "grades": Counter(str(row["grade_bucket"]) for row in verified),
        "source_identity": sum(row["source_identity"] == "yes" for row in verified),
        "stars": Counter(int(row["stars"]) for row in verified),
    }
    return summary


def count_rows(summary: Dict[str, object]) -> List[Dict[str, str]]:
    rows = [
        ("defter_satiri", summary["rows"]),
        ("dogrulanmis_iddia", summary["verified"]),
        ("backfill_bekleyen", summary["backfill"]),
        ("aralik_1_481", summary["range_1_481"]),
        ("aralik_482_597", summary["range_482_597"]),
        ("aralik_600_885", summary["range_600_885"]),
        ("kaynak_kimlikli_dogrulanmis", summary["source_identity"]),
    ]
    for name, count in sorted(summary["buckets"].items()):
        rows.append((f"hukum_{name}", count))
    for name, count in sorted(summary["grades"].items()):
        rows.append((f"derece_{name}", count))
    for stars, count in sorted(summary["stars"].items()):
        rows.append((f"yildiz_{stars}", count))
    return [{"metrik": name, "deger": str(value)} for name, value in rows]


def atomic_write(path: Path, content: str, encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding=encoding, newline="") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def csv_text(fieldnames: List[str], rows: Iterable[Dict[str, object]]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buffer.getvalue()


def register_text(claims: List[Dict[str, object]]) -> str:
    fields = ["id", "range", "bucket", "verdict", "class", "grade", "grade_bucket",
              "source_identity", "stars", "linked", "source", "claim"]
    return csv_text(fields, claims)


def inventory_rows(root: Path) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        if rel.parts[:2] == RAW_DATA.parts:
            continue
        if rel.parts[:1] == ("09_SENTEZ",) and path.name in GENERATED:
            continue
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        kind = {
            ".md": "belge", ".py": "betik", ".ps1": "arac", ".tex": "makale-kaynagi",
            ".pdf": "makale", ".docx": "makale", ".csv": "cikti", ".parquet": "veri",
            ".png": "figur", ".svg": "figur", ".tiff": "figur", ".json": "veri",
        }.get(suffix, "diger")
        rows.append({
            "yol": rel.as_posix(),
            "ust_dizin": rel.parts[0] if len(rel.parts) > 1 else ".",
            "tur": kind,
            "boyut_kb": f"{path.stat().st_size / 1024:.1f}",
            "tarih": date.fromtimestamp(path.stat().st_mtime).isoformat(),
        })
    for path in sorted((root / RAW_DATA).glob("*")):
        if not path.is_dir():
            continue
        files = [item for item in path.rglob("*") if item.is_file()]
        size = sum(item.stat().st_size for item in files)
        rows.append({
            "yol": (RAW_DATA / path.name).as_posix() + "/",
            "ust_dizin": "07_ANALIZ",
            "tur": "veri-dizini (git disi)",
            "boyut_kb": f"{size / 1024:.1f}",
            "tarih": date.fromtimestamp(path.stat().st_mtime).isoformat(),
            "not": f"{len(files)} dosya",
        })
    return rows


def inventory_text(rows: List[Dict[str, object]]) -> str:
    return csv_text(["yol", "ust_dizin", "tur", "boyut_kb", "tarih", "not"], rows)


def generate(root: Optional[Path] = None, with_inventory: bool = False) -> Dict[str, str]:
    base = Path(root) if root is not None else ROOT
    ledger = base / "02_LITERATUR" / "iddia-defteri.md"
    claims = parse_claims(ledger.read_text(encoding="utf-8"))
    summary = summarize(claims)
    outputs = {
        REGISTER.name: register_text(claims),
        COUNTS.name: csv_text(["metrik", "deger"], count_rows(summary)),
    }
    if with_inventory:
        outputs[INVENTORY.name] = inventory_text(inventory_rows(base))
    return outputs


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail when a generated file is stale")
    args = parser.parse_args(argv)
    outputs = generate()
    stale = [name for name, content in outputs.items()
             if not (OUT_DIR / name).is_file() or (OUT_DIR / name).read_text(encoding="utf-8-sig") != content]
    if args.check:
        if stale:
            print(f"[FAIL] sentez projections stale: {', '.join(stale)}")
            print("Fix: python 08_ARACLAR/sentez_uret.py")
            return 1
        print("[OK] sentez projections are fresh")
        return 0
    for name, content in outputs.items():
        atomic_write(OUT_DIR / name, content, encoding="utf-8-sig")
    claims = parse_claims(LEDGER.read_text(encoding="utf-8"))
    summary = summarize(claims)
    print(f"[OK] {summary['rows']} claim rows -> {summary['verified']} verified, "
          f"{summary['backfill']} backfill; {len(outputs)} files in {OUT_DIR.name}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
