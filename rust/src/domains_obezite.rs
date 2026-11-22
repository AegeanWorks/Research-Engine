//! Obezite domain pack: citation extraction and claim-row de-duplication.

use std::collections::BTreeMap;
use std::sync::OnceLock;

use regex::Regex;
use serde_json::{json, Value};

use crate::error::Result;

fn cleaners() -> &'static [Regex] {
    static PATTERNS: OnceLock<Vec<Regex>> = OnceLock::new();
    PATTERNS.get_or_init(|| [
        r"\[[^\]]*\]\([^)]*\)", r"(?i)PMID[:\s]*\d+", r"(?i)PMC\d+", r"(?i)NCT\d+",
        r"(?i)doi[^\s·|]*", r"10\.\d{4,}/[^\s·|)]*", r"10\.\d+",
        r"\d{4}\s*;\s*\d+\s*(\([^)]*\))?\s*:\s*[\dEe\-–]+", r"\b(19|20)\d{2}\b",
        r"\b\d+\s*[-–]\s*\d+\b", r"\bv?\d+\s*\(\d+\)",
        r"\p{Lu}[\w.\-]*\s+(ve\s+ark\.|et\s+al\.?)", r"(?i)(VA|Ç|K|T|H|G|Z|D|E|L)\-?\d+",
    ].iter().map(|pattern| Regex::new(pattern).expect("static citation pattern")).collect())
}

/// Extract claim numbers from a source column after stripping citation noise.
pub fn atiflar(text: &str) -> Vec<i64> {
    let mut cleaned = text.to_string();
    for pattern in cleaners() {
        cleaned = pattern.replace_all(&cleaned, " ").to_string();
    }
    let found = Regex::new(r"\d+").unwrap();
    let bytes = cleaned.as_bytes();
    let mut ids: Vec<i64> = found.find_iter(&cleaned).filter_map(|m| {
        let before = if m.start() > 0 { bytes.get(m.start() - 1).copied() } else { None };
        let after = bytes.get(m.end()).copied();
        let boundary = |c: Option<u8>| c.map(|value| value.is_ascii_alphanumeric() || value == b'_' || value == b'-').unwrap_or(false);
        if boundary(before) || boundary(after) { return None; }
        let digits = m.as_str();
        if digits.starts_with('0') || digits.len() > 3 { return None; }
        digits.parse::<i64>().ok()
    }).collect();
    ids.sort();
    ids.dedup();
    ids
}

/// (claim id, full line, zero-based line index) for every ledger claim row.
pub fn parse_claims(path: &std::path::Path) -> Vec<(i64, String, usize)> {
    if !path.is_file() { return Vec::new(); }
    let Ok(text) = std::fs::read_to_string(path) else { return Vec::new(); };
    let pattern = Regex::new(r"^\|\s*\*\*(\d+)\*\*\s*\|").unwrap();
    text.lines().enumerate().filter_map(|(index, line)| {
        pattern.captures(line).and_then(|captures| captures.get(1)
            .and_then(|m| m.as_str().parse::<i64>().ok())
            .map(|id| (id, line.to_string(), index)))
    }).collect()
}

pub fn find_duplicates(chunks: &[std::path::PathBuf], retracted: &std::path::Path) -> Vec<Value> {
    let mut first: BTreeMap<i64, (std::path::PathBuf, String, usize)> = BTreeMap::new();
    for chunk in chunks {
        for (id, line, index) in parse_claims(chunk) {
            first.entry(id).or_insert_with(|| (chunk.clone(), line, index));
        }
    }
    let mut duplicates = Vec::new();
    for (id, line, index) in parse_claims(retracted) {
        if let Some((chunk, chunk_line, chunk_index)) = first.get(&id) {
            duplicates.push(json!({
                "id": id,
                "chunk": chunk.to_string_lossy(),
                "chunk_name": chunk.file_name().map(|n| n.to_string_lossy().to_string()).unwrap_or_default(),
                "chunk_line": chunk_line,
                "chunk_index": chunk_index,
                "retracted": retracted.to_string_lossy(),
                "retracted_line": line,
                "retracted_index": index,
            }));
        }
    }
    duplicates
}

pub fn deduplicate(
    chunks: &[std::path::PathBuf],
    retracted: &std::path::Path,
    archive: &std::path::Path,
    updated: &std::path::Path,
    stamp: &str,
) -> Result<Value> {
    let duplicates = find_duplicates(chunks, retracted);
    let mut lines = vec![
        format!("# İDDİA DEFTERİ — MÜKERRER KAYITLAR (Arşiv: {stamp})\n\n"),
        "> Bu dosya `deduplicate_defter.py` tarafından otomatik oluşturuldu.\n".to_string(),
        "> **Kural:** İlk oluşum (chunk dosyalarında) korunur, ikinci oluşum buraya taşınır.\n".to_string(),
        "> Orijinal satır numaraları ve dosya kaynakları not edilmiştir.\n\n".to_string(),
        "## Mükerrer İddialar\n\n".to_string(),
        "| İddia | Chunk Dosyası | Chunk Satır | CURUTULMUS Satır | Not |\n".to_string(),
        "|-------|---------------|-------------|------------------|-----|\n".to_string(),
    ];
    let mut remove: std::collections::BTreeSet<usize> = std::collections::BTreeSet::new();
    for row in &duplicates {
        let id = row.get("id").and_then(Value::as_i64).unwrap_or(0);
        let chunk_name = row.get("chunk_name").and_then(Value::as_str).unwrap_or("");
        let chunk_index = row.get("chunk_index").and_then(Value::as_u64).unwrap_or(0);
        let retracted_index = row.get("retracted_index").and_then(Value::as_u64).unwrap_or(0);
        let retracted_line = row.get("retracted_line").and_then(Value::as_str).unwrap_or("");
        remove.insert(retracted_index as usize);
        lines.push(format!("| {id} | {chunk_name} | {} | {} | İlk oluşum chunk dosyasında; CURUTULMUS'tan taşındı |\n",
            chunk_index + 1, retracted_index + 1));
        lines.push(format!("\n### İddia {id} (CURUTULMUS'tan taşınan satır)\n\n"));
        lines.push("```markdown\n".to_string());
        lines.push(format!("{}\n", retracted_line.trim_end()));
        lines.push("```\n\n".to_string());
    }
    crate::util::atomic_write_text(archive, &lines.join(""))?;
    let raw = std::fs::read_to_string(retracted)?;
    let kept: Vec<&str> = raw.split_inclusive('\n').enumerate()
        .filter(|(index, _)| !remove.contains(index)).map(|(_, line)| line).collect();
    crate::util::atomic_write_text(updated, &kept.join(""))?;
    Ok(json!({
        "duplicates": duplicates.len(),
        "archive": archive.to_string_lossy(),
        "updated": updated.to_string_lossy(),
        "remaining": kept.len(),
    }))
}
