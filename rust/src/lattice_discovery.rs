//! Lattice literature discovery: offline corpus provider and provider helpers.

use std::collections::{BTreeMap, BTreeSet};

use rusqlite::Connection;
use serde_json::{json, Value};

use crate::error::{EngineError, Result};
use crate::lattice::normalize_text;
use crate::lattice_repo as repo;

pub const PROVIDERS: &[&str] = &["offline", "arxiv", "crossref", "openalex", "europepmc"];

fn doc(title: &str, authors: &str, year: &str, venue: &str, doi: &str, arxiv: &str,
       url: &str, abstract_text: &str, tags: &str, study_type: &str) -> BTreeMap<String, String> {
    let mut map = BTreeMap::new();
    for (key, value) in [("title", title), ("authors", authors), ("year", year), ("venue", venue),
        ("doi", doi), ("arxiv", arxiv), ("url", url), ("abstract", abstract_text),
        ("tags", tags), ("study_type", study_type)] {
        map.insert(key.to_string(), value.to_string());
    }
    map
}

pub fn seed_corpus() -> Vec<BTreeMap<String, String>> {
    vec![
        doc("Slow-Wave Sleep Consolidates Declarative Hippocampal Memory Traces",
            "Elena Vance; Marcus Chen", "2023", "Nature Neuroscience", "10.1038/nn.2023.014", "",
            "https://doi.org/10.1038/nn.2023.014",
            "Slow-wave sleep increased declarative recall accuracy by 28% compared with wakeful rest across 120 human participants. Targeted acoustic stimulation amplified spindle-oscillation coupling and stabilized hippocampal-neocortical memory traces.",
            "sleep, memory, hippocampus, slow-wave", "Experimental Study"),
        doc("REM Sleep Deprivation Fails to Impair Motor Skill Retention in Young Adults",
            "Haruki Sato; Priya Nair", "2024", "Sleep", "10.1093/sleep/zsae042", "",
            "https://doi.org/10.1093/sleep/zsae042",
            "Selective REM sleep suppression did not reduce procedural motor sequence retention compared with uninterrupted sleep controls. Cortical plasticity markers remained unchanged after 48 hours of recovery.",
            "sleep, rem, motor memory, plasticity", "Experimental Study"),
        doc("Quote-Backed Evidence Graphs Eliminate Citation Drift in Scientific Synthesis",
            "Ada Lovelace; Grace Hopper", "2025", "Journal of AI Research", "10.1613/jair.2025.109",
            "2502.04109", "https://arxiv.org/abs/2502.04109",
            "Enforcing exact verbatim quotes and typed claim-question links reduced unsupported synthesis statements by 73% across 500 biomedical literature reviews. Contradiction edges surfaced replication failures that flat vector retrieval missed.",
            "evidence graph, citation, synthesis, provenance", "Literature Review"),
        doc("Transformer Scaling Laws Exhibit Diminishing Returns Under Noisy Pretraining Corpora",
            "Linus Kowalski; Mei Lin", "2024", "ICML", "10.5555/icml.2024.881", "2406.08810",
            "https://arxiv.org/abs/2406.08810",
            "Curated deduplication improved downstream scientific question-answering accuracy by 19% at one-quarter of the compute budget compared with unfiltered web text.",
            "transformer, scaling, pretraining, deduplication", "Computational Study"),
    ]
}

fn field(value: &Value, name: &str) -> String {
    value.get(name).and_then(Value::as_str).unwrap_or("").to_string()
}

fn candidate(record: &BTreeMap<String, String>) -> Value {
    let get = |key: &str| record.get(key).cloned().unwrap_or_default();
    let mut metadata = serde_json::Map::new();
    for key in ["title", "authors", "year", "venue", "doi", "arxiv", "url", "abstract", "tags", "study_type"] {
        metadata.insert(key.to_string(), json!(get(key)));
    }
    metadata.insert("kind".to_string(), json!("paper"));
    metadata.insert("source".to_string(), json!("offline"));
    Value::Object(metadata)
}

pub fn validate_search_args(query: &str, limit: i64) -> Result<String> {
    let cleaned: String = query.split_whitespace().collect::<Vec<_>>().join(" ");
    if cleaned.is_empty() {
        return Err(EngineError::new("discovery needs a search query",
            "an empty query cannot be dispatched to a literature catalog",
            "pass a scientific topic or phrase to search"));
    }
    if limit < 1 {
        return Err(EngineError::new(format!("limit {limit} is not positive"),
            "discovery must request at least one candidate paper", "pass --limit 1 or more"));
    }
    Ok(cleaned)
}

pub fn offline_search(query: &str, limit: i64) -> Result<Vec<Value>> {
    let cleaned = validate_search_args(query, limit)?;
    let terms: Vec<String> = normalize_text(&cleaned).split_whitespace().map(|s| s.to_string()).collect();
    let mut scored: Vec<(i64, i64, Value)> = Vec::new();
    for (index, record) in seed_corpus().iter().enumerate() {
        let title = record.get("title").cloned().unwrap_or_default();
        let haystack = normalize_text(&format!("{} {} {} {}", title,
            record.get("abstract").cloned().unwrap_or_default(),
            record.get("authors").cloned().unwrap_or_default(),
            record.get("venue").cloned().unwrap_or_default()));
        let normalized_title = normalize_text(&title);
        let score: i64 = terms.iter().filter(|term| haystack.contains(term.as_str()))
            .map(|term| if normalized_title.contains(term) { 2 } else { 1 }).sum();
        if score > 0 {
            scored.push((score, -(index as i64), candidate(record)));
        }
    }
    scored.sort_by(|a, b| (b.0, b.1).cmp(&(a.0, a.1)));
    Ok(scored.into_iter().take(limit.max(0) as usize).map(|(_, _, value)| value).collect())
}

pub fn dedupe(candidates: &[Value]) -> Vec<Value> {
    let mut seen_dois = BTreeSet::new();
    let mut seen_arxiv = BTreeSet::new();
    let mut seen_titles = BTreeSet::new();
    let mut unique = Vec::new();
    for item in candidates {
        let doi = field(item, "doi").trim().to_lowercase();
        let arxiv = field(item, "arxiv").trim().to_lowercase();
        let title = normalize_text(&field(item, "title"));
        if !doi.is_empty() && seen_dois.contains(&doi) { continue; }
        if !arxiv.is_empty() && seen_arxiv.contains(&arxiv) { continue; }
        if !title.is_empty() && seen_titles.contains(&title) { continue; }
        if !doi.is_empty() { seen_dois.insert(doi); }
        if !arxiv.is_empty() { seen_arxiv.insert(arxiv); }
        if !title.is_empty() { seen_titles.insert(title); }
        unique.push(item.clone());
    }
    unique
}

pub fn discover(conn: &Connection, query: &str, source: &str, limit: i64, ingest: bool) -> Result<Value> {
    let sources: Vec<String> = source.split(',').map(|s| s.trim().to_string()).filter(|s| !s.is_empty()).collect();
    let sources = if sources.is_empty() { vec!["offline".to_string()] } else { sources };
    let cleaned = validate_search_args(query, limit)?;
    let mut raw = Vec::new();
    for source_name in &sources {
        if source_name != "offline" {
            return Err(EngineError::new(format!("unknown literature provider '{source_name}'"),
                format!("registered providers are: {}.", PROVIDERS.join(", ")),
                format!("pass --source with one of: {}", PROVIDERS.join(", "))));
        }
        raw.extend(offline_search(&cleaned, limit)?);
    }
    let candidates: Vec<Value> = dedupe(&raw).into_iter().take(limit.max(0) as usize).collect();
    let mut records = Vec::new();
    let mut created_count = 0usize;
    for candidate in &candidates {
        let mut entry = candidate.clone();
        if ingest {
            let mut metadata = BTreeMap::new();
            if let Value::Object(map) = candidate {
                for (key, value) in map {
                    if let Some(text) = value.as_str() { metadata.insert(key.clone(), text.to_string()); }
                }
            }
            let (paper, created) = repo::add_paper(conn, &metadata)?;
            entry.as_object_mut().unwrap().insert("id".to_string(), paper.get("id").cloned().unwrap_or_default());
            entry.as_object_mut().unwrap().insert("created".to_string(), json!(created));
            if created { created_count += 1; }
        }
        records.push(entry);
    }
    Ok(json!({
        "query": query, "source": sources.join(","), "ingested": ingest,
        "count": records.len(), "created": created_count, "records": records,
    }))
}

pub fn format_crossref_authors(authors: &[Value]) -> String {
    let names: Vec<String> = authors.iter().filter_map(|author| {
        let given = author.get("given").and_then(Value::as_str).unwrap_or("").trim();
        let family = author.get("family").or_else(|| author.get("name"))
            .and_then(Value::as_str).unwrap_or("").trim();
        let full: String = [given, family].into_iter().filter(|part| !part.is_empty())
            .collect::<Vec<_>>().join(" ");
        if full.is_empty() { None } else { Some(full) }
    }).collect();
    names.join("; ")
}

pub fn extract_crossref_year(item: &Value) -> String {
    for key in ["issued", "published-print", "published-online", "created"] {
        if let Some(parts) = item.get(key).and_then(|v| v.get("date-parts")).and_then(Value::as_array) {
            if let Some(first) = parts.first().and_then(Value::as_array) {
                if let Some(year) = first.first() { return year.to_string(); }
            }
        }
    }
    String::new()
}

pub fn reconstruct_inverted_abstract(inverted: &Value) -> String {
    let Some(object) = inverted.as_object() else { return String::new(); };
    let mut positions: BTreeMap<usize, String> = BTreeMap::new();
    for (word, indices) in object {
        let Some(list) = indices.as_array() else { continue; };
        for index in list.iter().filter_map(Value::as_u64) {
            positions.insert(index as usize, word.clone());
        }
    }
    let mut result = Vec::new();
    for (_, word) in positions { result.push(word); }
    result.join(" ")
}

pub fn provider_names() -> Vec<String> {
    let mut names: Vec<String> = PROVIDERS.iter().map(|name| name.to_string()).collect();
    names.sort();
    names
}
