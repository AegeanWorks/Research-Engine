//! Transitive invalidation and source retraction: G-004 and G-005.

use rusqlite::{params, Connection};
use serde_json::{json, Value};

use crate::core::{get_claim, get_source, set_verdict_inner};
use crate::db::{next_id, utc_now};
use crate::error::{EngineError, Result};
use crate::util::{query_json, sha256_text};
use crate::vocab::FAILED_STATUSES;

const BULK_LIMIT: usize = 10;

fn field(value: &Value, name: &str) -> String {
    value.get(name).and_then(Value::as_str).unwrap_or("").to_string()
}

fn normalize_doi(value: &str) -> String {
    let text = value.trim();
    let lowered = text.to_lowercase();
    let mut stripped = text;
    for prefix in ["https://doi.org/", "http://doi.org/", "https://dx.doi.org/",
        "http://dx.doi.org/", "https://www.doi.org/", "http://www.doi.org/", "doi:"] {
        if lowered.starts_with(prefix) {
            stripped = &text[prefix.len()..];
            break;
        }
    }
    stripped.trim().to_lowercase()
}

pub fn dependents(conn: &Connection, claim_id: &str) -> Vec<(String, usize)> {
    let mut seen = vec![claim_id.to_string()];
    let mut frontier = vec![claim_id.to_string()];
    let mut found = Vec::new();
    let mut depth = 0;
    while !frontier.is_empty() {
        depth += 1;
        let mut next = Vec::new();
        for current in &frontier {
            let rows = query_json(conn,
                "SELECT src_id FROM edge WHERE src_kind='claim' AND dst_kind='claim' AND dst_id=?1 AND rel IN ('derived_from','depends_on') ORDER BY src_id",
                params![current]).unwrap_or_default();
            for row in rows {
                let candidate = field(&row, "src_id");
                if seen.contains(&candidate) { continue; }
                seen.push(candidate.clone());
                found.push((candidate.clone(), depth));
                next.push(candidate);
            }
        }
        frontier = next;
    }
    found
}

fn plan_digest(conn: &Connection, claim_ids: &[String], source_ids: &[String]) -> String {
    let mut entries: Vec<String> = Vec::new();
    for id in claim_ids {
        let row = query_json(conn, "SELECT status, superseded_by FROM claim WHERE id=?1", params![id]);
        if let Some(row) = row.ok().and_then(|r| r.into_iter().next()) {
            entries.push(["claim", id.as_str(), field(&row, "status").as_str(),
                field(&row, "superseded_by").as_str()].join("|"));
        }
    }
    for id in source_ids {
        let row = query_json(conn, "SELECT status FROM source WHERE id=?1", params![id]);
        if let Some(row) = row.ok().and_then(|r| r.into_iter().next()) {
            entries.push(["source", id.as_str(), field(&row, "status").as_str(), ""].join("|"));
        }
    }
    entries.sort();
    sha256_text(&entries.join("\n"))
}

pub fn preview(conn: &Connection, reference: &str) -> Result<Value> {
    if let Ok(claim) = get_claim(conn, reference) {
        let planned = dependents(conn, &field(&claim, "id"));
        let affected: Vec<Value> = planned.iter().map(|(id, depth)| -> Result<Value> {
            let row = get_claim(conn, id)?;
            Ok(json!({
                "id": id, "depth": depth, "status": field(&row, "status"),
                "would_invalidate": !FAILED_STATUSES.contains(&field(&row, "status").as_str()),
                "text": field(&row, "text"),
            }))
        }).collect::<Result<Vec<_>>>()?;
        let mut claims = vec![field(&claim, "id")];
        claims.extend(planned.iter().map(|(id, _)| id.clone()));
        let digest = plan_digest(conn, &claims, &[]);
        return Ok(json!({"root": field(&claim, "id"), "root_status": field(&claim, "status"),
            "affected": affected, "digest": digest}));
    }
    let source = get_source(conn, reference)?;
    let mut sources = vec![field(&source, "id")];
    let work = normalize_doi(&field(&source, "doi"));
    if !work.is_empty() {
        for row in query_json(conn, "SELECT id, doi, status FROM source WHERE research_id=?1 AND id<>?2 ORDER BY id",
            params![field(&source, "research_id"), field(&source, "id")])? {
            if normalize_doi(&field(&row, "doi")) == work && field(&row, "status") != "retracted" {
                sources.push(field(&row, "id"));
            }
        }
    }
    let mut claim_ids = Vec::new();
    let mut affected = Vec::new();
    for source_id in &sources {
        for row in query_json(conn,
            "SELECT id, status, research_id FROM claim WHERE source_id=?1 AND status NOT IN ('FALSIFIED','RETRACTED','INVALIDATED') ORDER BY id",
            params![source_id])? {
            let claim = get_claim(conn, &field(&row, "id"))?;
            for (id, depth) in dependents(conn, &field(&claim, "id")) {
                if !claim_ids.contains(&id) { claim_ids.push(id.clone()); }
                let dependent = get_claim(conn, &id)?;
                affected.push(json!({"id": id, "depth": depth, "status": field(&dependent, "status"),
                    "would_invalidate": !FAILED_STATUSES.contains(&field(&dependent, "status").as_str()),
                    "text": field(&dependent, "text")}));
            }
            if !claim_ids.contains(&field(&claim, "id")) { claim_ids.push(field(&claim, "id")); }
            affected.push(json!({"id": field(&claim, "id"), "depth": 0,
                "status": field(&claim, "status"), "would_invalidate": true, "text": field(&claim, "text")}));
        }
    }
    let digest = plan_digest(conn, &claim_ids, &sources);
    Ok(json!({"root": field(&source, "id"), "root_status": field(&source, "status"),
        "affected": affected, "digest": digest}))
}

pub fn invalidate(
    conn: &Connection,
    reference: &str,
    status: &str,
    reason: &str,
    evidence: &str,
    actor: &str,
    allow_bulk: bool,
    expected_digest: &str,
) -> Result<Value> {
    if status != "FALSIFIED" && status != "RETRACTED" {
        return Err(EngineError::new(format!("invalid status for a collapse: {status}"),
            "a collapse must record the root claim as FALSIFIED or RETRACTED.",
            "pass --status FALSIFIED or --status RETRACTED."));
    }
    if reason.trim().is_empty() || evidence.trim().is_empty() {
        return Err(EngineError::new("collapse has no reason or evidence",
            "a dependent claim is only invalidated with an explicit reason and evidence path.",
            "pass --reason and --evidence."));
    }
    let root = get_claim(conn, reference)?;
    let planned = dependents(conn, &field(&root, "id"));
    if planned.len() > BULK_LIMIT && !allow_bulk {
        return Err(EngineError::new(format!("collapse would retire {} records", planned.len()),
            "a collapse this wide is usually a wrong root, not a real cascade.",
            "run `cascade preview`, then repeat with --allow-bulk when every dependent really falls."));
    }
    if !expected_digest.is_empty() {
        let mut claims = vec![field(&root, "id")];
        claims.extend(planned.iter().map(|(id, _)| id.clone()));
        if plan_digest(conn, &claims, &[]) != expected_digest {
            return Err(EngineError::new("the graph changed since the preview",
                "a status, edge or claim changed after `cascade preview` ran.",
                "re-run `cascade preview` and repeat with the fresh digest."));
        }
    }
    let tx = conn.unchecked_transaction()?;
    set_verdict_inner(&tx, &root, status, evidence, reason, "", actor)?;
    let mut affected = Vec::new();
    for (id, depth) in &planned {
        let dependent = get_claim(&tx, id)?;
        if FAILED_STATUSES.contains(&field(&dependent, "status").as_str()) { continue; }
        let previous = field(&dependent, "status");
        set_verdict_inner(&tx, &dependent, "INVALIDATED", &format!("cascade:{}", field(&root, "id")),
            &format!("premise {} became {status}: {reason}", field(&root, "id")), "", actor)?;
        affected.push(json!({"id": id, "depth": depth, "previous_status": previous}));
    }
    tx.execute(
        "INSERT INTO invalidation(id, root_kind, root_id, reason, actor, at, affected_json) VALUES (?1,'claim',?2,?3,?4,?5,?6)",
        params![next_id(&tx, "x")?, field(&root, "id"), reason.trim(), actor, utc_now(),
            serde_json::to_string(&affected)?],
    )?;
    tx.commit()?;
    Ok(json!({"root": field(&root, "id"), "status": status, "affected": affected,
        "failed_states": FAILED_STATUSES}))
}

pub fn retract_source(
    conn: &Connection,
    reference: &str,
    reason: &str,
    evidence: &str,
    actor: &str,
    allow_bulk: bool,
    expected_digest: &str,
) -> Result<Value> {
    if reason.trim().is_empty() || evidence.trim().is_empty() {
        return Err(EngineError::new("retraction has no reason or evidence",
            "claims are only retired with a recorded reason and evidence path.",
            "pass --reason and --evidence."));
    }
    let source = get_source(conn, reference)?;
    if field(&source, "status") == "retracted" {
        return Err(EngineError::new("source is already retracted",
            "a retraction is recorded once and then remains in the record.",
            "inspect the source and its affected claims."));
    }
    let plan = preview(conn, reference)?;
    let affected_view = plan.get("affected").and_then(Value::as_array).cloned().unwrap_or_default();
    if affected_view.len() > BULK_LIMIT && !allow_bulk {
        return Err(EngineError::new(format!("retraction would retire {} records", affected_view.len()),
            "a retraction this wide usually means the wrong source.",
            "run `cascade preview`, then repeat with --allow-bulk."));
    }
    if !expected_digest.is_empty() && field(&plan, "digest") != expected_digest {
        return Err(EngineError::new("the graph changed since the preview",
            "the source or its claims changed after `cascade preview` ran.",
            "re-run `cascade preview` and repeat with the fresh digest."));
    }
    let tx = conn.unchecked_transaction()?;
    let mut affected = Vec::new();
    for entry in &affected_view {
        let id = field(entry, "id");
        let claim = get_claim(&tx, &id)?;
        if FAILED_STATUSES.contains(&field(&claim, "status").as_str()) { continue; }
        let previous = field(&claim, "status");
        set_verdict_inner(&tx, &claim, "RETRACTED", evidence, reason, "", actor)?;
        let mut cascade = Vec::new();
        for (dep, _) in dependents(&tx, &id) {
            let d = get_claim(&tx, &dep)?;
            if FAILED_STATUSES.contains(&field(&d, "status").as_str()) { continue; }
            set_verdict_inner(&tx, &d, "INVALIDATED", &format!("cascade:{id}"),
                &format!("premise {id} was retracted: {reason}"), "", actor)?;
            cascade.push(dep);
        }
        affected.push(json!({"id": id, "previous_status": previous, "cascade": cascade}));
    }
    let work = normalize_doi(&field(&source, "doi"));
    if !work.is_empty() {
        for row in query_json(&tx, "SELECT id, doi, status FROM source WHERE research_id=?1 ORDER BY id",
            params![field(&source, "research_id")])? {
            if normalize_doi(&field(&row, "doi")) == work && field(&row, "status") != "retracted" {
                tx.execute("UPDATE source SET status='retracted', status_note=?1, status_at=?2 WHERE id=?3",
                    params![reason.trim(), utc_now(), field(&row, "id")])?;
            }
        }
    }
    tx.commit()?;
    Ok(json!({"source": field(&source, "id"), "affected": affected, "siblings": []}))
}
