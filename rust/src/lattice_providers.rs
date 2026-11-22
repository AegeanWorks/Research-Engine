//! Network-backed lattice literature providers: URL construction and response parsing.
//! Fetching is injectable, so these parsers are testable offline.

use std::sync::OnceLock;

use regex::Regex;
use serde_json::{json, Value};

use crate::error::{EngineError, Result};
use crate::lattice_discovery::validate_search_args;
use crate::util::to_stable_json;

fn tag_re() -> &'static Regex {
    static RE: OnceLock<Regex> = OnceLock::new();
    RE.get_or_init(|| Regex::new(r"<[^>]+>").unwrap())
}

fn collapse(text: &str) -> String {
    text.split_whitespace().collect::<Vec<_>>().join(" ")
}

fn strip_tags(text: &str) -> String {
    collapse(&tag_re().replace_all(text, " ").to_string())
}

fn candidate(source: &str, title: &str, authors: &str, year: &str, venue: &str,
             doi: &str, arxiv: &str, url: &str, abstract_text: &str, tags: &str) -> Value {
    json!({
        "title": title, "authors": authors, "year": year, "venue": venue, "doi": doi,
        "arxiv": arxiv, "url": url, "abstract": abstract_text, "tags": tags,
        "study_type": "", "kind": "paper", "source": source,
    })
}

fn quote_plus(value: &str) -> String {
    let mut out = String::new();
    for byte in value.as_bytes() {
        match byte {
            b'A'..=b'Z' | b'a'..=b'z' | b'0'..=b'9' | b'-' | b'_' | b'.' | b'~' => out.push(*byte as char),
            b' ' => out.push('+'),
            other => out.push_str(&format!("%{other:02X}")),
        }
    }
    out
}

pub fn query_url(source: &str, query: &str, limit: i64) -> Result<String> {
    let cleaned = validate_search_args(query, limit)?;
    let encoded = quote_plus(&cleaned);
    Ok(match source {
        "arxiv" => format!("http://export.arxiv.org/api/query?search_query={}&start=0&max_results={limit}",
            quote_plus(&format!("all:{cleaned}"))),
        "crossref" => format!("https://api.crossref.org/works?query={encoded}&rows={limit}"),
        "openalex" => format!("https://api.openalex.org/works?search={encoded}&per-page={limit}"),
        "europepmc" => format!("https://www.ebi.ac.uk/europepmc/webservices/rest/search?query={encoded}&format=json&resultType=core&pageSize={limit}"),
        other => return Err(EngineError::new(format!("unknown literature provider '{other}'"),
            "providers are a closed vocabulary", "pass arxiv, crossref, openalex or europepmc")),
    })
}

fn xml_text(block: &str, tag: &str) -> String {
    let pattern = format!(r"(?s)<(?:[A-Za-z0-9_-]+:)?{tag}(?:\s[^>]*)?>(.*?)</(?:[A-Za-z0-9_-]+:)?{tag}>");
    let re = Regex::new(&pattern).unwrap();
    re.captures(block).map(|c| collapse(&c[1].replace("&lt;", "<").replace("&gt;", ">")
        .replace("&quot;", "\"").replace("&apos;", "'").replace("&amp;", "&"))).unwrap_or_default()
}

pub fn parse_arxiv(payload: &str, limit: i64) -> Vec<Value> {
    let entry_re = Regex::new(r"(?s)<entry(?:\s[^>]*)?>(.*?)</entry>").unwrap();
    let mut out = Vec::new();
    for capture in entry_re.captures_iter(payload) {
        let entry = &capture[1];
        let title = xml_text(entry, "title");
        if title.is_empty() { continue; }
        let summary = xml_text(entry, "summary");
        let published = xml_text(entry, "published");
        let year = if published.len() >= 4 && published[..4].chars().all(|c| c.is_ascii_digit()) {
            published[..4].to_string()
        } else { String::new() };
        let raw_id = xml_text(entry, "id");
        let arxiv_id = if let Some(index) = raw_id.rfind("/abs/") { raw_id[index + 5..].to_string() } else { raw_id.clone() };
        let doi = xml_text(entry, "doi");
        let author_re = Regex::new(r"(?s)<author(?:\s[^>]*)?>(.*?)</author>").unwrap();
        let authors: Vec<String> = author_re.captures_iter(entry)
            .map(|c| xml_text(&c[1], "name")).filter(|name| !name.is_empty()).collect();
        out.push(candidate("arxiv", &title, &authors.join("; "), &year, "arXiv", &doi,
            &arxiv_id, &raw_id, &summary, ""));
    }
    out.into_iter().take(limit.max(0) as usize).collect()
}

fn items(payload: &str, key: &str) -> Vec<Value> {
    let data: Value = match serde_json::from_str(payload) { Ok(value) => value, Err(_) => return Vec::new() };
    data.get(key).and_then(Value::as_array).cloned().unwrap_or_default()
}

fn first_text(value: &Value, key: &str) -> String {
    value.get(key).and_then(Value::as_array).and_then(|a| a.first())
        .and_then(Value::as_str).map(collapse).unwrap_or_default()
}

pub fn parse_crossref(payload: &str, limit: i64) -> Vec<Value> {
    let data: Value = match serde_json::from_str(payload) { Ok(value) => value, Err(_) => return Vec::new() };
    let items = data.get("message").and_then(|m| m.get("items")).and_then(Value::as_array)
        .cloned().unwrap_or_default();
    let mut out = Vec::new();
    for item in items {
        let title = first_text(&item, "title");
        if title.is_empty() { continue; }
        let mut names = Vec::new();
        for author in item.get("author").and_then(Value::as_array).into_iter().flatten() {
            let given = author.get("given").and_then(Value::as_str).unwrap_or("").trim();
            let family = author.get("family").and_then(Value::as_str)
                .or_else(|| author.get("name").and_then(Value::as_str)).unwrap_or("").trim();
            let full = [given, family].into_iter().filter(|s| !s.is_empty()).collect::<Vec<_>>().join(" ");
            if !full.is_empty() { names.push(full); }
        }
        let mut year = String::new();
        for key in ["issued", "published-print", "published-online", "created"] {
            if let Some(parts) = item.get(key).and_then(|v| v.get("date-parts")).and_then(Value::as_array) {
                if let Some(first) = parts.first().and_then(Value::as_array) {
                    if let Some(value) = first.first() { year = value.to_string(); break; }
                }
            }
        }
        let raw_abstract = item.get("abstract").and_then(Value::as_str).unwrap_or("");
        let tags: Vec<String> = item.get("subject").and_then(Value::as_array).into_iter().flatten()
            .filter_map(Value::as_str).map(str::trim).filter(|s| !s.is_empty()).map(String::from).collect();
        out.push(candidate("crossref", &title, &names.join("; "), &year,
            &first_text(&item, "container-title"),
            item.get("DOI").and_then(Value::as_str).unwrap_or("").trim(),
            "", item.get("URL").and_then(Value::as_str).unwrap_or("").trim(),
            &strip_tags(raw_abstract), &tags.join(", ")));
    }
    out.into_iter().take(limit.max(0) as usize).collect()
}

fn reconstruct_inverted(inverted: &Value) -> String {
    let Some(object) = inverted.as_object() else { return String::new(); };
    let mut positions = std::collections::BTreeMap::new();
    for (word, indices) in object {
        if let Some(list) = indices.as_array() {
            for index in list.iter().filter_map(Value::as_u64) { positions.insert(index as usize, word.clone()); }
        }
    }
    positions.into_values().collect::<Vec<_>>().join(" ")
}

pub fn parse_openalex(payload: &str, limit: i64) -> Vec<Value> {
    let mut out = Vec::new();
    for item in items(payload, "results") {
        let title = collapse(item.get("title").and_then(Value::as_str).unwrap_or(""));
        if title.is_empty() { continue; }
        let mut doi = item.get("doi").and_then(Value::as_str).unwrap_or("").trim().to_string();
        for prefix in ["https://doi.org/", "http://doi.org/", "doi:"] {
            if doi.to_lowercase().starts_with(prefix) { doi = doi[prefix.len()..].to_string(); break; }
        }
        let authors: Vec<String> = item.get("authorships").and_then(Value::as_array).into_iter().flatten()
            .filter_map(|a| a.get("author").and_then(|x| x.get("display_name")).and_then(Value::as_str))
            .map(str::trim).filter(|s| !s.is_empty()).map(String::from).collect();
        let year = match item.get("publication_year") {
            Some(value) if !value.is_null() => value.to_string(),
            _ => String::new(),
        };
        let venue = item.get("primary_location").and_then(|v| v.get("source"))
            .and_then(|s| s.get("display_name")).and_then(Value::as_str).unwrap_or("").trim().to_string();
        let abstract_text = reconstruct_inverted(item.get("abstract_inverted_index").unwrap_or(&Value::Null));
        let tags: Vec<String> = item.get("keywords").and_then(Value::as_array).into_iter().flatten()
            .map(|k| k.as_str().map(str::to_string)
                .unwrap_or_else(|| k.get("display_name").and_then(Value::as_str).unwrap_or("").to_string()))
            .map(|s| s.trim().to_string()).filter(|s| !s.is_empty()).collect();
        out.push(candidate("openalex", &title, &authors.join("; "), &year, &venue, &doi, "",
            item.get("id").and_then(Value::as_str).unwrap_or("").trim(), &abstract_text, &tags.join(", ")));
    }
    out.into_iter().take(limit.max(0) as usize).collect()
}

pub fn parse_europepmc(payload: &str, limit: i64) -> Vec<Value> {
    let data: Value = match serde_json::from_str(payload) { Ok(value) => value, Err(_) => return Vec::new() };
    let items = data.get("resultList").and_then(|m| m.get("result")).and_then(Value::as_array)
        .cloned().unwrap_or_default();
    let mut out = Vec::new();
    for item in items {
        let title = collapse(item.get("title").and_then(Value::as_str).unwrap_or(""));
        if title.is_empty() { continue; }
        let pmid = item.get("id").and_then(Value::as_str).unwrap_or("").trim();
        let mut keywords: Vec<String> = match item.get("keywordList").and_then(|k| k.get("keyword")) {
            Some(Value::Array(list)) => list.iter().filter_map(Value::as_str).map(|s| s.trim().to_string()).collect(),
            Some(Value::String(text)) => vec![text.trim().to_string()],
            _ => Vec::new(),
        };
        keywords.retain(|s| !s.is_empty());
        let url = if pmid.is_empty() { String::new() } else { format!("https://europepmc.org/article/MED/{pmid}") };
        out.push(candidate("europepmc", &title,
            &collapse(item.get("authorString").and_then(Value::as_str).unwrap_or("")),
            item.get("pubYear").and_then(Value::as_str).unwrap_or("").trim(),
            &collapse(item.get("journalTitle").and_then(Value::as_str).unwrap_or("")),
            item.get("doi").and_then(Value::as_str).unwrap_or("").trim(), "", &url,
            &strip_tags(item.get("abstractText").and_then(Value::as_str).unwrap_or("")), &keywords.join(", ")));
    }
    out.into_iter().take(limit.max(0) as usize).collect()
}

pub fn parse(source: &str, payload: &str, limit: i64) -> Result<Vec<Value>> {
    match source {
        "arxiv" => Ok(parse_arxiv(payload, limit)),
        "crossref" => Ok(parse_crossref(payload, limit)),
        "openalex" => Ok(parse_openalex(payload, limit)),
        "europepmc" => Ok(parse_europepmc(payload, limit)),
        other => Err(EngineError::new(format!("unknown literature provider '{other}'"),
            "providers are a closed vocabulary", "pass arxiv, crossref, openalex or europepmc")),
    }
}

pub fn as_json(values: &[Value]) -> String {
    to_stable_json(&Value::Array(values.to_vec()))
}
