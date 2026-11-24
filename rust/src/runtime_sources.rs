//! Duplicate-source detection by normalized DOI and title (engine/duplicates.py).

use std::collections::BTreeMap;

use serde_json::{json, Value};

use crate::error::{EngineError, Result};

const DOI_PREFIXES: &[&str] = &[
    "https://doi.org/", "http://doi.org/", "https://dx.doi.org/",
    "http://dx.doi.org/", "https://www.doi.org/", "http://www.doi.org/", "doi:",
];

pub fn normalize_doi(value: &str) -> String {
    let mut text = value.trim().to_string();
    let lowered = text.to_lowercase();
    for prefix in DOI_PREFIXES {
        if lowered.starts_with(prefix) {
            text = text[prefix.len()..].to_string();
            break;
        }
    }
    text.trim().to_lowercase()
}

/// NFKD-fold accents, case and punctuation while keeping letters from every script.
pub fn normalize_title(value: &str) -> String {
    use unicode_normalization::UnicodeNormalization;
    let decomposed: String = value.nfkd()
        .filter(|c| !crate::util::is_combining(*c))
        .flat_map(|c| match c {
            'ß' => "ss".chars().collect::<Vec<_>>(),
            'Æ' => "AE".chars().collect::<Vec<_>>(),
            'æ' => "ae".chars().collect::<Vec<_>>(),
            'Œ' => "OE".chars().collect::<Vec<_>>(),
            'œ' => "oe".chars().collect::<Vec<_>>(),
            other => vec![other],
        })
        .collect();
    decomposed.to_lowercase().chars().map(|c| if c.is_alphanumeric() { c } else { ' ' })
        .collect::<String>().split_whitespace().collect::<Vec<_>>().join(" ")
}

fn text(value: &Value, key: &str) -> String {
    value.get(key).and_then(Value::as_str).unwrap_or("").to_string()
}

fn group(items: &[&Value], reason: &str, key: &str) -> Value {
    let mut ordered: Vec<&Value> = items.to_vec();
    ordered.sort_by(|a, b| text(a, "id").cmp(&text(b, "id")));
    json!({
        "research": text(ordered[0], "research_id"),
        "reason": reason,
        "key": key,
        "keep": text(ordered[0], "id"),
        "count": ordered.len(),
        "sources": ordered.iter().map(|item| json!({
            "id": text(item, "id"), "title": text(item, "title"),
            "year": item.get("year").cloned().unwrap_or(Value::Null),
            "doi": text(item, "doi"), "url": text(item, "url"),
            "status": text(item, "status"),
        })).collect::<Vec<_>>(),
    })
}

pub fn duplicate_sources(sources: &[Value], limit: Option<usize>) -> Result<Value> {
    if limit == Some(0) {
        return Err(EngineError::new("duplicate limit is 0",
            "a report needs at least one group", "pass --limit 1 or more"));
    }
    let mut groups: Vec<Value> = Vec::new();
    let mut assigned: std::collections::BTreeSet<String> = std::collections::BTreeSet::new();

    let mut by_doi: BTreeMap<(String, String), Vec<&Value>> = BTreeMap::new();
    for source in sources {
        let doi = normalize_doi(&text(source, "doi"));
        if !doi.is_empty() {
            by_doi.entry((text(source, "research_id"), doi)).or_default().push(source);
        }
    }
    for ((_, doi), items) in by_doi {
        if items.len() < 2 { continue; }
        groups.push(group(&items, "doi", &doi));
        for item in items { assigned.insert(text(item, "id")); }
    }

    let mut by_title_year: BTreeMap<(String, String, i64), Vec<&Value>> = BTreeMap::new();
    for source in sources {
        let title = normalize_title(&text(source, "title"));
        let id = text(source, "id");
        if title.is_empty() || assigned.contains(&id) { continue; }
        let year = source.get("year").and_then(Value::as_i64).unwrap_or(0);
        by_title_year.entry((text(source, "research_id"), title, year)).or_default().push(source);
    }
    for ((_, title, year), items) in by_title_year {
        if items.len() < 2 { continue; }
        groups.push(group(&items, "title_year",
            &format!("{title}|{}", if year == 0 { String::new() } else { year.to_string() })));
        for item in items { assigned.insert(text(item, "id")); }
    }

    let mut by_title: BTreeMap<(String, String), Vec<&Value>> = BTreeMap::new();
    for source in sources {
        let title = normalize_title(&text(source, "title"));
        if title.is_empty() || assigned.contains(&text(source, "id")) { continue; }
        by_title.entry((text(source, "research_id"), title)).or_default().push(source);
    }
    for ((_, title), items) in by_title {
        if items.len() < 2 { continue; }
        groups.push(group(&items, "title_variant", &title));
    }

    groups.sort_by(|a, b| {
        let ca = b.get("count").and_then(Value::as_u64).unwrap_or(0)
            .cmp(&a.get("count").and_then(Value::as_u64).unwrap_or(0));
        if ca != std::cmp::Ordering::Equal { return ca; }
        let ka = (text(a, "keep"), text(a, "reason"));
        let kb = (text(b, "keep"), text(b, "reason"));
        ka.cmp(&kb)
    });
    let total = groups.len();
    if let Some(limit) = limit { groups.truncate(limit); }
    Ok(json!({"research": "all", "groups": groups, "total": total, "returned": groups.len()}))
}
