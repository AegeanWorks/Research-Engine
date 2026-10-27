"""Command-line surface: one entry point for every engine mechanic."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Callable, Dict, List

from engine import __version__
from engine.analysis import (
    claim_statistics,
    claim_trend,
    contradictions,
    evidence_matrix,
    expose,
    keystone_claims,
    unlinked_contradictions,
)
from engine.bundle import export_jsonl, verify_export
from engine.cascade import invalidate, preview, retract_source
from engine.claims import (
    add_claim,
    get_claim,
    link_claims,
    link_to_question,
    list_claims,
    set_verdict,
)
from engine.context import DEFAULT_BUDGET, brief, claim_brief, outline
from engine.database import SCHEMA_VERSION, connect, initialize
from engine.diffing import diff_files, render as render_diff
from engine.demo import seed_demo
from engine.errors import EngineError
from engine.hypotheses import (
    add_hypothesis,
    get_hypothesis,
    list_hypotheses,
    preregistration_card,
    record_outcome,
)
from engine.integrity import check, has_errors, render_json, render_markdown
from engine.killtests import add_test, list_runs, list_tests, run_test, verify_test
from engine.questions import add_question, close_question, get_question, list_questions
from engine.researches import create_research, get_research, list_researches, research_counts
from engine.screening import prisma_flow, set_screening
from engine.sources import add_source, list_sources, set_source_status
from engine.events import list_events
from engine.maintenance import backup, integrity_check
from engine.manifest import check_report, write_report
from engine.observations import (
    add_observation,
    list_observations,
    void_observation,
)
from engine.merging import merge_claims
from engine.synthesis import claim_detail, inventory, report, scorecard
from engine.provenance import provenance


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m engine",
        description="Falsification-first research engine: provenance, pre-registration, kill tests.",
    )
    parser.add_argument("--db", default="research.db", help="SQLite database path (default: research.db)")
    parser.add_argument("--json", action="store_true", help="print stable JSON instead of text")
    parser.add_argument("--version", action="version", version=f"research-engine {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("init", help="create the database schema")
    commands.add_parser("demo", help="seed a synthetic program that exercises every mechanic")
    commands.add_parser("check", help="audit provenance, evidence and dependency integrity")
    commands.add_parser("inventory", help="show engine-wide counts")

    research = commands.add_parser("research", help="manage research programs")
    research_sub = research.add_subparsers(dest="action", required=True)
    add_r = research_sub.add_parser("add", help="create a research program")
    add_r.add_argument("title")
    add_r.add_argument("--scope", default="")
    add_r.add_argument("--slug")
    research_sub.add_parser("list", help="list research programs")
    show_r = research_sub.add_parser("show", help="show one program with counts")
    show_r.add_argument("ref")

    question = commands.add_parser("question", help="manage research questions")
    question_sub = question.add_subparsers(dest="action", required=True)
    add_q = question_sub.add_parser("add", help="add a question")
    add_q.add_argument("research")
    add_q.add_argument("text")
    list_q = question_sub.add_parser("list", help="list questions")
    list_q.add_argument("--research")
    close_q = question_sub.add_parser("close", help="close a question")
    close_q.add_argument("ref")

    source = commands.add_parser("source", help="manage bibliographic sources")
    source_sub = source.add_subparsers(dest="action", required=True)
    add_s = source_sub.add_parser("add", help="register a source")
    add_s.add_argument("research")
    add_s.add_argument("--title", required=True)
    add_s.add_argument("--year", type=int)
    add_s.add_argument("--doi", default="")
    add_s.add_argument("--url", default="")
    add_s.add_argument("--authors", default="")
    add_s.add_argument("--kind", default="paper")
    list_s = source_sub.add_parser("list", help="list sources")
    list_s.add_argument("--research")
    status_s = source_sub.add_parser("status", help="record a source's evidence status")
    status_s.add_argument("ref")
    status_s.add_argument("--status", required=True)
    status_s.add_argument("--note", default="")
    retract_s = source_sub.add_parser("retract", help="retract a source and retire its claims")
    retract_s.add_argument("ref")
    retract_s.add_argument("--reason", required=True)
    retract_s.add_argument("--evidence", required=True)
    screen_s = source_sub.add_parser("screen", help="record a screening decision")
    screen_s.add_argument("ref")
    screen_s.add_argument("--status", required=True)
    screen_s.add_argument("--reason", default="")
    prisma_s = source_sub.add_parser("prisma", help="show the screening flow")
    prisma_s.add_argument("--research")

    observation = commands.add_parser("observation", help="record and retire measurements")
    observation_sub = observation.add_subparsers(dest="action", required=True)
    add_o = observation_sub.add_parser("add", help="record one measurement")
    add_o.add_argument("claim")
    add_o.add_argument("--group", required=True)
    add_o.add_argument("--value", type=float, required=True)
    add_o.add_argument("--note", default="")
    list_o = observation_sub.add_parser("list", help="list measurements of a claim")
    list_o.add_argument("claim")
    list_o.add_argument("--group")
    list_o.add_argument("--include-voided", action="store_true")
    void_o = observation_sub.add_parser("void", help="retire a measurement with a reason")
    void_o.add_argument("ref")
    void_o.add_argument("--reason", required=True)

    claim = commands.add_parser("claim", help="manage claims and verdicts")
    claim_sub = claim.add_subparsers(dest="action", required=True)
    add_c = claim_sub.add_parser("add", help="record a claim")
    add_c.add_argument("research")
    add_c.add_argument("--text", required=True)
    add_c.add_argument("--kind", required=True)
    add_c.add_argument("--source")
    add_c.add_argument("--quote", default="")
    add_c.add_argument("--locator", default="")
    add_c.add_argument("--confidence", type=float, default=0.5)
    add_c.add_argument("--kill-test", default="")
    add_c.add_argument("--basis", default="")
    add_c.add_argument("--from", dest="prerequisites", action="append", default=[])
    list_c = claim_sub.add_parser("list", help="list claims")
    list_c.add_argument("--research")
    list_c.add_argument("--status")
    show_c = claim_sub.add_parser("show", help="show one claim in full")
    show_c.add_argument("ref")
    link_c = claim_sub.add_parser("link", help="link two claims")
    link_c.add_argument("src")
    link_c.add_argument("dst")
    link_c.add_argument("--rel", required=True)
    link_q = claim_sub.add_parser("link-question", help="attach a claim to a question")
    link_q.add_argument("claim")
    link_q.add_argument("question")
    link_q.add_argument("--stance", required=True)
    verdict_c = claim_sub.add_parser("verdict", help="record an evidence-backed verdict")
    verdict_c.add_argument("ref")
    verdict_c.add_argument("--status", required=True)
    verdict_c.add_argument("--evidence", required=True)
    verdict_c.add_argument("--note", default="")
    verdict_c.add_argument("--group", dest="evidence_group", default="",
                           help="the verified run group a NUMERIC verdict cites")
    merge_c = claim_sub.add_parser("merge", help="merge duplicates into one survivor")
    merge_c.add_argument("keep")
    merge_c.add_argument("duplicates", nargs="+")
    merge_c.add_argument("--note", default="")
    context_c = claim_sub.add_parser("context", help="token-budgeted view of one claim")
    context_c.add_argument("ref")
    context_c.add_argument("--budget", type=int, default=DEFAULT_BUDGET)
    inv_c = claim_sub.add_parser("invalidate", help="collapse a claim and every dependent")
    inv_c.add_argument("ref")
    inv_c.add_argument("--status", required=True, choices=("FALSIFIED", "RETRACTED"))
    inv_c.add_argument("--reason", required=True)
    inv_c.add_argument("--evidence", required=True)

    hypothesis = commands.add_parser("hypothesis", help="pre-register hypotheses and record outcomes")
    hypothesis_sub = hypothesis.add_subparsers(dest="action", required=True)
    add_h = hypothesis_sub.add_parser("add", help="pre-register a hypothesis")
    add_h.add_argument("research")
    add_h.add_argument("--statement", required=True)
    add_h.add_argument("--criterion", required=True)
    add_h.add_argument("--confidence", type=float, default=0.5)
    add_h.add_argument("--question")
    list_h = hypothesis_sub.add_parser("list", help="list hypotheses")
    list_h.add_argument("--research")
    outcome_h = hypothesis_sub.add_parser("outcome", help="record an outcome")
    outcome_h.add_argument("ref")
    outcome_h.add_argument("--status", required=True)
    outcome_h.add_argument("--evidence", required=True)
    outcome_h.add_argument("--note", default="")
    card_h = hypothesis_sub.add_parser("card", help="render the pre-registration card")
    card_h.add_argument("ref")

    test = commands.add_parser("test", help="manage executable kill tests")
    test_sub = test.add_subparsers(dest="action", required=True)
    add_t = test_sub.add_parser("add", help="bind a command to a claim or hypothesis")
    add_t.add_argument("research")
    add_t.add_argument("--name", required=True)
    add_t.add_argument("--command", dest="shell_command", required=True)
    add_t.add_argument("--claim")
    add_t.add_argument("--hypothesis")
    add_t.add_argument("--expect-exit", type=int, default=0)
    add_t.add_argument("--timeout", type=int, default=120)
    add_t.add_argument("--input", dest="inputs", action="append", default=[],
                       help="a file whose content the test depends on; repeatable")
    add_t.add_argument("--control", dest="control_command", default="",
                       help="a negative control that must fail for the test to be falsifiable")
    list_t = test_sub.add_parser("list", help="list kill tests")
    list_t.add_argument("--research")
    run_t = test_sub.add_parser("run", help="run a test one or more times")
    run_t.add_argument("ref")
    run_t.add_argument("--runs", type=int, default=1)
    verify_t = test_sub.add_parser("verify", help="run a test twice and require agreement")
    verify_t.add_argument("ref")
    runs_t = test_sub.add_parser("runs", help="list recent runs")
    runs_t.add_argument("ref", nargs="?")
    runs_t.add_argument("--limit", type=int, default=20)

    cascade = commands.add_parser("cascade", help="preview a transitive invalidation")
    cascade_sub = cascade.add_subparsers(dest="action", required=True)
    preview_c = cascade_sub.add_parser("preview", help="show dependents without writing")
    preview_c.add_argument("ref")

    report_c = commands.add_parser("report", help="generate a research report and its manifest")
    report_c.add_argument("ref")
    report_output = report_c.add_mutually_exclusive_group()
    report_output.add_argument("--out", help="write the report and report.manifest.json atomically")
    report_output.add_argument("--check", metavar="PATH",
                               help="verify a committed report against the current graph")
    report_c.add_argument("--strict", action="store_true",
                          help="with --check, also compare the exact record digest")
    outline_c = commands.add_parser("outline", help="token-budgeted index of a program")
    outline_c.add_argument("ref")
    outline_c.add_argument("--budget", type=int, default=DEFAULT_BUDGET)
    brief_c = commands.add_parser("brief", help="token-budgeted per-question evidence view")
    brief_c.add_argument("ref")
    brief_c.add_argument("--budget", type=int, default=DEFAULT_BUDGET)

    analysis_c = commands.add_parser("analysis", help="discovery and ranking over the graph")
    analysis_sub = analysis_c.add_subparsers(dest="action", required=True)
    contradictions_c = analysis_sub.add_parser("contradictions", help="rank support/contradict pairs")
    contradictions_c.add_argument("ref")
    contradictions_c.add_argument("--min-score", type=float, default=0.0)
    contradictions_c.add_argument("--unlinked", action="store_true",
                                  help="propose pairs that have no contradicts edge yet")
    matrix_c = analysis_sub.add_parser("matrix", help="source x question coverage matrix")
    matrix_c.add_argument("ref")
    keystone_c = analysis_sub.add_parser("keystone", help="claims the graph leans on")
    keystone_c.add_argument("ref")
    keystone_c.add_argument("--limit", type=int, default=10)
    expose_c = analysis_sub.add_parser("expose", help="what a claim would take down")
    stats_c = analysis_sub.add_parser("stats", help="compare two observation groups of a claim")
    stats_c.add_argument("claim")
    stats_c.add_argument("--baseline", required=True)
    stats_c.add_argument("--treatment", required=True)
    stats_c.add_argument("--seed", type=int, default=0)
    stats_c.add_argument("--resamples", type=int, default=2000)
    trend_c = analysis_sub.add_parser("trend", help="fit a trend over one observation group")
    trend_c.add_argument("claim")
    trend_c.add_argument("--group", required=True)
    expose_c.add_argument("ref")

    db_c = commands.add_parser("db", help="database maintenance")
    db_sub = db_c.add_subparsers(dest="action", required=True)
    db_sub.add_parser("integrity", help="run SQLite integrity and foreign-key checks")
    db_backup = db_sub.add_parser("backup", help="write a verified copy of the database")
    db_backup.add_argument("path")

    events_c = commands.add_parser("events", help="list recorded events, newest first")
    events_c.add_argument("--research")
    events_c.add_argument("--kind")
    events_c.add_argument("--limit", type=int, default=50)

    diff_c = commands.add_parser("diff", help="compare two exported snapshots")
    diff_c.add_argument("old")
    diff_c.add_argument("new")
    diff_c.add_argument("--exact", action="store_true", help="also compare run bookkeeping")

    score_c = commands.add_parser("scorecard", help="generate a one-line-per-claim scorecard")
    score_c.add_argument("ref")
    export_c = commands.add_parser("export", help="export the graph as JSONL")
    export_c.add_argument("path")
    export_c.add_argument("--research")
    export_c.add_argument("--check", action="store_true",
                          help="verify an existing snapshot instead of writing one")
    return parser


def _emit(payload, as_json: bool, text: str) -> int:
    if as_json:
        if hasattr(payload, "__dataclass_fields__"):
            payload = asdict(payload)
        elif isinstance(payload, list):
            payload = [
                asdict(item) if hasattr(item, "__dataclass_fields__") else dict(item)
                for item in payload
            ]
        print(json.dumps(payload, indent=2, sort_keys=True, default=str))
    else:
        print(text, end="" if text.endswith("\n") else "\n")
    return 0


def _records_payload(rows) -> list:
    return [dict(row) if not hasattr(row, "__dataclass_fields__") else asdict(row) for row in rows]


def _cmd_research(conn: sqlite3.Connection, args) -> int:
    if args.action == "add":
        record = create_research(conn, args.title, args.scope, args.slug)
        return _emit(record, args.json, f"{record.id} {record.slug} {record.title}\n")
    if args.action == "list":
        records = list_researches(conn)
        text = "".join(f"{r.id}  {r.slug:<24} {r.title}\n" for r in records) or "no research programs\n"
        return _emit(_records_payload(records), args.json, text)
    record = get_research(conn, args.ref)
    counts = research_counts(conn, record.id)
    text = (
        f"{record.id}  {record.slug}\n{record.title}\nscope: {record.scope or '-'}\n"
        f"created: {record.created_at}\n"
        + "".join(f"{key}: {value}\n" for key, value in counts.items())
    )
    return _emit({"research": asdict(record), "counts": counts}, args.json, text)


def _cmd_question(conn: sqlite3.Connection, args) -> int:
    if args.action == "add":
        record = add_question(conn, args.research, args.text)
        return _emit(record, args.json, f"{record.id} {record.text}\n")
    if args.action == "close":
        record = close_question(conn, args.ref)
        return _emit(record, args.json, f"{record.id} closed\n")
    records = list_questions(conn, args.research)
    text = "".join(f"{q.id}  {q.status:<7} {q.text}\n" for q in records) or "no questions\n"
    return _emit(_records_payload(records), args.json, text)


def _cmd_source(conn: sqlite3.Connection, args) -> int:
    if args.action == "add":
        record = add_source(
            conn,
            args.research,
            args.title,
            year=args.year,
            doi=args.doi,
            url=args.url,
            authors=args.authors,
            kind=args.kind,
        )
        return _emit(record, args.json, f"{record.id} {record.title}\n")
    if args.action == "status":
        record = set_source_status(conn, args.ref, args.status, args.note)
        return _emit(record, args.json, f"{record.id} -> {record.status}\n")
    if args.action == "retract":
        result = retract_source(conn, args.ref, args.reason, args.evidence)
        text = f"{result['source']} -> retracted\n"
        for item in result["affected"]:
            text += f"  {item['id']} {item['previous_status']} -> RETRACTED"
            if item["cascade"]:
                text += " (invalidated: " + ", ".join(item["cascade"]) + ")"
            text += "\n"
        return _emit(result, args.json, text)
    if args.action == "screen":
        record = set_screening(conn, args.ref, args.status, args.reason)
        detail = f" ({record.screening_reason})" if record.screening_reason else ""
        return _emit(record, args.json, f"{record.id} -> {record.screening}{detail}\n")
    if args.action == "prisma":
        flow = prisma_flow(conn, getattr(args, "research", None))
        text = "".join(f"{key}: {value}\n" for key, value in flow["counts"].items())
        if flow["reasons"]:
            text += "reasons: " + ", ".join(
                f"{name}={count}" for name, count in flow["reasons"].items()
            ) + "\n"
        text += f"included fraction: {flow['included_fraction']:.2%}\n"
        return _emit(flow, args.json, text)
    records = list_sources(conn, args.research)
    text = "".join(
        f"{s.id}  {s.year or '----'}  {s.status:<20} {s.screening:<12} {s.title}\n"
        for s in records
    ) or "no sources\n"
    return _emit(_records_payload(records), args.json, text)


def _cmd_observation(conn: sqlite3.Connection, args) -> int:
    if args.action == "add":
        record = add_observation(conn, args.claim, args.group, args.value, args.note)
        return _emit(record, args.json, f"{record.id} {record.group_label}={record.value}\n")
    if args.action == "void":
        record = void_observation(conn, args.ref, args.reason)
        return _emit(record, args.json, f"{record.id} voided\n")
    records = list_observations(conn, args.claim, args.group, args.include_voided)
    text = "".join(
        f"{o.id}  {o.group_label:<12} {o.value:12.6g}  {o.at}"
        + ("  VOIDED" if o.voided else "") + "\n"
        for o in records
    ) or "no observations\n"
    return _emit(_records_payload(records), args.json, text)


def _cmd_claim(conn: sqlite3.Connection, args) -> int:
    if args.action == "add":
        record = add_claim(
            conn,
            args.research,
            args.text,
            args.kind,
            source_ref=args.source,
            quote=args.quote,
            locator=args.locator,
            confidence=args.confidence,
            kill_test=args.kill_test,
            basis=args.basis,
            prerequisites=args.prerequisites,
        )
        return _emit(record, args.json, f"{record.id} {record.status} {record.text}\n")
    if args.action == "show":
        return _emit(get_claim(conn, args.ref), args.json, claim_detail(conn, args.ref))
    if args.action == "link":
        edge_id = link_claims(conn, args.src, args.dst, args.rel)
        return _emit({"edge": edge_id}, args.json, f"{edge_id} {args.rel}\n")
    if args.action == "link-question":
        edge_id = link_to_question(conn, args.claim, args.question, args.stance)
        return _emit({"edge": edge_id}, args.json, f"{edge_id} {args.stance}\n")
    if args.action == "verdict":
        record = set_verdict(
            conn, args.ref, args.status, args.evidence, args.note,
            evidence_group=args.evidence_group,
        )
        return _emit(record, args.json, f"{record.id} -> {record.status}\n")
    if args.action == "merge":
        result = merge_claims(conn, args.keep, args.duplicates, args.note)
        text = f"kept {result['keep']}\n"
        for claim_id in result["retired"]:
            text += f"  retired {claim_id}\n"
        text += f"  edges repointed: {len(result['edges_repointed'])}\n"
        return _emit(result, args.json, text)
    if args.action == "context":
        view = claim_brief(conn, args.ref, args.budget)
        return _emit(view.to_dict(), args.json, view.text)
    if args.action == "invalidate":
        result = invalidate(conn, args.ref, args.status, args.reason, args.evidence)
        text = f"{result['root']} -> {result['status']}\n"
        for item in result["affected"]:
            text += f"  {item['id']} depth {item['depth']} ({item['previous_status']} -> INVALIDATED)\n"
        return _emit(result, args.json, text)
    records = list_claims(conn, args.research, args.status)
    text = "".join(
        f"{c.id}  {c.status:<11} {c.confidence:.2f}  {c.text}\n" for c in records
    ) or "no claims\n"
    return _emit(_records_payload(records), args.json, text)


def _cmd_hypothesis(conn: sqlite3.Connection, args) -> int:
    if args.action == "add":
        record = add_hypothesis(
            conn, args.research, args.statement, args.criterion, args.confidence, args.question
        )
        return _emit(record, args.json, f"{record.id} {record.status} {record.statement}\n")
    if args.action == "outcome":
        record = record_outcome(conn, args.ref, args.status, args.evidence, args.note)
        return _emit(record, args.json, f"{record.id} -> {record.status}\n")
    if args.action == "card":
        return _emit({"card": preregistration_card(conn, args.ref)}, args.json,
                     preregistration_card(conn, args.ref))
    records = list_hypotheses(conn, args.research)
    text = "".join(
        f"{h.id}  {h.status:<13} {h.confidence:.2f}  {h.statement}\n" for h in records
    ) or "no hypotheses\n"
    return _emit(_records_payload(records), args.json, text)


def _cmd_test(conn: sqlite3.Connection, args) -> int:
    if args.action == "add":
        record = add_test(
            conn,
            args.research,
            args.name,
            args.shell_command,
            claim_ref=args.claim,
            hypothesis_ref=args.hypothesis,
            expect_exit=args.expect_exit,
            timeout_seconds=args.timeout,
            inputs=args.inputs,
            control_command=args.control_command,
        )
        return _emit(record, args.json, f"{record.id} {record.name}\n")
    if args.action in ("run", "verify"):
        result = verify_test(conn, args.ref) if args.action == "verify" else run_test(conn, args.ref, args.runs)
        text = (
            f"{result['test']} {'PASS' if result['passed'] else 'FAIL'} "
            f"(reproducible: {result['reproducible']}, group {result['run_group']})\n"
        )
        if result["control_declared"]:
            state = "falsified" if result["control_falsified"] else "DID NOT FAIL"
            text += f"  control: {state}\n"
        else:
            text += "  control: none (vacuity not excluded)\n"
        if result["workspace_changed_during_runs"]:
            text += "  warning: the workspace changed while the test was running\n"
        for run in result["runs"]:
            text += f"  {run['run_tag']}  exit {run['exit_code']}  {run['duration_ms']} ms\n"
        _emit(result, args.json, text)
        return 0 if result["passed"] else 1
    if args.action == "runs":
        records = list_runs(conn, args.ref, args.limit)
        text = "".join(
            f"{r.id}  {r.test_id}  {r.run_tag}  {'PASS' if r.passed else 'FAIL'}"
            f"  exit {r.exit_code}  code {r.code_sha256[:8]}\n"
            for r in records
        ) or "no runs\n"
        return _emit(_records_payload(records), args.json, text)
    records = list_tests(conn, args.research)
    text = "".join(
        f"{t.id}  {t.claim_id or t.hypothesis_id}  {t.name}  `{t.command}`\n" for t in records
    ) or "no tests\n"
    return _emit(_records_payload(records), args.json, text)


def main(argv: List[str] | None = None) -> int:
    """Parse one command, open the database, and dispatch it."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        conn = connect(args.db)
        try:
            migration = initialize(conn)
            if migration:
                print(
                    f"notice: database upgraded from schema {migration['migrated_from']} to"
                    f" {migration['migrated_to']}; {migration['unbound_numeric_claims']}"
                    " numeric claim(s) have no bound evidence group (see `check`).",
                    file=sys.stderr,
                )
            if args.command == "init":
                payload = {
                    "database": str(args.db),
                    "schema": SCHEMA_VERSION,
                    "migration": migration,
                }
                return _emit(payload, args.json,
                             f"initialized {args.db} (schema {SCHEMA_VERSION})\n")
            if args.command == "demo":
                result = seed_demo(conn)
                return _emit(result, args.json, json.dumps(result, indent=2, sort_keys=True) + "\n")
            if args.command == "inventory":
                counts = inventory(conn)
                payload = {"counts": counts, "provenance": provenance()}
                text = "".join(f"{key}: {value}\n" for key, value in counts.items())
                commit = payload["provenance"]["git_commit"][:12]
                text += f"engine code: {payload['provenance']['code_sha256'][:16]}\n"
                text += f"git: {commit} (dirty: {payload['provenance']['git_dirty']})\n"
                return _emit(payload, args.json, text)
            if args.command == "check":
                findings = check(conn)
                text = render_markdown(findings)
                if args.json:
                    print(render_json(findings))
                else:
                    print(text, end="")
                return 1 if has_errors(findings) else 0
            if args.command == "outline":
                view = outline(conn, args.ref, args.budget)
                return _emit(view.to_dict(), args.json, view.text)
            if args.command == "brief":
                view = brief(conn, args.ref, args.budget)
                return _emit(view.to_dict(), args.json, view.text)
            if args.command == "db":
                if args.action == "integrity":
                    result = integrity_check(conn)
                    counts = "".join(
                        f"  {key}: {value}\n" for key, value in result["counts"].items()
                    )
                    text = (
                        f"integrity: {', '.join(result['integrity'])}\n"
                        f"foreign keys: {len(result['foreign_key_violations'])} violation(s)\n"
                        f"schema: {result['schema_version']}/{result['expected_schema_version']}\n"
                        f"journal: {result['journal_mode']}\n" + counts
                    )
                    _emit(result, args.json, text)
                    return 0 if result["ok"] else 1
                result = backup(conn, Path(args.path))
                text = f"backup: {result['path']} ({result['bytes']} bytes, verified)\n"
                return _emit(result, args.json, text)
            if args.command == "events":
                records = list_events(conn, args.research, args.kind, args.limit)
                text = "".join(
                    f"{e.at}  {e.kind:<18} {e.subject:<14} {e.detail}\n" for e in records
                ) or "no events\n"
                return _emit(_records_payload(records), args.json, text)
            if args.command == "diff":
                result = diff_files(Path(args.old), Path(args.new), semantic=not args.exact)
                _emit(result, args.json, render_diff(result))
                return 0 if result["identical"] else 1
            if args.command == "analysis":
                if args.action == "contradictions":
                    if args.unlinked:
                        result = unlinked_contradictions(conn, args.ref)
                        text = "".join(
                            f"{item['left']} <> {item['right']} score {item['score']:.2f}\n"
                            for item in result
                        ) or "no unlinked contradictions\n"
                        return _emit(result, args.json, text)
                    result = contradictions(conn, args.ref, args.min_score)
                    text = "".join(
                        f"Q {item['question']} + {item['support']} - {item['contradicts']}"
                        f" score {item['score']:.2f}\n"
                        for item in result
                    ) or "no contradictions\n"
                    return _emit(result, args.json, text)
                if args.action == "matrix":
                    result = evidence_matrix(conn, args.ref)
                    header = "source " + " ".join(result["questions"]) + " total\n"
                    body = "".join(
                        f"{row['source']} " + " ".join(str(cell) for cell in row["cells"])
                        + f" {row['total']}\n"
                        for row in result["rows"]
                    )
                    return _emit(result, args.json, header + body)
                if args.action == "keystone":
                    result = keystone_claims(conn, args.ref, args.limit)
                    text = "".join(
                        f"{item['claim']} weight {item['weight']} dependents {item['dependents']}"
                        f" depth {item['max_depth']} [{item['status']}]\n"
                        for item in result
                    ) or "no claims\n"
                    return _emit(result, args.json, text)
                if args.action == "trend":
                    result = claim_trend(conn, args.claim, args.group)
                    text = (
                        f"{result['claim']} {result['group']} n={result['n']}"
                        f"  slope={result['slope']:+.6g}  r={result['r']:.3f}"
                        f"  p={result['p']:.4g}\n"
                    )
                    for warning in result["warnings"]:
                        text += f"  warning: {warning}\n"
                    return _emit(result, args.json, text)
                if args.action == "stats":
                    result = claim_statistics(
                        conn, args.claim, args.baseline, args.treatment,
                        seed=args.seed, resamples=args.resamples,
                    )
                    text = (
                        f"{result['claim']} {result['baseline_label']} -> {result['treatment_label']}"
                        f"  n={result['baseline']['n']}/{result['treatment']['n']}\n"
                        f"  difference {result['difference']:+.6g}"
                        f"  d={result['cohens_d']:.3f}\n"
                        f"  welch p={result['welch']['p']:.4g}"
                        f"  mwu p={result['mann_whitney']['p']:.4g}"
                        f" ({result['mann_whitney']['method']})\n"
                        f"  bootstrap 95% [{result['bootstrap']['low']:+.6g},"
                        f" {result['bootstrap']['high']:+.6g}]"
                        f" seed={result['bootstrap']['seed']}\n"
                        f"  significant={result['significant']}"
                        f" agree={result['tests_agree']}\n"
                    )
                    for warning in result["warnings"]:
                        text += f"  warning: {warning}\n"
                    return _emit(result, args.json, text)
                result = expose(conn, args.ref)
                text = f"{result['claim']} [{result['status']}]\n"
                for item in result["dependents"]:
                    text += f"  dependent {item['id']} depth {item['depth']}\n"
                for item in result["inbound"]:
                    text += f"  inbound {item['rel']} {item['src_kind']}:{item['src_id']}\n"
                return _emit(result, args.json, text)
            if args.command == "cascade":
                result = preview(conn, args.ref)
                text = f"{result['root']} ({result['root_status']})\n"
                for item in result["affected"]:
                    text += f"  {item['id']} depth {item['depth']} {item['status']} {item['text']}\n"
                return _emit(result, args.json, text)
            if args.command == "report":
                if args.check:
                    result = check_report(conn, args.ref, Path(args.check), strict=args.strict)
                    text = (
                        f"clean: {result['clean']} ({result['manifest']})"
                        f"{' [strict]' if result['strict'] else ''}\n"
                        + "".join(f"  drift: {item}\n" for item in result["drift"])
                    )
                    _emit(result, args.json, text)
                    return 0 if result["clean"] else 1
                if args.out:
                    result = write_report(conn, args.ref, Path(args.out))
                    text = (
                        f"wrote {result['report']}\nwrote {result['manifest']}\n"
                        f"graph: {result['graph_sha256'][:16]}\n"
                    )
                    return _emit(result, args.json, text)
                return _emit({"report": report(conn, args.ref)}, args.json, report(conn, args.ref))
            if args.command == "scorecard":
                return _emit({"scorecard": scorecard(conn, args.ref)}, args.json, scorecard(conn, args.ref))
            if args.command == "export":
                if args.check and args.research:
                    raise EngineError(
                        "--research cannot be combined with --check",
                        "verification reads the snapshot's own scope; filtering it would be"
                        " misleading.",
                        "drop --research when checking a file.",
                    )
                if args.check:
                    result = verify_export(Path(args.path))
                    text = (
                        f"intact: {result['ok']} ({result['path']})\n"
                        f"  records: {result['records']}\n"
                        f"  digest: {result['digest'][:16]}\n"
                    )
                    if not result["counts_match"]:
                        text += f"  count mismatch: meta says {result['recorded_records']}\n"
                    _emit(result, args.json, text)
                    return 0 if result["ok"] and result["counts_match"] else 1
                counts = export_jsonl(conn, Path(args.path), args.research)
                text = f"exported {sum(counts.values())} records to {args.path}\n"
                return _emit(counts, args.json, text)
            handlers: Dict[str, Callable] = {
                "research": _cmd_research,
                "question": _cmd_question,
                "source": _cmd_source,
                "claim": _cmd_claim,
                "hypothesis": _cmd_hypothesis,
                "observation": _cmd_observation,
                "test": _cmd_test,
            }
            return handlers[args.command](conn, args)
        finally:
            conn.close()
    except EngineError as error:
        print(error.render(), file=sys.stderr)
        return 1
