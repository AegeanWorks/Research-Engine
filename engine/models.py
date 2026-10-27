"""Frozen domain records and the engine's closed vocabularies."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

CLAIM_STATUSES = (
    "UNVERIFIED",
    "PROVEN",
    "NUMERIC",
    "UNKNOWN",
    "FALSIFIED",
    "RETRACTED",
    "INVALIDATED",
)
PROMOTED_STATUSES = ("PROVEN", "NUMERIC")
FAILED_STATUSES = ("FALSIFIED", "RETRACTED", "INVALIDATED")
NON_SUPPORTING_STATUSES = FAILED_STATUSES + ("UNKNOWN",)
CLAIM_KINDS = ("empirical", "derived", "assumption", "speculation")
HYPOTHESIS_OUTCOMES = ("SUPPORTED", "REFUTED", "INCONCLUSIVE")
SOURCE_KINDS = ("paper", "preprint", "dataset", "book", "report", "web")
SOURCE_STATUSES = ("active", "expression_of_concern", "retracted")
BROKEN_SOURCE_STATUSES = ("retracted",)
DEPENDENCY_RELATIONS = ("derived_from", "depends_on")
CLAIM_CLAIM_RELATIONS = (
    "supports",
    "contradicts",
    "replicates",
    "extends",
    "uses_method",
    "measures",
    "related",
)
CLAIM_QUESTION_RELATIONS = ("supports", "contradicts", "answers", "mentions")
CLAIM_HYPOTHESIS_RELATIONS = ("supports", "contradicts", "tests")


@dataclass(frozen=True)
class Research:
    id: str
    slug: str
    title: str
    scope: str
    created_at: str


@dataclass(frozen=True)
class Source:
    id: str
    research_id: str
    kind: str
    title: str
    authors: str
    year: Optional[int]
    doi: str
    url: str
    retrieved_at: str
    status: str = "active"
    status_note: str = ""
    status_at: str = ""


@dataclass(frozen=True)
class Question:
    id: str
    research_id: str
    text: str
    status: str
    created_at: str


@dataclass(frozen=True)
class Claim:
    id: str
    research_id: str
    source_id: Optional[str]
    text: str
    quote: str
    locator: str
    kind: str
    basis: str
    kill_test: str
    status: str
    confidence: float
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class Hypothesis:
    id: str
    research_id: str
    question_id: Optional[str]
    statement: str
    criterion: str
    confidence: float
    registered_at: str
    status: str
    outcome_note: str
    updated_at: str


@dataclass(frozen=True)
class KillTest:
    id: str
    research_id: str
    claim_id: Optional[str]
    hypothesis_id: Optional[str]
    name: str
    command: str
    expect_exit: int
    timeout_seconds: int
    created_at: str
    inputs_json: str = "[]"


@dataclass(frozen=True)
class TestRun:
    id: str
    test_id: str
    run_group: str
    run_tag: str
    started_at: str
    duration_ms: int
    exit_code: int
    passed: bool
    stdout_sha256: str
    stderr_sha256: str
    output_tail: str
    command_sha256: str = ""
    code_sha256: str = ""
    inputs_sha256: str = ""
    git_commit: str = ""
    git_dirty: bool = False
    python_version: str = ""
    platform: str = ""


@dataclass(frozen=True)
class Finding:
    code: str
    severity: str
    subject: str
    message: str
    fix: str
