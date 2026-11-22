//! Studio turnkey client facade (studio/client.py).

use rusqlite::Connection;
use serde_json::{json, Value};

use crate::error::EngineError;
use crate::studio_mcp;
use crate::studio_mcp_specs::{PROMPTS_JSON, RESOURCES_JSON, TOOLS_JSON};

pub const DEFAULT_DB: &str = "lattice.db";

const READ_ONLY_TOOLS: &[&str] = &[
    "search", "get_entity", "neighbors", "subgraph", "related_findings", "outline",
    "brief", "review", "synthesize", "stats", "analyze_graph", "detect_contradictions",
    "diff_snapshot", "find_path", "propose_hypotheses", "get_prisma_flow", "get_context_pack",
    "compute_meta_analysis",
];

pub fn tool_schemas(read_only: bool) -> Value {
    let tools: Value = serde_json::from_str(TOOLS_JSON).unwrap_or(json!([]));
    let mut result: Vec<Value> = tools.as_array().cloned().unwrap_or_default()
        .into_iter().filter(|item| !read_only || READ_ONLY_TOOLS.contains(&item.get("name").and_then(Value::as_str).unwrap_or("")))
        .collect();
    if read_only {
        for item in &mut result {
            let name = item.get("name").and_then(Value::as_str).unwrap_or("");
            if name == "analyze_graph" || name == "detect_contradictions" {
                if let Some(properties) = item.get_mut("inputSchema").and_then(|s| s.get_mut("properties")) {
                    if let Some(map) = properties.as_object_mut() { map.remove("auto_link"); }
                }
            }
        }
    }
    Value::Array(result)
}

pub fn resource_schemas() -> Value {
    serde_json::from_str(RESOURCES_JSON).unwrap_or(json!([]))
}

pub fn prompt_schemas() -> Value {
    serde_json::from_str(PROMPTS_JSON).unwrap_or(json!([]))
}

pub fn call_tool(conn: &Connection, read_only: bool, name: &str,
                 arguments: &Value, kwargs: &Value) -> Result<Value, EngineError> {
    if name.trim().is_empty() {
        return Err(EngineError::new("a tool name is required",
            "tool names are strings advertised by tool_schemas()", "pass a name from tool_schemas()"));
    }
    let Some(arguments) = arguments.as_object() else {
        return Err(EngineError::new("tool arguments must be an object",
            "schemas declare named fields", "pass a dict such as {'query': 'sleep'}"));
    };
    let mut payload = serde_json::Map::new();
    for (key, value) in arguments { payload.insert(key.clone(), value.clone()); }
    if let Some(extra) = kwargs.as_object() {
        for (key, value) in extra { payload.insert(key.clone(), value.clone()); }
    }
    if read_only {
        if !READ_ONLY_TOOLS.contains(&name) {
            return Err(EngineError::new(format!("tool '{name}' is not available in read-only mode"),
                "the read-only client advertises only non-mutating tools",
                "use one of the tools in tool_schemas() or create a writable client"));
        }
        if (name == "analyze_graph" || name == "detect_contradictions")
            && payload.get("auto_link").and_then(Value::as_bool).unwrap_or(false) {
            return Err(EngineError::new(format!("tool '{name}' cannot auto-link in read-only mode"),
                "auto_link writes edge rows", "omit auto_link or create a writable client"));
        }
    }
    studio_mcp::dispatch(conn, name, &Value::Object(payload))
}

pub fn read_resource(conn: &Connection, uri: &str) -> Result<Value, EngineError> {
    studio_mcp::read_resource(conn, uri)
}
