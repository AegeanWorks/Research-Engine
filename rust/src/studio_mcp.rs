//! Studio MCP JSON-RPC dispatcher over the lattice repository.

use rusqlite::Connection;
use serde_json::{json, Value};

use crate::error::EngineError;
use crate::lattice_discovery as discovery;
use crate::lattice_query as query;
use crate::lattice_repo as repo;
use crate::meta;
use crate::studio_api;
use crate::studio_mcp_specs::{PROMPTS_JSON, RESOURCES_JSON, TOOLS_JSON};
use crate::util::query_json;

const PROTOCOL_VERSION: &str = "2024-11-05";
const SERVER_NAME: &str = "lattice";
const VERSION: &str = "0.4.0";

fn field(value: &Value, name: &str) -> String {
    value.get(name).and_then(Value::as_str).unwrap_or("").to_string()
}

fn result(id: Value, value: Value) -> Value {
    json!({"jsonrpc": "2.0", "id": id, "result": value})
}

fn error(id: Value, code: i64, message: &str) -> Value {
    json!({"jsonrpc": "2.0", "id": id, "error": {"code": code, "message": message}})
}

fn required_text(args: &Value, name: &str) -> std::result::Result<String, String> {
    match args.get(name).and_then(Value::as_str) {
        Some(value) if !value.trim().is_empty() => Ok(value.to_string()),
        _ => Err(format!("argument '{name}' must be a non-empty string")),
    }
}

fn optional_int(args: &Value, name: &str, default: i64) -> i64 {
    args.get(name).and_then(Value::as_i64).unwrap_or(default)
}

fn dispatch(conn: &Connection, name: &str, args: &Value) -> Result<Value, EngineError> {
    match name {
        "search" => {
            let query_text = required_text(args, "query").map_err(|m| EngineError::new(m.clone(), m.clone(), m))?;
            let found = repo::search(conn, &query_text, optional_int(args, "limit", 20))?;
            query::compact_search(&found, optional_int(args, "tokens", 800))
        }
        "outline" => query::outline(conn, optional_int(args, "tokens", 400)),
        "stats" => repo::stats(conn),
        "get_entity" => {
            let reference = required_text(args, "ref").map_err(|m| EngineError::new(m.clone(), m.clone(), m))?;
            repo::get(conn, &reference)
        }
        "neighbors" => {
            let reference = required_text(args, "ref").map_err(|m| EngineError::new(m.clone(), m.clone(), m))?;
            Ok(Value::Array(repo::neighbors(conn, &reference)?))
        }
        "detect_contradictions" => {
            let pairs = query::detect_contradictions(conn, args.get("auto_link").and_then(Value::as_bool).unwrap_or(false))?;
            Ok(json!({"count": pairs.len(), "contradictions": pairs}))
        }
        "add_paper" => {
            let mut metadata = std::collections::BTreeMap::new();
            if let Value::Object(map) = args {
                for (key, value) in map {
                    if let Some(text) = value.as_str() { metadata.insert(key.clone(), text.to_string()); }
                }
            }
            let (paper, created) = repo::add_paper(conn, &metadata)?;
            Ok(json!({"paper": paper, "created": created}))
        }
        "add_claim" => {
            let paper = required_text(args, "paper").map_err(|m| EngineError::new(m.clone(), m.clone(), m))?;
            let text = required_text(args, "text").map_err(|m| EngineError::new(m.clone(), m.clone(), m))?;
            let quote = required_text(args, "quote").map_err(|m| EngineError::new(m.clone(), m.clone(), m))?;
            let claim = repo::add_claim(conn, &paper, &text, &quote,
                &field(args, "locator"), &if field(args, "stance").is_empty() { "mentions".to_string() } else { field(args, "stance") },
                args.get("confidence").and_then(Value::as_f64).unwrap_or(0.5))?;
            Ok(json!({"claim": claim}))
        }
        "add_question" => {
            let text = required_text(args, "text").map_err(|m| EngineError::new(m.clone(), m.clone(), m))?;
            Ok(json!({"question": repo::add_question(conn, &text)?}))
        }
        "add_edge" => {
            let src = required_text(args, "src").map_err(|m| EngineError::new(m.clone(), m.clone(), m))?;
            let dst = required_text(args, "dst").map_err(|m| EngineError::new(m.clone(), m.clone(), m))?;
            let kind = required_text(args, "kind").map_err(|m| EngineError::new(m.clone(), m.clone(), m))?;
            Ok(json!({"edge": repo::add_edge(conn, &src, &dst, &kind, &field(args, "note"))?}))
        }
        "get_context_pack" => {
            let targets: Vec<String> = match args.get("targets").or_else(|| args.get("target")) {
                Some(Value::Array(list)) => list.iter().filter_map(Value::as_str).map(|s| s.to_string()).collect(),
                Some(Value::String(text)) => vec![text.clone()],
                _ => Vec::new(),
            };
            let tokens = if args.get("max_tokens").is_some() {
                optional_int(args, "max_tokens", 2000)
            } else { optional_int(args, "tokens", 2000) };
            let format = if field(args, "format").is_empty() { "markdown".to_string() } else { field(args, "format") };
            query::build_context_pack(conn, &targets, tokens, &format)
        }
        "compute_meta_analysis" => {
            let model = if field(args, "model").is_empty() { "random".to_string() } else { field(args, "model") };
            let studies: Vec<Value> = args.get("studies").and_then(Value::as_array).cloned().unwrap_or_default();
            let result = meta::compute_meta_analysis(&studies, &model)?;
            let mut out = json!({"result": result});
            let format = field(args, "format").to_lowercase();
            if format == "ascii" {
                out.as_object_mut().unwrap().insert("ascii".to_string(), json!(meta::render_forest_ascii(&result, 40)));
            }
            Ok(out)
        }
        "discover_papers" => {
            let text = required_text(args, "query").map_err(|m| EngineError::new(m.clone(), m.clone(), m))?;
            let source = if field(args, "source").is_empty() { "offline".to_string() } else { field(args, "source") };
            discovery::discover(conn, &text, &source, optional_int(args, "limit", 10),
                args.get("ingest").and_then(Value::as_bool).unwrap_or(true))
        }
        "analyze_graph" => {
            let auto_link = args.get("auto_link").and_then(Value::as_bool).unwrap_or(false);
            let pairs = query::detect_contradictions(conn, auto_link)?;
            Ok(json!({
                "contradictions": pairs,
                "related_pairs": 0,
                "related_links_created": 0,
                "keystone": [],
                "matrix": studio_api::build_evidence_matrix(conn)?,
            }))
        }
        _ => Err(EngineError::new(format!("unknown tool '{name}'"),
            "the server advertises its tools in tools/list",
            "call one of the names returned by tools/list")),
    }
}

pub fn read_resource(conn: &Connection, uri: &str) -> Result<Value, EngineError> {
    match uri.trim() {
        "lattice://stats" => repo::stats(conn),
        "lattice://questions" => Ok(json!({"questions": query_json(conn, "SELECT * FROM questions ORDER BY id", [])?})),
        "lattice://matrix" => studio_api::build_evidence_matrix(conn),
        other => Err(EngineError::new(format!("unknown resource uri: {other}"),
            "the server advertises its resources",
            "use lattice://stats, lattice://questions or lattice://matrix")),
    }
}

fn call_tool(conn: &Connection, id: Value, params: &Value) -> Value {
    let Some(name) = params.get("name").and_then(Value::as_str).filter(|s| !s.trim().is_empty()) else {
        return error(id, -32602, "tools/call needs a tool name");
    };
    let arguments = params.get("arguments").cloned().unwrap_or(json!({}));
    if !arguments.is_object() { return error(id, -32602, "arguments must be an object"); }
    match dispatch(conn, name, &arguments) {
        Ok(payload) => result(id, json!({
            "content": [{"type": "text", "text": serde_json::to_string_pretty(&payload).unwrap_or_default()}],
            "isError": false,
        })),
        Err(err) => result(id, json!({
            "content": [{"type": "text", "text": err.what}],
            "isError": true,
        })),
    }
}

pub fn handle_message(conn: &Connection, message: &Value) -> Option<Value> {
    if !message.is_object() || !message.get("method").and_then(Value::as_str).is_some() {
        return Some(error(json!(null), -32600, "invalid request"));
    }
    let id = message.get("id").cloned().unwrap_or(json!(null));
    let method = field(message, "method");
    let params = message.get("params").cloned().unwrap_or(json!({}));
    match method.as_str() {
        "initialize" => Some(result(id, json!({
            "protocolVersion": PROTOCOL_VERSION,
            "serverInfo": {"name": SERVER_NAME, "version": VERSION},
            "capabilities": {"tools": {}, "resources": {}, "prompts": {}},
        }))),
        "notifications/initialized" | "initialized" | "shutdown" => None,
        "ping" => Some(result(id, json!({}))),
        "tools/list" => Some(result(id, json!({"tools": serde_json::from_str::<Value>(TOOLS_JSON).unwrap_or(json!([]))}))),
        "tools/call" => Some(call_tool(conn, id, &params)),
        "resources/list" => Some(result(id, json!({"resources": serde_json::from_str::<Value>(RESOURCES_JSON).unwrap_or(json!([]))}))),
        "resources/read" => {
            if !params.is_object() { return Some(error(id, -32602, "params must be an object")); }
            let uri = field(&params, "uri");
            match read_resource(conn, &uri) {
                Ok(payload) => Some(result(id, json!({"contents": [{
                    "uri": uri, "mimeType": "application/json", "text": serde_json::to_string_pretty(&payload).unwrap_or_default(),
                }]}))),
                Err(err) => Some(error(id, -32602, &err.what)),
            }
        }
        "prompts/list" => Some(result(id, json!({"prompts": serde_json::from_str::<Value>(PROMPTS_JSON).unwrap_or(json!([]))}))),
        "prompts/get" => Some(error(id, -32602, "prompt 'literature-synthesis' requires 'target'")),
        other => Some(error(id, -32601, &format!("method not found: {other}"))),
    }
}
