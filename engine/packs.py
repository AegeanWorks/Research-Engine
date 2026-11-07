"""Domain-pack registry: declared boundaries, never cross-domain imports.

A pack is a self-contained research domain that exposes a public API and keeps its data outside
the host database. The registry records the pack version, the engine API it targets, the external
data root and an optional digest of its manifest. It does not import the pack.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from typing import List

from engine.artifacts import utc_now
from engine.database import transaction
from engine.errors import EngineError, NotFound

PACK_API_VERSION = "engine/v1"
PACK_STATUSES = ("registered", "disabled")
_NAME = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
_DIGEST = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class Pack:
    name: str
    version: str
    api_version: str
    data_root: str
    manifest_sha256: str
    status: str
    registered_at: str


def _to_pack(row: sqlite3.Row) -> Pack:
    return Pack(**{key: row[key] for key in Pack.__dataclass_fields__})


def register_pack(
    conn: sqlite3.Connection,
    name: str,
    version: str,
    api_version: str = PACK_API_VERSION,
    data_root: str = "",
    manifest_sha256: str = "",
    status: str = "registered",
) -> Pack:
    """Register one domain pack; the name is the isolation boundary."""
    name = str(name).strip()
    if not _NAME.match(name):
        raise EngineError(
            f"invalid pack name: {name!r}",
            "a pack name is a lowercase identifier of 2-64 characters.",
            "use a name such as fluid_universe or pnn.",
        )
    version = str(version).strip()
    if not version:
        raise EngineError(
            "pack version is empty",
            "a registered pack must name the version it exposes.",
            "pass a version such as 1.0.0.",
        )
    if api_version != PACK_API_VERSION:
        raise EngineError(
            f"unknown pack API version: {api_version}",
            f"packs may use only the public host API {PACK_API_VERSION}.",
            "pass the API version the pack was tested against.",
        )
    if status not in PACK_STATUSES:
        raise EngineError(
            f"unknown pack status: {status}",
            f"allowed statuses are {', '.join(PACK_STATUSES)}.",
            "pass registered or disabled.",
        )
    digest = str(manifest_sha256).strip().lower()
    if digest and not _DIGEST.match(digest):
        raise EngineError(
            f"invalid manifest digest: {manifest_sha256!r}",
            "a manifest digest is a lowercase SHA-256 hex string.",
            "pass the 64-character digest of the pack manifest, or leave it empty.",
        )
    record = Pack(
        name=name,
        version=version,
        api_version=api_version,
        data_root=str(data_root).strip(),
        manifest_sha256=digest,
        status=status,
        registered_at=utc_now(),
    )
    with transaction(conn):
        try:
            conn.execute(
                "INSERT INTO domain_pack(name, version, api_version, data_root,"
                " manifest_sha256, status, registered_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    record.name,
                    record.version,
                    record.api_version,
                    record.data_root,
                    record.manifest_sha256,
                    record.status,
                    record.registered_at,
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise EngineError(
                f"pack already registered: {name}",
                "a pack name is stable; replacing it would hide a contract change.",
                "register a new version under a new name, or inspect the existing pack.",
            ) from exc
    return record


def get_pack(conn: sqlite3.Connection, name: str) -> Pack:
    row = conn.execute("SELECT * FROM domain_pack WHERE name = ?", (name,)).fetchone()
    if row is None:
        raise NotFound("domain pack", name)
    return _to_pack(row)


def list_packs(conn: sqlite3.Connection) -> List[Pack]:
    rows = conn.execute("SELECT * FROM domain_pack ORDER BY name").fetchall()
    return [_to_pack(row) for row in rows]


def set_pack_status(conn: sqlite3.Connection, name: str, status: str) -> Pack:
    """Enable or disable a pack without deleting its registration."""
    if status not in PACK_STATUSES:
        raise EngineError(
            f"unknown pack status: {status}",
            f"allowed statuses are {', '.join(PACK_STATUSES)}.",
            "pass registered or disabled.",
        )
    with transaction(conn):
        result = conn.execute(
            "UPDATE domain_pack SET status = ? WHERE name = ?", (status, name)
        )
        if result.rowcount == 0:
            raise NotFound("domain pack", name)
    return get_pack(conn, name)
