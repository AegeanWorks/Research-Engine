//! Lattice knowledge-graph repository: papers, claims, questions, typed edges.
//! Port of `adapters/lattice/repository.py` over its own schema-v2 SQLite store.

use std::collections::{BTreeMap, BTreeSet};

use rusqlite::{params, Connection};
use serde_json::{json, Value};

use crate::error::{EngineError, Result};
use crate::lattice;
use crate::util::query_json;

pub const SCHEMA_VERSION: i64 = 2;

const SCHEMA: &str = r#"
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS papers (
    id TEXT PRIMARY KEY, kind TEXT NOT NULL DEFAULT 'paper', title TEXT NOT NULL,
    authors TEXT NOT NULL DEFAULT '', year TEXT NOT NULL DEFAULT '', venue TEXT NOT NULL DEFAULT '',
    doi TEXT NOT NULL DEFAULT '', arxiv TEXT NOT NULL DEFAULT '', url TEXT NOT NULL DEFAULT '',
    abstract TEXT NOT NULL DEFAULT '', tags TEXT NOT NULL DEFAULT '',
    study_type TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL);
CREATE UNIQUE INDEX IF NOT EXISTS papers_doi ON papers(lower(doi)) WHERE doi != '';
CREATE UNIQUE INDEX IF NOT EXISTS papers_arxiv ON papers(lower(arxiv)) WHERE arxiv != '';
CREATE TABLE IF NOT EXISTS claims (
    id TEXT PRIMARY KEY, paper_id TEXT NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    text TEXT NOT NULL, quote TEXT NOT NULL, locator TEXT NOT NULL DEFAULT '',
    stance TEXT NOT NULL CHECK (stance IN ('supports','contradicts','mentions')),
    confidence REAL NOT NULL DEFAULT 0.5 CHECK (confidence >= 0 AND confidence <= 1),
    created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS questions (
    id TEXT PRIMARY KEY, text TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','answered','abandoned')),
    created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS edges (
    id INTEGER PRIMARY KEY AUTOINCREMENT, src TEXT NOT NULL, dst TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('cites','supports','contradicts','replicates','extends',
        'uses_method','measures','answers','mentions','related')),
    note TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, UNIQUE(src, dst, kind));
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL, action TEXT NOT NULL, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS screening (
    paper_id TEXT PRIMARY KEY REFERENCES papers(id) ON DELETE CASCADE,
    status TEXT NOT NULL CHECK (status IN ('identified','screened_in','screened_out','included','excluded')),
    reason TEXT NOT NULL DEFAULT '', notes TEXT NOT NULL DEFAULT '', screened_at TEXT NOT NULL);
"#;

fn field(value: &Value, name: &str) -> String {
    value.get(name).and_then(Value::as_str).unwrap_or("").to_string()
}

fn utc_now() -> String {
    chrono::Utc::now().format("%Y-%m-%dT%H:%M:%S+00:00").to_string()
}

pub fn open(path: &str) -> Result<Connection> {
    if path != ":memory:" {
        if let Some(parent) = std::path::Path::new(path).parent() {
            if !parent.as_os_str().is_empty() { std::fs::create_dir_all(parent)?; }
        }
    }
    let conn = Connection::open(path)?;
    conn.execute_batch("PRAGMA foreign_keys=ON; PRAGMA busy_timeout=3000; PRAGMA synchronous=FULL;")?;
    conn.execute_batch(SCHEMA)?;
    conn.execute("INSERT OR IGNORE INTO meta(key, value) VALUES('schema_version', ?1)",
        params![SCHEMA_VERSION.to_string()])?;
    Ok(conn)
}

fn normalize_doi(value: &str) -> String {
    let text = value.trim();
    let lowered = text.to_lowercase();
    for prefix in ["https://doi.org/", "http://doi.org/", "doi:"] {
        if lowered.starts_with(prefix) { return text[prefix.len()..].trim().to_lowercase(); }
    }
    lowered
}

fn normalize_arxiv(value: &str) -> String {
    let text = value.trim();
    if text.to_lowercase().starts_with("arxiv:") { text[6..].trim().to_string() } else { text.to_string() }
}

pub fn resolve_ref(value: &str) -> Result<String> {
    resolve(value)
}

pub fn summary_public(conn: &Connection, reference: &str) -> Value {
    summary(conn, reference)
}

fn resolve(value: &str) -> Result<String> {
    let text = value.trim();
    if text.contains(':') { return lattice::validate_ref(text); }
    if let Some(kind) = text.chars().next().filter(|c| matches!(c, 'p' | 'c' | 'q')) {
        if text.chars().nth(1) == Some('_') {
            let name = match kind { 'p' => "paper", 'c' => "claim", _ => "question" };
            return Ok(format!("{name}:{text}"));
        }
    }
    Err(EngineError::new(format!("'{value}' is not an entity reference"),
        "ids look like p_xxx, c_xxx or q_xxx",
        "use `search` to find an id, then pass it with its prefix"))
}

fn one(conn: &Connection, table: &str, id: &str) -> Option<Value> {
    query_json(conn, &format!("SELECT * FROM {table} WHERE id=?1"), params![id])
        .ok().and_then(|rows| rows.into_iter().next())
}

fn paper_json(row: Value) -> Value { row }
fn claim_json(row: Value) -> Value { row }
fn question_json(row: Value) -> Value { row }

pub fn add_paper(conn: &Connection, metadata: &BTreeMap<String, String>) -> Result<(Value, bool)> {
    let title = metadata.get("title").map(|s| s.trim()).unwrap_or("");
    if title.is_empty() {
        return Err(EngineError::new("a paper needs a title", "the title is the human-facing identity",
            "pass title in the BibTeX, RIS, CSV or front matter"));
    }
    let get = |key: &str| metadata.get(key).map(|s| s.trim()).unwrap_or("").to_string();
    let mut record = BTreeMap::new();
    for name in ["kind", "title", "authors", "year", "venue", "doi", "arxiv", "url",
        "abstract", "tags", "study_type"] {
        record.insert(name.to_string(), get(name));
    }
    record.insert("title".to_string(), title.to_string());
    record.insert("doi".to_string(), normalize_doi(&get("doi")));
    record.insert("arxiv".to_string(), normalize_arxiv(&get("arxiv")));
    if record["kind"].is_empty() { record.insert("kind".to_string(), "paper".to_string()); }
    let tags = if record["tags"].is_empty() {
        lattice::derive_tags(title, &record["abstract"], 6)?
    } else { lattice::normalize_tags(&record["tags"]) };
    record.insert("tags".to_string(), tags);
    let study_type = {
        let explicit = lattice::normalize_study_type(&record["study_type"]);
        if explicit.is_empty() { lattice::infer_study_type(title, &record["abstract"]) } else { explicit }
    };
    record.insert("study_type".to_string(), study_type);

    // Duplicate detection: DOI, arXiv, then normalized title with compatible year.
    let mut existing: Option<Value> = None;
    if !record["doi"].is_empty() {
        existing = query_json(conn, "SELECT * FROM papers WHERE lower(doi)=?1", params![record["doi"].to_lowercase()])?
            .into_iter().next();
    }
    if existing.is_none() && !record["arxiv"].is_empty() {
        existing = query_json(conn, "SELECT * FROM papers WHERE lower(arxiv)=?1", params![record["arxiv"].to_lowercase()])?
            .into_iter().next();
    }
    if existing.is_none() {
        let wanted = lattice::normalize_text(&record["title"]);
        for row in query_json(conn, "SELECT * FROM papers", [])? {
            if lattice::normalize_text(&field(&row, "title")) != wanted { continue; }
            let year = field(&row, "year");
            if record["year"].is_empty() || year.is_empty() || year == record["year"] {
                existing = Some(row);
                break;
            }
        }
    }
    if let Some(old) = existing {
        let mut updates: BTreeMap<String, String> = BTreeMap::new();
        for name in ["kind", "title", "authors", "year", "venue", "doi", "arxiv", "url",
            "abstract", "tags", "study_type"] {
            if !record[name].is_empty() && field(&old, name).is_empty() {
                updates.insert(name.to_string(), record[name].clone());
            }
        }
        let id = field(&old, "id");
        if !updates.is_empty() {
            let assignments: Vec<String> = updates.keys().map(|k| format!("{k}=?")).collect();
            let mut values: Vec<&dyn rusqlite::ToSql> = updates.values().map(|v| v as &dyn rusqlite::ToSql).collect();
            values.push(&id);
            let sql = format!("UPDATE papers SET {} WHERE id=?", assignments.join(", "));
            conn.execute(&sql, values.as_slice())?;
        }
        log(conn, "paper.merge", &json!({"id": id, "changed": updates.keys().collect::<Vec<_>>()}))?;
        return Ok((one(conn, "papers", &id).unwrap(), false));
    }

    let id = lattice::paper_id(title, &record["doi"], &record["arxiv"])?;
    let tx = conn.unchecked_transaction()?;
    tx.execute(
        "INSERT INTO papers(id,kind,title,authors,year,venue,doi,arxiv,url,abstract,tags,study_type,created_at) VALUES (?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?12,?13)",
        params![id, record["kind"], record["title"], record["authors"], record["year"],
            record["venue"], record["doi"], record["arxiv"], record["url"], record["abstract"],
            record["tags"], record["study_type"], utc_now()],
    )?;
    tx.commit()?;
    log(conn, "paper.add", &json!({"id": id}))?;
    Ok((one(conn, "papers", &id).unwrap(), true))
}

pub fn add_claim(conn: &Connection, paper: &str, text: &str, quote: &str, locator: &str,
                 stance: &str, confidence: f64) -> Result<Value> {
    let paper_ref = resolve(paper)?;
    let bare = lattice::bare_id(&paper_ref)?;
    if !paper_ref.starts_with("paper:") {
        return Err(EngineError::new(format!("'{paper}' is not a paper reference"),
            "claims must point at a source paper", "pass --paper paper:p_xxx or the bare p_xxx id"));
    }
    if one(conn, "papers", &bare).is_none() {
        return Err(EngineError::new(format!("paper '{paper}' does not exist"),
            "a claim must cite an ingested source", "ingest the paper first, then pass its p_ id"));
    }
    let claim_text: String = text.split_whitespace().collect::<Vec<_>>().join(" ");
    let source_quote: String = quote.split_whitespace().collect::<Vec<_>>().join(" ");
    if claim_text.is_empty() {
        return Err(EngineError::new("a claim needs text", "an empty claim carries no assertion", "pass the claim as --text"));
    }
    if source_quote.is_empty() {
        return Err(EngineError::new("a claim needs a quote", "provenance is the point of the graph", "pass the exact source sentence as --quote"));
    }
    let clean_locator = lattice::validate_locator(locator)?;
    let ids: Vec<String> = query_json(conn, "SELECT id FROM claims", [])?
        .into_iter().map(|r| field(&r, "id")).collect();
    let id = lattice::next_id("c", &ids);
    let tx = conn.unchecked_transaction()?;
    tx.execute(
        "INSERT INTO claims(id,paper_id,text,quote,locator,stance,confidence,created_at) VALUES (?1,?2,?3,?4,?5,?6,?7,?8)",
        params![id, bare, claim_text, source_quote, clean_locator,
            lattice::validate_stance(Some(stance))?, lattice::parse_confidence(Some(confidence))?, utc_now()],
    )?;
    tx.commit()?;
    log(conn, "claim.add", &json!({"id": id, "paper": paper_ref}))?;
    Ok(one(conn, "claims", &id).unwrap())
}

pub fn add_question(conn: &Connection, text: &str) -> Result<Value> {
    let value: String = text.split_whitespace().collect::<Vec<_>>().join(" ");
    if value.is_empty() {
        return Err(EngineError::new("a question needs text", "an empty question cannot collect evidence", "pass the question as a quoted argument"));
    }
    let ids: Vec<String> = query_json(conn, "SELECT id FROM questions", [])?
        .into_iter().map(|r| field(&r, "id")).collect();
    let id = lattice::next_id("q", &ids);
    let tx = conn.unchecked_transaction()?;
    tx.execute("INSERT INTO questions(id,text,status,created_at) VALUES (?1,?2,'open',?3)",
        params![id, value, utc_now()])?;
    tx.commit()?;
    log(conn, "question.add", &json!({"id": id}))?;
    Ok(one(conn, "questions", &id).unwrap())
}

pub fn add_edge(conn: &Connection, src: &str, dst: &str, kind: &str, note: &str) -> Result<Value> {
    let source = resolve(src)?;
    let target = resolve(dst)?;
    if source == target {
        return Err(EngineError::new("an edge needs two different endpoints", "a self-relation adds no information",
            "link the entity to a different paper, claim or question"));
    }
    let edge_kind = lattice::validate_edge_kind(kind)?;
    let tx = conn.unchecked_transaction()?;
    let result = tx.execute("INSERT INTO edges(src,dst,kind,note,created_at) VALUES (?1,?2,?3,?4,?5)",
        params![source, target, edge_kind, note.trim(), utc_now()]);
    if result.is_err() {
        return Err(EngineError::new(format!("edge {source} -{edge_kind}-> {target} already exists"),
            "the graph stores each typed relation once", "inspect it with `show`, or use a different kind"));
    }
    let id = tx.last_insert_rowid();
    tx.commit()?;
    log(conn, "edge.add", &json!({"src": source, "dst": target, "kind": edge_kind}))?;
    Ok(json!({"id": id, "src": source, "dst": target, "kind": edge_kind,
        "note": note.trim(), "created_at": "", "details": {}}))
}

fn log(conn: &Connection, action: &str, payload: &Value) -> Result<()> {
    conn.execute("INSERT INTO events(at, action, payload) VALUES (?1,?2,?3)",
        params![utc_now(), action, crate::util::to_python_json(payload)])?;
    Ok(())
}

const LITERATURE_STOPWORDS: &[&str] = &[
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in", "into", "is", "it",
    "of", "on", "or", "that", "the", "to", "was", "were", "with",
];

pub fn search_literature(
    conn: &Connection,
    query: &str,
    tags: &str,
    study_type: &str,
    year: Option<&str>,
    limit: i64,
) -> Result<Value> {
    let value: String = query.split_whitespace().collect::<Vec<_>>().join(" ");
    let tag_filter: Vec<String> = crate::lattice::normalize_tags(tags)
        .split(", ").filter(|tag| !tag.is_empty()).map(|s| s.to_string()).collect();
    let type_filter = crate::lattice::normalize_study_type(study_type).to_lowercase();
    let terms: Vec<String> = crate::lattice::normalize_text(&value).split_whitespace()
        .filter(|term| term.len() >= 2 && !LITERATURE_STOPWORDS.contains(term))
        .map(|s| s.to_string()).collect();
    let rows = query_json(conn, "SELECT * FROM papers ORDER BY year DESC, title", [])?;
    let needle = value.to_lowercase();
    let normalized_needle = crate::lattice::normalize_text(&value);
    let mut scored: Vec<(i64, i64, Value)> = Vec::new();
    for (index, row) in rows.into_iter().enumerate() {
        if let Some(filter) = year {
            if field(&row, "year") != filter { continue; }
        }
        let paper_tags: BTreeSet<String> = crate::lattice::normalize_tags(&field(&row, "tags"))
            .split(", ").filter(|tag| !tag.is_empty()).map(|s| s.to_string()).collect();
        if !tag_filter.is_empty() && !tag_filter.iter().all(|tag| paper_tags.contains(tag)) { continue; }
        if !type_filter.is_empty() && !field(&row, "study_type").to_lowercase().contains(&type_filter) { continue; }
        let blob = format!("{} {} {} {} {} {} {} {} {} {}", field(&row, "title"), field(&row, "authors"),
            field(&row, "year"), field(&row, "venue"), field(&row, "doi"), field(&row, "arxiv"),
            field(&row, "url"), field(&row, "abstract"), field(&row, "tags"), field(&row, "study_type")).to_lowercase();
        let primary = field(&row, "title").to_lowercase();
        let mut score = 0i64;
        if blob.contains(&needle) { score += 100; }
        if primary.contains(&needle) { score += 50; }
        let matched: Vec<&String> = terms.iter().filter(|term| blob.contains(term.as_str())).collect();
        if !matched.is_empty() {
            score += matched.iter().map(|term| if primary.contains(term.as_str()) { 3 } else { 1 }).sum::<i64>();
        }
        if !normalized_needle.is_empty() && !blob.contains(&needle)
            && crate::lattice::normalize_text(&blob).contains(&normalized_needle) { score += 100; }
        if score > 0 { scored.push((score, -(index as i64), row)); }
    }
    scored.sort_by(|a, b| (b.0, b.1).cmp(&(a.0, a.1)));
    let total = scored.len();
    let papers: Vec<Value> = scored.into_iter().take(limit.max(0) as usize).map(|(_, _, row)| row).collect();
    Ok(json!({
        "query": value,
        "tags": tag_filter.join(", "),
        "study_type": crate::lattice::normalize_study_type(study_type),
        "total": total,
        "papers": papers,
    }))
}

pub fn get_paper(conn: &Connection, reference: &str) -> Result<Value> {
    let bare = lattice::bare_id(&resolve(reference)?)?;
    one(conn, "papers", &bare).ok_or_else(|| EngineError::new(
        format!("paper '{reference}' does not exist"), "the graph has no such record", "use `search` to find an ingested paper"))
}

pub fn get_claim(conn: &Connection, reference: &str) -> Result<Value> {
    let bare = lattice::bare_id(&resolve(reference)?)?;
    one(conn, "claims", &bare).ok_or_else(|| EngineError::new(
        format!("claim '{reference}' does not exist"), "the graph has no such record", "use `search` to find a recorded claim"))
}

pub fn get_question(conn: &Connection, reference: &str) -> Result<Value> {
    let bare = lattice::bare_id(&resolve(reference)?)?;
    one(conn, "questions", &bare).ok_or_else(|| EngineError::new(
        format!("question '{reference}' does not exist"), "the graph has no such record", "use `search` or add it with the question command"))
}

pub fn neighbors(conn: &Connection, reference: &str) -> Result<Vec<Value>> {
    let resolved = resolve(reference)?;
    let edges = query_json(conn, "SELECT * FROM edges WHERE src=?1 OR dst=?2 ORDER BY id",
        params![resolved, resolved])?;
    Ok(edges.into_iter().map(|mut edge| {
        let other = if field(&edge, "src") == resolved { field(&edge, "dst") } else { field(&edge, "src") };
        let details = json!({"other": summary(conn, &other)});
        edge.as_object_mut().unwrap().insert("details".to_string(), details);
        edge
    }).collect())
}

fn summary(conn: &Connection, reference: &str) -> Value {
    let resolved = match resolve(reference) { Ok(value) => value, Err(_) => return json!({"ref": reference, "missing": true}) };
    let kind = resolved.split(':').next().unwrap_or("");
    let id = lattice::bare_id(&resolved).unwrap_or_default();
    let Some(row) = one(conn, match kind { "paper" => "papers", "claim" => "claims", _ => "questions" }, &id) else {
        return json!({"ref": resolved, "missing": true});
    };
    let mut value = row;
    value.as_object_mut().unwrap().insert("type".to_string(), json!(kind));
    if kind == "claim" {
        if let Some(paper) = one(conn, "papers", &field(&value, "paper_id")) {
            let paper_summary = json!({
                "id": field(&paper, "id"), "title": field(&paper, "title"),
                "authors": field(&paper, "authors"), "year": field(&paper, "year"),
                "doi": field(&paper, "doi"), "venue": field(&paper, "venue"),
                "tags": field(&paper, "tags"), "study_type": field(&paper, "study_type"),
            });
            value.as_object_mut().unwrap().insert("paper".to_string(), paper_summary);
            value.as_object_mut().unwrap().insert("study_type".to_string(), json!(field(&paper, "study_type")));
        }
    }
    value
}

pub fn get(conn: &Connection, reference: &str) -> Result<Value> {
    let resolved = resolve(reference)?;
    let edges = query_json(conn, "SELECT * FROM edges WHERE src=?1 OR dst=?2 ORDER BY id",
        params![resolved, resolved])?;
    let edges: Vec<Value> = edges.into_iter().map(|mut edge| {
        let other = if field(&edge, "src") == resolved { field(&edge, "dst") } else { field(&edge, "src") };
        let details = json!({"other": summary(conn, &other)});
        edge.as_object_mut().unwrap().insert("details".to_string(), details);
        edge
    }).collect();
    Ok(json!({"ref": resolved, "entity": summary(conn, &resolved), "edges": edges}))
}

fn lexical_score(needle: &str, terms: &[String], blob: &str, primary: &str) -> i64 {
    let mut score = 0;
    if blob.contains(needle) { score += 100; }
    if primary.contains(needle) { score += 50; }
    if terms.len() > 1 {
        let matched: Vec<&String> = terms.iter().filter(|term| blob.contains(term.as_str())).collect();
        if matched.len() >= 2 || (terms.len() == 1 && !matched.is_empty()) {
            score += matched.iter().map(|term| if primary.contains(term.as_str()) { 3 } else { 1 }).sum::<i64>();
        }
    }
    score
}

pub fn search(conn: &Connection, query: &str, limit: i64) -> Result<Value> {
    let value = query.trim();
    if value.is_empty() {
        return Err(EngineError::new("search needs a query", "an empty query would match everything", "pass a word or phrase"));
    }
    let terms: Vec<String> = lattice::normalize_text(value).split_whitespace()
        .filter(|word| word.len() >= 2).map(|s| s.to_string()).collect();
    let needle = value.to_lowercase();
    let mut papers: Vec<(i64, usize, Value)> = Vec::new();
    for (index, row) in query_json(conn, "SELECT * FROM papers ORDER BY year DESC, title", [])?.into_iter().enumerate() {
        let blob = format!("{} {} {} {} {}", field(&row, "title"), field(&row, "authors"),
            field(&row, "abstract"), field(&row, "doi"), field(&row, "arxiv")).to_lowercase();
        let score = lexical_score(&needle, &terms, &blob, &field(&row, "title").to_lowercase());
        if score > 0 { papers.push((score, usize::MAX - index, paper_json(row))); }
    }
    papers.sort_by(|a, b| (b.0, b.1).cmp(&(a.0, a.1)));
    let mut claims: Vec<(i64, usize, Value)> = Vec::new();
    for (index, row) in query_json(conn, "SELECT * FROM claims ORDER BY id", [])?.into_iter().enumerate() {
        let blob = format!("{} {}", field(&row, "text"), field(&row, "quote")).to_lowercase();
        let score = lexical_score(&needle, &terms, &blob, &field(&row, "text").to_lowercase());
        if score > 0 { claims.push((score, usize::MAX - index, claim_json(row))); }
    }
    claims.sort_by(|a, b| (b.0, b.1).cmp(&(a.0, a.1)));
    let mut questions: Vec<(i64, usize, Value)> = Vec::new();
    for (index, row) in query_json(conn, "SELECT * FROM questions ORDER BY id", [])?.into_iter().enumerate() {
        let blob = field(&row, "text").to_lowercase();
        let score = lexical_score(&needle, &terms, &blob, &blob);
        if score > 0 { questions.push((score, usize::MAX - index, question_json(row))); }
    }
    questions.sort_by(|a, b| (b.0, b.1).cmp(&(a.0, a.1)));
    let take = limit.max(0) as usize;
    let claim_rows: Vec<Value> = claims.into_iter().take(take).map(|(_, _, row)| {
        let paper = summary(conn, &format!("paper:{}", field(&row, "paper_id")));
        let mut value = row;
        value.as_object_mut().unwrap().insert("paper".to_string(), paper);
        value
    }).collect();
    Ok(json!({
        "query": value,
        "papers": papers.into_iter().take(take).map(|(_, _, row)| row).collect::<Vec<_>>(),
        "claims": claim_rows,
        "questions": questions.into_iter().take(take).map(|(_, _, row)| row).collect::<Vec<_>>(),
    }))
}

pub fn stats(conn: &Connection) -> Result<Value> {
    let mut counts = serde_json::Map::new();
    for table in ["papers", "claims", "questions", "edges"] {
        let n: i64 = conn.query_row(&format!("SELECT COUNT(*) FROM {table}"), [], |r| r.get(0))?;
        counts.insert(table.to_string(), json!(n));
    }
    let mut kinds = serde_json::Map::new();
    for row in query_json(conn, "SELECT kind, COUNT(*) AS n FROM edges GROUP BY kind ORDER BY kind", [])? {
        kinds.insert(field(&row, "kind"), row.get("n").cloned().unwrap_or(json!(0)));
    }
    counts.insert("edge_kinds".to_string(), Value::Object(kinds));

    let mut by_status = BTreeMap::new();
    for row in query_json(conn, "SELECT status, COUNT(*) AS n FROM questions GROUP BY status", [])? {
        by_status.insert(field(&row, "status"), row.get("n").and_then(Value::as_i64).unwrap_or(0));
    }
    let mut linked: BTreeMap<String, BTreeSet<String>> = BTreeMap::new();
    let mut stances: BTreeMap<String, BTreeSet<String>> = BTreeMap::new();
    for row in query_json(conn, "SELECT src, dst, kind FROM edges WHERE kind IN ('supports','contradicts','answers')", [])? {
        let src = field(&row, "src");
        let dst = field(&row, "dst");
        let kind = field(&row, "kind");
        let (claim_ref, question) = if src.starts_with("claim:") && dst.starts_with("question:") {
            (src, dst.split_once(':').unwrap().1.to_string())
        } else if dst.starts_with("claim:") && src.starts_with("question:") {
            (dst, src.split_once(':').unwrap().1.to_string())
        } else { continue; };
        linked.entry(question.clone()).or_default().insert(claim_ref);
        if kind == "supports" || kind == "contradicts" {
            stances.entry(question).or_default().insert(kind);
        }
    }
    let papers = counts.get("papers").and_then(Value::as_i64).unwrap_or(0);
    let claims = counts.get("claims").and_then(Value::as_i64).unwrap_or(0);
    let total_questions: i64 = by_status.values().sum();
    counts.insert("evidence".to_string(), json!({
        "claims_per_paper": if papers > 0 { ((claims as f64 / papers as f64) * 100.0).round() / 100.0 } else { 0.0 },
        "questions_answered": by_status.get("answered").copied().unwrap_or(0),
        "questions_open": by_status.get("open").copied().unwrap_or(0),
        "questions_abandoned": by_status.get("abandoned").copied().unwrap_or(0),
        "linked_questions": linked.len(),
        "coverage_gaps": total_questions - linked.len() as i64,
        "contested_questions": stances.values().filter(|kinds| kinds.contains("supports") && kinds.contains("contradicts")).count(),
        "evidence_links": linked.values().map(|refs| refs.len()).sum::<usize>(),
    }));
    Ok(Value::Object(counts))
}
