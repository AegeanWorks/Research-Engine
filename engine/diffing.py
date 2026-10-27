"""Snapshot comparison: what changed between two exported graphs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Dict, List, Tuple

from engine.bundle import content_records
from engine.errors import EngineError

VOLATILE_FIELDS = frozenset({"id", "run_group", "started_at", "duration_ms", "output_tail"})


def load_jsonl(path: Path) -> List[dict]:
    """Read an export, dropping its meta line; a malformed file is refused."""
    source = Path(path)
    if not source.is_file():
        raise EngineError(
            f"snapshot not found: {source}",
            "a diff needs two exported snapshots to compare.",
            "create one with `export PATH --research REF`.",
        )
    records: List[dict] = []
    for number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except ValueError as error:
            raise EngineError(
                f"snapshot line {number} is not valid JSON: {source}",
                f"{error}",
                "re-export the snapshot with this engine version.",
            ) from error
        if record.get("type") == "meta":
            continue
        records.append(record)
    return records


def _key(record: dict) -> Tuple[str, str]:
    """Identity of a record: its id, or a digest of a projection that has no id."""
    identity = str(record.get("id") or "")
    if not identity and "projection" in record:
        payload = json.dumps(record["projection"], sort_keys=True)
        identity = "run:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    return str(record.get("type")), identity


def _strip(record: dict) -> dict:
    return {key: value for key, value in record.items() if key not in VOLATILE_FIELDS}


def _index(records: List[dict], semantic: bool) -> Dict[Tuple[str, str], object]:
    """Index records by type and identity, optionally collapsing run churn.

    A semantic run id is `(test, run_tag)`, so several run groups can share one id. They are kept
    as a sorted list rather than overwritten: overwriting would let the last record hide a change
    in an earlier one.
    """
    if semantic:
        records = content_records(records)
    buckets: Dict[Tuple[str, str], List[dict]] = {}
    for record in records:
        buckets.setdefault(_key(record), []).append(_strip(record))
    index: Dict[Tuple[str, str], object] = {}
    for key, values in buckets.items():
        index[key] = values[0] if len(values) == 1 else sorted(
            values, key=lambda value: json.dumps(value, sort_keys=True)
        )
    return index


def diff_records(old: List[dict], new: List[dict], semantic: bool = True) -> dict:
    """Compare two record sets and classify added, removed and changed records."""
    before = _index(old, semantic)
    after = _index(new, semantic)
    added = sorted(set(after) - set(before))
    removed = sorted(set(before) - set(after))
    changed = sorted(
        key for key in set(before) & set(after) if before[key] != after[key]
    )
    return {
        "semantic": semantic,
        "added": [{"type": kind, "id": identity} for kind, identity in added],
        "removed": [{"type": kind, "id": identity} for kind, identity in removed],
        "changed": [{"type": kind, "id": identity} for kind, identity in changed],
        "counts": {
            "added": len(added),
            "removed": len(removed),
            "changed": len(changed),
        },
        "identical": not (added or removed or changed),
    }


def diff_files(old: Path, new: Path, semantic: bool = True) -> dict:
    """Compare two exported snapshots."""
    return diff_records(load_jsonl(old), load_jsonl(new), semantic=semantic)


def render(result: dict) -> str:
    """Render a diff as a compact, deterministic report."""
    counts = result["counts"]
    mode = "semantic" if result["semantic"] else "exact"
    lines = [
        f"diff ({mode}): {counts['added']} added, {counts['removed']} removed,"
        f" {counts['changed']} changed"
    ]
    for label, key in (("+", "added"), ("-", "removed"), ("~", "changed")):
        for item in result[key]:
            lines.append(f"  {label} {item['type']}:{item['id']}")
    if result["identical"]:
        lines.append("  no differences")
    return "\n".join(lines) + "\n"
