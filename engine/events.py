"""Append-only event log for actions that are not verdicts.

Verdicts and invalidations already record themselves. Everything else that changes the meaning of
the record — a source losing its status, a duplicate being merged, a report being generated, a
schema being migrated — needs one place a reviewer can scan in order.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import List, Optional

from engine.artifacts import utc_now
from engine.database import next_id, transaction
from engine.errors import EngineError, NotFound


@dataclass(frozen=True)
class Event:
    id: str
    at: str
    research_id: str
    kind: str
    subject: str
    detail: str
    actor: str
    seq: int = 0
    root_id: str = ""
    parent_id: str = ""


def _to_event(row: sqlite3.Row) -> Event:
    return Event(**{key: row[key] for key in Event.__dataclass_fields__})


def record(
    conn: sqlite3.Connection,
    kind: str,
    subject: str,
    detail: str = "",
    research_id: str = "",
    actor: str = "agent",
    parent_id: str = "",
) -> Event:
    """Append one event. Callers run inside their own write transaction.

    A parent links this event into a causal tree; the parent must already exist in the same
    research program. The sequence is allocated per program inside the writer transaction.
    """
    with transaction(conn):
        event_id = next_id(conn, "ev")
        parent_id = parent_id.strip()
        root_id = event_id
        if parent_id:
            parent = conn.execute(
                "SELECT * FROM event WHERE id = ?", (parent_id,)
            ).fetchone()
            if parent is None:
                raise EngineError(
                    f"parent event not found: {parent_id}",
                    "a nested event must name an event that already exists.",
                    "record the parent first, then pass its id as --parent.",
                )
            if str(parent["research_id"]) != research_id:
                raise EngineError(
                    "parent event belongs to another research program",
                    "a causal tree cannot cross a program boundary.",
                    "use a parent in the same program, or omit the parent.",
                )
            root_id = str(parent["root_id"]) or str(parent["id"])
        row = conn.execute(
            "SELECT COALESCE(MAX(seq), 0) + 1 AS next_seq FROM event WHERE research_id = ?",
            (research_id,),
        ).fetchone()
        event = Event(
            id=event_id,
            at=utc_now(),
            research_id=research_id,
            kind=kind.strip(),
            subject=subject.strip(),
            detail="".join(
                character if character.isprintable() or character == " " else " "
                for character in detail
            ).strip()[:2000],
            actor=actor,
            seq=int(row["next_seq"]),
            root_id=root_id,
            parent_id=parent_id,
        )
        conn.execute(
            "INSERT INTO event(id, at, research_id, kind, subject, detail, actor, seq, root_id,"
            " parent_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                event.id,
                event.at,
                event.research_id,
                event.kind,
                event.subject,
                event.detail,
                event.actor,
                event.seq,
                event.root_id,
                event.parent_id,
            ),
        )
    return event


def list_events(
    conn: sqlite3.Connection,
    research_ref: Optional[str] = None,
    kind: Optional[str] = None,
    limit: int = 50,
) -> List[Event]:
    """Recent events, newest first, optionally filtered by program and kind."""
    from engine.researches import get_research

    clauses: List[str] = []
    params: List[object] = []
    if research_ref:
        clauses.append("research_id = ?")
        params.append(get_research(conn, research_ref).id)
    if kind:
        clauses.append("kind = ?")
        params.append(kind.strip())
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = conn.execute(
        f"SELECT * FROM event{where} ORDER BY id DESC LIMIT ?", (*params, max(int(limit), 1))
    ).fetchall()
    return [_to_event(row) for row in rows]


def count(conn: sqlite3.Connection) -> int:
    """Total recorded events."""
    return int(conn.execute("SELECT COUNT(*) AS n FROM event").fetchone()["n"])


def _one_event(conn: sqlite3.Connection, ref: str) -> Event:
    row = conn.execute("SELECT * FROM event WHERE id = ?", (ref,)).fetchone()
    if row is None:
        raise NotFound("event", ref)
    return _to_event(row)


def event_path(conn: sqlite3.Connection, ref: str) -> List[Event]:
    """The causal chain from the root event to one event, root first."""
    event = _one_event(conn, ref)
    chain = [event]
    seen = {event.id}
    while event.parent_id:
        parent = _one_event(conn, event.parent_id)
        if parent.id in seen:
            raise EngineError(
                "event parent cycle",
                f"the chain revisits {parent.id}, so it cannot be ordered.",
                "repair the parent links before rendering the path.",
            )
        chain.insert(0, parent)
        seen.add(parent.id)
        event = parent
    return chain


def event_tree(conn: sqlite3.Connection, ref: str) -> List[dict]:
    """A root event and its descendants, breadth-first with a depth per event."""
    root = _one_event(conn, ref)
    if root.root_id and root.root_id != root.id:
        raise EngineError(
            f"event {root.id} is not a root",
            f"its root is {root.root_id}.",
            f"run `events --tree {root.root_id}` instead.",
        )
    if not root.root_id:
        return [{"depth": 0, "event": root}]
    rows = conn.execute(
        "SELECT * FROM event WHERE root_id = ? ORDER BY seq, id", (root.root_id,)
    ).fetchall()
    children: dict[str, List[Event]] = {}
    for row in rows:
        event = _to_event(row)
        if event.id == root.id:
            continue
        children.setdefault(event.parent_id, []).append(event)
    tree: List[dict] = []
    queue = [(0, root)]
    seen = {root.id}
    while queue:
        depth, event = queue.pop(0)
        tree.append({"depth": depth, "event": event})
        for child in children.get(event.id, []):
            if child.id in seen:
                continue
            seen.add(child.id)
            queue.append((depth + 1, child))
    return tree
