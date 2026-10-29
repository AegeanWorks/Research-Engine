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
ATTEMPT_OUTCOMES = ("completed", "subject_failed", "infra_failed", "indeterminate")
REPLACEABLE_ATTEMPT_OUTCOMES = ("infra_failed", "indeterminate")
INSTRUMENT_KINDS = ("rubric", "script", "assay", "survey", "sensor", "other")
RATER_KINDS = ("human", "llm", "automated", "none")
AGGREGATIONS = ("raw", "mean", "median", "p95", "sum")
PROMOTED_STATUSES = ("PROVEN", "NUMERIC")
FAILED_STATUSES = ("FALSIFIED", "RETRACTED", "INVALIDATED")
NON_SUPPORTING_STATUSES = FAILED_STATUSES + ("UNKNOWN",)
CLAIM_KINDS = ("empirical", "derived", "assumption", "speculation")
HYPOTHESIS_OUTCOMES = ("SUPPORTED", "REFUTED", "INCONCLUSIVE")
SOURCE_KINDS = ("paper", "preprint", "dataset", "book", "report", "web")
SOURCE_STATUSES = ("active", "expression_of_concern", "retracted")
BROKEN_SOURCE_STATUSES = ("retracted",)
SCREENING_STATUSES = ("identified", "screened_in", "screened_out", "included", "excluded")
SCREENING_REASONS = (
    "duplicate",
    "not_relevant",
    "wrong_population",
    "wrong_outcome",
    "no_primary_data",
    "not_peer_reviewed",
    "language",
    "full_text_unavailable",
    "superseded",
    "other",
)
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
    screening: str = "identified"
    screening_reason: str = ""
    screening_at: str = ""


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
    revision_of: Optional[str] = None
    superseded_by: Optional[str] = None
    revision_reason: str = ""


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
    control_command: str = ""


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
    role: str = "main"


@dataclass(frozen=True)
class Attempt:
    id: str
    test_id: str
    attempt_no: int
    run_group: str
    outcome: str
    reason: str
    created_at: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "test_id": self.test_id,
            "attempt_no": self.attempt_no,
            "run_group": self.run_group,
            "outcome": self.outcome,
            "reason": self.reason,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class Observation:
    id: str
    research_id: str
    claim_id: str
    group_label: str
    value: float
    note: str
    at: str
    voided: bool
    void_reason: str
    instrument_kind: str = ""
    instrument_id: str = ""
    instrument_digest: str = ""
    rater_kind: str = ""
    rater_id: str = ""
    rater_version: str = ""
    protocol_id: str = ""
    sample_size: int = 1
    aggregation: str = "raw"
    unit: str = ""


@dataclass(frozen=True)
class Protocol:
    id: str
    measures: str
    includes_generation: bool
    includes_judge: bool
    doc_digest: str
    registered_at: str


@dataclass(frozen=True)
class Finding:
    code: str
    severity: str
    subject: str
    message: str
    fix: str
