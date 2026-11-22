//! Studio web request dispatcher (studio/web.py routes, without sockets).

use rusqlite::Connection;
use serde_json::{json, Value};

use crate::error::EngineError;
use crate::lattice_checks;
use crate::lattice_query;
use crate::lattice_repo as repo;
use crate::lattice_snapshots as snaps;
use crate::studio_api;
use crate::studio_web_html::WEB_HTML;
use crate::util::query_json;

const JSON_TYPE: &str = "application/json; charset=utf-8";

fn field(value: &Value, name: &str) -> String {
    value.get(name).and_then(Value::as_str).unwrap_or("").to_string()
}

fn json_response(status: i64, payload: &Value) -> Value {
    json!({
        "status": status, "content_type": JSON_TYPE,
        "body": serde_json::to_string_pretty(payload).unwrap_or_default(),
        "headers": {},
    })
}

fn decode(value: &str) -> String {
    let mut out = String::new();
    let bytes = value.as_bytes();
    let mut index = 0;
    while index < bytes.len() {
        if bytes[index] == b'%' && index + 2 < bytes.len() {
            if let Ok(byte) = u8::from_str_radix(&value[index + 1..index + 3], 16) {
                out.push(byte as char);
                index += 3;
                continue;
            }
        }
        out.push(bytes[index] as char);
        index += 1;
    }
    out
}

fn parse_query(query: &str) -> std::collections::BTreeMap<String, Vec<String>> {
    let mut result: std::collections::BTreeMap<String, Vec<String>> = std::collections::BTreeMap::new();
    for part in query.split('&').filter(|part| !part.is_empty()) {
        let (key, value) = part.split_once('=').unwrap_or((part, ""));
        result.entry(decode(key)).or_default().push(decode(value));
    }
    result
}

fn first(query: &std::collections::BTreeMap<String, Vec<String>>, key: &str) -> String {
    query.get(key).and_then(|values| values.first()).map(|s| s.trim().to_string()).unwrap_or_default()
}

fn overview(conn: &Connection) -> Result<Value, EngineError> {
    let papers = query_json(conn, "SELECT * FROM papers ORDER BY year DESC, title LIMIT 100", [])?;
    let questions = query_json(conn, "SELECT * FROM questions ORDER BY id DESC LIMIT 100", [])?;
    let claims = query_json(conn, "SELECT * FROM claims ORDER BY id DESC LIMIT 100", [])?;
    let edges = query_json(conn, "SELECT * FROM edges ORDER BY id DESC LIMIT 100", [])?;
    let mut study_types: Vec<String> = papers.iter().map(|p| field(p, "study_type"))
        .filter(|s| !s.trim().is_empty()).collect();
    study_types.sort();
    study_types.dedup();
    let mut tags: Vec<String> = papers.iter()
        .flat_map(|p| field(p, "tags").split(',').map(|t| t.trim().to_string()).collect::<Vec<_>>())
        .filter(|t| !t.is_empty()).collect();
    tags.sort();
    tags.dedup();
    Ok(json!({
        "stats": repo::stats(conn)?,
        "check": lattice_checks::run_checks(conn),
        "papers": papers, "questions": questions, "claims": claims, "edges": edges,
        "study_types": study_types, "tags": tags,
    }))
}

fn post_dispatch(conn: &Connection, route: &str, payload: &Value) -> Result<Value, EngineError> {
    let value = |key: &str| field(payload, key);
    match route {
        "/api/discover" => {
            let source = if value("source").is_empty() { "offline".to_string() } else { value("source") };
            let limit = payload.get("limit").and_then(Value::as_i64).unwrap_or(10);
            let ingest = payload.get("ingest").and_then(Value::as_bool).unwrap_or(true);
            Ok(json_response(200, &crate::lattice_discovery::discover(conn, &value("query"), &source, limit, ingest)?))
        }
        "/api/detect-contradictions" => {
            let auto_link = payload.get("auto_link").and_then(Value::as_bool).unwrap_or(true);
            let pairs = lattice_query::detect_contradictions(conn, auto_link)?;
            Ok(json_response(200, &json!({"count": pairs.len(), "contradictions": pairs})))
        }
        "/api/questions" => {
            let question = repo::add_question(conn, &value("text"))?;
            Ok(json_response(200, &json!({"question": question})))
        }
        "/api/question-status" => {
            let question = repo::set_question_status(conn, &value("question"), &value("status"))?;
            Ok(json_response(200, &json!({"question": question})))
        }
        "/api/papers" => {
            let mut metadata = std::collections::BTreeMap::new();
            if let Value::Object(map) = payload {
                for (key, item) in map {
                    if let Some(text) = item.as_str() { metadata.insert(key.clone(), text.to_string()); }
                }
            }
            let (paper, created) = repo::add_paper(conn, &metadata)?;
            Ok(json_response(200, &json!({"paper": paper, "created": created})))
        }
        "/api/claims" => {
            let claim = repo::add_claim(conn, &value("paper"), &value("text"), &value("quote"),
                &value("locator"), &if value("stance").is_empty() { "mentions".to_string() } else { value("stance") },
                payload.get("confidence").and_then(Value::as_f64).unwrap_or(0.5))?;
            let question_ref = value("question");
            let edge = if question_ref.is_empty() { Value::Null } else {
                let question = repo::get_question(conn, &question_ref)?;
                let stance = field(&claim, "stance");
                let kind = if stance == "supports" || stance == "contradicts" { stance } else { "answers".to_string() };
                repo::add_edge(conn, &format!("claim:{}", field(&claim, "id")),
                    &format!("question:{}", field(&question, "id")), &kind, "linked via web studio")?
            };
            Ok(json_response(200, &json!({"claim": claim, "edge": edge})))
        }
        "/api/edges" => {
            let edge = repo::add_edge(conn, &value("src"), &value("dst"), &value("kind"), &value("note"))?;
            Ok(json_response(200, &json!({"edge": edge})))
        }
        other => Ok(json_response(404, &json!({"error": format!("route not found: POST {other}")}))),
    }
}

pub fn dispatch_web_request(conn: &Connection, method: &str, path: &str,
                            body: Option<&str>) -> Result<Value, EngineError> {
    let (raw_path, query_string) = path.split_once('?').unwrap_or((path, ""));
    let route = raw_path.trim_end_matches('/');
    let route = if route.is_empty() { "/" } else { route };
    let query = parse_query(query_string);
    let verb = (if method.is_empty() { "GET" } else { method }).to_uppercase();
    if verb == "POST" {
        let payload: Value = match body {
            Some(text) if !text.trim().is_empty() => serde_json::from_str(text).map_err(|e| EngineError::new(
                format!("request body is not valid JSON: {e}"), "POST routes expect JSON objects",
                "send a JSON object payload"))?,
            _ => json!({}),
        };
        if !payload.is_object() {
            return Ok(json_response(400, &json!({"error": "request body must be a JSON object"})));
        }
        return post_dispatch(conn, route, &payload);
    }
    if verb != "GET" {
        return Ok(json_response(404, &json!({"error": format!("route not found: {verb} {route}")})));
    }
    match route {
        "/" => Ok(json!({"status": 200, "content_type": "text/html; charset=utf-8",
            "body": WEB_HTML, "headers": {}})),
        "/api/overview" => Ok(json_response(200, &overview(conn)?)),
        "/api/matrix" => Ok(json_response(200, &json!({
            "matrix": studio_api::build_evidence_matrix(conn)?,
            "contradictions": lattice_query::detect_contradictions(conn, false)?,
            "keystone": lattice_query::rank_influential_entities(conn, 10)?,
        }))),
        "/api/export" => Ok(json!({"status": 200,
            "content_type": "application/x-ndjson; charset=utf-8",
            "body": snaps::export_jsonl_string(conn)?, "headers": {}})),
        "/api/search" => {
            let q = first(&query, "q");
            let limit = first(&query, "limit").parse::<i64>().unwrap_or(20);
            let found = repo::search(conn, &q, limit)?;
            Ok(json_response(200, &found))
        }
        "/api/literature" => {
            let q = first(&query, "q");
            let tags = query.get("tags").cloned().unwrap_or_default().into_iter()
                .chain(query.get("tag").cloned().unwrap_or_default()).collect::<Vec<_>>().join(",");
            let study_type = {
                let value = first(&query, "study_type");
                if value.is_empty() { first(&query, "type") } else { value }
            };
            let year = {
                let value = first(&query, "year");
                if value.is_empty() { None } else { Some(value) }
            };
            let limit = first(&query, "limit").parse::<i64>().unwrap_or(50);
            Ok(json_response(200, &repo::search_literature(conn, &q, &tags, &study_type, year.as_deref(), limit)?))
        }
        "/api/outline" => {
            let tokens = first(&query, "tokens").parse::<i64>().unwrap_or(400);
            Ok(json_response(200, &lattice_query::outline(conn, tokens)?))
        }
        "/api/export-bibtex" => Ok(json!({
            "status": 200, "content_type": "application/x-bibtex; charset=utf-8",
            "body": snaps::format_bibtex(conn)?,
            "headers": {"Content-Disposition": "attachment; filename=\"lattice-references.bib\""},
        })),
        "/api/export-graphml" => Ok(json!({
            "status": 200, "content_type": "application/xml; charset=utf-8",
            "body": snaps::graphml_string(conn)?,
            "headers": {"Content-Disposition": "attachment; filename=\"lattice-graph.graphml\""},
        })),
        "/api/export-cytoscape" => Ok(json!({
            "status": 200, "content_type": "application/json; charset=utf-8",
            "body": serde_json::to_string_pretty(&snaps::cytoscape_data(conn)?).unwrap_or_default(),
            "headers": {"Content-Disposition": "attachment; filename=\"lattice-cytoscape.json\""},
        })),
        other => Ok(json!({"status": 404, "content_type": JSON_TYPE,
            "body": serde_json::to_string_pretty(&json!({"error": format!("route not found: {verb} {other}")})).unwrap_or_default(),
            "headers": {}})),
    }
}
