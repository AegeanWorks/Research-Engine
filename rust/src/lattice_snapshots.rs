//! Portable lattice graph snapshots: JSONL, BibTeX, GraphML and Cytoscape data.

use rusqlite::Connection;
use serde_json::{json, Value};

use crate::error::Result;
use crate::util::{query_json, to_python_json};

const RECORD_TABLES: &[(&str, &str)] = &[
    ("paper", "papers"), ("question", "questions"), ("claim", "claims"), ("edge", "edges"),
];
const GRAPHML_NS: &str = "http://graphml.graphdrawing.org/xmlns";

fn field(value: &Value, name: &str) -> String {
    value.get(name).and_then(Value::as_str).unwrap_or("").to_string()
}

fn get(value: &Value, name: &str) -> Value {
    value.get(name).cloned().unwrap_or(Value::Null)
}

pub fn collect_records(conn: &Connection) -> Result<Vec<Value>> {
    let mut records = Vec::new();
    for (kind, table) in RECORD_TABLES {
        for row in query_json(conn, &format!("SELECT * FROM {table} ORDER BY id"), [])? {
            let mut record = serde_json::Map::new();
            record.insert("record_type".to_string(), json!(kind));
            if let Value::Object(map) = row {
                for (key, value) in map { record.insert(key, value); }
            }
            records.push(Value::Object(record));
        }
    }
    Ok(records)
}

pub fn export_jsonl_string(conn: &Connection) -> Result<String> {
    let records = collect_records(conn)?;
    let lines: Vec<String> = records.iter().map(to_python_json).collect();
    let mut payload = lines.join("\n");
    if !lines.is_empty() { payload.push('\n'); }
    Ok(payload)
}

pub fn export_snapshot(conn: &Connection, path: &std::path::Path) -> Result<Value> {
    let records = collect_records(conn)?;
    let lines: Vec<String> = records.iter().map(to_python_json).collect();
    let mut payload = lines.join("\n");
    if !lines.is_empty() { payload.push('\n'); }
    crate::util::atomic_write_text(path, &payload)?;
    let mut counts = serde_json::Map::new();
    for (_, table) in RECORD_TABLES {
        counts.insert(table.to_string(), json!(0usize));
    }
    for record in &records {
        let table = RECORD_TABLES.iter().find(|(kind, _)| *kind == field(record, "record_type"))
            .map(|(_, table)| *table).unwrap_or("");
        if let Some(value) = counts.get_mut(table) { *value = json!(value.as_u64().unwrap_or(0) + 1); }
    }
    let mut result = serde_json::Map::new();
    result.insert("path".to_string(), json!(path.to_string_lossy()));
    for (key, value) in counts { result.insert(key, value); }
    Ok(Value::Object(result))
}

pub fn format_bibtex(conn: &Connection) -> Result<String> {
    let records = collect_records(conn)?;
    let papers: Vec<&Value> = records.iter().filter(|r| field(r, "record_type") == "paper").collect();
    let mut entries = Vec::new();
    for paper in papers {
        let mut lines = vec![format!("@article{{{},", field(paper, "id"))];
        lines.push(format!("  title = {{{}}},", field(paper, "title")));
        let authors = field(paper, "authors");
        if !authors.is_empty() { lines.push(format!("  author = {{{}}},", authors.replace(';', " and"))); }
        let year = field(paper, "year");
        if !year.is_empty() { lines.push(format!("  year = {{{year}}},")); }
        let venue = field(paper, "venue");
        if !venue.is_empty() { lines.push(format!("  journal = {{{venue}}},")); }
        let doi = field(paper, "doi");
        if !doi.is_empty() { lines.push(format!("  doi = {{{doi}}},")); }
        let arxiv = field(paper, "arxiv");
        if !arxiv.is_empty() { lines.push(format!("  eprint = {{{arxiv}}},")); }
        let url = field(paper, "url");
        if !url.is_empty() { lines.push(format!("  url = {{{url}}},")); }
        lines.push("}".to_string());
        entries.push(lines.join("\n"));
    }
    Ok(entries.join("\n\n"))
}

pub fn cytoscape_data(conn: &Connection) -> Result<Value> {
    let records = collect_records(conn)?;
    let mut nodes = Vec::new();
    let mut edges = Vec::new();
    let mut paper_study_types = serde_json::Map::new();
    for record in &records {
        let id = field(record, "id");
        match field(record, "record_type").as_str() {
            "paper" => {
                let study = field(record, "study_type");
                paper_study_types.insert(id.clone(), json!(study));
                nodes.push(json!({"data": {
                    "id": format!("paper:{id}"), "type": "paper",
                    "label": if field(record, "title").is_empty() { json!(id.clone()) } else { get(record, "title") },
                    "title": field(record, "title"), "authors": field(record, "authors"),
                    "year": get(record, "year"), "venue": field(record, "venue"),
                    "study_type": study,
                }}));
            }
            "question" => {
                nodes.push(json!({"data": {
                    "id": format!("question:{id}"), "type": "question",
                    "label": if field(record, "text").is_empty() { json!(id.clone()) } else { get(record, "text") },
                    "status": if field(record, "status").is_empty() { json!("open") } else { get(record, "status") },
                }}));
            }
            "claim" => {
                let assertion = field(record, "assertion");
                let paper_id = field(record, "paper_id");
                nodes.push(json!({"data": {
                    "id": format!("claim:{id}"), "type": "claim",
                    "label": if assertion.is_empty() { json!(id.clone()) } else { json!(assertion) },
                    "quote": field(record, "quote"), "locator": field(record, "locator"),
                    "confidence": get(record, "confidence"),
                    "stance": if field(record, "stance").is_empty() { json!("supports") } else { get(record, "stance") },
                    "paper_id": paper_id,
                    "study_type": paper_study_types.get(&paper_id).cloned().unwrap_or(Value::Null),
                }}));
            }
            "edge" => {
                edges.push(json!({"data": {
                    "id": format!("e_{}", get(record, "id")),
                    "source": field(record, "src"), "target": field(record, "dst"),
                    "kind": if field(record, "kind").is_empty() { json!("related") } else { get(record, "kind") },
                    "weight": 1.0,
                }}));
            }
            _ => {}
        }
    }
    Ok(json!({"format": "cytoscape", "elements": {"nodes": nodes, "edges": edges}}))
}

fn xml_escape(text: &str) -> String {
    text.replace('&', "&amp;").replace('<', "&lt;").replace('>', "&gt;")
}

fn data(key: &str, value: &str) -> String {
    format!("<ns0:data key=\"{key}\">{}</ns0:data>", xml_escape(value))
}

pub fn graphml_string(conn: &Connection) -> Result<String> {
    let records = collect_records(conn)?;
    let mut out = String::from("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n");
    out.push_str(&format!("<ns0:graphml xmlns:ns0=\"{GRAPHML_NS}\">"));
    for (id, for_type, name, attr_type) in [
        ("d_type", "node", "type", "string"),
        ("d_label", "node", "label", "string"),
        ("d_title", "node", "title", "string"),
        ("d_study_type", "node", "study_type", "string"),
        ("d_year", "node", "year", "string"),
        ("d_confidence", "node", "confidence", "double"),
        ("d_status", "node", "status", "string"),
        ("e_kind", "edge", "kind", "string"),
        ("e_weight", "edge", "weight", "double"),
    ] {
        out.push_str(&format!("<ns0:key id=\"{id}\" for=\"{for_type}\" attr.name=\"{name}\" attr.type=\"{attr_type}\" />"));
    }
    out.push_str("<ns0:graph id=\"lattice\" edgedefault=\"directed\">");
    let mut paper_study_types = serde_json::Map::new();
    for record in &records {
        let id = field(record, "id");
        match field(record, "record_type").as_str() {
            "paper" => {
                let study = field(record, "study_type");
                paper_study_types.insert(id.clone(), json!(study.clone()));
                let node_id = format!("paper:{id}");
                out.push_str(&format!("<ns0:node id=\"{}\">", xml_escape(&node_id)));
                out.push_str(&data("d_type", "paper"));
                let title = field(record, "title");
                out.push_str(&data("d_label", if title.is_empty() { &node_id } else { &title }));
                out.push_str(&data("d_title", &title));
                if !study.is_empty() { out.push_str(&data("d_study_type", &study)); }
                let year = field(record, "year");
                if !year.is_empty() { out.push_str(&data("d_year", &year)); }
                out.push_str("</ns0:node>");
            }
            "question" => {
                let node_id = format!("question:{id}");
                out.push_str(&format!("<ns0:node id=\"{}\">", xml_escape(&node_id)));
                out.push_str(&data("d_type", "question"));
                let text = field(record, "text");
                out.push_str(&data("d_label", if text.is_empty() { &node_id } else { &text }));
                let status = field(record, "status");
                if !status.is_empty() { out.push_str(&data("d_status", &status)); }
                out.push_str("</ns0:node>");
            }
            "claim" => {
                let node_id = format!("claim:{id}");
                out.push_str(&format!("<ns0:node id=\"{}\">", xml_escape(&node_id)));
                out.push_str(&data("d_type", "claim"));
                let assertion = field(record, "assertion");
                out.push_str(&data("d_label", if assertion.is_empty() { &node_id } else { &assertion }));
                let confidence = get(record, "confidence");
                if !confidence.is_null() { out.push_str(&data("d_confidence", &confidence.to_string())); }
                let paper_id = field(record, "paper_id");
                if let Some(study) = paper_study_types.get(&paper_id).and_then(Value::as_str) {
                    if !study.is_empty() { out.push_str(&data("d_study_type", study)); }
                }
                out.push_str("</ns0:node>");
            }
            "edge" => {
                let edge_id = format!("edge:{}", get(record, "id"));
                out.push_str(&format!("<ns0:edge id=\"{}\" source=\"{}\" target=\"{}\">",
                    xml_escape(&edge_id), xml_escape(&field(record, "src")), xml_escape(&field(record, "dst"))));
                let kind = field(record, "kind");
                out.push_str(&data("e_kind", if kind.is_empty() { "related" } else { &kind }));
                out.push_str(&data("e_weight", "1.0"));
                out.push_str("</ns0:edge>");
            }
            _ => {}
        }
    }
    out.push_str("</ns0:graph></ns0:graphml>");
    Ok(out)
}
