//! AI provenance adapter: notarize model I/O, ingest UNVERIFIED claims, propose template tests.

use rusqlite::{params, Connection};
use serde_json::{json, Value};

use crate::core::{get_claim, get_research, get_source, record_event};
use crate::db::{next_id, utc_now};
use crate::error::{EngineError, Result};
use crate::killtest;
use crate::markdown::sanitize;
use crate::util::{query_json, sha256_text, to_python_json};
use crate::vocab::AI_KINDS;

pub const TEMPLATE_NAMES: &[&str] = &["constant-probe"];

/// Whether a test's command/control pair still matches an AI probe template.
pub fn matches_template(command: &str, control: &str) -> Result<bool> {
    Ok(templates()?.values().any(|spec| {
        field(spec, "command") == command && field(spec, "control_command") == control
    }))
}

fn field(value: &Value, name: &str) -> String {
    value.get(name).and_then(Value::as_str).unwrap_or("").to_string()
}

fn templates() -> Result<std::collections::BTreeMap<&'static str, Value>> {
    #[cfg(windows)]
    let resolved = killtest::capture("where python", 10)?;
    #[cfg(not(windows))]
    let resolved = killtest::capture("which python", 10)?;
    let python = resolved.lines().next().unwrap_or("python").trim().to_string();
    let quoted = format!("\"{python}\"");
    let mut map = std::collections::BTreeMap::new();
    map.insert("constant-probe", json!({
        "command": format!("{quoted} -c \"print('ai-probe:constant')\""),
        "control_command": format!("{quoted} -c \"import sys; print('ai-probe:control-diverged'); sys.exit(2)\""),
        "expect_exit": 0,
    }));
    Ok(map)
}

pub fn get_artifact(conn: &Connection, reference: &str) -> Result<Value> {
    let rows = query_json(conn, "SELECT * FROM ai_artifact WHERE id=?1", params![reference])?;
    rows.into_iter().next().ok_or_else(|| EngineError::not_found("AI artifact", reference))
}

pub fn list_artifacts(conn: &Connection, research_ref: Option<&str>) -> Result<Vec<Value>> {
    if let Some(reference) = research_ref {
        let research = get_research(conn, reference)?;
        query_json(conn, "SELECT * FROM ai_artifact WHERE research_id=?1 ORDER BY id",
            params![field(&research, "id")])
    } else {
        query_json(conn, "SELECT * FROM ai_artifact ORDER BY id", [])
    }
}

fn validate_cited(cited: &[Value]) -> Result<String> {
    let mut normalized = Vec::new();
    for entry in cited {
        let Some(object) = entry.as_object() else {
            return Err(EngineError::new("AI citation is not an object",
                "each cited source must name a source_id and a locator.",
                "pass --cited '[{\"source_id\": \"s_000001\", \"locator\": \"p. 3\"}]'."));
        };
        let source_id = field(&Value::Object(object.clone()), "source_id").trim().to_string();
        let locator = field(&Value::Object(object.clone()), "locator").trim().to_string();
        if source_id.is_empty() || locator.is_empty() {
            return Err(EngineError::new("AI citation lacks a source_id or locator",
                "a citation without both cannot be resolved or audited.",
                "pass --cited '[{\"source_id\": \"s_000001\", \"locator\": \"p. 3\"}]'."));
        }
        normalized.push(json!({"source_id": source_id, "locator": locator}));
    }
    Ok(to_python_json(&Value::Array(normalized)))
}

#[allow(clippy::too_many_arguments)]
pub fn record(
    conn: &Connection,
    research_ref: &str,
    kind: &str,
    model_id: &str,
    prompt_text: &str,
    output_text: &str,
    cited: &[Value],
) -> Result<Value> {
    let research = get_research(conn, research_ref)?;
    if !AI_KINDS.contains(&kind) {
        return Err(EngineError::new(format!("unknown AI artifact kind: {kind}"),
            format!("allowed kinds are {}.", AI_KINDS.join(", ")), "pass one of the listed kinds."));
    }
    if model_id.trim().is_empty() {
        return Err(EngineError::new("AI artifact has no model id",
            "provenance must name which model produced the output.",
            "pass --model such as local:qwen2.5-coder-1.5b-hf."));
    }
    if prompt_text.trim().is_empty() || output_text.trim().is_empty() {
        return Err(EngineError::new("AI artifact has empty prompt or output",
            "a hash of nothing proves nothing.",
            "pass the exact prompt and output bytes that were exchanged."));
    }
    let cited_json = validate_cited(cited)?;
    let tx = conn.unchecked_transaction()?;
    let id = next_id(&tx, "a")?;
    let prompt_hash = sha256_text(prompt_text);
    let output_hash = sha256_text(output_text);
    let actor = format!("model:{}", model_id.trim());
    tx.execute(
        "INSERT INTO ai_artifact(id, research_id, kind, model_id, prompt_sha256, output_sha256, cited_json, actor, created_at) VALUES (?1,?2,?3,?4,?5,?6,?7,?8,?9)",
        params![id, field(&research, "id"), kind, model_id.trim(), prompt_hash, output_hash,
            cited_json, actor, utc_now()],
    )?;
    record_event(&tx, &field(&research, "id"), "ai.record", &id,
        &format!("{kind} by {} prompt={} output={}", model_id.trim(),
            &prompt_hash[..16], &output_hash[..16]), &actor)?;
    tx.commit()?;
    get_artifact(conn, &id)
}

fn resolve_actor(artifact: &Value, actor: &str) -> String {
    if actor == "agent" { field(artifact, "actor") } else { actor.to_string() }
}

fn ensure_cited_resolve(conn: &Connection, artifact: &Value, source_ref: Option<&str>) -> Result<()> {
    if field(artifact, "kind") == "sweep" { return Ok(()); }
    let cited: Vec<Value> = serde_json::from_str(field(artifact, "cited_json").as_str())
        .unwrap_or_default();
    let mut cited_ids = Vec::new();
    for entry in cited {
        let source_id = field(&entry, "source_id").trim().to_string();
        let locator = field(&entry, "locator").trim().to_string();
        cited_ids.push(source_id.clone());
        let exists = conn.query_row(
            "SELECT 1 FROM source WHERE id=?1 AND research_id=?2",
            params![source_id, field(artifact, "research_id")], |_| Ok(())).is_ok();
        if locator.is_empty() || !exists {
            return Err(EngineError::new(
                format!("AI cited source is unresolvable: {}", if source_id.is_empty() { "(none)" } else { &source_id }),
                "a citation without a registered in-program source and locator cannot be audited.",
                "register the source first, or remove the entry from --cited."));
        }
    }
    if let Some(source_ref) = source_ref {
        if !cited_ids.iter().any(|id| id == source_ref.trim()) {
            return Err(EngineError::new("AI claim source is not among the artifact citations",
                "the ingested source must be one the model actually cited.",
                "pass --source with one of the cited source ids, or re-notarize the model I/O."));
        }
    }
    Ok(())
}

#[allow(clippy::too_many_arguments)]
pub fn ingest_claim(
    conn: &Connection,
    artifact_ref: &str,
    text: &str,
    kind: &str,
    source_ref: Option<&str>,
    quote: &str,
    locator: &str,
    confidence: f64,
    kill_test: &str,
    basis: &str,
    prerequisites: &[String],
    question_ref: Option<&str>,
    stance: &str,
    actor: &str,
) -> Result<Value> {
    let artifact = get_artifact(conn, artifact_ref)?;
    let resolved_actor = resolve_actor(&artifact, actor);
    let allowed: &[&str] = match field(&artifact, "kind").as_str() {
        "extraction" => &["empirical", "derived"],
        "idea" => &["derived", "assumption", "speculation"],
        _ => &[],
    };
    if !allowed.contains(&kind) {
        return Err(EngineError::new(
            format!("kind {kind} cannot come from a {} artifact", field(&artifact, "kind")),
            format!("a {} artifact may propose {}.", field(&artifact, "kind"), allowed.join(", ")),
            "record an artifact of the matching kind first."));
    }
    let result = (|| -> Result<Value> {
        ensure_cited_resolve(conn, &artifact, if kind == "empirical" { source_ref } else { None })?;
        let source_id = match source_ref {
            Some(reference) => Some(field(&get_source(conn, reference)?, "id")),
            None => None,
        };
        let claim = crate::core::add_claim(conn, &field(&artifact, "research_id"), text, kind,
            source_id.as_deref(), quote, locator, confidence, kill_test, basis, prerequisites)?;
        let tx = conn.unchecked_transaction()?;
        if let Some(reference) = question_ref {
            let question = crate::core::get_question(&tx, reference)?;
            crate::core::record_edge(&tx, "claim", &field(&claim, "id"), "question",
                &field(&question, "id"), stance)?;
        }
        tx.execute("UPDATE ai_artifact SET claim_id=?1 WHERE id=?2",
            params![field(&claim, "id"), field(&artifact, "id")])?;
        record_event(&tx, &field(&artifact, "research_id"), "ai.ingest", &field(&claim, "id"),
            &format!("{} -> {} ({kind}, UNVERIFIED)", field(&artifact, "id"), field(&claim, "id")),
            &resolved_actor)?;
        tx.commit()?;
        get_claim(conn, &field(&claim, "id"))
    })();
    if let Err(error) = result {
        record_event(conn, &field(&artifact, "research_id"), "ai.reject", &field(&artifact, "id"),
            &format!("ingest refused: {}", error.what), &resolved_actor)?;
        return Err(error);
    }
    result
}

pub fn ingest_hypothesis(
    conn: &Connection,
    artifact_ref: &str,
    statement: &str,
    criterion: &str,
    confidence: f64,
    question_ref: Option<&str>,
    actor: &str,
) -> Result<Value> {
    let artifact = get_artifact(conn, artifact_ref)?;
    let resolved_actor = resolve_actor(&artifact, actor);
    if field(&artifact, "kind") != "idea" {
        return Err(EngineError::new(
            format!("a hypothesis cannot come from a {} artifact", field(&artifact, "kind")),
            "hypotheses are new ideas, pre-registered before any test.",
            "record an idea artifact first."));
    }
    let result = (|| -> Result<Value> {
        ensure_cited_resolve(conn, &artifact, None)?;
        let hypothesis = crate::core::add_hypothesis(conn, &field(&artifact, "research_id"),
            statement, criterion, confidence, question_ref)?;
        let tx = conn.unchecked_transaction()?;
        tx.execute("UPDATE ai_artifact SET hypothesis_id=?1 WHERE id=?2",
            params![field(&hypothesis, "id"), field(&artifact, "id")])?;
        record_event(&tx, &field(&artifact, "research_id"), "ai.ingest", &field(&hypothesis, "id"),
            &format!("{} -> {} (hypothesis, PREREGISTERED)", field(&artifact, "id"), field(&hypothesis, "id")),
            &resolved_actor)?;
        tx.commit()?;
        crate::core::get_hypothesis(conn, &field(&hypothesis, "id"))
    })();
    if let Err(error) = result {
        record_event(conn, &field(&artifact, "research_id"), "ai.reject", &field(&artifact, "id"),
            &format!("ingest refused: {}", error.what), &resolved_actor)?;
        return Err(error);
    }
    result
}

pub fn propose_test(
    conn: &Connection,
    artifact_ref: &str,
    template: &str,
    name: &str,
    claim_ref: Option<&str>,
    hypothesis_ref: Option<&str>,
    actor: &str,
) -> Result<Value> {
    let artifact = get_artifact(conn, artifact_ref)?;
    let resolved_actor = resolve_actor(&artifact, actor);
    let table = templates()?;
    let spec = table.get(template).ok_or_else(|| EngineError::new(
        format!("unknown test template: {template}"),
        "AI-proposed kill tests come from a fixed template list, never from free-form model text.",
        format!("pass one of: {}.", TEMPLATE_NAMES.join(", "))))?;
    let test = crate::killtest::add_test(conn, &field(&artifact, "research_id"), name,
        &field(spec, "command"), claim_ref, hypothesis_ref,
        spec.get("expect_exit").and_then(Value::as_i64).unwrap_or(0), 120, &[],
        &field(spec, "control_command"))?;
    let tx = conn.unchecked_transaction()?;
    tx.execute("UPDATE ai_artifact SET test_id=?1 WHERE id=?2",
        params![field(&test, "id"), field(&artifact, "id")])?;
    record_event(&tx, &field(&artifact, "research_id"), "ai.test", &field(&test, "id"),
        &format!("{} proposed {template} as {}", field(&artifact, "id"), field(&test, "id")),
        &resolved_actor)?;
    tx.commit()?;
    killtest::get_test(conn, &field(&test, "id"))
}

pub fn render_draft(conn: &Connection, reference: &str) -> Result<String> {
    const DRAFT_LIMITS: &[&str] = &[
        "AI output is a hypothesis source, never evidence.",
        "Article text is guilty until the kill tests clear it: only PROVEN and NUMERIC claims appear above; everything else is withheld below with its status.",
        "A receipt names the verified run group behind each surviving claim.",
    ];
    let research = get_research(conn, reference)?;
    let rid = field(&research, "id");
    let findings = crate::context::findings_for_research(conn, &rid)?;
    if findings.iter().any(|f| field(f, "severity") == "error") {
        return Err(EngineError::new(format!("draft refused: {rid} has error-level findings"),
            "an article cannot be assembled over a failing gate.",
            "resolve `check` errors first, then re-render the draft."));
    }
    let errors = findings.iter().filter(|f| field(f, "severity") == "error").count();
    let warnings = findings.iter().filter(|f| field(f, "severity") == "warning").count();
    let mut lines = vec![
        format!("# Article draft: {}", field(&research, "title")),
        String::new(),
        "**Status:** DRAFT — guilty until the kill tests clear it. This text makes no claim beyond what the receipts below establish.".to_string(),
        format!("**Program:** `{rid}` (`{}`)", field(&research, "slug")),
        format!("**Scope:** {}", if field(&research, "scope").is_empty() { "-".to_string() } else { field(&research, "scope") }),
        format!("**Graph:** content `{}`", crate::bundle::content_sha256(conn, Some(&rid))?),
        format!("**Graph (exact):** `{}`", crate::bundle::graph_sha256(conn, Some(&rid))?),
        format!("**Integrity:** {errors} error(s), {warnings} warning(s)."),
        String::new(),
        "## Established claims".to_string(),
    ];
    let heads = crate::core::list_claims(conn, Some(&rid), None, false)?;
    let mut established = Vec::new();
    let mut withheld = Vec::new();
    for claim in heads {
        if ["PROVEN", "NUMERIC"].contains(&field(&claim, "status").as_str()) { established.push(claim); }
        else { withheld.push(claim); }
    }
    for claim in &established {
        let receipt = if field(claim, "status") == "NUMERIC" {
            let rows = query_json(conn,
                "SELECT evidence_group FROM verdict WHERE subject_kind='claim' AND subject_id=?1 AND status='NUMERIC' ORDER BY id DESC LIMIT 1",
                params![field(claim, "id")])?;
            match rows.first() {
                Some(row) => format!("group {}", field(row, "evidence_group")),
                None => "no cited group".to_string(),
            }
        } else {
            match killtest::claim_groups(conn, &field(claim, "id"))?.first() {
                Some(group) => format!("group {group}"),
                None => "argument only, no executable run".to_string(),
            }
        };
        let provenance = if field(claim, "kind") == "empirical" {
            format!("quote at {} (source {})", field(claim, "locator"), field(claim, "source_id"))
        } else if !field(claim, "basis").is_empty() { field(claim, "basis") } else { "derived".to_string() };
        lines.push(format!("- [{} | {} | {}] {} — {}", field(claim, "id"), field(claim, "status"),
            receipt, sanitize(&field(claim, "text"), 160), sanitize(&provenance, 160)));
    }
    if established.is_empty() { lines.push("none: no claim has survived its kill tests yet.".to_string()); }
    lines.extend(["".to_string(), "## Withheld: not established".to_string()]);
    for claim in &withheld {
        lines.push(format!("- [{} | {}] {}", field(claim, "id"), field(claim, "status"), sanitize(&field(claim, "text"), 160)));
    }
    if withheld.is_empty() { lines.push("none withheld.".to_string()); }
    lines.extend(["".to_string(), "## Questions".to_string()]);
    for question in query_json(conn, "SELECT * FROM question WHERE research_id=?1 ORDER BY id", params![rid])? {
        lines.push(format!("- [{}] {}", field(&question, "id"), field(&question, "text")));
    }
    lines.extend(["".to_string(), "## Limits".to_string()]);
    for limit in DRAFT_LIMITS { lines.push(format!("- {limit}")); }
    Ok(lines.join("\n") + "\n")
}
