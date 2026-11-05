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
from engine.ai import (
    TEMPLATES as AI_TEMPLATES,
)
from engine.ai import (
    get_artifact as get_ai_artifact,
)
from engine.ai import (
    ingest_claim as ingest_ai_claim,
)
from engine.ai import (
    ingest_hypothesis as ingest_ai_hypothesis,
)
from engine.ai import (
    list_artifacts as list_ai_artifacts,
)
from engine.ai import (
    propose_test as propose_ai_test,
)
from engine.ai import (
    record_artifact as record_ai_artifact,
)
from engine.ai import (
    render_draft as render_ai_draft,
)
from engine.analysis import (
    batch_statistics,
    claim_statistics,
    claim_trend,
    contradictions,
    evidence_matrix,
    expose,
    group_correlations,
    keystone_claims,
    unlinked_contradictions,
)
from engine.attempts import for_group, list_attempts
from engine.bundle import export_jsonl, verify_export
from engine.calibration import score as calibration_score
from engine.cascade import invalidate, preview, retract_source
from engine.claims import (
    add_claim,
    get_claim,
    link_claims,
    link_to_question,
    list_claims,
    revise_claim,
    revision_chain,
    set_verdict,
)
from engine.context import DEFAULT_BUDGET, brief, claim_brief, outline
from engine.database import SCHEMA_VERSION, connect, initialize
from engine.diffing import diff_files, render as render_diff
from engine.demo import seed_demo
from engine.duplicates import duplicate_sources
from engine.errors import EngineError
from engine.models import (
    AI_KINDS,
    CLAIM_CLAIM_RELATIONS,
    CLAIM_KINDS,
    CLAIM_QUESTION_RELATIONS,
    CLAIM_STATUSES,
    DEPENDENCY_RELATIONS,
    HYPOTHESIS_OUTCOMES,
    SCREENING_STATUSES,
    SOURCE_STATUSES,
)
from engine.hypotheses import (
    add_hypothesis,
    amend_hypothesis,
    get_hypothesis,
    list_hypotheses,
    preregistration_card,
    record_outcome,
)
from engine.integrity import check, has_errors, render_json, render_markdown
from engine.killtests import add_test, list_runs, list_tests, run_test, verify_test
from engine.questions import add_question, close_question, get_question, list_questions
from engine.search import KINDS as SEARCH_KINDS
from engine.search import search as search_graph
from engine.plans import add_plan
from engine.protocols import amend_protocol, list_protocols, register_protocol
from engine.researches import create_research, get_research, list_researches, research_counts
from engine.screening import prisma_flow, set_screening
from engine.sources import add_source, list_sources, set_source_status
from engine.events import event_path, event_tree, list_events, verify_ledger
from engine.maintenance import backup, integrity_check
from engine.manifest import check_report, write_report
from engine.observations import (
    CSV_TEMPLATE_HEADER,
    add_observation,
    import_observations_csv,
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
    search_c = commands.add_parser(
        "search", help="search claims, sources, questions and hypotheses"
    )
    search_c.add_argument("query")
    search_c.add_argument("--research")
    search_c.add_argument("--kind", action="append", choices=SEARCH_KINDS,
                          help="restrict to one kind; repeatable")
    search_c.add_argument("--limit", type=int, default=5,
                          help="maximum hits per kind (default: 5)")
    search_c.add_argument("--budget", type=int, default=800,
                          help="text output budget in estimated tokens (default: 800)")
    search_c.add_argument("--all", action="store_true",
                          help="include superseded claim revisions")

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
    status_s.add_argument("--status", required=True, choices=SOURCE_STATUSES)
    status_s.add_argument("--note", default="")
    retract_s = source_sub.add_parser("retract", help="retract a source and retire its claims")
    retract_s.add_argument("ref")
    retract_s.add_argument("--reason", required=True)
    retract_s.add_argument("--evidence", required=True)
    retract_s.add_argument("--allow-bulk", action="store_true",
                           help="retire more than 10 claims in one retraction")
    retract_s.add_argument("--preview-digest", default="",
                           help="refuse unless the graph still matches a cascade preview")
    screen_s = source_sub.add_parser("screen", help="record a screening decision")
    screen_s.add_argument("ref")
    screen_s.add_argument("--status", required=True, choices=SCREENING_STATUSES)
    screen_s.add_argument("--reason", default="")
    prisma_s = source_sub.add_parser("prisma", help="show the screening flow")
    prisma_s.add_argument("--research")
    duplicates_s = source_sub.add_parser("duplicates", help="find sources that share an identity")
    duplicates_s.add_argument("--research")
    duplicates_s.add_argument("--limit", type=int, default=20)

    protocol = commands.add_parser("protocol", help="manage measurement protocols")
    protocol_sub = protocol.add_subparsers(dest="action", required=True)
    add_p = protocol_sub.add_parser("add", help="register an immutable protocol id")
    add_p.add_argument("--id", required=True)
    add_p.add_argument("--measures", required=True)
    add_p.add_argument("--includes-generation", action="store_true")
    add_p.add_argument("--includes-judge", action="store_true")
    add_p.add_argument("--doc-digest", default="")
    add_p.add_argument("--doc-path", default="")
    protocol_sub.add_parser("list", help="list registered protocols")
    amend_p = protocol_sub.add_parser("amend", help="correct a protocol's measures text")
    amend_p.add_argument("ref")
    amend_p.add_argument("--measures", required=True)
    amend_p.add_argument("--reason", required=True)
    amend_p.add_argument("--actor", default="agent",
                         help="who records the amendment (default: agent)")

    observation = commands.add_parser("observation", help="record and retire measurements")
    observation_sub = observation.add_subparsers(dest="action", required=True)
    add_o = observation_sub.add_parser("add", help="record one measurement")
    add_o.add_argument("claim")
    add_o.add_argument("--group", required=True)
    add_o.add_argument("--value", type=float, required=True)
    add_o.add_argument("--note", default="")
    add_o.add_argument("--instrument-kind", default="")
    add_o.add_argument("--instrument-id", default="")
    add_o.add_argument("--instrument-digest", default="")
    add_o.add_argument("--rater-kind", default="")
    add_o.add_argument("--rater-id", default="")
    add_o.add_argument("--rater-version", default="")
    add_o.add_argument("--protocol", dest="protocol_id", default="")
    add_o.add_argument("--sample-size", type=int, default=1)
    add_o.add_argument("--aggregation", default="raw")
    add_o.add_argument("--unit", default="")
    add_o.add_argument("--provenance-class", default="unclassified")
    add_o.add_argument("--producer-path", default="")
    add_o.add_argument("--producer-digest", default="")
    list_o = observation_sub.add_parser("list", help="list measurements of a claim")
    list_o.add_argument("claim")
    list_o.add_argument("--group")
    list_o.add_argument("--include-voided", action="store_true")
    void_o = observation_sub.add_parser("void", help="retire a measurement with a reason")
    void_o.add_argument("ref")
    void_o.add_argument("--reason", required=True)
    import_o = observation_sub.add_parser(
        "import-csv", help="bulk-record measurements from a CSV file"
    )
    import_o.add_argument("claim", nargs="?", default="")
    import_o.add_argument("path", nargs="?", default="",
                          help="CSV file with group_label,value columns")
    import_o.add_argument("--template", action="store_true",
                          help="print the CSV header and exit without writing")

    claim = commands.add_parser("claim", help="manage claims and verdicts")
    claim_sub = claim.add_subparsers(dest="action", required=True)
    add_c = claim_sub.add_parser("add", help="record a claim")
    add_c.add_argument("research")
    add_c.add_argument("--text", required=True)
    add_c.add_argument("--kind", required=True, choices=CLAIM_KINDS)
    add_c.add_argument("--source")
    add_c.add_argument("--quote", default="")
    add_c.add_argument("--locator", default="")
    add_c.add_argument("--confidence", type=float, default=0.5)
    add_c.add_argument("--kill-test", default="")
    add_c.add_argument("--basis", default="")
    add_c.add_argument("--from", dest="prerequisites", action="append", default=[])
    list_c = claim_sub.add_parser("list", help="list claims")
    list_c.add_argument("--research")
    list_c.add_argument("--status", choices=CLAIM_STATUSES)
    list_c.add_argument("--history", action="store_true",
                        help="include superseded revisions")
    revise_c = claim_sub.add_parser("revise", help="append a revision and supersede the old claim")
    revise_c.add_argument("ref")
    revise_c.add_argument("--text", required=True)
    revise_c.add_argument("--reason", required=True)
    revise_c.add_argument("--source")
    revise_c.add_argument("--quote", default="")
    revise_c.add_argument("--locator", default="")
    revise_c.add_argument("--confidence", type=float, default=0.5)
    revise_c.add_argument("--kill-test", default="")
    revise_c.add_argument("--basis", default="")
    revise_c.add_argument("--from", dest="prerequisites", action="append", default=[])
    history_c = claim_sub.add_parser("history", help="show one claim's revision chain")
    history_c.add_argument("ref")
    show_c = claim_sub.add_parser("show", help="show one claim in full")
    show_c.add_argument("ref")
    link_c = claim_sub.add_parser("link", help="link two claims")
    link_c.add_argument("src")
    link_c.add_argument("dst")
    link_c.add_argument("--rel", required=True,
                        choices=CLAIM_CLAIM_RELATIONS + DEPENDENCY_RELATIONS)
    link_q = claim_sub.add_parser("link-question", help="attach a claim to a question")
    link_q.add_argument("claim")
    link_q.add_argument("question")
    link_q.add_argument("--stance", required=True, choices=CLAIM_QUESTION_RELATIONS)
    verdict_c = claim_sub.add_parser("verdict", help="record an evidence-backed verdict")
    verdict_c.add_argument("ref")
    verdict_c.add_argument("--status", required=True, choices=CLAIM_STATUSES)
    verdict_c.add_argument("--evidence", required=True)
    verdict_c.add_argument("--note", default="")
    verdict_c.add_argument("--group", dest="evidence_group", default="",
                           help="the verified run group a NUMERIC verdict cites")
    verdict_c.add_argument("--actor", default="agent",
                           help="who records the verdict (default: agent)")
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
    inv_c.add_argument("--allow-bulk", action="store_true",
                       help="retire more than 10 records in one collapse")
    inv_c.add_argument("--preview-digest", default="",
                       help="refuse unless the graph still matches a cascade preview")

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
    outcome_h.add_argument("--status", required=True, choices=HYPOTHESIS_OUTCOMES)
    outcome_h.add_argument("--evidence", required=True)
    outcome_h.add_argument("--note", default="")
    outcome_h.add_argument("--actor", default="agent",
                           help="who records the outcome (default: agent)")
    card_h = hypothesis_sub.add_parser("card", help="render the pre-registration card")
    card_h.add_argument("ref")
    amend_h = hypothesis_sub.add_parser("amend", help="correct a live preregistration")
    amend_h.add_argument("ref")
    amend_h.add_argument("--statement", default=None)
    amend_h.add_argument("--criterion", default=None)
    amend_h.add_argument("--reason", required=True)
    amend_h.add_argument("--actor", default="agent",
                         help="who records the amendment (default: agent)")

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
    attempts_t = test_sub.add_parser("attempts", help="list recorded attempts")
    attempts_t.add_argument("ref", nargs="?")
    attempts_t.add_argument("--limit", type=int, default=50)

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
    stats_c.add_argument("--allow-incomparable", action="store_true",
                         help="compare different protocols/instruments with a recorded caveat")
    stats_c.add_argument("--allow-self-reported", action="store_true",
                         help="allow a self-reported measurement with a recorded caveat")
    stats_c.add_argument("--plan", default="",
                         help="cite a preregistered analysis plan for this comparison")
    stats_all_c = analysis_sub.add_parser(
        "stats-all", help="compare one group pair across every claim in a program"
    )
    stats_all_c.add_argument("ref", help="research program to batch over")
    stats_all_c.add_argument("--baseline", required=True)
    stats_all_c.add_argument("--treatment", required=True)
    stats_all_c.add_argument("--seed", type=int, default=0)
    stats_all_c.add_argument("--resamples", type=int, default=2000)
    stats_all_c.add_argument("--allow-incomparable", action="store_true",
                         help="compare different protocols/instruments with a recorded caveat")
    stats_all_c.add_argument("--allow-self-reported", action="store_true",
                         help="allow a self-reported measurement with a recorded caveat")
    correlation_c = analysis_sub.add_parser(
        "correlation", help="advisory pairwise correlations between a claim's groups"
    )
    correlation_c.add_argument("claim")
    correlation_c.add_argument("--groups", default="",
                               help="comma-separated group labels; default is every pair")
    correlation_c.add_argument("--allow-incomparable", action="store_true",
                         help="compare different protocols/instruments with a recorded caveat")
    correlation_c.add_argument("--allow-self-reported", action="store_true",
                         help="allow a self-reported measurement with a recorded caveat")
    plan_sub = analysis_sub.add_parser("plan", help="preregister an analysis comparison")
    plan_sub.add_argument("claim")
    plan_sub.add_argument("--baseline", required=True)
    plan_sub.add_argument("--treatment", required=True)
    plan_sub.add_argument("--prediction", required=True)
    trend_c = analysis_sub.add_parser("trend", help="fit a trend over one observation group")
    trend_c.add_argument("claim")
    trend_c.add_argument("--group", required=True)
    calibration_c = analysis_sub.add_parser(
        "calibration", help="score hypothesis confidence against recorded outcomes"
    )
    calibration_c.add_argument("ref")
    calibration_c.add_argument("--min-n", type=int, default=10,
                               help="resolved count below which the score is descriptive")
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
    event_view = events_c.add_mutually_exclusive_group()
    event_view.add_argument("--tree", metavar="ROOT", help="render a causal tree from a root event")
    event_view.add_argument("--path", metavar="EVENT", help="render the root-to-event chain")
    event_view.add_argument("--verify", action="store_true", help="verify the ledger hash chain")

    diff_c = commands.add_parser("diff", help="compare two exported snapshots")
    diff_c.add_argument("old")
    diff_c.add_argument("new")
    diff_c.add_argument("--exact", action="store_true", help="also compare run bookkeeping")

    score_c = commands.add_parser("scorecard", help="generate a one-line-per-claim scorecard")
    score_c.add_argument("ref")
    ai_c = commands.add_parser(
        "ai", help="notarize model I/O and ingest UNVERIFIED AI output (local-only)")
    ai_sub = ai_c.add_subparsers(dest="action", required=True)
    sweep_c = ai_sub.add_parser("sweep", help="notarize a model invocation (any kind)")
    sweep_c.add_argument("research")
    sweep_c.add_argument("--kind", default="sweep", choices=AI_KINDS,
                         help="artifact kind: sweep, extraction, idea or draft")
    sweep_c.add_argument("--model", required=True, help="model id, e.g. local:qwen2.5-coder-1.5b-hf")
    sweep_c.add_argument("--prompt-file", required=True, help="path to the exact prompt bytes")
    sweep_c.add_argument("--output-file", required=True, help="path to the raw model output")
    sweep_c.add_argument("--cited", default="[]",
                         help="JSON list of {source_id, locator} the model cited")
    extract_c = ai_sub.add_parser("extract", help="ingest one AI-proposed claim as UNVERIFIED")
    extract_c.add_argument("--artifact", required=True)
    extract_c.add_argument("--text", required=True)
    extract_c.add_argument("--kind", required=True, choices=CLAIM_KINDS)
    extract_c.add_argument("--source")
    extract_c.add_argument("--quote", default="")
    extract_c.add_argument("--locator", default="")
    extract_c.add_argument("--confidence", type=float, default=0.5)
    extract_c.add_argument("--kill-test", default="")
    extract_c.add_argument("--basis", default="")
    extract_c.add_argument("--from", dest="prerequisites", action="append", default=[])
    extract_c.add_argument("--question")
    extract_c.add_argument("--stance", default="supports",
                           choices=CLAIM_QUESTION_RELATIONS)
    extract_c.add_argument("--actor", default="agent")
    idea_c = ai_sub.add_parser("idea", help="pre-register one AI-proposed hypothesis")
    idea_c.add_argument("--artifact", required=True)
    idea_c.add_argument("--statement", required=True)
    idea_c.add_argument("--criterion", required=True)
    idea_c.add_argument("--confidence", type=float, default=0.5)
    idea_c.add_argument("--question")
    idea_c.add_argument("--actor", default="agent")
    propose_c = ai_sub.add_parser("propose-test", help="bind a fixed-template kill test")
    propose_c.add_argument("--artifact", required=True)
    propose_c.add_argument("--template", required=True, choices=tuple(sorted(AI_TEMPLATES)),
                           help="one of the fixed templates")
    propose_c.add_argument("--name", required=True)
    propose_c.add_argument("--claim")
    propose_c.add_argument("--hypothesis")
    propose_c.add_argument("--actor", default="agent")
    draft_c = ai_sub.add_parser("draft", help="assemble an article draft from surviving claims")
    draft_c.add_argument("ref")
    draft_c.add_argument("--out", help="write the draft atomically instead of printing it")
    artifacts_c = ai_sub.add_parser("artifacts", help="list AI artifacts")
    artifacts_c.add_argument("--research")
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


def _need_budget(value: int, command: str) -> int:
    if value <= 0:
        raise EngineError(
            f"{command} budget must be positive: {value}",
            "a view needs at least one token to render its anchor line.",
            f"pass --budget 1 or more, for example `--budget 800 {command}`.",
        )
    return value


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
        result = retract_source(
            conn, args.ref, args.reason, args.evidence, allow_bulk=args.allow_bulk,
            preview_digest=args.preview_digest,
        )
        text = f"{result['source']} -> retracted\n"
        if result["siblings"]:
            text += f"  twin rows retracted: {', '.join(result['siblings'])}\n"
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
    if args.action == "duplicates":
        result = duplicate_sources(conn, args.research, args.limit)
        text = f"duplicate source groups: {result['total']} (shown {result['returned']})\n"
        for group in result["groups"]:
            text += (
                f"  [{group['reason']}] keep {group['keep']}: {group['count']} source(s)"
                f" share {group['key']}\n"
            )
            for item in group["sources"]:
                text += f"    {item['id']}  {item['year'] or '----'}  {item['title']}\n"
        return _emit(result, args.json, text)
    records = list_sources(conn, args.research)
    text = "".join(
        f"{s.id}  {s.year or '----'}  {s.status:<20} {s.screening:<12} {s.title}\n"
        for s in records
    ) or "no sources\n"
    return _emit(_records_payload(records), args.json, text)


def _cmd_protocol(conn: sqlite3.Connection, args) -> int:
    if args.action == "add":
        record = register_protocol(
            conn,
            args.id,
            args.measures,
            includes_generation=args.includes_generation,
            includes_judge=args.includes_judge,
            doc_digest=args.doc_digest,
            doc_path=args.doc_path,
        )
        return _emit(record, args.json, f"{record.id} {record.measures}\n")
    if args.action == "amend":
        record = amend_protocol(
            conn, args.ref, args.measures, args.reason, actor=args.actor,
        )
        return _emit(record, args.json, f"{record.id} amended {record.measures}\n")
    records = list_protocols(conn)
    text = "".join(
        f"{p.id}  generation={int(p.includes_generation)} judge={int(p.includes_judge)}"
        f"  {p.measures}\n"
        for p in records
    ) or "no protocols\n"
    return _emit(_records_payload(records), args.json, text)


def _cmd_observation(conn: sqlite3.Connection, args) -> int:
    if args.action == "add":
        record = add_observation(
            conn,
            args.claim,
            args.group,
            args.value,
            args.note,
            instrument_kind=args.instrument_kind,
            instrument_id=args.instrument_id,
            instrument_digest=args.instrument_digest,
            rater_kind=args.rater_kind,
            rater_id=args.rater_id,
            rater_version=args.rater_version,
            protocol_id=args.protocol_id,
            sample_size=args.sample_size,
            aggregation=args.aggregation,
            unit=args.unit,
            provenance_class=args.provenance_class,
            producer_path=args.producer_path,
            producer_digest=args.producer_digest,
        )
        return _emit(record, args.json, f"{record.id} {record.group_label}={record.value}\n")
    if args.action == "void":
        record = void_observation(conn, args.ref, args.reason)
        return _emit(record, args.json, f"{record.id} voided\n")
    if args.action == "import-csv":
        if args.template:
            return _emit(
                {"template": CSV_TEMPLATE_HEADER}, args.json,
                CSV_TEMPLATE_HEADER + "\n",
            )
        if not args.claim or not args.path:
            raise EngineError(
                "observation import-csv needs a claim and a path",
                "a bulk import records named measurements on one live claim.",
                "pass CLAIM PATH, or --template to print the CSV header.",
            )
        result = import_observations_csv(conn, args.claim, args.path)
        text = (
            f"{result['claim']} imported {result['imported']}"
            f" skipped {result['skipped']} ({result['path']})\n"
        )
        for item in result["skipped_rows"]:
            text += f"  row {item['row']}: {item['reason']}\n"
        return _emit(result, args.json, text)
    records = list_observations(conn, args.claim, args.group, args.include_voided)
    text = "".join(
        f"{o.id}  {o.group_label:<12} {o.value:12.6g}  {o.unit or '-'}"
        f"  {o.protocol_id or '-'}  {o.provenance_class}  {o.at}"
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
    if args.action == "revise":
        record = revise_claim(
            conn,
            args.ref,
            args.text,
            args.reason,
            source_ref=args.source,
            quote=args.quote,
            locator=args.locator,
            confidence=args.confidence,
            kill_test=args.kill_test,
            basis=args.basis,
            prerequisites=args.prerequisites,
        )
        return _emit(
            record,
            args.json,
            f"{args.ref} -> {record.id} (revised; {args.ref} superseded)\n",
        )
    if args.action == "history":
        records = revision_chain(conn, args.ref)
        text = "".join(
            f"{claim.id}  {claim.status:<11} {'superseded' if claim.superseded_by else 'head'}"
            f"  {claim.text}\n"
            for claim in records
        )
        return _emit(_records_payload(records), args.json, text)
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
            actor=args.actor, evidence_group=args.evidence_group,
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
        view = claim_brief(conn, args.ref, _need_budget(args.budget, "context"))
        return _emit(view.to_dict(), args.json, view.text)
    if args.action == "invalidate":
        result = invalidate(
            conn, args.ref, args.status, args.reason, args.evidence,
            allow_bulk=args.allow_bulk, preview_digest=args.preview_digest,
        )
        text = f"{result['root']} -> {result['status']}\n"
        for item in result["affected"]:
            text += f"  {item['id']} depth {item['depth']} ({item['previous_status']} -> INVALIDATED)\n"
        return _emit(result, args.json, text)
    records = list_claims(conn, args.research, args.status, include_superseded=args.history)
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
        record = record_outcome(
            conn, args.ref, args.status, args.evidence, args.note, actor=args.actor
        )
        return _emit(record, args.json, f"{record.id} -> {record.status}\n")
    if args.action == "amend":
        record = amend_hypothesis(
            conn, args.ref, args.reason, statement=args.statement,
            criterion=args.criterion, actor=args.actor,
        )
        return _emit(record, args.json, f"{record.id} amended\n")
    if args.action == "card":
        card = preregistration_card(conn, args.ref)
        return _emit({"card": card}, args.json, card)
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
        attempt = result.get("attempt")
        if attempt:
            text += f"  attempt {attempt['attempt_no']}: {attempt['outcome']}"
            if attempt["reason"]:
                text += f" ({attempt['reason']})"
            text += "\n"
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
        text = ""
        for run in records:
            attempt = for_group(conn, run.test_id, run.run_group)
            marker = (
                f"  attempt {attempt.attempt_no} {attempt.outcome}"
                if attempt is not None and run.role == "main"
                else "  attempt -"
            )
            text += (
                f"{run.id}  {run.test_id}  {run.run_tag}  {'PASS' if run.passed else 'FAIL'}"
                f"  exit {run.exit_code}  code {run.code_sha256[:8]}{marker}\n"
            )
        return _emit(_records_payload(records), args.json, text or "no runs\n")
    if args.action == "attempts":
        records = list_attempts(conn, args.ref, args.limit)
        text = "".join(
            f"{a.id}  {a.test_id}  attempt {a.attempt_no}  {a.outcome}"
            f"  group {a.run_group}  {a.reason or '-'}\n"
            for a in records
        ) or "no attempts\n"
        return _emit(_records_payload(records), args.json, text)
    records = list_tests(conn, args.research)
    text = "".join(
        f"{t.id}  {t.claim_id or t.hypothesis_id}  {t.name}  `{t.command}`\n" for t in records
    ) or "no tests\n"
    return _emit(_records_payload(records), args.json, text)


def _ensure_outside_repo(path_str: str) -> Path:
    """Refuse model I/O files that live inside the project checkout.

    Raw prompt/output bytes must never enter the repo history; the database
    keeps hashes only. Resolving against the engine package root keeps the
    boundary in code, not convention.
    """
    candidate = Path(path_str).expanduser()
    try:
        resolved = candidate.resolve()
    except OSError as error:
        raise EngineError(
            f"cannot resolve model I/O path: {path_str}",
            "the adapter notarizes exact bytes from outside the repository.",
            "pass a path to a file outside the project checkout.",
        ) from error
    root = Path(__file__).resolve().parents[1]
    try:
        resolved.relative_to(root)
    except ValueError:
        return resolved
    raise EngineError(
        f"model I/O file inside the repository: {resolved}",
        "raw prompt/output bytes must not enter version control; only hashes"
        " belong in the database.",
        "move the file outside the project checkout (e.g. the system temp"
        " directory) and pass that path.",
    )


def _cmd_ai(conn: sqlite3.Connection, args) -> int:
    if args.action == "sweep":
        try:
            cited = json.loads(args.cited)
        except ValueError as error:
            raise EngineError(
                f"cited payload is not valid JSON: {error}",
                "citations arrive as data, not prose.",
                'pass --cited \'[{"source_id": "s_000001", "locator": "p. 3"}]\'.',
            ) from error
        if not isinstance(cited, list):
            raise EngineError(
                "cited payload is not a list",
                "citations arrive as a list of {source_id, locator} objects.",
                'pass --cited \'[{"source_id": "s_000001", "locator": "p. 3"}]\'.',
            )
        prompt_path = _ensure_outside_repo(args.prompt_file)
        output_path = _ensure_outside_repo(args.output_file)
        try:
            prompt_text = prompt_path.read_text(encoding="utf-8")
            output_text = output_path.read_text(encoding="utf-8")
        except OSError as error:
            raise EngineError(
                f"cannot read model I/O file: {error.filename}",
                "the adapter notarizes exact bytes; a missing file proves nothing.",
                "pass paths to files that exist outside the repository.",
            ) from error
        record = record_ai_artifact(
            conn, args.research, args.kind, args.model, prompt_text, output_text, cited
        )
        return _emit(record, args.json, f"{record.id} {record.kind} {record.model_id}\n")
    if args.action == "extract":
        claim = ingest_ai_claim(
            conn,
            args.artifact,
            args.text,
            args.kind,
            source_ref=args.source,
            quote=args.quote,
            locator=args.locator,
            confidence=args.confidence,
            kill_test=args.kill_test,
            basis=args.basis,
            prerequisites=args.prerequisites,
            question_ref=args.question,
            stance=args.stance,
            actor=args.actor,
        )
        return _emit(claim, args.json, f"{claim.id} UNVERIFIED {claim.text}\n")
    if args.action == "idea":
        hypothesis = ingest_ai_hypothesis(
            conn,
            args.artifact,
            args.statement,
            args.criterion,
            args.confidence,
            args.question,
            actor=args.actor,
        )
        return _emit(
            hypothesis, args.json, f"{hypothesis.id} {hypothesis.status} {hypothesis.statement}\n"
        )
    if args.action == "propose-test":
        test = propose_ai_test(
            conn,
            args.artifact,
            args.template,
            args.name,
            claim_ref=args.claim,
            hypothesis_ref=args.hypothesis,
            actor=args.actor,
        )
        return _emit(test, args.json, f"{test.id} {test.name}\n")
    if args.action == "draft":
        text = render_ai_draft(conn, args.ref)
        if args.out:
            from engine.artifacts import atomic_write_text

            atomic_write_text(Path(args.out), text)
            return _emit({"draft": args.out}, args.json, f"wrote {args.out}\n")
        return _emit({"draft": text}, args.json, text)
    records = list_ai_artifacts(conn, args.research)
    text = "".join(
        f"{a.id}  {a.kind:<10} {a.model_id}  prompt={a.prompt_sha256[:12]}"
        f"  output={a.output_sha256[:12]}\n"
        for a in records
    ) or "no AI artifacts\n"
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
            if args.command == "search":
                result = search_graph(
                    conn,
                    args.query,
                    args.research,
                    tuple(args.kind) if args.kind else None,
                    args.limit,
                    args.all,
                    _need_budget(args.budget, "search"),
                )
                payload = {key: value for key, value in result.items() if key != "text"}
                return _emit(payload, args.json, result["text"])
            if args.command == "check":
                findings = check(conn)
                text = render_markdown(findings)
                if args.json:
                    _emit(json.loads(render_json(findings)), True, text)
                else:
                    print(text, end="")
                return 1 if has_errors(findings) else 0
            if args.command == "outline":
                view = outline(conn, args.ref, _need_budget(args.budget, "outline"))
                return _emit(view.to_dict(), args.json, view.text)
            if args.command == "brief":
                view = brief(conn, args.ref, _need_budget(args.budget, "brief"))
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
                if (args.tree or args.path) and (
                    args.research or args.kind or args.limit != 50
                ):
                    raise EngineError(
                        "--tree and --path ignore list filters",
                        "a causal tree or chain is rooted at one event, not filtered.",
                        "drop --research, --kind and --limit when using --tree or --path.",
                    )
                if args.tree:
                    tree = event_tree(conn, args.tree)
                    text = "".join(
                        "  " * item["depth"]
                        + f"{item['event'].id} seq {item['event'].seq} {item['event'].kind}"
                        + f" {item['event'].subject} {item['event'].detail}\n"
                        for item in tree
                    )
                    payload = [
                        {"depth": item["depth"], "event": asdict(item["event"])}
                        for item in tree
                    ]
                    return _emit(payload, args.json, text)
                if args.path:
                    chain = event_path(conn, args.path)
                    text = "".join(
                        f"{event.id} seq {event.seq} {event.kind} {event.subject}\n"
                        for event in chain
                    )
                    return _emit(_records_payload(chain), args.json, text)
                if args.verify:
                    programs = [args.research] if args.research else [
                        str(row["research_id"]) for row in conn.execute(
                            "SELECT DISTINCT research_id FROM event ORDER BY research_id"
                        ).fetchall()
                    ]
                    breaks = [
                        (program, event_id, reason)
                        for program in programs or [""]
                        for event_id, reason in verify_ledger(conn, program)
                    ]
                    if breaks:
                        detail = "; ".join(
                            f"{program or '-'}:{event_id} {reason}"
                            for program, event_id, reason in breaks
                        )
                        raise EngineError(
                            "event ledger is broken",
                            f"the hash chain does not verify: {detail}.",
                            "restore the event rows from a backup; never hand-edit the log.",
                        )
                    checked = len(programs or [""])
                    text = f"ledger ok ({checked} program(s) verified)\n"
                    return _emit({"programs": programs, "breaks": []}, args.json, text)
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
                if args.action == "calibration":
                    result = calibration_score(conn, args.ref, args.min_n)
                    counts = result["counts"]
                    lines = [
                        f"CALIBRATION {result['research']}:"
                        f" {counts['resolved']}/{counts['total']} resolved"
                        f" (coverage {result['coverage']:.0%})"
                    ]
                    if result["brier"] is not None:
                        skill = (
                            "n/a" if result["skill"] is None
                            else f"{result['skill']:+.4f}"
                        )
                        lines.append(
                            f"  Brier {result['brier']:.4f}  log loss {result['log_loss']:.4f}"
                            f"  baseline {result['brier_baseline']:.4f}  skill {skill}"
                        )
                        lines.append(
                            f"  supported {counts['supported']}  refuted {counts['refuted']}"
                            f"  inconclusive {counts['inconclusive']}"
                        )
                        for item in result["bins"]:
                            if item["n"]:
                                lines.append(
                                    f"  {item['low']:.1f}-{item['high']:.1f}: n={item['n']}"
                                    f"  predicted {item['mean_confidence']:.2f}"
                                    f"  observed {item['observed']:.2f}"
                                    f"  gap {item['gap']:+.2f}"
                                )
                    for warning in result["warnings"]:
                        lines.append(f"  warning: {warning}")
                    return _emit(result, args.json, "\n".join(lines) + "\n")
                if args.action == "contradictions":
                    if args.unlinked:
                        result = unlinked_contradictions(conn, args.ref)
                        text = "".join(
                            f"{item['left']} <> {item['right']} score {item['score']:.2f}"
                            f"{' polarity-mismatch' if item['polarity_mismatch'] else ''}\n"
                            for item in result
                        ) or "no unlinked contradictions\n"
                        return _emit(result, args.json, text)
                    result = contradictions(conn, args.ref, args.min_score)
                    text = "".join(
                        f"Q {item['question']} + {item['support']} - {item['contradicts']}"
                        f" score {item['score']:.2f}"
                        f"{' polarity-mismatch' if item['polarity_mismatch'] else ''}\n"
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
                        allow_incomparable=args.allow_incomparable,
                        allow_self_reported=args.allow_self_reported,
                        plan_ref=args.plan,
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
                    if result.get("plan"):
                        text += f"  plan: {result['plan']}\n"
                    return _emit(result, args.json, text)
                if args.action == "plan":
                    plan = add_plan(
                        conn, args.claim, args.baseline, args.treatment,
                        args.prediction,
                    )
                    return _emit(
                        plan, args.json,
                        f"{plan.id} preregistered {plan.baseline}->{plan.treatment}\n",
                    )
                if args.action == "stats-all":
                    result = batch_statistics(
                        conn, args.ref, args.baseline, args.treatment,
                        seed=args.seed, resamples=args.resamples,
                        allow_incomparable=args.allow_incomparable,
                        allow_self_reported=args.allow_self_reported,
                    )
                    lines = [
                        f"BATCH {result['research']} {result['baseline']}"
                        f"->{result['treatment']}:"
                        f" {len(result['results'])} ok, {len(result['errors'])} errors"
                    ]
                    for claim_id in sorted(result["results"]):
                        detail = result["results"][claim_id]
                        lines.append(
                            f"  {claim_id} d={detail['cohens_d']:.3f}"
                            f" welch_p={detail['welch']['p']:.4g}"
                        )
                    for claim_id in sorted(result["errors"]):
                        lines.append(
                            f"  {claim_id} ERROR {result['errors'][claim_id]['error']}"
                        )
                    for warning in result["global_warnings"]:
                        lines.append(f"  warning: {warning}")
                    return _emit(result, args.json, "\n".join(lines) + "\n")
                if args.action == "correlation":
                    wanted = (
                        [item.strip() for item in args.groups.split(",") if item.strip()]
                        if args.groups else None
                    )
                    result = group_correlations(
                        conn, args.claim, wanted,
                        allow_incomparable=args.allow_incomparable,
                        allow_self_reported=args.allow_self_reported,
                    )
                    text = "".join(
                        f"{item['left']} <> {item['right']} r={item['r']:+.3f}"
                        f" n={item['n']}"
                        + (" INCOMPARABLE" if not item["comparable"] else "")
                        + "".join(f" [{warning}]" for warning in item["warnings"])
                        + "\n"
                        for item in result
                    ) or "no correlations\n"
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
                text += f"  digest: {result['digest']}\n"
                return _emit(result, args.json, text)
            if args.command == "report":
                if args.strict and not args.check:
                    raise EngineError(
                        "--strict needs --check",
                        "strictness only changes manifest comparison, not rendering.",
                        "pass --check PATH together with --strict, or drop --strict.",
                    )
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
                result = report(conn, args.ref)
                return _emit({"report": result}, args.json, result)
            if args.command == "scorecard":
                result = scorecard(conn, args.ref)
                return _emit({"scorecard": result}, args.json, result)
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
                        f"  schema: {result['schema']}"
                        f"{'' if result['schema_supported'] else ' (unsupported)'}\n"
                        f"  records: {result['records']}\n"
                        f"  digest: {result['digest'][:16]}\n"
                    )
                    if not result["counts_match"]:
                        text += f"  count mismatch: meta says {result['recorded_records']}\n"
                    _emit(result, args.json, text)
                    return 0 if (
                        result["ok"]
                        and result["counts_match"]
                        and result["schema_supported"]
                    ) else 1
                counts = export_jsonl(conn, Path(args.path), args.research)
                text = f"exported {sum(counts.values())} records to {args.path}\n"
                return _emit(counts, args.json, text)
            handlers: Dict[str, Callable] = {
                "research": _cmd_research,
                "question": _cmd_question,
                "source": _cmd_source,
                "claim": _cmd_claim,
                "hypothesis": _cmd_hypothesis,
                "protocol": _cmd_protocol,
                "observation": _cmd_observation,
                "test": _cmd_test,
                "ai": _cmd_ai,
            }
            return handlers[args.command](conn, args)
        finally:
            conn.close()
    except EngineError as error:
        print(error.render(), file=sys.stderr)
        return 1
