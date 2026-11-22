//! Core lifecycle graph: programs, sources, questions, claims, hypotheses and edges.

use rusqlite::{params, Connection};
use serde_json::{json, Value};

use crate::db::{next_id, utc_now};
use crate::error::{EngineError, Result};
use crate::util::{query_json, slugify};
use crate::vocab::*;

fn one(conn: &Connection, sql: &str, id: &str, kind: &str) -> Result<Value> {
    let rows = query_json(conn, sql, params![id])?;
    rows.into_iter().next().ok_or_else(|| EngineError::not_found(kind, id))
}

pub fn get_research(conn: &Connection, reference: &str) -> Result<Value> {
    one(conn, "SELECT * FROM research WHERE id = ?1 OR slug = ?1", reference, "research")
}

pub fn get_source(conn: &Connection, id: &str) -> Result<Value> {
    one(conn, "SELECT * FROM source WHERE id = ?1", id, "source")
}

pub fn get_claim(conn: &Connection, id: &str) -> Result<Value> {
    one(conn, "SELECT * FROM claim WHERE id = ?1", id, "claim")
}

pub fn get_question(conn: &Connection, id: &str) -> Result<Value> {
    one(conn, "SELECT * FROM question WHERE id = ?1", id, "question")
}

pub fn get_hypothesis(conn: &Connection, id: &str) -> Result<Value> {
    one(conn, "SELECT * FROM hypothesis WHERE id = ?1", id, "hypothesis")
}

fn text(value: &Value, field: &str) -> String {
    value.get(field).and_then(Value::as_str).unwrap_or("").to_string()
}

fn validate_choice(value: &str, allowed: &[&str], what: &str, fix: &str) -> Result<()> {
    if is_member(value, allowed) {
        Ok(())
    } else {
        Err(EngineError::new(
            format!("{what}: {value}"),
            format!("allowed values are {}.", allowed.join(", ")),
            fix,
        ))
    }
}

// ---------------------------------------------------------------------------
// Research programs
// ---------------------------------------------------------------------------

pub fn add_research(conn: &Connection, title: &str, scope: &str, slug: Option<&str>) -> Result<Value> {
    let title = title.trim();
    if title.is_empty() {
        return Err(EngineError::new("research title is empty", "a program needs a name.", "pass a non-empty title."));
    }
    let tx = conn.unchecked_transaction()?;
    let chosen = match slug {
        Some(value) if !value.trim().is_empty() => value.trim().to_string(),
        _ => {
            let base = slugify(title);
            let mut candidate = base.clone();
            let mut suffix = 2;
            while tx.query_row("SELECT 1 FROM research WHERE slug = ?1", params![candidate], |_| Ok(()))
                .is_ok()
            {
                candidate = format!("{base}-{suffix}");
                suffix += 1;
            }
            candidate
        }
    };
    if chosen.is_empty()
        || !chosen.chars().next().map(|c| c.is_ascii_alphanumeric()).unwrap_or(false)
        || !chosen.chars().all(|c| c.is_ascii_alphanumeric() || c == '-')
    {
        return Err(EngineError::new(
            format!("invalid research slug: {chosen}"),
            "slugs are lowercase letters, digits and hyphens, and start with a letter or digit.",
            "use a slug such as `fluid-universe`.",
        ));
    }
    if tx.query_row("SELECT 1 FROM research WHERE slug = ?1", params![chosen], |_| Ok(())).is_ok() {
        return Err(EngineError::new(
            format!("research slug already exists: {chosen}"),
            "two programs cannot share a slug.",
            "choose another slug or use `research show` on the existing program.",
        ));
    }
    let id = next_id(&tx, "r")?;
    let stamp = utc_now();
    tx.execute(
        "INSERT INTO research(id, slug, title, scope, created_at) VALUES (?1,?2,?3,?4,?5)",
        params![id, chosen, title, scope.trim(), stamp],
    )?;
    tx.commit()?;
    get_research(conn, &id)
}

pub fn list_researches(conn: &Connection) -> Result<Vec<Value>> {
    query_json(conn, "SELECT * FROM research ORDER BY id", [])
}

pub fn research_counts(conn: &Connection, id: &str) -> Result<Value> {
    get_research(conn, id)?;
    let mut out = serde_json::Map::new();
    for table in ["source", "question", "claim", "hypothesis", "killtest"] {
        let n: i64 = conn.query_row(&format!("SELECT COUNT(*) FROM {table} WHERE research_id = ?1"), params![id], |r| r.get(0))?;
        out.insert(table.to_string(), json!(n));
    }
    let open: i64 = conn.query_row(
        "SELECT COUNT(*) FROM question WHERE research_id = ?1 AND status = 'open'", params![id], |r| r.get(0))?;
    out.insert("open_questions".to_string(), json!(open));
    Ok(Value::Object(out))
}

// ---------------------------------------------------------------------------
// Sources
// ---------------------------------------------------------------------------

#[allow(clippy::too_many_arguments)]
pub fn add_source(
    conn: &Connection,
    research_ref: &str,
    title: &str,
    year: Option<i64>,
    doi: &str,
    url: &str,
    authors: &str,
    kind: &str,
) -> Result<Value> {
    let research = get_research(conn, research_ref)?;
    let title = title.trim();
    if title.is_empty() {
        return Err(EngineError::new("source title is empty", "a source needs a title.", "pass --title."));
    }
    validate_choice(kind, SOURCE_KINDS, &format!("unknown source kind: {kind}"), "pass one of the listed kinds with --kind.")?;
    if let Some(year) = year {
        if !(1000..=9999).contains(&year) {
            return Err(EngineError::new(
                format!("implausible year: {year}"),
                "the year must be a four-digit calendar year.",
                "pass the publication year, for example --year 2024.",
            ));
        }
    }
    if doi.trim().is_empty() && url.trim().is_empty() && year.is_none() {
        return Err(EngineError::new(
            "source has no identifier",
            "without a DOI, URL or year the source cannot be audited or found again.",
            "pass at least one of --doi, --url or --year.",
        ));
    }
    let tx = conn.unchecked_transaction()?;
    let id = next_id(&tx, "s")?;
    tx.execute(&(
        "INSERT INTO source(id, research_id, kind, title, authors, year, doi, url, retrieved_at)"
            .to_owned() + " VALUES (?1,?2,?3,?4,?5,?6,?7,?8,?9)"),
        params![id, text(&research, "id"), kind, title, authors.trim(), year, doi.trim(), url.trim(), utc_now()],
    )?;
    tx.commit()?;
    get_source(conn, &id)
}

pub fn list_sources(conn: &Connection, research_ref: Option<&str>) -> Result<Vec<Value>> {
    if let Some(reference) = research_ref {
        let research = get_research(conn, reference)?;
        query_json(conn, "SELECT * FROM source WHERE research_id = ?1 ORDER BY id", params![text(&research, "id")])
    } else {
        query_json(conn, "SELECT * FROM source ORDER BY id", [])
    }
}

pub fn set_source_status(conn: &Connection, id: &str, status: &str, note: &str) -> Result<Value> {
    validate_choice(status, SOURCE_STATUSES, &format!("unknown source status: {status}"), "pass one of the listed statuses with --status.")?;
    let source = get_source(conn, id)?;
    let tx = conn.unchecked_transaction()?;
    tx.execute(
        "UPDATE source SET status = ?1, status_note = ?2, status_at = ?3 WHERE id = ?4",
        params![status, note.trim(), utc_now(), text(&source, "id")],
    )?;
    tx.commit()?;
    get_source(conn, id)
}

pub fn set_screening(conn: &Connection, id: &str, status: &str, reason: &str) -> Result<Value> {
    validate_choice(status, SCREENING_STATUSES, &format!("unknown screening status: {status}"), "pass one of the listed statuses with --status.")?;
    if !reason.is_empty() {
        validate_choice(reason, SCREENING_REASONS, &format!("unknown screening reason: {reason}"), "pass a reason from the closed taxonomy.")?;
    }
    let source = get_source(conn, id)?;
    let tx = conn.unchecked_transaction()?;
    tx.execute(
        "UPDATE source SET screening = ?1, screening_reason = ?2, screening_at = ?3 WHERE id = ?4",
        params![status, reason, utc_now(), text(&source, "id")],
    )?;
    tx.commit()?;
    get_source(conn, id)
}

// ---------------------------------------------------------------------------
// Questions
// ---------------------------------------------------------------------------

pub fn add_question(conn: &Connection, research_ref: &str, question: &str) -> Result<Value> {
    let research = get_research(conn, research_ref)?;
    let question = question.trim();
    if question.is_empty() {
        return Err(EngineError::new("question text is empty", "a question needs a sentence.", "pass the question text."));
    }
    let tx = conn.unchecked_transaction()?;
    let id = next_id(&tx, "q")?;
    tx.execute(
        "INSERT INTO question(id, research_id, text, status, created_at) VALUES (?1,?2,?3,'open',?4)",
        params![id, text(&research, "id"), question, utc_now()],
    )?;
    tx.commit()?;
    get_question(conn, &id)
}

pub fn list_questions(conn: &Connection, research_ref: Option<&str>) -> Result<Vec<Value>> {
    if let Some(reference) = research_ref {
        let research = get_research(conn, reference)?;
        query_json(conn, "SELECT * FROM question WHERE research_id = ?1 ORDER BY id", params![text(&research, "id")])
    } else {
        query_json(conn, "SELECT * FROM question ORDER BY id", [])
    }
}

pub fn close_question(conn: &Connection, id: &str) -> Result<Value> {
    let question = get_question(conn, id)?;
    if text(&question, "status") == "closed" {
        return Err(EngineError::new(
            format!("question {id} is already closed"),
            "closing twice would hide when the question was actually resolved.",
            "list open questions instead, or inspect this one's history.",
        ));
    }
    let tx = conn.unchecked_transaction()?;
    tx.execute("UPDATE question SET status = 'closed' WHERE id = ?1", params![id])?;
    tx.commit()?;
    get_question(conn, id)
}

// ---------------------------------------------------------------------------
// Edges, claims and verdicts
// ---------------------------------------------------------------------------

pub fn record_edge(
    conn: &Connection,
    src_kind: &str,
    src_id: &str,
    dst_kind: &str,
    dst_id: &str,
    rel: &str,
) -> Result<String> {
    let exists: bool = conn.query_row(
        "SELECT 1 FROM edge WHERE src_kind=?1 AND src_id=?2 AND dst_kind=?3 AND dst_id=?4 AND rel=?5",
        params![src_kind, src_id, dst_kind, dst_id, rel], |_| Ok(true)).unwrap_or(false);
    if exists {
        let id: String = conn.query_row(
            "SELECT id FROM edge WHERE src_kind=?1 AND src_id=?2 AND dst_kind=?3 AND dst_id=?4 AND rel=?5",
            params![src_kind, src_id, dst_kind, dst_id, rel], |r| r.get(0))?;
        return Ok(id);
    }
    let id = next_id(conn, "e")?;
    conn.execute(
        "INSERT INTO edge(id, src_kind, src_id, dst_kind, dst_id, rel, created_at) VALUES (?1,?2,?3,?4,?5,?6,?7)",
        params![id, src_kind, src_id, dst_kind, dst_id, rel, utc_now()],
    )?;
    Ok(id)
}

#[allow(clippy::too_many_arguments)]
pub fn add_claim(
    conn: &Connection,
    research_ref: &str,
    claim_text: &str,
    kind: &str,
    source_ref: Option<&str>,
    quote: &str,
    locator: &str,
    confidence: f64,
    kill_test: &str,
    basis: &str,
    prerequisites: &[String],
) -> Result<Value> {
    let research = get_research(conn, research_ref)?;
    let claim_text = claim_text.trim();
    if claim_text.is_empty() {
        return Err(EngineError::new("claim text is empty", "a claim is an assertion.", "pass --text."));
    }
    validate_choice(kind, CLAIM_KINDS, &format!("unknown claim kind: {kind}"), "pass one of the listed kinds with --kind.")?;
    if !(0.0..=1.0).contains(&confidence) {
        return Err(EngineError::new(
            format!("confidence out of range: {confidence}"),
            "confidence is a probability in the closed interval [0, 1].",
            "pass a value such as --confidence 0.7.",
        ));
    }
    let mut source_id: Option<String> = None;
    if kind == "empirical" {
        let source_ref = source_ref.ok_or_else(|| EngineError::new(
            "empirical claim has no source",
            "every empirical claim needs a registered source for provenance.",
            "register the source with `source add`, then pass --source.",
        ))?;
        let source = get_source(conn, source_ref)?;
        if text(&source, "research_id") != text(&research, "id") {
            return Err(EngineError::new(
                "source belongs to another research program",
                "evidence cannot cross program boundaries in one claim.",
                "register the source in this program or use the program that owns it.",
            ));
        }
        if quote.trim().is_empty() || locator.trim().is_empty() {
            return Err(EngineError::new(
                "empirical claim has no quote or locator",
                "a claim without an exact quote and a locator cannot be audited.",
                "pass --quote with the source sentence and --locator with its section, page or line.",
            ));
        }
        source_id = Some(text(&source, "id"));
    } else if !quote.trim().is_empty() {
        return Err(EngineError::new(
            "quote supplied for a non-empirical claim",
            "quotes are evidence from a source; derived and assumed claims argue instead.",
            "remove --quote and use --basis for the derivation or assumption.",
        ));
    }
    if kind != "empirical" && source_ref.is_some() {
        return Err(EngineError::new(
            "source supplied for a non-empirical claim",
            "only empirical claims cite a source; derived and assumed claims use a basis.",
            "remove --source or record the assertion as empirical.",
        ));
    }
    if kind == "derived" && basis.trim().is_empty() && prerequisites.is_empty() {
        return Err(EngineError::new(
            "derived claim has no basis",
            "a derived claim must name its premises or its derivation.",
            "pass --basis with the argument or --from with one or more prerequisite claim IDs.",
        ));
    }
    let mut prereq_ids = Vec::new();
    for reference in prerequisites {
        let claim = get_claim(conn, reference)?;
        if text(&claim, "research_id") != text(&research, "id") {
            return Err(EngineError::new(
                "prerequisite belongs to another research program",
                "dependency edges cannot cross program boundaries.",
                "link claims from the same program.",
            ));
        }
        if !claim.get("superseded_by").and_then(Value::as_str).unwrap_or("").is_empty() {
            return Err(EngineError::new(
                format!("prerequisite {reference} is superseded"),
                "a new claim must depend on the current head, not on history.",
                "use the current head claim as the prerequisite.",
            ));
        }
        prereq_ids.push(text(&claim, "id"));
    }
    let tx = conn.unchecked_transaction()?;
    let id = next_id(&tx, "c")?;
    let stamp = utc_now();
    tx.execute(&(
        "INSERT INTO claim(id, research_id, source_id, text, quote, locator, kind, basis,"
            .to_owned() + " kill_test, status, confidence, created_at, updated_at)"
            + " VALUES (?1,?2,?3,?4,?5,?6,?7,?8,?9,'UNVERIFIED',?10,?11,?11)"),
        params![id, text(&research, "id"), source_id, claim_text, quote.trim(), locator.trim(),
            kind, basis.trim(), kill_test.trim(), confidence, stamp],
    )?;
    for prereq in &prereq_ids {
        record_edge(&tx, "claim", &id, "claim", prereq, "derived_from")?;
    }
    tx.commit()?;
    get_claim(conn, &id)
}

pub fn list_claims(conn: &Connection, research_ref: Option<&str>, status: Option<&str>, history: bool) -> Result<Vec<Value>> {
    let mut sql = String::from("SELECT * FROM claim WHERE 1=1");
    let mut params_vec: Vec<Box<dyn rusqlite::ToSql>> = Vec::new();
    if let Some(reference) = research_ref {
        let research = get_research(conn, reference)?;
        sql.push_str(" AND research_id = ?");
        params_vec.push(Box::new(text(&research, "id")));
    }
    if let Some(status) = status {
        sql.push_str(" AND status = ?");
        params_vec.push(Box::new(status.to_string()));
    }
    if !history {
        sql.push_str(" AND (superseded_by IS NULL OR superseded_by = '')");
    }
    sql.push_str(" ORDER BY id");
    let bindings: Vec<&dyn rusqlite::ToSql> = params_vec.iter().map(|p| p.as_ref()).collect();
    query_json(conn, &sql, bindings.as_slice())
}

pub fn set_verdict(
    conn: &Connection,
    reference: &str,
    status: &str,
    evidence: &str,
    note: &str,
    group: &str,
    actor: &str,
) -> Result<Value> {
    validate_choice(status, CLAIM_STATUSES, &format!("unknown claim status: {status}"), "pass one of the listed statuses with --status.")?;
    let claim = get_claim(conn, reference)?;
    if status == "NUMERIC" {
        crate::killtest::numeric_gate(conn, &text(&claim, "id"))?;
        let valid = crate::killtest::claim_groups(conn, &text(&claim, "id"))?;
        if group.is_empty() || !valid.iter().any(|g| g == group) {
            return Err(EngineError::new(
                format!("NUMERIC verdict is not tied to an authoritative run group: {}", if group.is_empty() { "none" } else { group }),
                "the promotion must cite the verified group that is current for this test.",
                &format!("run `test verify`, then pass --group {} with one of: {}.",
                    valid.first().cloned().unwrap_or_else(|| "<group>".to_string()),
                    if valid.is_empty() { "none".to_string() } else { valid.join(", ") }),
            ));
        }
    }
    let tx = conn.unchecked_transaction()?;
    let result = set_verdict_inner(&tx, &claim, status, evidence, note, group, actor)?;
    tx.commit()?;
    Ok(result)
}

/// Insert one verdict without opening a transaction; callers that cascade
/// several retirements wrap this in a single transaction.
pub fn set_verdict_inner(
    conn: &Connection,
    claim: &Value,
    status: &str,
    evidence: &str,
    note: &str,
    group: &str,
    actor: &str,
) -> Result<Value> {
    let id = next_id(conn, "v")?;
    conn.execute(&(
        "INSERT INTO verdict(id, subject_kind, subject_id, status, previous_status, evidence, note, actor, at, evidence_group)"
            .to_owned() + " VALUES (?1,'claim',?2,?3,?4,?5,?6,?7,?8,?9)"),
        params![id, text(claim, "id"), status, text(claim, "status"), evidence, note, actor, utc_now(), group],
    )?;
    conn.execute("UPDATE claim SET status = ?1, updated_at = ?2 WHERE id = ?3",
        params![status, utc_now(), text(claim, "id")])?;
    get_claim(conn, &text(claim, "id"))
}

// ---------------------------------------------------------------------------
// Hypotheses
// ---------------------------------------------------------------------------

pub fn add_hypothesis(
    conn: &Connection,
    research_ref: &str,
    statement: &str,
    criterion: &str,
    confidence: f64,
    question_ref: Option<&str>,
) -> Result<Value> {
    let research = get_research(conn, research_ref)?;
    if statement.trim().is_empty() {
        return Err(EngineError::new("hypothesis statement is empty", "a hypothesis needs a claim to test.", "pass --statement."));
    }
    if criterion.trim().is_empty() {
        return Err(EngineError::new("hypothesis criterion is empty", "a hypothesis needs a refuting observation at registration.", "pass --criterion."));
    }
    if !(0.0..=1.0).contains(&confidence) {
        return Err(EngineError::new("confidence out of range", "confidence is a probability in [0, 1].", "pass a value such as --confidence 0.7."));
    }
    let question_id = match question_ref {
        Some(reference) => {
            let question = get_question(conn, reference)?;
            if text(&question, "research_id") != text(&research, "id") {
                return Err(EngineError::new("question belongs to another program", "a hypothesis cannot cross program boundaries.", "use a question from this program."));
            }
            Some(text(&question, "id"))
        }
        None => None,
    };
    let tx = conn.unchecked_transaction()?;
    let id = next_id(&tx, "h")?;
    let stamp = utc_now();
    tx.execute(&(
        "INSERT INTO hypothesis(id, research_id, question_id, statement, criterion, confidence, registered_at, status, updated_at)"
            .to_owned() + " VALUES (?1,?2,?3,?4,?5,?6,?7,'PREREGISTERED',?7)"),
        params![id, text(&research, "id"), question_id, statement.trim(), criterion.trim(), confidence, stamp],
    )?;
    tx.commit()?;
    get_hypothesis(conn, &id)
}

pub fn list_hypotheses(conn: &Connection, research_ref: Option<&str>) -> Result<Vec<Value>> {
    if let Some(reference) = research_ref {
        let research = get_research(conn, reference)?;
        query_json(conn, "SELECT * FROM hypothesis WHERE research_id = ?1 ORDER BY id", params![text(&research, "id")])
    } else {
        query_json(conn, "SELECT * FROM hypothesis ORDER BY id", [])
    }
}

pub fn record_outcome(conn: &Connection, id: &str, status: &str, evidence: &str, note: &str, actor: &str) -> Result<Value> {
    validate_choice(status, HYPOTHESIS_OUTCOMES, &format!("unknown outcome: {status}"), "pass one of the listed outcomes with --status.")?;
    let hypothesis = get_hypothesis(conn, id)?;
    let tx = conn.unchecked_transaction()?;
    let vid = next_id(&tx, "v")?;
    tx.execute(&(
        "INSERT INTO verdict(id, subject_kind, subject_id, status, previous_status, evidence, note, actor, at)"
            .to_owned() + " VALUES (?1,'hypothesis',?2,?3,?4,?5,?6,?7,?8)"),
        params![vid, id, status, text(&hypothesis, "status"), evidence, note, actor, utc_now()],
    )?;
    tx.execute("UPDATE hypothesis SET status = ?1, outcome_note = ?2, updated_at = ?3 WHERE id = ?4",
        params![status, note, utc_now(), id])?;
    tx.commit()?;
    get_hypothesis(conn, id)
}

// ---------------------------------------------------------------------------
// Events (hash-chained ledger)
// ---------------------------------------------------------------------------

pub fn record_event(
    conn: &Connection,
    research_id: &str,
    kind: &str,
    subject: &str,
    detail: &str,
    actor: &str,
) -> Result<String> {
    let id = next_id(conn, "ev")?;
    let at = utc_now();
    let previous: Option<(String, String)> = conn
        .query_row("SELECT id, event_hash FROM event WHERE event_hash <> '' ORDER BY seq DESC, id DESC LIMIT 1", [], |r| Ok((r.get(0)?, r.get(1)?)))
        .optional()?;
    let (prev_id, prev_hash) = previous.unwrap_or_default();
    let seq: i64 = conn.query_row("SELECT COALESCE(MAX(seq), 0) + 1 FROM event", [], |r| r.get(0))?;
    let root_id = if prev_id.is_empty() { id.clone() } else {
        let root: String = conn.query_row("SELECT root_id FROM event WHERE id = ?1", params![prev_id], |r| r.get(0))?;
        if root.is_empty() { prev_id.clone() } else { root }
    };
    let event_hash = crate::util::event_hash_for(
        &prev_hash, &id, &at, research_id, kind, subject, detail, actor, seq, &root_id, &prev_id,
    );
    conn.execute(&(
        "INSERT INTO event(id, at, research_id, kind, subject, detail, actor, seq, root_id, parent_id, prev_hash, event_hash)"
            .to_owned() + " VALUES (?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?12)"),
        params![id, at, research_id, kind, subject, detail, actor, seq, root_id, prev_id, prev_hash, event_hash],
    )?;
    Ok(id)
}

pub fn verify_events(conn: &Connection) -> Result<Value> {
    let rows = query_json(conn, "SELECT * FROM event WHERE event_hash <> '' ORDER BY seq, id", [])?;
    let mut checked = 0usize;
    let mut errors: Vec<String> = Vec::new();
    let mut previous_hash = String::new();
    for event in &rows {
        let id = text(event, "id");
        let at = text(event, "at");
        let rid = text(event, "research_id");
        let kind = text(event, "kind");
        let subject = text(event, "subject");
        let detail = text(event, "detail");
        let actor = text(event, "actor");
        let seq = event.get("seq").and_then(Value::as_i64).unwrap_or(0);
        let root = text(event, "root_id");
        let parent = text(event, "parent_id");
        let prev = text(event, "prev_hash");
        let stored = text(event, "event_hash");
        if prev != previous_hash {
            errors.push(format!("{id}: prev_hash does not match the preceding event"));
        }
        if crate::util::event_hash_for(&prev, &id, &at, &rid, &kind, &subject, &detail, &actor, seq, &root, &parent) != stored {
            errors.push(format!("{id}: event_hash mismatch"));
        }
        previous_hash = stored;
        checked += 1;
    }
    Ok(json!({"ok": errors.is_empty(), "checked": checked, "errors": errors}))
}

use rusqlite::OptionalExtension;
