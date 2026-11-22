//! Engine errors carry a What/Why/Fix triad so CLI failures stay actionable.

use std::fmt;

#[derive(Debug, Clone)]
pub struct EngineError {
    pub what: String,
    pub why: String,
    pub fix: String,
}

impl EngineError {
    pub fn new(what: impl Into<String>, why: impl Into<String>, fix: impl Into<String>) -> Self {
        Self {
            what: what.into(),
            why: why.into(),
            fix: fix.into(),
        }
    }

    pub fn not_found(kind: &str, ref_id: &str) -> Self {
        Self::new(
            format!("{kind} not found: {ref_id}"),
            format!("a {kind} must be registered before it can be referenced."),
            format!("run `{kind} list` to see the registered identifiers."),
        )
    }
}

impl fmt::Display for EngineError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.what)
    }
}

impl std::error::Error for EngineError {}

pub type Result<T> = std::result::Result<T, EngineError>;

impl From<rusqlite::Error> for EngineError {
    fn from(error: rusqlite::Error) -> Self {
        Self::new(
            format!("database error: {error}"),
            "the state file could not satisfy the requested operation.",
            "check the database path, permissions and schema version, then retry.",
        )
    }
}

impl From<std::io::Error> for EngineError {
    fn from(error: std::io::Error) -> Self {
        Self::new(
            format!("io error: {error}"),
            "the file could not be read or written.",
            "check the path and permissions and retry.",
        )
    }
}

impl From<serde_json::Error> for EngineError {
    fn from(error: serde_json::Error) -> Self {
        Self::new(
            format!("invalid JSON: {error}"),
            "a JSON input did not parse.",
            "pass a valid JSON document.",
        )
    }
}
