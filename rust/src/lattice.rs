//! Lattice adapter value rules and bibliography parsers (pure, no repository state).

use std::collections::BTreeMap;
use std::sync::OnceLock;

use regex::Regex;
use serde_json::{json, Value};
use sha1::{Digest, Sha1};

use crate::error::{EngineError, Result};

pub const STANCES: &[&str] = &["supports", "contradicts", "mentions"];
pub const STUDY_TYPES: &[&str] = &[
    "Meta-Analysis", "Systematic Review", "Literature Review", "Review",
    "Randomized Controlled Trial", "Cohort Study", "Case-Control Study",
    "Cross-Sectional Study", "Observational Study", "Qualitative Study", "Case Study",
    "Experimental Study", "In Vitro Study", "Animal Study", "Computational Study",
    "General Study",
];
pub const EDGE_KINDS: &[&str] = &[
    "cites", "supports", "contradicts", "replicates", "extends", "uses_method",
    "measures", "answers", "mentions", "related",
];
const FIELDS: &[&str] = &["title", "authors", "year", "venue", "doi", "arxiv", "url",
    "abstract", "tags", "study_type", "kind"];
const CSV_ALIASES: &[(&str, &str)] = &[
    ("tag", "tags"), ("keyword", "tags"), ("keywords", "tags"), ("subject", "tags"),
    ("study", "study_type"), ("study type", "study_type"), ("type", "study_type"),
];
const TAG_STOPWORDS: &[&str] = &[
    "a", "an", "and", "are", "as", "at", "be", "been", "being", "by", "can", "could", "did",
    "do", "does", "for", "from", "had", "has", "have", "how", "in", "into", "is", "it", "its",
    "may", "might", "more", "most", "of", "on", "or", "our", "over", "such", "than", "that",
    "the", "their", "them", "these", "they", "this", "those", "to", "under", "using", "was",
    "we", "were", "what", "when", "where", "which", "who", "why", "with", "within", "without",
    "study", "studies", "paper", "papers", "result", "results", "method", "methods", "approach",
    "approaches", "based", "new", "novel",
];

fn fail(what: impl Into<String>, why: impl Into<String>, fix: impl Into<String>) -> EngineError {
    EngineError::new(what, why, fix)
}

fn normalize_re() -> &'static Regex {
    static RE: OnceLock<Regex> = OnceLock::new();
    RE.get_or_init(|| Regex::new(r"[^a-z0-9]+").unwrap())
}

fn tag_word_re() -> &'static Regex {
    static RE: OnceLock<Regex> = OnceLock::new();
    RE.get_or_init(|| Regex::new(r"[A-Za-z][A-Za-z0-9-]{2,}").unwrap())
}

fn study_rules() -> &'static Vec<(&'static str, Regex)> {
    static RULES: OnceLock<Vec<(&'static str, Regex)>> = OnceLock::new();
    RULES.get_or_init(|| vec![
        ("Meta-Analysis", Regex::new(r"\bmeta[- ]?analy(?:sis|ses|tic)\b").unwrap()),
        ("Systematic Review", Regex::new(r"\bsystematic review\b").unwrap()),
        ("Literature Review", Regex::new(r"\bliterature review\b|\breview of (?:the )?literature\b").unwrap()),
        ("Review", Regex::new(r"\breview\b").unwrap()),
        ("Randomized Controlled Trial", Regex::new(r"\brandomi[sz]ed (?:controlled )?(?:trial|study)\b|\brct\b").unwrap()),
        ("Cohort Study", Regex::new(r"\bcohort\b").unwrap()),
        ("Case-Control Study", Regex::new(r"\bcase[- ]control\b").unwrap()),
        ("Cross-Sectional Study", Regex::new(r"\bcross[- ]sectional\b").unwrap()),
        ("Observational Study", Regex::new(r"\bobservational\b|\bsurvey\b|\bregistry\b").unwrap()),
        ("Qualitative Study", Regex::new(r"\bqualitative\b|\bfocus group(?:s)?\b|\binterview(?:s)?\b").unwrap()),
        ("Case Study", Regex::new(r"\bcase (?:study|report|series)\b").unwrap()),
        ("In Vitro Study", Regex::new(r"\bin vitro\b|\bcell cultur|\bassay\b|\bcultures?\b").unwrap()),
        ("Animal Study", Regex::new(r"\b(?:mice|mouse|rats?|rodents?|zebrafish|primates?|in vivo)\b").unwrap()),
        ("Computational Study", Regex::new(r"\bcomputational\b|\bsimulation\b|\bmachine learning\b|\bdeep learning\b|\btransformer\b|\bneural network\b").unwrap()),
        ("Experimental Study", Regex::new(r"\bexperiment(?:al|s)?\b|\btrial\b|\bintervention\b|\bstimulat(?:ed|ion)\b|\bparticipants?\b").unwrap()),
    ])
}

pub fn normalize_text(value: &str) -> String {
    normalize_re().replace_all(&value.to_lowercase(), " ").trim().to_string()
}

pub fn normalize_tags(value: &str) -> String {
    let mut tags: Vec<String> = Vec::new();
    for part in value.split(|c| c == ',' || c == ';') {
        let tag = normalize_text(part);
        if !tag.is_empty() && !tags.contains(&tag) { tags.push(tag); }
    }
    tags.join(", ")
}

pub fn derive_tags(title: &str, abstract_text: &str, limit: i64) -> Result<String> {
    if limit < 0 { return Err(fail(format!("tag limit {limit} is not an integer"), "tag derivation needs a numeric limit", "pass an integer limit such as 6")); }
    let mut counts: BTreeMap<String, i64> = BTreeMap::new();
    let mut order: BTreeMap<String, usize> = BTreeMap::new();
    for (source, weight) in [(title, 3i64), (abstract_text, 1i64)] {
        for found in tag_word_re().find_iter(source) {
            let word = found.as_str().to_lowercase();
            if TAG_STOPWORDS.contains(&word.as_str()) { continue; }
            *counts.entry(word.clone()).or_insert(0) += weight;
            let next_index = order.len();
            order.entry(word).or_insert(next_index);
        }
    }
    let mut ranked: Vec<String> = counts.keys().cloned().collect();
    ranked.sort_by(|a, b| (-counts[a], order[a], a).cmp(&(-counts[b], order[b], b)));
    Ok(ranked.into_iter().take(limit.max(0) as usize).collect::<Vec<_>>().join(", "))
}

pub fn normalize_study_type(value: &str) -> String {
    let cleaned: String = value.split_whitespace().collect::<Vec<_>>().join(" ");
    if cleaned.is_empty() { return String::new(); }
    let mut aliases: BTreeMap<String, &str> = BTreeMap::new();
    for name in STUDY_TYPES { aliases.insert(normalize_text(name), name); }
    for (key, value) in [
        ("meta analysis", "Meta-Analysis"),
        ("systematic literature review", "Systematic Review"),
        ("randomised controlled trial", "Randomized Controlled Trial"),
        ("randomized trial", "Randomized Controlled Trial"),
        ("rct", "Randomized Controlled Trial"),
        ("cohort", "Cohort Study"),
        ("case control", "Case-Control Study"),
        ("cross sectional", "Cross-Sectional Study"),
        ("qualitative", "Qualitative Study"),
        ("case report", "Case Study"),
        ("in vitro", "In Vitro Study"),
        ("animal", "Animal Study"),
        ("computational", "Computational Study"),
    ] { aliases.insert(key.to_string(), value); }
    aliases.get(&normalize_text(&cleaned)).map(|s| s.to_string()).unwrap_or(cleaned)
}

pub fn infer_study_type(title: &str, abstract_text: &str) -> String {
    let text = normalize_text(&format!("{title} {abstract_text}"));
    for (label, pattern) in study_rules().iter() {
        if pattern.is_match(&text) { return label.to_string(); }
    }
    "General Study".to_string()
}

pub fn paper_id(title: &str, doi: &str, arxiv: &str) -> Result<String> {
    let identity = {
        let doi = doi.trim().to_lowercase();
        let arxiv = arxiv.trim().to_lowercase();
        if !doi.is_empty() { doi } else if !arxiv.is_empty() { arxiv } else { normalize_text(title) }
    };
    if identity.is_empty() {
        return Err(fail("a paper needs a title, DOI or arXiv ID", "the identity would be empty", "pass a non-empty title or identifier"));
    }
    let mut hasher = Sha1::new();
    hasher.update(identity.as_bytes());
    let digest = format!("{:x}", hasher.finalize());
    Ok(format!("p_{}", &digest[..12]))
}

pub fn next_id(prefix: &str, rows: &[String]) -> String {
    let mut highest = 0u64;
    for value in rows {
        let suffix = value.strip_prefix(&format!("{prefix}_")).unwrap_or("");
        if !suffix.is_empty() && suffix.bytes().all(|b| b.is_ascii_digit()) {
            if let Ok(number) = suffix.parse::<u64>() { highest = highest.max(number); }
        }
    }
    format!("{prefix}_{:06}", highest + 1)
}

pub fn validate_stance(stance: Option<&str>) -> Result<String> {
    let value = stance.unwrap_or("mentions").trim().to_lowercase();
    if !STANCES.contains(&value.as_str()) {
        return Err(fail(format!("unknown stance \x27{}\x27", stance.unwrap_or("None")),
            format!("stance must be one of {}", STANCES.join(", ")),
            "use --stance supports, --stance contradicts or --stance mentions"));
    }
    Ok(value)
}

pub fn parse_confidence(value: Option<f64>) -> Result<f64> {
    let number = value.unwrap_or(0.5);
    if !(0.0..=1.0).contains(&number) {
        return Err(fail(format!("confidence {number} is outside [0, 1]"),
            "confidence is a probability-like weight", "pass a value between 0 and 1"));
    }
    Ok(number)
}

pub fn validate_edge_kind(kind: &str) -> Result<String> {
    let value = kind.trim().to_lowercase();
    if !EDGE_KINDS.contains(&value.as_str()) {
        return Err(fail(format!("unknown edge kind '{kind}'"),
            format!("kind must be one of {}", EDGE_KINDS.join(", ")), "use one of the listed --type values"));
    }
    Ok(value)
}

pub fn validate_locator(locator: &str) -> Result<String> {
    let value: String = locator.split_whitespace().collect::<Vec<_>>().join(" ");
    if value.is_empty() {
        return Err(fail("a claim needs a locator", "no locator, no entry: a quote without a pointer rots",
            "pass --locator abstract:s1, abstract, page 4, or key_findings"));
    }
    if value.len() > 200 {
        return Err(fail(format!("locator {value:?} is too long"), "a locator is a short pointer, not prose",
            "pass a short pointer such as abstract:s1 or page 4"));
    }
    Ok(value)
}

fn entity_type(reference: &str) -> Result<&'static str> {
    let Some((prefix, _)) = reference.split_once(':') else {
        return Err(fail(format!("'{reference}' is not a reference"),
            "references look like paper:p_xxx or claim:c_xxx", "pass a reference including its prefix"));
    };
    match prefix.trim().to_lowercase().as_str() {
        "paper" => Ok("paper"), "claim" => Ok("claim"), "question" => Ok("question"),
        other => Err(fail(format!("unknown reference prefix '{other}'"),
            "only paper, claim and question are entities", "use paper:, claim: or question:")),
    }
}

pub fn validate_ref(reference: &str) -> Result<String> {
    let kind = entity_type(reference)?;
    let value = reference.split_once(':').unwrap().1.trim();
    let prefix = match kind { "paper" => "p", "claim" => "c", _ => "q" };
    if !value.starts_with(&format!("{prefix}_")) {
        return Err(fail(format!("'{reference}' does not match its prefix"),
            format!("a {kind} id starts with '{prefix}_'"),
            format!("pass a reference such as {kind}:{prefix}_000001")));
    }
    Ok(format!("{kind}:{value}"))
}

pub fn bare_id(reference: &str) -> Result<String> {
    Ok(validate_ref(reference)?.split_once(':').unwrap().1.to_string())
}

pub fn estimate_tokens(text: &str) -> usize { ((text.len() + 3) / 4).max(1) }

fn empty_record() -> BTreeMap<String, String> {
    FIELDS.iter().map(|name| (name.to_string(), String::new())).collect()
}

fn clean(value: &str) -> String {
    let mut text: String = value.replace('\n', " ").split_whitespace().collect::<Vec<_>>().join(" ");
    if text.len() >= 2 && text.starts_with('{') && text.ends_with('}') {
        text = text[1..text.len() - 1].trim().to_string();
    } else if text.len() >= 2 && text.starts_with('"') && text.ends_with('"') {
        text = text[1..text.len() - 1].trim().to_string();
    }
    text
}

fn braced_span(text: &str, start: usize) -> isize {
    let mut depth = 0i32;
    for (index, ch) in text.char_indices().skip_while(|(i, _)| *i < start) {
        if ch == '{' { depth += 1; }
        else if ch == '}' {
            depth -= 1;
            if depth == 0 { return index as isize; }
        }
    }
    -1
}

fn split_top_level(text: &str) -> Vec<String> {
    let mut parts = Vec::new();
    let mut depth = 0i32;
    let mut quoted = false;
    let mut start = 0usize;
    for (index, ch) in text.char_indices() {
        if ch == '"' && depth == 0 { quoted = !quoted; }
        else if !quoted && ch == '{' { depth += 1; }
        else if !quoted && ch == '}' { depth = (depth - 1).max(0); }
        else if ch == ',' && depth == 0 && !quoted {
            parts.push(text[start..index].to_string());
            start = index + 1;
        }
    }
    parts.push(text[start..].to_string());
    parts.into_iter().filter(|p| !p.trim().is_empty()).collect()
}

pub fn parse_bibtex(text: &str) -> Result<Vec<Value>> {
    let mut records = Vec::new();
    let mut position = 0usize;
    loop {
        let Some(at) = text[position..].find('@').map(|i| position + i) else { break; };
        let Some(open) = text[at..].find('{').map(|i| at + i) else { break; };
        let close = braced_span(text, open);
        if close < 0 { return Err(fail("unbalanced braces in BibTeX input", "an entry never closes", "check the braces around the entry and its fields")); }
        let close = close as usize;
        let body = &text[open + 1..close];
        position = close + 1;
        let Some(comma) = body.find(',') else { continue; };
        let mut record = empty_record();
        for field in split_top_level(&body[comma + 1..]) {
            let Some((name, value)) = field.split_once('=') else { continue; };
            let key = name.trim().to_lowercase();
            let value = clean(value);
            match key.as_str() {
                "author" => insert(&mut record, "authors", value.replace(" and ", "; ")),
                "journal" | "booktitle" | "publisher" => insert(&mut record, "venue", value),
                "year" | "date" => insert(&mut record, "year", value.chars().take(4).collect()),
                "doi" | "url" | "abstract" => insert(&mut record, &key, value),
                "keywords" | "keyword" => insert(&mut record, "tags", value.replace(" and ", ", ")),
                "studytype" | "study_type" | "study-type" => insert(&mut record, "study_type", value),
                "eprint" => insert(&mut record, "arxiv", value),
                "title" => insert(&mut record, "title", value),
                _ => {}
            }
        }
        if !record["title"].is_empty() { records.push(json!(record)); }
    }
    Ok(records)
}

fn insert(record: &mut BTreeMap<String, String>, key: &str, value: String) {
    record.insert(key.to_string(), value);
}

pub fn parse_ris(text: &str) -> Vec<Value> {
    let mut records = Vec::new();
    let mut current = empty_record();
    let mut authors: Vec<String> = Vec::new();
    for line in text.lines() {
        let chars: Vec<char> = line.chars().collect();
        if chars.len() < 6 || chars[2] != ' ' || chars[3] != ' ' { continue; }
        let tag: String = chars[..2].iter().collect::<String>().trim().to_uppercase();
        let value: String = chars[5..].iter().collect::<String>().trim().to_string();
        match tag.as_str() {
            "TY" => { current = empty_record(); authors.clear(); }
            "TI" => insert(&mut current, "title", value),
            "AU" => authors.push(value),
            "JO" | "T2" | "JF" | "JA" => insert(&mut current, "venue", value),
            "PY" => insert(&mut current, "year", value.chars().take(4).collect()),
            "DO" => insert(&mut current, "doi", value),
            "UR" => insert(&mut current, "url", value),
            "AB" => insert(&mut current, "abstract", value),
            "KW" => {
                let existing = current["tags"].clone();
                insert(&mut current, "tags", format!("{existing}, {value}").trim_start_matches(", ").to_string());
            }
            "M3" => insert(&mut current, "study_type", value),
            "AN" if value.to_lowercase().contains("arxiv") => insert(&mut current, "arxiv",
                value.rsplit(':').next().unwrap_or("").trim().to_string()),
            "ER" => {
                if !current["title"].is_empty() {
                    insert(&mut current, "authors", authors.join("; "));
                    records.push(json!(current));
                }
                current = empty_record();
                authors.clear();
            }
            _ => {}
        }
    }
    if !current["title"].is_empty() {
        insert(&mut current, "authors", authors.join("; "));
        records.push(json!(current));
    }
    records
}

fn parse_csv_rows(text: &str) -> (Vec<String>, Vec<BTreeMap<String, String>>) {
    // Minimal RFC-4180 reader, sufficient for the metadata fields lattice accepts.
    let mut records = Vec::new();
    let mut header: Vec<String> = Vec::new();
    let mut field = String::new();
    let mut row: Vec<String> = Vec::new();
    let mut quoted = false;
    let chars: Vec<char> = text.chars().collect();
    let mut index = 0usize;
    while index < chars.len() {
        let ch = chars[index];
        if quoted {
            if ch == '"' {
                if index + 1 < chars.len() && chars[index + 1] == '"' { field.push('"'); index += 1; }
                else { quoted = false; }
            } else { field.push(ch); }
        } else if ch == '"' && field.trim().is_empty() {
            quoted = true;
        } else if ch == ',' {
            row.push(std::mem::take(&mut field));
        } else if ch == '\n' || ch == '\r' {
            if ch == '\r' && index + 1 < chars.len() && chars[index + 1] == '\n' { index += 1; }
            row.push(std::mem::take(&mut field));
            if header.is_empty() { header = row.iter().map(|s| s.trim().to_lowercase()).collect(); }
            else {
                let mut map = BTreeMap::new();
                for (key, value) in header.iter().zip(row.iter()) {
                    map.insert(key.clone(), value.trim().to_string());
                }
                records.push(map);
            }
            row.clear();
        } else { field.push(ch); }
        index += 1;
    }
    if !field.is_empty() || !row.is_empty() {
        row.push(field);
        if header.is_empty() { header = row.iter().map(|s| s.trim().to_lowercase()).collect(); }
        else {
            let mut map = BTreeMap::new();
            for (key, value) in header.iter().zip(row.iter()) { map.insert(key.clone(), value.trim().to_string()); }
            records.push(map);
        }
    }
    (header, records)
}

pub fn parse_csv(text: &str) -> Result<Vec<Value>> {
    let (header, rows) = parse_csv_rows(text);
    if header.is_empty() {
        return Err(fail("the CSV has no header row", "column names map the data to metadata fields",
            "add a header such as title,authors,year,doi,venue,url,abstract"));
    }
    let mut records = Vec::new();
    for row in rows {
        let mut record = empty_record();
        for field in FIELDS {
            insert(&mut record, field, row.get(*field).cloned().unwrap_or_default());
        }
        for (alias, target) in CSV_ALIASES {
            if record[*target].is_empty() {
                if let Some(value) = row.get(*alias) { insert(&mut record, target, value.clone()); }
            }
        }
        if !record["title"].is_empty() { records.push(json!(record)); }
    }
    Ok(records)
}

pub fn parse_csl_json(text: &str) -> Result<Vec<Value>> {
    let data: Value = serde_json::from_str(text)
        .map_err(|e| fail(format!("malformed CSL-JSON: {e}"), "CSL-JSON must be valid JSON", "check the syntax of the JSON input"))?;
    let items: Vec<Value> = if data.is_array() {
        data.as_array().unwrap().clone()
    } else if let Some(items) = data.get("items").and_then(Value::as_array) {
        items.clone()
    } else { vec![data.clone()] };
    let mut records = Vec::new();
    for item in items {
        let Some(object) = item.as_object() else { continue; };
        let get = |keys: &[&str]| -> String {
            for key in keys {
                if let Some(value) = object.get(*key) {
                    match value {
                        Value::Null => continue,
                        Value::String(s) => return clean(s),
                        other => return clean(&other.to_string()),
                    }
                }
            }
            String::new()
        };
        let mut record = empty_record();
        insert(&mut record, "title", get(&["title", "shortTitle"]));
        let authors: Vec<String> = match object.get("author").or_else(|| object.get("editor")) {
            Some(Value::String(s)) => vec![clean(s)],
            Some(Value::Array(items)) => items.iter().filter_map(|entry| {
                match entry {
                    Value::String(s) if !s.trim().is_empty() => Some(clean(s)),
                    Value::Object(map) => {
                        let literal = map.get("literal").and_then(Value::as_str).map(clean);
                        if let Some(value) = literal { return Some(value); }
                        let family = map.get("family").and_then(Value::as_str).map(clean).unwrap_or_default();
                        let given = map.get("given").and_then(Value::as_str).map(clean).unwrap_or_default();
                        if !family.is_empty() && !given.is_empty() { Some(format!("{given} {family}")) }
                        else if !family.is_empty() { Some(family) }
                        else if !given.is_empty() { Some(given) }
                        else { None }
                    }
                    _ => None,
                }
            }).collect(),
            _ => Vec::new(),
        };
        insert(&mut record, "authors", authors.join("; "));
        let issued = object.get("issued").or_else(|| object.get("created"))
            .or_else(|| object.get("published-print")).or_else(|| object.get("published-online"));
        let year_re = Regex::new(r"\b(19\d\d|20\d\d)\b").unwrap();
        let mut year = String::new();
        if let Some(Value::Object(map)) = issued {
            if let Some(Value::Array(parts)) = map.get("date-parts") {
                if let Some(Value::Array(first)) = parts.first() {
                    if let Some(value) = first.first() { year = value.to_string().chars().take(4).collect(); }
                }
            }
            if year.is_empty() {
                if let Some(raw) = map.get("raw").and_then(Value::as_str) {
                    if let Some(found) = year_re.find(raw) { year = found.as_str().to_string(); }
                }
            }
        } else if let Some(value) = issued {
            if let Some(found) = year_re.find(&value.to_string()) { year = found.as_str().to_string(); }
        }
        insert(&mut record, "year", year);
        insert(&mut record, "venue", get(&["container-title", "journalAbbreviation", "publisher", "collection-title"]));
        insert(&mut record, "doi", get(&["DOI", "doi"]));
        insert(&mut record, "url", get(&["URL", "url"]));
        insert(&mut record, "abstract", get(&["abstract", "note"]));
        let mut arxiv = get(&["arxiv", "eprint"]);
        if arxiv.is_empty() {
            let re = Regex::new(r"arxiv\.org/(?:abs|pdf)/([0-9]+\.[0-9]+(?:v[0-9]+)?)").unwrap();
            if let Some(found) = re.captures(&record["url"]) { arxiv = found[1].to_string(); }
        }
        insert(&mut record, "arxiv", arxiv);
        let tags = match object.get("keyword").or_else(|| object.get("keywords"))
            .or_else(|| object.get("tags")).or_else(|| object.get("categories")) {
            Some(Value::Array(values)) => values.iter().map(|v| clean(&v.to_string())).filter(|s| !s.is_empty()).collect::<Vec<_>>().join(", "),
            Some(Value::String(s)) => clean(s),
            _ => String::new(),
        };
        insert(&mut record, "tags", tags);
        let raw_type = get(&["study_type", "study-type", "studyType"]);
        if !raw_type.is_empty() { insert(&mut record, "study_type", normalize_study_type(&raw_type)); }
        if record["study_type"].is_empty() {
            let inferred = infer_study_type(&record["title"], &record["abstract"]);
            let study_type = if inferred != "General Study" { inferred }
                else if object.get("type").and_then(Value::as_str).unwrap_or("").to_lowercase().contains("review") { "Review".to_string() }
                else { "General Study".to_string() };
            insert(&mut record, "study_type", study_type);
        }
        if !record["title"].is_empty() { records.push(json!(record)); }
    }
    Ok(records)
}
