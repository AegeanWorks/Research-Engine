//! Cohesive research-engine facade.
//!
//! This module is the single entry point for the capabilities that matter to the
//! host lifecycle: design-rule screening, safety qualification, academic
//! horizon primitives and evidence-grounded reporting. It deliberately does
//! not mirror every function of the imported source projects.

use serde_json::{json, Value};

use crate::engine_bridge as bridge;
use crate::engine_corpus as obezite;
use crate::engine_rules as rules;
use crate::engine_safety as safety;
use crate::engine_screen as screen;
use crate::error::{EngineError, Result};
use crate::lattice;

fn field(value: &Value, key: &str) -> String {
    value.get(key).and_then(Value::as_str).unwrap_or("").to_string()
}

fn number(value: &Value, key: &str, default: f64) -> f64 {
    value.get(key).and_then(Value::as_f64).unwrap_or(default)
}

/// One integrated analysis of a candidate program.
pub fn analyze(input: &Value) -> Result<Value> {
    let compound = input.get("compound").ok_or_else(|| EngineError::new(
        "input must contain a 'compound' object", "the engine analyzes one candidate at a time",
        "pass a compound object with the core physicochemical fields"))?;
    let design = rules::evaluate(compound);
    let passes = design.iter().filter(|row| row.get("status").and_then(Value::as_str) == Some("PASS")).count();
    let unknowns = design.iter().filter(|row| row.get("status").and_then(Value::as_str) == Some("UNKNOWN")).count();
    let failures = design.len() - passes - unknowns;

    let studies = input.get("tox_studies").and_then(Value::as_array).cloned().unwrap_or_default();
    let pharm = input.get("pharm");
    let tox = if studies.is_empty() { Vec::new() } else {
        safety::assess(&studies, pharm, 10.0, 30.0, 10.0, 50.0, 30.0, 60.0)?
    };

    let bridge_input = input.get("bridge");
    let primitives = match bridge_input {
        Some(config) => json!({
            "diffusivity": bridge::diffusivity(number(config, "hbar", 1.0), number(config, "mass", 1.0))?,
            "horizon": bridge::horizon(number(config, "omega", 1.0))?,
        }),
        None => Value::Null,
    };

    let safety_ok = tox.iter().all(|row| {
        row.get("status").and_then(Value::as_str) != Some("FAIL")
    });
    let verdict = if failures > 0 || !safety_ok { "REJECT" }
        else if unknowns > 0 { "UNVERIFIED" }
        else { "CANDIDATE" };

    Ok(json!({
        "program": field(input.get("program").unwrap_or(&Value::Null), "title"),
        "summary": {
            "criteria": design.len(),
            "passes": passes,
            "failures": failures,
            "unknowns": unknowns,
            "safety_findings": tox.len(),
            "verdict": verdict,
        },
        "design": design,
        "safety": tox,
        "bridge": primitives,
    }))
}

/// Capabilities retained by the cohesive engine, grouped into four subsystems.
pub const CAPABILITIES: &[&str] = &[
    "catalog.normalize", "catalog.study-type", "catalog.paper-id",
    "candidate.rules", "candidate.screen", "candidate.noael-hed",
    "bridge.primitives", "corpus.citations",
];

/// Execute one retained capability through the single engine entry point.
pub fn execute(capability: &str, input: &Value) -> Result<Value> {
    match capability {
        // catalog — literature identity rules
        "catalog.normalize" => Ok(json!({"value": lattice::normalize_text(&field(input, "text"))})),
        "catalog.study-type" => Ok(json!({"value": lattice::normalize_study_type(&field(input, "text"))})),
        "catalog.paper-id" => Ok(json!({"value": lattice::paper_id(
            &field(input, "title"), &field(input, "doi"), &field(input, "arxiv"))?})),
        // candidate — design, safety and screen verdicts
        "candidate.rules" | "pnn-rules" => {
            let compound = input.get("compound").unwrap_or(input);
            Ok(Value::Array(rules::evaluate(compound)))
        }
        "candidate.screen" => {
            let compounds: Vec<Value> = input.get("compounds").and_then(Value::as_array)
                .cloned().unwrap_or_default();
            Ok(json!({"screen": screen::screen_compounds(&compounds),
                "summary": screen::summarize(&screen::screen_compounds(&compounds))}))
        }
        "candidate.noael-hed" => Ok(json!({"value": safety::noael_hed(
            number(input, "noael", 0.0), &field(input, "species"), number(input, "km", 3.0))?})),
        // bridge — Gaussian/fluid primitives
        "bridge.primitives" | "fluid-bridge" => Ok(json!({
            "diffusivity": bridge::diffusivity(number(input, "hbar", 1.0), number(input, "mass", 1.0))?,
            "horizon": bridge::horizon(number(input, "omega", 1.0))?,
        })),
        // corpus — bibliography parsing helpers
        "corpus.citations" | "obezite-atiflar" => Ok(Value::Array(
            obezite::atiflar(&field(input, "text")).into_iter().map(Value::from).collect())),
        other => Err(EngineError::new(format!("unknown capability: {other}"),
            "capabilities are a closed vocabulary",
            "pass one of catalog.*, candidate.*, bridge.primitives or corpus.citations")),
    }
}

pub fn render_report(analysis: &Value) -> String {
    let summary = analysis.get("summary").unwrap_or(&Value::Null);
    let mut lines = vec![
        "# Research Engine — Integrated Candidate Analysis".to_string(),
        String::new(),
        format!("**Program**: {}", field(analysis, "program")),
        String::new(),
        format!("**Verdict**: {}", field(summary, "verdict")),
        format!("Design criteria: {} PASS, {} FAIL, {} UNKNOWN",
            summary.get("passes").and_then(Value::as_u64).unwrap_or(0),
            summary.get("failures").and_then(Value::as_u64).unwrap_or(0),
            summary.get("unknowns").and_then(Value::as_u64).unwrap_or(0)),
        format!("Safety findings: {}", summary.get("safety_findings").and_then(Value::as_u64).unwrap_or(0)),
        String::new(),
        "## Design verdicts".to_string(),
        String::new(),
    ];
    for row in analysis.get("design").and_then(Value::as_array).into_iter().flatten() {
        lines.push(format!("- {}: {} ({})", field(row, "name"), field(row, "status"), field(row, "detail")));
    }
    if let Some(safety) = analysis.get("safety").and_then(Value::as_array) {
        if !safety.is_empty() {
            lines.extend(vec![String::new(), "## Safety qualifications".to_string(), String::new()]);
            for row in safety {
                lines.push(format!("- {}", field(row, "compound_id")));
            }
        }
    }
    lines.join("\n")
}
