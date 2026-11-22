//! Research Engine: provenance-backed claims, pre-registered hypotheses, executable kill tests.
//!
//! This crate is the Rust implementation of the host lifecycle. It reads and writes
//! the same schema-14 SQLite graph as the Python engine, so migration is incremental
//! and evidence is never discarded.

pub mod cascade;
pub mod cli;
pub mod core;
pub mod db;
pub mod error;
pub mod integrity;
pub mod killtest;
pub mod provenance;
pub mod synthesis;
pub mod util;
pub mod vocab;

pub use error::{EngineError, Result};
