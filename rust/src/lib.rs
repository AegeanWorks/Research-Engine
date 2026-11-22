//! Research Engine: provenance-backed claims, pre-registered hypotheses, executable kill tests.
//!
//! This crate is the Rust implementation of the host lifecycle. It reads and writes
//! the same schema-14 SQLite graph as the Python engine, so migration is incremental
//! and evidence is never discarded.

pub mod analysis;
pub mod bundle;
pub mod calibration;
pub mod cascade;
pub mod cli;
pub mod context;
pub mod core;
pub mod db;
pub mod error;
pub mod integrity;
pub mod killtest;
pub mod manifest;
pub mod markdown;
pub mod observations;
pub mod protocols;
pub mod provenance;
pub mod search;
pub mod stats;
pub mod synthesis;
pub mod util;
pub mod vocab;

pub use error::{EngineError, Result};
