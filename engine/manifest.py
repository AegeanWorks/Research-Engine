"""Generated-report manifests and drift detection."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import List

from engine import __version__
from engine.artifacts import atomic_write_text, digest, utc_now
from engine.bundle import content_sha256, graph_sha256
from engine.errors import EngineError
from engine.integrity import check
from engine.researches import get_research, research_counts
from engine.synthesis import LIMITS, report

REPORT_SCHEMA = "research-engine.report/3"
LICENSE_ID = "ASL-1.1"
LICENSE_FILE = Path(__file__).resolve().parents[1] / "LICENSE"
MANIFEST_SUFFIX = ".manifest.json"


def license_block() -> dict:
    """Identify the terms the generated artifact is offered under, by id and text digest."""
    try:
        raw = LICENSE_FILE.read_bytes()
    except OSError:
        return {"id": "unknown", "sha256": ""}
    normalized = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return {"id": LICENSE_ID, "sha256": digest("license/1", normalized)}


def manifest_path(report_path: Path) -> Path:
    """The sidecar path for a report, accepting a report or a manifest path."""
    path = Path(report_path)
    if path.name.endswith(MANIFEST_SUFFIX):
        return path
    return Path(str(path) + MANIFEST_SUFFIX)


def build_manifest(conn: sqlite3.Connection, research_ref: str, text: str) -> dict:
    """Describe one generated report: schema, digests, counts, findings and limits."""
    research = get_research(conn, research_ref)
    findings = check(conn)
    return {
        "schema": REPORT_SCHEMA,
        "engine": __version__,
        "research": {"id": research.id, "slug": research.slug},
        "generated_at": utc_now(),
        "license": license_block(),
        "report_sha256": digest("report/1", text),
        "content_sha256": content_sha256(conn, research.id),
        "graph_sha256": graph_sha256(conn, research.id),
        "counts": research_counts(conn, research.id),
        "findings": {
            "errors": sum(item.severity == "error" for item in findings),
            "warnings": sum(item.severity == "warning" for item in findings),
        },
        "limits": list(LIMITS),
    }


def write_report(conn: sqlite3.Connection, research_ref: str, path: Path) -> dict:
    """Write the report and its manifest atomically; return both paths and the digests."""
    text = report(conn, research_ref)
    manifest = build_manifest(conn, research_ref, text)
    destination = Path(path)
    sidecar = manifest_path(destination)
    atomic_write_text(destination, text)
    atomic_write_text(sidecar, json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    from engine.events import record as record_event

    record_event(
        conn,
        "report.write",
        str(sidecar),
        f"report {manifest['report_sha256'][:16]} graph {manifest['graph_sha256'][:16]}",
        research_id=manifest["research"]["id"],
    )
    return {
        "report": str(destination),
        "manifest": str(sidecar),
        "report_sha256": manifest["report_sha256"],
        "content_sha256": manifest["content_sha256"],
        "graph_sha256": manifest["graph_sha256"],
    }


def _load_manifest(sidecar: Path) -> dict:
    """Read a manifest and refuse an unknown schema."""
    if not sidecar.is_file():
        raise EngineError(
            f"manifest not found: {sidecar}",
            "a generated report is only verifiable together with its manifest.",
            "regenerate it with `report REF --out PATH`, then commit both files.",
        )
    try:
        stored = json.loads(sidecar.read_text(encoding="utf-8"))
    except ValueError as error:
        raise EngineError(
            f"manifest is not valid JSON: {sidecar}",
            f"{error}",
            "regenerate the report to rebuild the manifest.",
        ) from error
    if stored.get("schema") != REPORT_SCHEMA:
        raise EngineError(
            f"unsupported manifest schema: {stored.get('schema')}",
            f"this build reads {REPORT_SCHEMA} only.",
            "regenerate the report with this engine version.",
        )
    return stored


def check_report(
    conn: sqlite3.Connection, research_ref: str, path: Path, strict: bool = False
) -> dict:
    """Compare a committed report and its manifest with the current graph.

    The default comparison is semantic: it ignores run allocation artefacts, so re-verifying an
    unchanged test does not report drift. `strict` also compares the exact record digest, which
    changes whenever a run is recorded.
    """
    sidecar = manifest_path(path)
    stored = _load_manifest(sidecar)
    current_research = get_research(conn, research_ref)
    reported_id = str((stored.get("research") or {}).get("id", ""))
    drift: List[str] = []
    if reported_id != current_research.id:
        drift.append(f"research {reported_id or 'missing'} != {current_research.id}")

    current_content = content_sha256(conn, current_research.id)
    if current_content != stored.get("content_sha256"):
        drift.append("graph content changed since the report was generated")

    current_graph = graph_sha256(conn, current_research.id)
    if strict and current_graph != stored.get("graph_sha256"):
        drift.append("record set changed since the report was generated (strict)")

    current_text = report(conn, current_research.id)
    current_report = digest("report/1", current_text)
    if current_report != stored.get("report_sha256"):
        drift.append("rendered report changed since it was generated")

    if stored.get("license") != license_block():
        drift.append("license terms changed since the report was generated")

    current_counts = research_counts(conn, current_research.id)
    if stored.get("counts") != current_counts:
        drift.append("record counts changed since the report was generated")

    return {
        "manifest": str(sidecar),
        "clean": not drift,
        "strict": bool(strict),
        "drift": drift,
        "content_sha256": current_content,
        "graph_sha256": current_graph,
        "report_sha256": current_report,
        "generated_at": stored.get("generated_at"),
    }
