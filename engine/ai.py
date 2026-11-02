"""AI provenance adapter: notarize model I/O, ingest UNVERIFIED claims, propose template tests.

AI output is a hypothesis source, never evidence. Every AI artifact is tagged at
birth (model id, prompt hash, output hash, cited sources): no tag, no entry.
This module never calls `set_verdict`, `invalidate`, `retract`, `merge` or
`record_outcome`; promotions and collapses stay operator-invoked through the
same kill-test gates as human claims.

The engine core makes no network calls. Model execution happens outside the
engine (a local model run by the operator); this module only notarizes the
prompt/output bytes as hashes, so raw payloads never enter the database or the
repository. The external-API adapter is a stub that refuses: this build is
local-only, and the data boundary (hashes in, raw text out) holds by code.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from typing import List, Optional, Sequence

from engine.artifacts import sha256_text, utc_now
from engine.claims import add_claim, get_claim, link_to_question
from engine.database import next_id, transaction
from engine.errors import EngineError, NotFound
from engine.events import record as record_event
from engine.hypotheses import add_hypothesis
from engine.killtests import add_test
from engine.models import AI_KINDS, AIArtifact
from engine.researches import get_research

# Fixed deterministic probes an AI test proposal may use. Free-form shell from a
# model is refused: _run_once executes through a shell, so model-supplied
# commands would be arbitrary code execution at `test run` time. Per-claim kill
# tests with real discriminating power remain researcher-authored.
TEMPLATES = {
    "constant-probe": {
        "command": (
            '"' + sys.executable + '" -c "print(\'ai-probe:constant\')"'
        ),
        "control_command": (
            '"' + sys.executable + '" -c "import sys;'
            ' print(\'ai-probe:control-diverged\'); sys.exit(2)"'
        ),
        "expect_exit": 0,
    },
}

_CLAIM_KINDS_FOR_ARTIFACT = {
    "extraction": ("empirical", "derived"),
    "idea": ("derived", "assumption", "speculation"),
}

_DRAFT_LIMITS = (
    "AI output is a hypothesis source, never evidence.",
    "Article text is guilty until the kill tests clear it: only PROVEN and NUMERIC"
    " claims appear above; everything else is withheld below with its status.",
    "A receipt names the verified run group behind each surviving claim.",
)


def actor_for(model_id: str) -> str:
    """Attribution for AI-proximate actions: the model, not the default agent."""
    return f"model:{model_id.strip()}"


def _to_artifact(row: sqlite3.Row) -> AIArtifact:
    return AIArtifact(**{key: row[key] for key in AIArtifact.__dataclass_fields__})


def _validate_cited(cited: Sequence[dict]) -> str:
    """Check citation shape only; existence is enforced at ingest and by AI-001."""
    normalized = []
    for entry in cited:
        if not isinstance(entry, dict):
            raise EngineError(
                "AI citation is not an object",
                "each cited source must name a source_id and a locator.",
                'pass --cited \'[{"source_id": "s_000001", "locator": "p. 3"}]\'.',
            )
        source_id = str(entry.get("source_id", "")).strip()
        locator = str(entry.get("locator", "")).strip()
        if not source_id or not locator:
            raise EngineError(
                "AI citation lacks a source_id or locator",
                "a citation without both cannot be resolved or audited.",
                'pass --cited \'[{"source_id": "s_000001", "locator": "p. 3"}]\'.',
            )
        normalized.append({"source_id": source_id, "locator": locator})
    return json.dumps(normalized, sort_keys=True)


def record_artifact(
    conn: sqlite3.Connection,
    research_ref: str,
    kind: str,
    model_id: str,
    prompt_text: str,
    output_text: str,
    cited: Sequence[dict] = (),
) -> AIArtifact:
    """Notarize one model invocation: hashes in, raw text never stored."""
    research = get_research(conn, research_ref)
    if kind not in AI_KINDS:
        raise EngineError(
            f"unknown AI artifact kind: {kind}",
            f"allowed kinds are {', '.join(AI_KINDS)}.",
            "pass one of the listed kinds.",
        )
    if not model_id.strip():
        raise EngineError(
            "AI artifact has no model id",
            "provenance must name which model produced the output.",
            "pass --model such as local:qwen2.5-coder-1.5b-hf.",
        )
    if not prompt_text.strip() or not output_text.strip():
        raise EngineError(
            "AI artifact has empty prompt or output",
            "a hash of nothing proves nothing.",
            "pass the exact prompt and output bytes that were exchanged.",
        )
    with transaction(conn):
        record = AIArtifact(
            id=next_id(conn, "a"),
            research_id=research.id,
            kind=kind,
            model_id=model_id.strip(),
            prompt_sha256=sha256_text(prompt_text),
            output_sha256=sha256_text(output_text),
            cited_json=_validate_cited(cited),
            actor=actor_for(model_id),
            created_at=utc_now(),
        )
        conn.execute(
            "INSERT INTO ai_artifact(id, research_id, kind, model_id, prompt_sha256,"
            " output_sha256, cited_json, actor, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                record.id,
                record.research_id,
                record.kind,
                record.model_id,
                record.prompt_sha256,
                record.output_sha256,
                record.cited_json,
                record.actor,
                record.created_at,
            ),
        )
        record_event(
            conn,
            "ai.record",
            record.id,
            f"{kind} by {record.model_id} prompt={record.prompt_sha256[:16]}"
            f" output={record.output_sha256[:16]}",
            research_id=research.id,
            actor=record.actor,
        )
    return record


def get_artifact(conn: sqlite3.Connection, ref: str) -> AIArtifact:
    """Fetch one AI artifact by identifier."""
    row = conn.execute("SELECT * FROM ai_artifact WHERE id = ?", (ref,)).fetchone()
    if row is None:
        raise NotFound("ai_artifact", ref)
    return _to_artifact(row)


def list_artifacts(
    conn: sqlite3.Connection, research_ref: str | None = None
) -> List[AIArtifact]:
    """List AI artifacts, optionally filtered by program."""
    if research_ref:
        research = get_research(conn, research_ref)
        rows = conn.execute(
            "SELECT * FROM ai_artifact WHERE research_id = ? ORDER BY id",
            (research.id,),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM ai_artifact ORDER BY id").fetchall()
    return [_to_artifact(row) for row in rows]


def ingest_claim(
    conn: sqlite3.Connection,
    artifact_ref: str,
    text: str,
    kind: str,
    source_ref: Optional[str] = None,
    quote: str = "",
    locator: str = "",
    confidence: float = 0.5,
    kill_test: str = "",
    basis: str = "",
    prerequisites: Sequence[str] = (),
    question_ref: Optional[str] = None,
    stance: str = "supports",
    actor: str = "agent",
) -> object:
    """Enter one AI-proposed claim as UNVERIFIED, or refuse it loudly.

    No tag, no entry: the artifact must exist first. A failed ingest records an
    `ai.reject` event on the artifact and re-raises, so the fabricated run is
    flagged even though the claim never enters the graph.
    """
    artifact = get_artifact(conn, artifact_ref)
    allowed = _CLAIM_KINDS_FOR_ARTIFACT.get(artifact.kind, ())
    if kind not in allowed:
        raise EngineError(
            f"kind {kind} cannot come from a {artifact.kind} artifact",
            f"a {artifact.kind} artifact may propose {', '.join(allowed) or 'nothing'}.",
            "record an artifact of the matching kind first.",
        )
    try:
        with transaction(conn):
            claim = add_claim(
                conn,
                artifact.research_id,
                text,
                kind,
                source_ref=source_ref,
                quote=quote,
                locator=locator,
                confidence=confidence,
                kill_test=kill_test,
                basis=basis,
                prerequisites=prerequisites,
            )
            if question_ref:
                link_to_question(conn, claim.id, question_ref, stance)
            conn.execute(
                "UPDATE ai_artifact SET claim_id = ? WHERE id = ?",
                (claim.id, artifact.id),
            )
            record_event(
                conn,
                "ai.ingest",
                claim.id,
                f"{artifact.id} -> {claim.id} ({kind}, UNVERIFIED)",
                research_id=artifact.research_id,
                actor=actor,
            )
    except EngineError as error:
        with transaction(conn):
            record_event(
                conn,
                "ai.reject",
                artifact.id,
                f"ingest refused: {error}",
                research_id=artifact.research_id,
                actor=actor,
            )
        raise
    return get_claim(conn, claim.id)


def ingest_hypothesis(
    conn: sqlite3.Connection,
    artifact_ref: str,
    statement: str,
    criterion: str,
    confidence: float = 0.5,
    question_ref: Optional[str] = None,
    actor: str = "agent",
) -> object:
    """Pre-register one AI-proposed hypothesis from an idea artifact."""
    artifact = get_artifact(conn, artifact_ref)
    if artifact.kind != "idea":
        raise EngineError(
            f"a hypothesis cannot come from a {artifact.kind} artifact",
            "hypotheses are new ideas, pre-registered before any test.",
            "record an idea artifact first.",
        )
    with transaction(conn):
        hypothesis = add_hypothesis(
            conn,
            artifact.research_id,
            statement,
            criterion,
            confidence,
            question_ref,
        )
        conn.execute(
            "UPDATE ai_artifact SET hypothesis_id = ? WHERE id = ?",
            (hypothesis.id, artifact.id),
        )
        record_event(
            conn,
            "ai.ingest",
            hypothesis.id,
            f"{artifact.id} -> {hypothesis.id} (hypothesis, PREREGISTERED)",
            research_id=artifact.research_id,
            actor=actor,
        )
    return hypothesis


def propose_test(
    conn: sqlite3.Connection,
    artifact_ref: str,
    template: str,
    name: str,
    claim_ref: Optional[str] = None,
    hypothesis_ref: Optional[str] = None,
    actor: str = "agent",
) -> object:
    """Bind a fixed-template kill test to a claim or hypothesis.

    Only named templates are accepted; free-form model-supplied shell is
    refused. Creating the row is safe — running it stays the operator's act.
    """
    artifact = get_artifact(conn, artifact_ref)
    spec = TEMPLATES.get(template)
    if spec is None:
        raise EngineError(
            f"unknown test template: {template}",
            "AI-proposed kill tests come from a fixed template list, never from"
            " free-form model text.",
            f"pass one of: {', '.join(sorted(TEMPLATES))}.",
        )
    with transaction(conn):
        test = add_test(
            conn,
            artifact.research_id,
            name,
            spec["command"],
            claim_ref=claim_ref,
            hypothesis_ref=hypothesis_ref,
            expect_exit=spec["expect_exit"],
            control_command=spec["control_command"],
        )
        conn.execute(
            "UPDATE ai_artifact SET test_id = ? WHERE id = ?",
            (test.id, artifact.id),
        )
        record_event(
            conn,
            "ai.test",
            test.id,
            f"{artifact.id} proposed {template} as {test.id}",
            research_id=artifact.research_id,
            actor=actor,
        )
    return test


def fetch_external(*args: object, **kwargs: object) -> object:
    """Refusing stub for the external-API adapter: this build is local-only."""
    raise EngineError(
        "external AI fetch is not enabled in this build",
        "no model payload may leave the box until an explicit, logged external"
        " adapter with key hygiene is reviewed and enabled.",
        "run the model locally and notarize its I/O with `ai sweep`.",
    )


def render_draft(conn: sqlite3.Connection, research_ref: str) -> str:
    """Assemble an article draft from surviving claims only. Never upgrades a verdict.

    Refuses when the program has error-level findings. Every established claim
    carries its kill-test receipt; everything else is withheld with its status.
    """
    from engine import integrity
    from engine.evidence import claim_groups

    research = get_research(conn, research_ref)
    findings = integrity.findings_for_research(conn, research.id)
    if integrity.has_errors(findings):
        raise EngineError(
            f"draft refused: {research.id} has error-level findings",
            "an article cannot be assembled over a failing gate.",
            "resolve `check` errors first, then re-render the draft.",
        )
    from engine.bundle import content_sha256, graph_sha256
    from engine.claims import list_claims
    from engine.markdown import sanitize

    lines = [
        f"# Article draft: {research.title}",
        "",
        "**Status:** DRAFT — guilty until the kill tests clear it. This text makes no"
        " claim beyond what the receipts below establish.",
        f"**Program:** `{research.id}` (`{research.slug}`)",
        f"**Scope:** {research.scope or '-'}",
        f"**Graph:** content `{content_sha256(conn, research.id)}`",
        f"**Graph (exact):** `{graph_sha256(conn, research.id)}`",
        f"**Integrity:** {sum(1 for f in findings if f.severity == 'error')} error(s),"
        f" {sum(1 for f in findings if f.severity == 'warning')} warning(s).",
        "",
        "## Established claims",
    ]
    heads = list_claims(conn, research.id)
    established = [c for c in heads if c.status in ("PROVEN", "NUMERIC")]
    withheld = [c for c in heads if c.status not in ("PROVEN", "NUMERIC")]
    for claim in established:
        if claim.status == "NUMERIC":
            row = conn.execute(
                "SELECT evidence_group FROM verdict WHERE subject_kind = 'claim'"
                " AND subject_id = ? AND status = 'NUMERIC' ORDER BY id DESC LIMIT 1",
                (claim.id,),
            ).fetchone()
            receipt = f"group {row['evidence_group']}" if row else "no cited group"
        else:
            groups = claim_groups(conn, claim.id)
            receipt = f"group {groups[0]}" if groups else "argument only, no executable run"
        provenance = (
            f"quote at {claim.locator} (source {claim.source_id})"
            if claim.kind == "empirical"
            else (claim.basis or "derived")
        )
        lines.append(
            f"- [{claim.id} | {claim.status} | {receipt}] {sanitize(claim.text)}"
            f" — {sanitize(provenance)}"
        )
    if not established:
        lines.append("none: no claim has survived its kill tests yet.")
    lines += ["", "## Withheld: not established"]
    for claim in withheld:
        lines.append(f"- [{claim.id} | {claim.status}] {sanitize(claim.text)}")
    if not withheld:
        lines.append("none withheld.")
    lines += ["", "## Questions"]
    for question in conn.execute(
        "SELECT * FROM question WHERE research_id = ? ORDER BY id", (research.id,)
    ).fetchall():
        lines.append(f"- [{question['id']}] {question['text']}")
    lines += ["", "## Limits"]
    lines += [f"- {limit}" for limit in _DRAFT_LIMITS]
    return "\n".join(lines) + "\n"
