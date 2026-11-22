//! Research Engine: provenance-backed claims, pre-registered hypotheses, executable kill tests.
//!
//! This crate is the Rust implementation of the host lifecycle. It reads and writes
//! the same schema-14 SQLite graph as the Python engine, so migration is incremental
//! and evidence is never discarded.

pub mod ai;
pub mod analysis;
pub mod bundle;
pub mod calibration;
pub mod cascade;
pub mod cli;
pub mod context;
pub mod core;
pub mod db;
pub mod diffing;
pub mod domains_atlas;
pub mod domains_atlas_schema_spec;
pub mod domains_fluid_bridge;
pub mod domains_fluid_frank_oseen;
pub mod domains_fluid_vortex_core;
pub mod domains_hydrogen_radial;
pub mod domains_fluid_circulant;
pub mod domains_fluid_reduction;
pub mod domains_fluid_variational_width;
pub mod domains_fluid_nelson_closure;
pub mod domains_fluid_convergence;
pub mod domains_fluid_topology;
pub mod domains_obezite;
pub mod domains_pnn_docking;
pub mod domains_pnn_compounds;
pub mod domains_pnn_screen;
pub mod domains_pnn_tables;
pub mod domains_pnn_curation;
pub mod domains_fluid_water_analogue;
pub mod domains_pnn_reports;
pub mod domains_fluid_water_well;
pub mod domains_fluid_water_electron;
pub mod domains_fluid_water_vde;
pub mod domains_fluid_water_dispersive;
pub mod domains_fluid_two_state_marcus;
pub mod domains_pnn_rules;
pub mod domains_pnn_safety;
pub mod discovery;
pub mod error;
pub mod experiments;
pub mod integrity;
pub mod killtest;
pub mod lattice;
pub mod lattice_checks;
pub mod lattice_discovery;
pub mod lattice_providers;
pub mod lattice_query;
pub mod lattice_repo;
pub mod lattice_snapshots;
pub mod manifest;
pub mod markdown;
pub mod meta;
pub mod observations;
pub mod protocols;
pub mod provenance;
pub mod search;
pub mod stats;
pub mod studio_api;
pub mod studio_client;
pub mod studio_web;
pub mod studio_web_html;
pub mod studio_mcp;
pub mod studio_mcp_specs;
pub mod synthesis;
pub mod util;
pub mod vocab;

pub use error::{EngineError, Result};
