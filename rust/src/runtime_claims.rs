//! Claim revision and merge: auditable history, one head, every edge repointed.
//! Ports engine/claims.py::revise_claim and engine/merging.py::merge_claims.

use rusqlite::{params, Connection};

use serde_json::Value;

use crate::core;
use crate::error::{EngineError, Result};
use crate::vocab::FAILED_STATUSES;

fn field(value: &Value, key: &str) -> String {
    value.get(key).and_then(Value::as_str).unwrap_or("").to_string()
}

fn is_failed(status: &str) -> bool {
    FAILED_STATUSES.iter().any(|s| *s == status)
}

pub fn revise_claim(
    conn: &Connection,
    reference: &str,
    text: &str,
    reason: &str,
    source_ref: Option<&str>,
    quote: &str,
    locator: &str,
    confidence: f64,
    kill_test: &str,
    basis: &str,
    prerequisites: &[String],
    actor: &str,
) -> Result<Value> {
    let old = core::get_claim(conn, reference)?;
    let old_id = field(&old, "id");
    let superseded = field(&old, "superseded_by");
    if !superseded.is_empty() {
        return Err(EngineError::new(
            format!("claim {old_id} is already superseded by {superseded}"),
            "a revision chain has one head; revise the head instead.",
            &format!("run `claim revise {superseded}` or inspect `claim history {old_id}`."),
        ));
    }
    if reason.trim().is_empty() {
        return Err(EngineError::new("revision has no reason",
            "a later reader must know why the assertion changed.",
            "pass --reason with the new evidence or narrowing."));
    }
    if prerequisites.iter().any(|p| p == &old_id) {
        return Err(EngineError::new(
            format!("revision lists {old_id} as its own prerequisite"),
            "the old claim is superseded by the revision; it cannot also support it.",
            "remove the revised claim from --from, or depend on a different claim."));
    }
    let tx = conn.unchecked_transaction()?;
    let new = core::add_claim_in(&tx, &field(&old, "research_id"), text,
        &field(&old, "kind"), source_ref, quote, locator, confidence, kill_test,
        basis, prerequisites, Some(&old_id), reason.trim())?;
    let new_id = field(&new, "id");
    repoint_edges(&tx, &old_id, &new_id)?;
    tx.execute("UPDATE claim SET superseded_by = ?1 WHERE id = ?2",
        params![new_id, old_id])?;
    core::record_event(&tx, &field(&old, "research_id"), "claim.revise", &new_id,
        &format!("{old_id} -> {new_id}: {}", reason.trim()), actor)?;
    tx.commit()?;
    core::get_claim(conn, &new_id)
}

/// Move every edge touching `from` onto `to`, then delete the original edges.
fn repoint_edges(conn: &Connection, from: &str, to: &str) -> Result<usize> {
    let mut stmt = conn.prepare(
        "SELECT id, src_kind, src_id, dst_kind, dst_id, rel FROM edge \
         WHERE (src_kind='claim' AND src_id=?1) OR (dst_kind='claim' AND dst_id=?1) \
         ORDER BY id")?;
    let rows: Vec<(String, String, String, String, String, String)> = stmt
        .query_map(params![from], |r| Ok((
            r.get(0)?, r.get(1)?, r.get(2)?, r.get(3)?, r.get(4)?, r.get(5)?)))?
        .collect::<std::result::Result<Vec<_>, _>>()?;
    let mut moved = 0;
    for (id, src_kind, src_id, dst_kind, dst_id, rel) in rows {
        let new_src = if src_kind == "claim" && src_id == from { to } else { &src_id };
        let new_dst = if dst_kind == "claim" && dst_id == from { to } else { &dst_id };
        if new_src == new_dst {
            continue;
        }
        core::record_edge(conn, &src_kind, new_src, &dst_kind, new_dst, &rel)?;
        let _ = id;
        moved += 1;
    }
    conn.execute(
        "DELETE FROM edge WHERE (src_kind='claim' AND src_id=?1) OR (dst_kind='claim' AND dst_id=?1)",
        params![from])?;
    Ok(moved)
}

pub fn merge_claims(conn: &Connection, keep_ref: &str, drop_refs: &[String],
                    note: &str, actor: &str) -> Result<Value> {
    let keep = core::get_claim(conn, keep_ref)?;
    let keep_id = field(&keep, "id");
    if drop_refs.is_empty() {
        return Err(EngineError::new("merge needs at least one duplicate",
            "merging one claim into itself changes nothing.",
            "pass one or more claim identifiers to merge into the survivor."));
    }
    if is_failed(&field(&keep, "status")) {
        return Err(EngineError::new(format!("survivor {keep_id} is {}", field(&keep, "status")),
            "a merge must keep a live claim, not a failed or retired one.",
            "choose the claim that remains part of the argument as the survivor."));
    }
    if !field(&keep, "superseded_by").is_empty() {
        return Err(EngineError::new(
            format!("survivor {keep_id} is superseded by {}", field(&keep, "superseded_by")),
            "a merge must keep the head of a revision chain.",
            "choose the head of the revision chain as the survivor."));
    }
    let mut drops = Vec::new();
    for reference in drop_refs {
        let claim = core::get_claim(conn, reference)?;
        let id = field(&claim, "id");
        if id == keep_id {
            return Err(EngineError::new("a claim cannot be merged into itself",
                "the survivor and the duplicate must differ.",
                "remove the survivor from the duplicate list."));
        }
        if field(&claim, "research_id") != field(&keep, "research_id") {
            return Err(EngineError::new("merge crosses research programs",
                "a program boundary is never rewritten by a merge.",
                "merge only claims from the same program."));
        }
        if is_failed(&field(&claim, "status")) {
            return Err(EngineError::new(format!("claim {id} is already {}", field(&claim, "status")),
                "a failed or retired claim has no live edges to repoint.",
                "choose a live duplicate."));
        }
        if !field(&claim, "superseded_by").is_empty() {
            return Err(EngineError::new(
                format!("claim {id} is superseded by {}", field(&claim, "superseded_by")),
                "a superseded claim is already history; merge the current head instead.",
                "choose a live duplicate from the current revision chain."));
        }
        drops.push(claim);
    }
    let tx = conn.unchecked_transaction()?;
    let mut moved = 0usize;
    let mut rebound = 0usize;
    let mut retired = Vec::new();
    for claim in &drops {
        let id = field(claim, "id");
        moved += repoint_edges(&tx, &id, &keep_id)?;
        for table in ["killtest", "observation", "ai_artifact"] {
            // These tables all carry a claim_id column.
            let count: usize = tx.execute(
                &format!("UPDATE {table} SET claim_id = ?1 WHERE claim_id = ?2"),
                params![keep_id, id])?;
            if table == "killtest" && count > 0 { rebound += 1; }
        }
    }
    for claim in &drops {
        let id = field(claim, "id");
        let evidence = if note.trim().is_empty() { format!("merged into {keep_id}") } else { note.trim().to_string() };
        core::set_verdict_inner(&tx, claim, "RETRACTED", &evidence, note.trim(), "", actor)?;
        retired.push(id);
    }
    core::record_event(&tx, &field(&keep, "research_id"), "claim.merge", &keep_id,
        &format!("retired {}", retired.join(", ")), actor)?;
    tx.commit()?;
    Ok(serde_json::json!({
        "keep": keep_id,
        "retired": retired,
        "edges_repointed": moved,
        "tests_repointed_from": rebound,
    }))
}
