"""Migration harness for lattice and N1 source databases.

Inspection is read-only and records the SHA-256 of the source file. Applying a snapshot writes
host rows inside one transaction and records the run in ``migration_run`` keyed by
``(source, source_digest)`` so the same snapshot cannot be imported twice. Source databases are
never opened for writing.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Optional

from engine.artifacts import utc_now
from engine.claims import add_claim
from engine.database import next_id, transaction
from engine.errors import EngineError
from engine.models import (
    CLAIM_QUESTION_RELATIONS,
    SCREENING_REASONS,
    SCREENING_STATUSES,
    SOURCE_KINDS,
)
from engine.questions import add_question, close_question
from engine.researches import get_research
from engine.screening import TERMINAL_OUT, set_screening
from engine.sources import add_source
from experiments.models import (
    add_event,
    add_intervention,
    add_metric,
    add_metric_definition,
)

_LATTICE_TABLES = ("papers", "claims", "questions", "edges", "screening")
_N1_TABLES = ("interventions", "metric_definitions", "metrics", "events")
_RESEARCH_TABLES = (
    "research",
    "source",
    "question",
    "claim",
    "hypothesis",
    "killtest",
    "test_run",
    "verdict",
    "observation",
    "event",
    "analysis_plan",
    "amendment",
    "experiment_intervention",
    "experiment_metric",
    "experiment_event",
    "domain_pack",
    "migration_run",
)


@dataclass(frozen=True)
class MigrationReport:
    """What one inspection or application observed and inserted."""

    source: str
    source_digest: str
    target_research: str
    tables: Dict[str, int] = field(default_factory=dict)
    inserted: Dict[str, int] = field(default_factory=dict)
    skipped: Dict[str, int] = field(default_factory=dict)
    dry_run: bool = False
    warnings: tuple = ()

    def as_dict(self) -> dict:
        return {
            "source": self.source,
            "source_digest": self.source_digest,
            "target_research": self.target_research,
            "tables": dict(self.tables),
            "inserted": dict(self.inserted),
            "skipped": dict(self.skipped),
            "dry_run": self.dry_run,
            "warnings": list(self.warnings),
        }


def _file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    # hygiene: allow binary read, text encoding does not apply
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_only(path: Path | str) -> sqlite3.Connection:
    """Open a source database with SQLite's read-only URI mode."""
    source = Path(path)
    if not source.is_file():
        raise EngineError(
            f"source database does not exist: {source}",
            "the migration harness reads a committed source snapshot.",
            "pass the path of an existing SQLite database file.",
        )
    conn = sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _table_count(conn: sqlite3.Connection, table: str) -> int:
    exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)
    ).fetchone()
    if exists is None:
        return 0
    return int(conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"])


def _inspect(path: Path | str, source: str, tables: tuple) -> MigrationReport:
    source_path = Path(path)
    conn = _read_only(source_path)
    try:
        counts = {table: _table_count(conn, table) for table in tables}
    finally:
        conn.close()
    return MigrationReport(
        source=source,
        source_digest=_file_digest(source_path),
        target_research="",
        tables=counts,
        dry_run=True,
    )


def inspect_lattice(path: Path | str) -> MigrationReport:
    """Describe a lattice database without writing to it."""
    return _inspect(path, "lattice", _LATTICE_TABLES)


def inspect_n1(path: Path | str) -> MigrationReport:
    """Describe an N1 database without writing to it."""
    return _inspect(path, "n1", _N1_TABLES)


def inspect_research(path: Path | str) -> MigrationReport:
    """Describe a host research database without writing to it."""
    report = _inspect(path, "research", _RESEARCH_TABLES)
    conn = _read_only(path)
    try:
        row = conn.execute("SELECT version FROM schema_meta").fetchone()
        version = int(row["version"]) if row is not None else None
    except sqlite3.Error:
        version = None
    finally:
        conn.close()
    tables = dict(report.tables)
    if version is not None:
        tables["schema_version"] = version
    return MigrationReport(
        source=report.source,
        source_digest=report.source_digest,
        target_research="",
        tables=tables,
        dry_run=True,
    )


def inspect_tree(
    path: Path | str,
    source: str,
    suffixes: tuple = (".json", ".md", ".csv", ".svg", ".txt"),
    excluded_dirs: tuple = (".git", "__pycache__", ".pytest_cache", "node_modules"),
) -> MigrationReport:
    """Fingerprint a source tree and count files by suffix."""
    root = Path(path)
    if not root.exists():
        raise EngineError(
            f"source tree does not exist: {root}",
            "the readiness check reads an existing committed tree.",
            "pass the path of the source checkout or fixture directory.",
        )
    counts = {suffix: 0 for suffix in suffixes}
    total = 0
    digest = hashlib.sha256()
    for file_path in sorted(root.rglob("*")):
        if not file_path.is_file():
            continue
        relative = file_path.relative_to(root)
        if any(part in excluded_dirs for part in relative.parts):
            continue
        suffix = file_path.suffix.lower()
        if suffixes and suffix not in suffixes:
            continue
        total += 1
        counts[suffix] += 1
        digest.update(relative.as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_path.read_bytes())
        digest.update(b"\0")
    if total == 0:
        raise EngineError(
            f"no matching files under {root}",
            "an empty manifest would hide missing evidence.",
            "check the suffixes and the source path.",
        )
    return MigrationReport(
        source=source,
        source_digest=digest.hexdigest(),
        target_research="",
        tables={"files": total, **{key: value for key, value in counts.items() if value}},
        dry_run=True,
    )


def inspect_obezite(path: Path | str) -> MigrationReport:
    """Describe the obezite Markdown claim ledger without writing to it."""
    ledger = Path(path)
    if not ledger.is_file():
        raise EngineError(
            f"obezite ledger does not exist: {ledger}",
            "the readiness check reads the canonical claim ledger.",
            "pass the path of 02_LITERATUR/iddia-defteri.md.",
        )
    claims = 0
    backfill = 0
    verified = 0
    for line in ledger.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| **"):
            continue
        text = line.strip()
        if text.startswith("|"):
            text = text[1:]
        if text.endswith("|"):
            text = text[:-1]
        cells = text.replace("\\|", "\x00").split("|")
        if len(cells) < 8:
            continue
        claims += 1
        verdict = cells[6].replace("\x00", "|").lower()
        if "backfill" in verdict:
            backfill += 1
        else:
            verified += 1
    return MigrationReport(
        source="obezite",
        source_digest=_file_digest(ledger),
        target_research="",
        tables={"claim": claims, "verified": verified, "backfill": backfill},
        dry_run=True,
    )


def applied_migrations(conn: sqlite3.Connection) -> list:
    """List migration runs in application order."""
    return conn.execute(
        "SELECT * FROM migration_run ORDER BY applied_at, id"
    ).fetchall()


def _refuse_repeat(conn: sqlite3.Connection, source: str, digest: str) -> None:
    row = conn.execute(
        "SELECT id FROM migration_run WHERE source = ? AND source_digest = ?",
        (source, digest),
    ).fetchone()
    if row is not None:
        raise EngineError(
            f"{source} snapshot already migrated: {digest[:12]}…",
            "re-importing one snapshot would duplicate its records.",
            "inspect the source again, or migrate a new snapshot.",
        )


def _year(value) -> Optional[int]:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        number = int(text)
    except ValueError:
        return None
    return number if 1000 <= number <= 9999 else None


def _text(value) -> str:
    return str(value or "").strip()


def _claim_kind(row: sqlite3.Row) -> str:
    return "empirical"


def _as_date(value) -> str:
    text = _text(value)
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError:
        try:
            return datetime.fromisoformat(text).date().isoformat()
        except ValueError as exc:
            raise EngineError(
                f"source date is not ISO-8601: {value!r}",
                "experiment windows compare calendar dates exactly.",
                "repair the source row or migrate a corrected snapshot.",
            ) from exc


def _as_timestamp(value) -> str:
    text = _text(value)
    try:
        datetime.fromisoformat(text)
    except ValueError as exc:
        raise EngineError(
            f"source timestamp is not ISO-8601: {value!r}",
            "an event needs an exact time so its order is auditable.",
            "repair the source row or migrate a corrected snapshot.",
        ) from exc
    return text


def _lattice_rows(path: Path | str) -> dict:
    conn = _read_only(path)
    try:
        return {
            "papers": conn.execute("SELECT * FROM papers ORDER BY id").fetchall(),
            "claims": conn.execute("SELECT * FROM claims ORDER BY id").fetchall(),
            "questions": conn.execute("SELECT * FROM questions ORDER BY id").fetchall(),
            "edges": conn.execute("SELECT * FROM edges ORDER BY id").fetchall(),
            "screening": conn.execute("SELECT * FROM screening").fetchall(),
        }
    finally:
        conn.close()


def _n1_rows(path: Path | str) -> dict:
    conn = _read_only(path)
    try:
        return {
            "interventions": conn.execute("SELECT * FROM interventions ORDER BY id").fetchall(),
            "metric_definitions": conn.execute(
                "SELECT * FROM metric_definitions ORDER BY id"
            ).fetchall(),
            "metrics": conn.execute("SELECT * FROM metrics ORDER BY id").fetchall(),
            "events": conn.execute("SELECT * FROM events ORDER BY id").fetchall(),
        }
    finally:
        conn.close()


def _lattice_screening(screening_rows) -> dict:
    decisions = {}
    for row in screening_rows:
        paper_id = _text(row["paper_id"])
        status = _text(row["status"]).lower()
        if paper_id:
            decisions[paper_id] = (status, _text(row["reason"]).lower(), _text(row["notes"]))
    return decisions


def _record_migration(
    conn: sqlite3.Connection,
    report: MigrationReport,
    mapping: dict,
) -> None:
    payload = report.as_dict()
    payload["mapping"] = mapping
    conn.execute(
        "INSERT INTO migration_run(id, source, source_digest, target_research,"
        " applied_at, report_json) VALUES (?, ?, ?, ?, ?, ?)",
        (
            next_id(conn, "mr"),
            report.source,
            report.source_digest,
            report.target_research,
            utc_now(),
            json.dumps(payload, sort_keys=True),
        ),
    )


def migrate_lattice(
    conn: sqlite3.Connection,
    research_ref: str,
    path: Path | str,
    dry_run: bool = False,
) -> MigrationReport:
    """Import a lattice snapshot into one host program without touching the source."""
    research = get_research(conn, research_ref)
    inspected = inspect_lattice(path)
    if dry_run:
        return MigrationReport(
            source=inspected.source,
            source_digest=inspected.source_digest,
            target_research=research.id,
            tables=inspected.tables,
            inserted={},
            dry_run=True,
        )
    _refuse_repeat(conn, inspected.source, inspected.source_digest)
    data = _lattice_rows(path)
    decisions = _lattice_screening(data["screening"])
    inserted = {"source": 0, "claim": 0, "question": 0, "edge": 0}
    skipped = {"edge": 0}
    warnings = []
    source_map: Dict[str, str] = {}
    claim_map: Dict[str, str] = {}
    question_map: Dict[str, str] = {}
    with transaction(conn):
        for row in data["papers"]:
            kind = _text(row["kind"]) or "paper"
            if kind not in SOURCE_KINDS:
                warnings.append(f"paper {row['id']}: unknown kind {kind!r} recorded as paper")
                kind = "paper"
            year = _year(row["year"])
            doi = _text(row["doi"])
            url = _text(row["url"])
            if not doi and not url and year is None:
                url = f"lattice://paper/{_text(row['id'])}"
            source = add_source(
                conn,
                research.id,
                _text(row["title"]) or f"lattice paper {_text(row['id'])}",
                year=year,
                doi=doi,
                url=url,
                authors=_text(row["authors"]),
                kind=kind,
                arxiv=_text(row["arxiv"]),
                venue=_text(row["venue"]),
                abstract=_text(row["abstract"]),
                tags=_text(row["tags"]),
                study_type=_text(row["study_type"]),
            )
            source_map[_text(row["id"])] = source.id
            inserted["source"] += 1
            decision = decisions.get(_text(row["id"]))
            if decision:
                status, reason, _notes = decision
                if status in SCREENING_STATUSES and status != "identified":
                    if status in TERMINAL_OUT and reason not in SCREENING_REASONS:
                        reason = "other"
                    if reason and reason not in SCREENING_REASONS:
                        reason = ""
                    set_screening(conn, source.id, status, reason=reason, actor="migration")
                elif status not in SCREENING_STATUSES:
                    warnings.append(
                        f"paper {row['id']}: unknown screening {status!r} left as identified"
                    )
        for row in data["questions"]:
            text = _text(row["text"])
            question = add_question(conn, research.id, text or f"lattice question {row['id']}")
            question_map[_text(row["id"])] = question.id
            inserted["question"] += 1
            if _text(row["status"]).lower() in ("answered", "abandoned", "closed"):
                close_question(conn, question.id)
        for row in data["claims"]:
            paper_id = _text(row["paper_id"])
            source_id = source_map.get(paper_id)
            if source_id is None:
                raise EngineError(
                    f"lattice claim {row['id']} cites an unknown paper {paper_id!r}",
                    "a migrated claim must keep its source provenance.",
                    "repair the source snapshot before migrating it.",
                )
            quote = _text(row["quote"])
            locator = _text(row["locator"]) or f"lattice claim {_text(row['id'])}"
            claim = add_claim(
                conn,
                research.id,
                _text(row["text"]) or f"lattice claim {_text(row['id'])}",
                _claim_kind(row),
                source_ref=source_id,
                quote=quote or _text(row["text"]),
                locator=locator,
                confidence=float(row["confidence"]),
                basis="migrated from lattice",
            )
            claim_map[_text(row["id"])] = claim.id
            inserted["claim"] += 1
        for row in data["edges"]:
            src = claim_map.get(_text(row["src"]))
            dst = question_map.get(_text(row["dst"]))
            rel = _text(row["kind"])
            if src is not None and dst is not None and rel in CLAIM_QUESTION_RELATIONS:
                edge_id = next_id(conn, "e")
                conn.execute(
                    "INSERT OR IGNORE INTO edge(id, src_kind, src_id, dst_kind, dst_id,"
                    " rel, created_at) VALUES (?, 'claim', ?, 'question', ?, ?, ?)",
                    (edge_id, src, dst, rel, utc_now()),
                )
                inserted["edge"] += 1
            else:
                skipped["edge"] += 1
    report = MigrationReport(
        source=inspected.source,
        source_digest=inspected.source_digest,
        target_research=research.id,
        tables=inspected.tables,
        inserted=inserted,
        skipped=skipped,
        warnings=tuple(warnings),
    )
    with transaction(conn):
        _record_migration(
            conn,
            report,
            {
                "papers": source_map,
                "claims": claim_map,
                "questions": question_map,
            },
        )
    return report


def migrate_n1(
    conn: sqlite3.Connection,
    research_ref: str,
    path: Path | str,
    dry_run: bool = False,
) -> MigrationReport:
    """Import an N1 snapshot into one host program without touching the source."""
    research = get_research(conn, research_ref)
    inspected = inspect_n1(path)
    if dry_run:
        return MigrationReport(
            source=inspected.source,
            source_digest=inspected.source_digest,
            target_research=research.id,
            tables=inspected.tables,
            inserted={},
            dry_run=True,
        )
    _refuse_repeat(conn, inspected.source, inspected.source_digest)
    data = _n1_rows(path)
    inserted = {
        "intervention": 0,
        "metric_definition": 0,
        "metric": 0,
        "event": 0,
    }
    warnings = []
    intervention_map: Dict[int, str] = {}
    with transaction(conn):
        for row in data["interventions"]:
            record = add_intervention(
                conn,
                research.id,
                _text(row["name"]) or f"N1 intervention {row['id']}",
                _as_date(row["start_date"]),
                projected_end_date=(
                    _as_date(row["projected_end_date"])
                    if row["projected_end_date"] is not None
                    else None
                ),
                end_date=(
                    _as_date(row["end_date"]) if row["end_date"] is not None else None
                ),
                dosage=_text(row["dosage"]),
                notes=_text(row["notes"]),
            )
            intervention_map[int(row["id"])] = record.id
            inserted["intervention"] += 1
        for row in data["metric_definitions"]:
            add_metric_definition(
                conn,
                research.id,
                _text(row["name"]),
                description=_text(row["description"]),
                unit=_text(row["unit"]),
            )
            inserted["metric_definition"] += 1
        for row in data["metrics"]:
            intervention_id = row["intervention_id"]
            host_intervention = (
                intervention_map.get(int(intervention_id))
                if intervention_id is not None
                else None
            )
            add_metric(
                conn,
                research.id,
                _text(row["metric_name"]),
                _as_date(row["date"]),
                float(row["value"]),
                intervention_ref=host_intervention,
            )
            inserted["metric"] += 1
        for row in data["events"]:
            intervention_id = row["intervention_id"]
            host_intervention = (
                intervention_map.get(int(intervention_id))
                if intervention_id is not None
                else None
            )
            severity = row["severity"]
            if severity is not None and not 1 <= int(severity) <= 5:
                warnings.append(
                    f"event {row['id']}: severity {severity} outside 1..5 recorded without it"
                )
                severity = None
            add_event(
                conn,
                research.id,
                _text(row["event_name"]) or f"N1 event {row['id']}",
                _as_timestamp(row["timestamp"]),
                severity=int(severity) if severity is not None else None,
                notes=_text(row["notes"]),
                intervention_ref=host_intervention,
            )
            inserted["event"] += 1
    report = MigrationReport(
        source=inspected.source,
        source_digest=inspected.source_digest,
        target_research=research.id,
        tables=inspected.tables,
        inserted=inserted,
        warnings=tuple(warnings),
    )
    with transaction(conn):
        _record_migration(
            conn, report, {"interventions": intervention_map}
        )
    return report
