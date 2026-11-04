"""Database maintenance: integrity verification and a crash-safe backup."""

from __future__ import annotations

import contextlib
import os
import sqlite3
import tempfile
from pathlib import Path
from typing import Dict, List

from engine.artifacts import utc_now
from engine.database import SCHEMA_VERSION
from engine.errors import EngineError


def integrity_check(conn: sqlite3.Connection) -> dict:
    """Run SQLite's own checks plus a few facts a reviewer wants before archiving."""
    quick: List[str] = [str(row[0]) for row in conn.execute("PRAGMA integrity_check")]
    foreign: List[dict] = [
        dict(row) for row in conn.execute("PRAGMA foreign_key_check")
    ]
    counts: Dict[str, int] = {}
    for table in (
        "research", "source", "question", "claim", "edge", "hypothesis", "killtest",
        "test_run", "test_attempt", "verdict", "invalidation", "event",
        "observation", "protocol", "ai_artifact",
    ):
        counts[table] = int(
            conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"]
        )
    schema = conn.execute("SELECT version FROM schema_meta").fetchone()
    try:
        version = int(schema["version"]) if schema else 0
    except (TypeError, ValueError):
        version = 0
    version_ok = version == SCHEMA_VERSION
    return {
        "ok": quick == ["ok"] and not foreign and version_ok,
        "integrity": quick,
        "foreign_key_violations": foreign,
        "schema_version": version,
        "expected_schema_version": SCHEMA_VERSION,
        "journal_mode": str(conn.execute("PRAGMA journal_mode").fetchone()[0]),
        "counts": counts,
    }


def _refuse_if_exists(target: Path, because: str) -> None:
    """Refuse to clobber an existing backup target."""
    if target.exists():
        raise EngineError(
            f"backup target already exists: {target}",
            because,
            "choose a new path, or delete the old backup first.",
        )


def backup(conn: sqlite3.Connection, destination: Path) -> dict:
    """Copy the live database through SQLite's backup API and verify the copy.

    The copy is written to a temporary file in the destination directory, fsynced, verified with
    `PRAGMA integrity_check`, and only then moved into place with `os.replace`. A failed backup
    therefore leaves no partial file that looks like a valid one. The pre-existing target check
    runs again immediately before the move, so a file created during the backup is refused
    instead of overwritten; a truly concurrent creator in the remaining microsecond window
    is out of scope for a single-writer tool.
    """
    target = Path(destination)
    _refuse_if_exists(target, "an existing file is never overwritten by a backup.")
    if conn.in_transaction:
        raise EngineError(
            "the database has an open write transaction",
            "backing up mid-transaction would snapshot uncommitted state or block.",
            "commit or roll back first, then retry the backup.",
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{target.name}.tmp_", dir=str(target.parent))
    os.close(fd)
    try:
        copy = sqlite3.connect(temporary)
        try:
            conn.backup(copy)
            copy.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            verdict = str(copy.execute("PRAGMA integrity_check").fetchone()[0])
        finally:
            copy.close()
        if verdict != "ok":
            raise EngineError(
                f"backup failed its integrity check: {verdict}",
                "a copy that does not verify is not a backup.",
                "check the source database with `db integrity`, then retry.",
            )
        with open(temporary, "rb+") as handle:
            os.fsync(handle.fileno())
        _refuse_if_exists(
            target, "a file appeared at the backup path while the backup was running."
        )
        os.replace(temporary, target)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(temporary)
        raise
    return {
        "path": str(target),
        "bytes": target.stat().st_size,
        "integrity": "ok",
        "at": utc_now(),
    }
