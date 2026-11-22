//! Frozen domain vocabularies, mirrored from `engine/models.py`.
//!
//! These are contracts: a string outside these tuples must be refused at the CLI
//! boundary, exactly as argparse choices refuse it in the Python implementation.

pub const VERSION: &str = "0.2.0";
pub const SCHEMA_VERSION: i64 = 14;

pub const CLAIM_STATUSES: &[&str] = &[
    "UNVERIFIED", "PROVEN", "NUMERIC", "UNKNOWN", "FALSIFIED", "RETRACTED", "INVALIDATED",
];
pub const ATTEMPT_OUTCOMES: &[&str] = &[
    "completed", "subject_failed", "infra_failed", "indeterminate",
];
pub const REPLACEABLE_ATTEMPT_OUTCOMES: &[&str] = &["infra_failed", "indeterminate"];
pub const INSTRUMENT_KINDS: &[&str] = &["rubric", "script", "assay", "survey", "sensor", "other"];
pub const RATER_KINDS: &[&str] = &["human", "llm", "automated", "none"];
pub const AGGREGATIONS: &[&str] = &["raw", "mean", "median", "p95", "sum"];
pub const PROVENANCE_CLASSES: &[&str] = &["independent", "self_reported", "unclassified"];
pub const PROMOTED_STATUSES: &[&str] = &["PROVEN", "NUMERIC"];
pub const FAILED_STATUSES: &[&str] = &["FALSIFIED", "RETRACTED", "INVALIDATED"];
pub const NON_SUPPORTING_STATUSES: &[&str] = &[
    "FALSIFIED", "RETRACTED", "INVALIDATED", "UNKNOWN",
];
pub const CLAIM_KINDS: &[&str] = &["empirical", "derived", "assumption", "speculation"];
pub const HYPOTHESIS_OUTCOMES: &[&str] = &["SUPPORTED", "REFUTED", "INCONCLUSIVE"];
pub const SOURCE_KINDS: &[&str] = &["paper", "preprint", "dataset", "book", "report", "web"];
pub const SOURCE_STATUSES: &[&str] = &["active", "expression_of_concern", "retracted"];
pub const BROKEN_SOURCE_STATUSES: &[&str] = &["retracted"];
pub const SCREENING_STATUSES: &[&str] = &[
    "identified", "screened_in", "screened_out", "included", "excluded",
];
pub const SCREENING_REASONS: &[&str] = &[
    "duplicate", "not_relevant", "wrong_population", "wrong_outcome", "no_primary_data",
    "not_peer_reviewed", "language", "full_text_unavailable", "superseded", "other",
];
pub const AI_KINDS: &[&str] = &["sweep", "extraction", "idea", "draft"];
pub const DEPENDENCY_RELATIONS: &[&str] = &["derived_from", "depends_on"];
pub const CORROBORATION_RELATIONS: &[&str] = &["supports", "extends", "replicates"];
pub const CLAIM_CLAIM_RELATIONS: &[&str] = &[
    "supports", "contradicts", "replicates", "extends", "uses_method", "measures", "related",
];
pub const CLAIM_QUESTION_RELATIONS: &[&str] = &["supports", "contradicts", "answers", "mentions"];
pub const CLAIM_HYPOTHESIS_RELATIONS: &[&str] = &["supports", "contradicts", "tests"];
pub const SEARCH_KINDS: &[&str] = &["claim", "source", "question", "hypothesis"];
pub const DEFAULT_BUDGET: i64 = 800;

pub fn is_member(value: &str, allowed: &[&str]) -> bool {
    allowed.contains(&value)
}
