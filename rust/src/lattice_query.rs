//! Lattice contradiction detection and token-budgeted context views.

use std::collections::{BTreeMap, BTreeSet};

use rusqlite::{params, Connection};
use serde_json::{json, Value};

use crate::error::{EngineError, Result};
use crate::lattice::{bare_id, entity_type, estimate_tokens, normalize_text};
use crate::lattice_repo as repo;
use crate::util::{query_json, to_python_json};

const MIN_TOKENS: i64 = 100;
const RESERVE: i64 = 40;
const EXTRA_STOPWORDS: &[&str] = &[
    "significantly", "improves", "improved", "improve", "fails", "failed", "fail",
    "increases", "decreases", "demonstrates", "indicates", "suggests", "associated", "compared",
];
const STOPWORDS: &[&str] = &[
    "about", "after", "also", "among", "because", "between", "could", "does", "from",
    "have", "into", "more", "most", "other", "should", "than", "that", "their", "there",
    "these", "they", "this", "those", "through", "under", "what", "when", "where", "which",
    "while", "with", "would",
];

fn field(value: &Value, name: &str) -> String {
    value.get(name).and_then(Value::as_str).unwrap_or("").to_string()
}

fn number(value: &Value, name: &str) -> f64 {
    value.get(name).and_then(Value::as_f64).unwrap_or(0.0)
}

fn budget(tokens: i64) -> Result<i64> {
    if tokens < MIN_TOKENS {
        return Err(EngineError::new(format!("token budget {tokens} is too small"),
            "a compact context needs room for handles", format!("pass {MIN_TOKENS} tokens or more")));
    }
    Ok(tokens)
}

fn truncate(text: &str, limit: usize) -> String {
    let value: String = text.split_whitespace().collect::<Vec<_>>().join(" ");
    if value.chars().count() <= limit { return value; }
    let prefix: String = value.chars().take(limit.saturating_sub(3)).collect();
    format!("{}...", prefix.trim_end())
}

fn cost(item: &Value) -> i64 {
    estimate_tokens(&to_python_json(item)) as i64
}

fn pack(items: &[Value], tokens: i64) -> (Vec<Value>, usize, i64) {
    let room = (tokens - RESERVE).max(0);
    let mut kept = Vec::new();
    let mut used = 0i64;
    for item in items {
        let item_cost = cost(item);
        if !kept.is_empty() && used + item_cost > room { break; }
        used += item_cost;
        kept.push(item.clone());
    }
    let omitted = items.len() - kept.len();
    (kept, omitted, used)
}

fn keywords(text: &str) -> BTreeSet<String> {
    normalize_text(text).split_whitespace()
        .filter(|word| word.len() >= 4 && !STOPWORDS.contains(word) && !EXTRA_STOPWORDS.contains(word))
        .map(|s| s.to_string()).collect()
}

fn claim_question_map(conn: &Connection) -> BTreeMap<String, BTreeSet<String>> {
    let mut mapping: BTreeMap<String, BTreeSet<String>> = BTreeMap::new();
    for row in query_json(conn, "SELECT src, dst FROM edges", []).unwrap_or_default() {
        let src = field(&row, "src");
        let dst = field(&row, "dst");
        if let (Ok(source_kind), Ok(target_kind)) = (entity_type(&src), entity_type(&dst)) {
            if source_kind == "claim" && target_kind == "question" {
                mapping.entry(bare_id(&src).unwrap_or_default()).or_default()
                    .insert(bare_id(&dst).unwrap_or_default());
            } else if target_kind == "claim" && source_kind == "question" {
                mapping.entry(bare_id(&dst).unwrap_or_default()).or_default()
                    .insert(bare_id(&src).unwrap_or_default());
            }
        }
    }
    mapping
}

pub fn detect_contradictions(conn: &Connection, auto_link: bool) -> Result<Vec<Value>> {
    let rows = query_json(conn,
        "SELECT id, paper_id, text, stance, confidence FROM claims ORDER BY id", [])?;
    let supporting: Vec<&Value> = rows.iter().filter(|r| field(r, "stance") == "supports").collect();
    let contradicting: Vec<&Value> = rows.iter().filter(|r| field(r, "stance") == "contradicts").collect();
    let q_map = claim_question_map(conn);
    let mut pairs = Vec::new();
    for sup in &supporting {
        let sup_id = field(sup, "id");
        let sup_kw = keywords(&field(sup, "text"));
        let sup_qs = q_map.get(&sup_id).cloned().unwrap_or_default();
        for con in &contradicting {
            let con_id = field(con, "id");
            if sup_id == con_id { continue; }
            let con_kw = keywords(&field(con, "text"));
            let con_qs = q_map.get(&con_id).cloned().unwrap_or_default();
            let shared_qs: Vec<String> = sup_qs.intersection(&con_qs).cloned().collect();
            let shared_kw: Vec<String> = sup_kw.intersection(&con_kw).cloned().collect();
            if shared_qs.is_empty() && shared_kw.len() < 2 { continue; }
            let avg_conf = (number(sup, "confidence") + number(con, "confidence")) / 2.0;
            let bonus = (shared_qs.len() as f64 * 0.4 + shared_kw.len() as f64 * 0.15).min(1.0);
            let score = ((avg_conf * 0.6 + bonus * 0.4).min(1.0) * 1000.0).round() / 1000.0;
            let ref_a = format!("claim:{sup_id}");
            let ref_b = format!("claim:{con_id}");
            let edge_id = query_json(conn,
                "SELECT id FROM edges WHERE kind='contradicts' AND ((src=?1 AND dst=?2) OR (src=?2 AND dst=?1)) LIMIT 1",
                params![ref_a, ref_b])?.into_iter().next()
                .and_then(|r| r.get("id").and_then(Value::as_i64));
            let edge_id = match edge_id {
                Some(id) => Some(id),
                None if auto_link => Some(repo::add_edge(conn, &ref_a, &ref_b, "contradicts",
                    "Auto-detected opposing stance on shared scientific topic")?
                    .get("id").and_then(Value::as_i64).unwrap_or(0)),
                None => None,
            };
            pairs.push(json!({
                "claim_a_id": sup_id, "claim_b_id": con_id,
                "claim_a_text": field(sup, "text"), "claim_b_text": field(con, "text"),
                "paper_a_id": field(sup, "paper_id"), "paper_b_id": field(con, "paper_id"),
                "shared_question_ids": shared_qs, "shared_keywords": shared_kw,
                "score": score, "linked_edge_id": edge_id,
            }));
        }
    }
    pairs.sort_by(|a, b| {
        let sa = number(a, "score");
        let sb = number(b, "score");
        sb.partial_cmp(&sa).unwrap_or(std::cmp::Ordering::Equal)
            .then_with(|| b.get("shared_question_ids").and_then(Value::as_array).map(|v| v.len()).unwrap_or(0)
                .cmp(&a.get("shared_question_ids").and_then(Value::as_array).map(|v| v.len()).unwrap_or(0)))
            .then_with(|| b.get("shared_keywords").and_then(Value::as_array).map(|v| v.len()).unwrap_or(0)
                .cmp(&a.get("shared_keywords").and_then(Value::as_array).map(|v| v.len()).unwrap_or(0)))
    });
    Ok(pairs)
}

pub fn rank_influential_entities(conn: &Connection, limit: i64) -> Result<Value> {
    let cap = limit.max(1) as usize;
    let edges = query_json(conn, "SELECT src, dst, kind FROM edges", [])?;
    let mut degree: BTreeMap<String, i64> = BTreeMap::new();
    let mut citations: BTreeMap<String, i64> = BTreeMap::new();
    for row in &edges {
        let src = field(row, "src");
        let dst = field(row, "dst");
        *degree.entry(src.clone()).or_insert(0) += 1;
        *degree.entry(dst.clone()).or_insert(0) += 1;
        if field(row, "kind") == "cites" && entity_type(&dst).map(|k| k == "paper").unwrap_or(false) {
            let id = bare_id(&dst).unwrap_or_default();
            *citations.entry(id).or_insert(0) += 1;
        }
    }
    let claim_rows = query_json(conn,
        "SELECT id, paper_id, text, stance, confidence FROM claims ORDER BY id", [])?;
    let mut by_paper: BTreeMap<String, Vec<Value>> = BTreeMap::new();
    let mut ranked_claims = Vec::new();
    for row in &claim_rows {
        let id = field(row, "id");
        let paper_id = field(row, "paper_id");
        let confidence = number(row, "confidence");
        let deg = *degree.get(&format!("claim:{id}")).unwrap_or(&0);
        let score = ((confidence + deg as f64 * 0.35) * 1000.0).round() / 1000.0;
        let entry = json!({"id": id, "paper_id": paper_id, "text": field(row, "text"),
            "stance": field(row, "stance"), "confidence": confidence,
            "edge_degree": deg, "score": score});
        by_paper.entry(paper_id).or_default().push(entry.clone());
        ranked_claims.push(entry);
    }
    ranked_claims.sort_by(|a, b| (number(b, "score"), number(b, "confidence"))
        .partial_cmp(&(number(a, "score"), number(a, "confidence"))).unwrap_or(std::cmp::Ordering::Equal));
    let paper_rows = query_json(conn, "SELECT id, title, authors, year, doi FROM papers ORDER BY id", [])?;
    let mut ranked_papers = Vec::new();
    for row in &paper_rows {
        let id = field(row, "id");
        let claims = by_paper.get(&id).cloned().unwrap_or_default();
        let claim_weight: f64 = claims.iter().map(|c| number(c, "score")).sum();
        let cite_count = *citations.get(&id).unwrap_or(&0);
        let deg = *degree.get(&format!("paper:{id}")).unwrap_or(&0);
        let score = ((claim_weight + cite_count as f64 * 0.75 + deg as f64 * 0.25 + 0.1) * 1000.0).round() / 1000.0;
        ranked_papers.push(json!({
            "id": id, "title": field(row, "title"), "authors": field(row, "authors"),
            "year": field(row, "year"), "doi": field(row, "doi"),
            "claim_count": claims.len(), "citation_count": cite_count,
            "edge_degree": deg, "score": score,
        }));
    }
    ranked_papers.sort_by(|a, b| (number(b, "score"),
        b.get("claim_count").and_then(Value::as_u64).unwrap_or(0))
        .partial_cmp(&(number(a, "score"), a.get("claim_count").and_then(Value::as_u64).unwrap_or(0)))
        .unwrap_or(std::cmp::Ordering::Equal));
    Ok(json!({"papers": ranked_papers.into_iter().take(cap).collect::<Vec<_>>(),
        "claims": ranked_claims.into_iter().take(cap).collect::<Vec<_>>()}))
}

pub fn outline(conn: &Connection, tokens: i64) -> Result<Value> {
    let tokens = budget(tokens)?;
    let stats = repo::stats(conn)?;
    let rows = query_json(conn,
        "SELECT q.id, q.text, q.status, (SELECT COUNT(*) FROM edges e WHERE (e.src = 'question:' || q.id OR e.dst = 'question:' || q.id) AND e.kind IN ('supports','contradicts','answers')) AS evidence FROM questions q ORDER BY evidence DESC, q.id",
        [])?;
    let questions: Vec<Value> = rows.iter().map(|row| json!({
        "ref": format!("question:{}", field(row, "id")),
        "text": truncate(&field(row, "text"), 110),
        "status": field(row, "status"),
        "evidence": row.get("evidence").and_then(Value::as_i64).unwrap_or(0),
    })).collect();
    let small_budget = 60.max(tokens - 140);
    let (kept, omitted, _) = pack(&questions, small_budget);
    let type_rows = query_json(conn,
        "SELECT study_type, COUNT(*) AS n FROM papers WHERE study_type != '' GROUP BY study_type ORDER BY n DESC, study_type LIMIT 8", [])?;
    let study_types: Vec<Value> = type_rows.iter().map(|row| json!({
        "study_type": field(row, "study_type"),
        "papers": row.get("n").and_then(Value::as_i64).unwrap_or(0),
    })).collect();
    let mut counts = serde_json::Map::new();
    if let Value::Object(map) = &stats {
        for (key, value) in map { if key != "edge_kinds" { counts.insert(key.clone(), value.clone()); } }
    }
    Ok(json!({
        "counts": Value::Object(counts),
        "edge_kinds": stats.get("edge_kinds").cloned().unwrap_or(json!({})),
        "study_types": study_types,
        "budget_tokens": tokens,
        "questions": kept,
        "omitted_questions": omitted,
        "next": "Pick a ref, then search, related_findings or subgraph; get_entity expands one node.",
    }))
}

pub fn compact_search(result: &Value, tokens: i64) -> Result<Value> {
    let tokens = budget(tokens)?;
    let share = (60i64).max(tokens / 3);
    let papers: Vec<Value> = result.get("papers").and_then(Value::as_array).cloned().unwrap_or_default()
        .iter().map(|p| json!({
            "ref": format!("paper:{}", field(p, "id")),
            "title": truncate(&field(p, "title"), 120),
            "year": field(p, "year"),
            "study_type": field(p, "study_type"),
        })).collect();
    let claims: Vec<Value> = result.get("claims").and_then(Value::as_array).cloned().unwrap_or_default()
        .iter().map(|c| json!({
            "ref": format!("claim:{}", field(c, "id")),
            "snippet": truncate(&field(c, "text"), 160),
            "snippet_is_quote": false,
            "locator": if field(c, "locator").is_empty() { "MISSING".to_string() } else { field(c, "locator") },
            "stance": field(c, "stance"),
            "confidence": c.get("confidence").cloned().unwrap_or(json!(0.0)),
            "paper": (c.get("paper").and_then(|p| p.get("id")).and_then(Value::as_str)).unwrap_or(""),
        })).collect();
    let questions: Vec<Value> = result.get("questions").and_then(Value::as_array).cloned().unwrap_or_default()
        .iter().map(|q| json!({
            "ref": format!("question:{}", field(q, "id")),
            "text": truncate(&field(q, "text"), 120),
            "status": field(q, "status"),
        })).collect();
    let (kept_p, omitted_p, _) = pack(&papers, share);
    let (kept_c, omitted_c, _) = pack(&claims, share);
    let (kept_q, omitted_q, _) = pack(&questions, 60.max(tokens - 2 * share));
    Ok(json!({
        "query": field(result, "query"), "budget_tokens": tokens,
        "papers": kept_p, "omitted_papers": omitted_p,
        "claims": kept_c, "omitted_claims": omitted_c,
        "questions": kept_q, "omitted_questions": omitted_q,
        "next": "Snippets are pointers, never quotes. Call get_entity on a ref for its verbatim quote plus locator.",
    }))
}

pub fn compact_related(result: &Value, tokens: i64) -> Result<Value> {
    let tokens = budget(tokens)?;
    let items: Vec<Value> = result.get("related").and_then(Value::as_array).cloned().unwrap_or_default()
        .iter().map(|item| json!({
            "ref": field(item, "ref"), "relation": field(item, "relation"),
            "snippet": truncate(&field(item, "text"), 160), "snippet_is_quote": false,
            "locator": if field(item, "locator").is_empty() { "MISSING".to_string() } else { field(item, "locator") },
            "stance": field(item, "stance"),
            "confidence": item.get("confidence").cloned().unwrap_or(json!(0.0)),
            "paper": field(item, "paper"), "study_type": field(item, "study_type"),
            "reason": truncate(&field(item, "reason"), 120),
            "via": item.get("via").cloned().unwrap_or(json!([])),
        })).collect();
    let (kept, omitted, _) = pack(&items, tokens);
    Ok(json!({
        "root": field(result, "root"), "type": field(result, "type"),
        "budget_tokens": tokens, "count": kept.len(), "omitted": omitted,
        "related": kept,
        "next": "Snippets are pointers, never quotes. Call related_findings on any ref to continue, or get_entity for the verbatim quote plus locator.",
    }))
}

pub fn compact_subgraph(result: &Value, tokens: i64) -> Result<Value> {
    let tokens = budget(tokens)?;
    let nodes: Vec<Value> = result.get("nodes").and_then(Value::as_array).cloned().unwrap_or_default()
        .iter().map(|node| {
            let label_source = if !field(node, "title").is_empty() { field(node, "title") }
                else if !field(node, "text").is_empty() { field(node, "text") } else { field(node, "ref") };
            let locator = if !field(node, "locator").is_empty() { field(node, "locator") }
                else if field(node, "type") == "claim" { "MISSING".to_string() } else { String::new() };
            json!({
                "ref": field(node, "ref"), "type": field(node, "type"),
                "label": truncate(&label_source, 100), "label_is_quote": false,
                "locator": locator, "study_type": field(node, "study_type"),
            })
        }).collect();
    let (kept_nodes, omitted_nodes, used) = pack(&nodes, tokens);
    let kept_refs: BTreeSet<String> = kept_nodes.iter().map(|n| field(n, "ref")).collect();
    let edges: Vec<Value> = result.get("edges").and_then(Value::as_array).cloned().unwrap_or_default()
        .into_iter().filter(|edge| kept_refs.contains(&field(edge, "src")) && kept_refs.contains(&field(edge, "dst")))
        .map(|edge| json!({"src": field(&edge, "src"), "dst": field(&edge, "dst"), "kind": field(&edge, "kind")}))
        .collect();
    let (kept_edges, omitted_edges, _) = pack(&edges, 60.max(tokens - used));
    Ok(json!({
        "root": field(result, "root"),
        "depth": result.get("depth").and_then(Value::as_i64).unwrap_or(1),
        "budget_tokens": tokens,
        "nodes": kept_nodes, "omitted_nodes": omitted_nodes,
        "edges": kept_edges, "omitted_edges": omitted_edges,
        "next": "Labels are pointers, never quotes. Pick a node ref and call subgraph again to walk outward, or get_entity for its verbatim quote plus locator.",
    }))
}

fn render_markdown_pack(
    targets: &[String], questions: &[Value], claims: &[Value], papers: &[Value],
    contradictions: &[Value], omitted_claims: usize,
) -> String {
        let mut by_id = BTreeMap::new();
    for paper in papers { by_id.insert(field(paper, "id"), paper.clone()); }
    let render = || -> String {
        let mut lines = vec![
            "# GraphRAG Evidence Pack".to_string(),
            format!("**Targets:** {}", if targets.is_empty() { "(global)".to_string() } else { targets.join(", ") }),
            String::new(),
            "## 1. Research Questions".to_string(),
        ];
        if questions.is_empty() { lines.push("*(No specific questions linked)*".to_string()); }
        for q in questions {
            lines.push(format!("- **[{}]** {} *(status: {})*", field(q, "id"), field(q, "text"),
                if field(q, "status").is_empty() { "open".to_string() } else { field(q, "status") }));
        }
        lines.extend(["".to_string(), "## 2. Evidentiary Claims & Quotes".to_string()]);
        if claims.is_empty() {
            lines.push("*(No empirical claims available)*".to_string());
        }
        for claim in claims {
            let paper = by_id.get(&field(claim, "paper_id"));
            let source = match paper {
                Some(p) => format!("{} ({})", field(p, "title"), if field(p, "year").is_empty() { "n.d.".to_string() } else { field(p, "year") }),
                None => if field(claim, "paper_id").is_empty() { "unknown".to_string() } else { field(claim, "paper_id") },
            };
            lines.push(format!("- **[{}]** {}", field(claim, "id"), field(claim, "text")));
            lines.push(format!("  - *Stance:* `{}` | *Confidence:* {:.2} | *Locator:* `{}`",
                if field(claim, "stance").is_empty() { "mentions".to_string() } else { field(claim, "stance") },
                number(claim, "confidence"), if field(claim, "locator").is_empty() { "MISSING".to_string() } else { field(claim, "locator") }));
            if !field(claim, "quote").is_empty() {
                lines.push(format!("  - *Verbatim Quote:* \"{}\"", field(claim, "quote")));
            }
            lines.push(format!("  - *Source Paper:* {source}"));
        }
        if omitted_claims > 0 {
            lines.push(format!("\n> [!NOTE]\n> {omitted_claims} claim(s) omitted to fit within token budget."));
        }
        if !contradictions.is_empty() {
            lines.extend(["".to_string(), "## 3. Scientific Contradictions & Tensions".to_string()]);
            for pair in contradictions {
                lines.push(format!("- **Tension:** `{}` vs `{}` (Score: {:.2})",
                    field(pair, "claim_a_id"), field(pair, "claim_b_id"), number(pair, "score")));
                lines.push(format!("  - *Claim A:* {}", field(pair, "claim_a_text")));
                lines.push(format!("  - *Claim B:* {}", field(pair, "claim_b_text")));
            }
        }
        lines.extend(["".to_string(), "## 4. Ingested Papers & Provenance".to_string()]);
        if papers.is_empty() {
            lines.push("*(No source papers)*".to_string());
        }
        for paper in papers {
            let venue = if field(paper, "venue").is_empty() { String::new() } else { format!(" | {}", field(paper, "venue")) };
            let doi = if field(paper, "doi").is_empty() { String::new() } else { format!(" | DOI: {}", field(paper, "doi")) };
            let study = if field(paper, "study_type").is_empty() { String::new() } else { format!(" [{}]", field(paper, "study_type")) };
            lines.push(format!("- **[{}]** {} ({}){study}{venue}{doi}", field(paper, "id"), field(paper, "title"),
                if field(paper, "year").is_empty() { "n.d.".to_string() } else { field(paper, "year") }));
        }
        lines.join("\n")
    };
    render()
}

pub fn build_context_pack(conn: &Connection, targets: &[String], max_tokens: i64, format: &str) -> Result<Value> {
    let tokens = budget(max_tokens)?;
    let normalized = format.trim().to_lowercase();
    if normalized != "markdown" && normalized != "json" {
        return Err(EngineError::new(format!("unknown format '{format}'"),
            "context packs support markdown or json", "pass format='markdown' or format='json'"));
    }
    let target_list: Vec<String> = if targets.is_empty() {
        query_json(conn, "SELECT id FROM questions ORDER BY id LIMIT 5", [])?
            .iter().map(|r| format!("question:{}", field(r, "id"))).collect()
    } else { targets.to_vec() };

    let mut questions_map: BTreeMap<String, Value> = BTreeMap::new();
    let mut claims_map: BTreeMap<String, Value> = BTreeMap::new();
    let mut papers_map: BTreeMap<String, Value> = BTreeMap::new();
    for target in &target_list {
        if target.starts_with("question:") || target.starts_with("q_") {
            let id = if let Some(rest) = target.strip_prefix("question:") { rest.to_string() } else { target.clone() };
            if let Ok(q) = repo::get_question(conn, &id) {
                questions_map.insert(field(&q, "id"), q.clone());
                for edge in repo::neighbors(conn, &format!("question:{}", field(&q, "id")))? {
                    let other = if field(&edge, "src").starts_with("question:") { field(&edge, "dst") } else { field(&edge, "src") };
                    if let Some(claim_id) = other.strip_prefix("claim:") {
                        if let Ok(c) = repo::get_claim(conn, claim_id) {
                            claims_map.insert(field(&c, "id"), c.clone());
                            if let Ok(p) = repo::get_paper(conn, &field(&c, "paper_id")) {
                                papers_map.insert(field(&p, "id"), p);
                            }
                        }
                    }
                }
            }
        } else if target.starts_with("paper:") || target.starts_with("p_") {
            let id = if let Some(rest) = target.strip_prefix("paper:") { rest.to_string() } else { target.clone() };
            if let Ok(p) = repo::get_paper(conn, &id) {
                papers_map.insert(field(&p, "id"), p.clone());
                for row in query_json(conn, "SELECT id FROM claims WHERE paper_id=?1", params![field(&p, "id")])? {
                    if let Ok(c) = repo::get_claim(conn, &field(&row, "id")) {
                        claims_map.insert(field(&c, "id"), c.clone());
                        for edge in repo::neighbors(conn, &format!("claim:{}", field(&c, "id")))? {
                            let other = if field(&edge, "src").starts_with("claim:") { field(&edge, "dst") } else { field(&edge, "src") };
                            if let Some(qid) = other.strip_prefix("question:") {
                                if let Ok(q) = repo::get_question(conn, qid) { questions_map.insert(field(&q, "id"), q); }
                            }
                        }
                    }
                }
            }
        } else if target.starts_with("claim:") || target.starts_with("c_") {
            let id = if let Some(rest) = target.strip_prefix("claim:") { rest.to_string() } else { target.clone() };
            if let Ok(c) = repo::get_claim(conn, &id) {
                claims_map.insert(field(&c, "id"), c.clone());
                if let Ok(p) = repo::get_paper(conn, &field(&c, "paper_id")) { papers_map.insert(field(&p, "id"), p); }
                for edge in repo::neighbors(conn, &format!("claim:{}", field(&c, "id")))? {
                    let other = if field(&edge, "src").starts_with("claim:") { field(&edge, "dst") } else { field(&edge, "src") };
                    if let Some(qid) = other.strip_prefix("question:") {
                        if let Ok(q) = repo::get_question(conn, qid) { questions_map.insert(field(&q, "id"), q); }
                    }
                }
            }
        } else {
            let hits = repo::search(conn, target, 5)?;
            for q in hits.get("questions").and_then(Value::as_array).into_iter().flatten() {
                questions_map.insert(field(q, "id"), q.clone());
            }
            for c in hits.get("claims").and_then(Value::as_array).into_iter().flatten() {
                claims_map.insert(field(c, "id"), c.clone());
                let paper_ref = field(c, "paper_id");
                if !paper_ref.is_empty() {
                    if let Ok(p) = repo::get_paper(conn, &paper_ref) { papers_map.insert(field(&p, "id"), p); }
                }
            }
            for p in hits.get("papers").and_then(Value::as_array).into_iter().flatten() {
                papers_map.insert(field(p, "id"), p.clone());
            }
        }
    }

    let all_contradictions = detect_contradictions(conn, false)?;
    let contradictions: Vec<Value> = all_contradictions.into_iter()
        .filter(|pair| claims_map.contains_key(&field(pair, "claim_a_id")) && claims_map.contains_key(&field(pair, "claim_b_id")))
        .collect();
    let contra_ids: BTreeSet<String> = contradictions.iter().flat_map(|pair| [field(pair, "claim_a_id"), field(pair, "claim_b_id")]).collect();
    let mut sorted_claims: Vec<Value> = claims_map.values().cloned().collect();
    sorted_claims.sort_by(|a, b| {
        let flag_a = if contra_ids.contains(&field(a, "id")) { 1 } else { 0 };
        let flag_b = if contra_ids.contains(&field(b, "id")) { 1 } else { 0 };
        flag_b.cmp(&flag_a)
            .then_with(|| number(b, "confidence").partial_cmp(&number(a, "confidence")).unwrap_or(std::cmp::Ordering::Equal))
            .then_with(|| field(b, "id").cmp(&field(a, "id")))
    });
    let questions: Vec<Value> = questions_map.values().cloned().collect();
    let papers: Vec<Value> = papers_map.values().cloned().collect();

    let (content, kept_claims, omitted_claims) = if normalized == "markdown" {
        let mut rendered = render_markdown_pack(&target_list, &questions, &sorted_claims, &papers, &contradictions, 0);
        while kept_count(&sorted_claims, &rendered) > 1 && estimate_tokens(&rendered) as i64 > tokens {
            // approximate: drop the last claim by re-rendering with a shorter slice
            let count = kept_count(&sorted_claims, &rendered) - 1;
            rendered = render_markdown_pack(&target_list, &questions, &sorted_claims[..count], &papers, &contradictions, sorted_claims.len() - count);
        }
        let count = kept_count(&sorted_claims, &rendered);
        (rendered, sorted_claims[..count].to_vec(), sorted_claims.len() - count)
    } else {
        let mut count = sorted_claims.len();
        let text = loop {
            let payload = json!({
                "targets": target_list, "budget_tokens": tokens,
                "counts": {"questions": questions.len(), "claims": count,
                    "omitted_claims": sorted_claims.len() - count, "papers": papers.len(),
                    "contradictions": contradictions.len()},
                "questions": questions, "claims": &sorted_claims[..count],
                "papers": papers, "contradictions": contradictions,
            });
            let rendered = serde_json::to_string_pretty(&payload).unwrap_or_default();
            if estimate_tokens(&rendered) as i64 <= tokens || count <= 1 { break rendered; }
            count -= 1;
        };
        (text, sorted_claims[..count].to_vec(), sorted_claims.len() - count)
    };

    let data = json!({
        "targets": target_list,
        "counts": {"questions": questions_map.len(), "claims": kept_claims.len(),
            "omitted_claims": omitted_claims, "papers": papers_map.len(),
            "contradictions": contradictions.len()},
        "questions": questions, "claims": kept_claims, "papers": papers,
        "contradictions": contradictions,
    });
    Ok(json!({
        "targets": data.get("targets").cloned().unwrap_or_default(),
        "budget_tokens": tokens,
        "estimated_tokens": estimate_tokens(&content),
        "format": normalized,
        "content": content,
        "data": data,
    }))
}

fn kept_count(claims: &[Value], rendered: &str) -> usize {
    // Each kept claim contributes a bullet with its id; count those markers.
    claims.iter().filter(|c| rendered.contains(&format!("**[{}]**", field(c, "id")))).count()
}
