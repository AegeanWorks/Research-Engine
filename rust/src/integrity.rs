//! Graph integrity checks, ported from `engine/integrity.py`.
//!
//! Codes, severities, subjects and messages are the contract: the JSON report is
//! compared against the Python engine in the parity tests.

use std::borrow::Borrow;
use std::collections::{HashMap, HashSet};

use rusqlite::{params, Connection};
use serde_json::{json, Value};

use crate::error::Result;
use crate::util::{event_hash_for, query_json};
use crate::vocab::{DEPENDENCY_RELATIONS, CORROBORATION_RELATIONS};

fn finding(code: &str, severity: &str, subject: &str, message: impl Into<String>, fix: impl Into<String>) -> Value {
    json!({"code": code, "severity": severity, "subject": subject,
           "message": message.into(), "fix": fix.into()})
}

fn field(value: impl Borrow<Value>, name: &str) -> String {
    value.borrow().get(name).and_then(Value::as_str).unwrap_or("").to_string()
}

fn entity(conn: &Connection, kind: &str, id: &str) -> bool {
    let table = match kind {
        "claim" => "claim", "question" => "question",
        "hypothesis" => "hypothesis", "source" => "source",
        _ => return false,
    };
    conn.query_row(&format!("SELECT 1 FROM {table} WHERE id = ?1"), params![id], |_| Ok(())).is_ok()
}

fn cycles(conn: &Connection, relations: &[&str]) -> Vec<Vec<String>> {
    let mut graph: HashMap<String, Vec<String>> = HashMap::new();
    for rel in relations {
        let sql = "SELECT src_id, dst_id FROM edge WHERE src_kind='claim' AND dst_kind='claim' AND rel=?1 ORDER BY src_id, dst_id";
        for row in query_json(conn, sql, params![rel]).unwrap_or_default() {
            graph.entry(field(&row, "src_id")).or_default().push(field(&row, "dst_id"));
        }
    }
    let mut state: HashMap<String, u8> = HashMap::new();
    let mut stack: Vec<String> = Vec::new();
    let mut found = Vec::new();
    let mut seen: HashSet<Vec<String>> = HashSet::new();
    let mut keys: Vec<String> = graph.keys().cloned().collect();
    keys.sort();
    for node in keys {
        if state.get(&node).copied().unwrap_or(0) == 0 {
            visit(&node, &graph, &mut state, &mut stack, &mut found, &mut seen);
        }
    }
    found
}

fn visit(node: &str, graph: &HashMap<String, Vec<String>>, state: &mut HashMap<String, u8>,
         stack: &mut Vec<String>, found: &mut Vec<Vec<String>>, seen: &mut HashSet<Vec<String>>) {
    state.insert(node.to_string(), 1);
    stack.push(node.to_string());
    for neighbour in graph.get(node).into_iter().flatten() {
        match state.get(neighbour).copied().unwrap_or(0) {
            0 => visit(neighbour, graph, state, stack, found, seen),
            1 => {
                let start = stack.iter().position(|n| n == neighbour).unwrap_or(0);
                let mut cycle: Vec<String> = stack[start..].to_vec();
                cycle.push(neighbour.clone());
                let mut key = cycle.clone();
                key.sort();
                key.dedup();
                if seen.insert(key) { found.push(cycle); }
            }
            _ => {}
        }
    }
    stack.pop();
    state.insert(node.to_string(), 2);
}

/// Return every integrity finding; an empty list means the graph is coherent.
/// Every historical main-role group that passed twice with identical output.
fn verified_groups_any(conn: &Connection, test_id: &str) -> Result<Vec<String>> {
    let rows = query_json(conn,
        "SELECT run_group FROM test_run WHERE test_id=?1 AND role='main' \
         GROUP BY run_group HAVING COUNT(*)>=2 AND SUM(passed)=COUNT(*) \
         AND COUNT(DISTINCT exit_code||':'||stdout_sha256||':'||stderr_sha256)=1",
        params![test_id])?;
    Ok(rows.iter().map(|r| field(r, "run_group")).collect())
}

const INFO_STOPWORDS: &[&str] = &[
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from", "has",
    "have", "if", "in", "into", "is", "it", "its", "of", "on", "or", "that", "the",
    "their", "then", "there", "these", "this", "to", "was", "were", "will", "with",
];

fn info_words(text: &str) -> Vec<String> {
    text.to_lowercase().chars()
        .map(|c| if c.is_alphanumeric() { c } else { ' ' })
        .collect::<String>().split_whitespace().map(str::to_string).collect()
}

/// Information-quality classes for a stored claim quote (engine/information.py).
fn information_classes(quote: &str, questions: &[String], others: &[String]) -> Vec<&'static str> {
    let words = info_words(quote);
    let normalized = words.join(" ");
    let content: Vec<&String> = words.iter().filter(|w| !INFO_STOPWORDS.contains(&w.as_str())).collect();
    let mut classes = Vec::new();
    if content.len() >= 2 && questions.iter().any(|q| {
        let needle = normalized.clone();
        !needle.is_empty() && info_words(q).join(" ").contains(&needle)
    }) {
        classes.push("restates_question");
    }
    if !normalized.is_empty() && others.iter().any(|o| info_words(o).join(" ") == normalized) {
        classes.push("duplicate_quote");
    }
    if content.is_empty() {
        classes.push("stopword_only");
    }
    classes
}

/// Whether the declared negative control was falsified in one run group.
fn control_falsified(conn: &Connection, test_id: &str, group: &str) -> Result<bool> {
    let rows = query_json(conn,
        "SELECT exit_code, passed, stdout_sha256, stderr_sha256 FROM test_run \
         WHERE test_id=?1 AND run_group=?2 AND role='control' ORDER BY id",
        params![test_id, group])?;
    if rows.len() < 2 { return Ok(false); }
    let mut fingerprints = std::collections::BTreeSet::new();
    for row in &rows {
        if row.get("passed").and_then(Value::as_i64).unwrap_or(0) != 0 { return Ok(false); }
        fingerprints.insert(format!("{}:{}:{}", field(row, "exit_code"),
            field(row, "stdout_sha256"), field(row, "stderr_sha256")));
    }
    Ok(fingerprints.len() == 1)
}

/// Declared input files that no longer exist, resolved like the fingerprint.
fn missing_inputs(tests: &[Value]) -> Result<Vec<String>> {
    let root = crate::provenance::project_root();
    let mut missing = Vec::new();
    for test in tests {
        let declared: Vec<String> = serde_json::from_str(&field(test, "inputs_json"))
            .unwrap_or_default();
        for name in crate::provenance::resolve_inputs(&declared)? {
            let path = std::path::Path::new(&name);
            let resolved = if path.is_absolute() { path.to_path_buf() } else { root.join(path) };
            if !resolved.is_file() { missing.push(resolved.to_string_lossy().into_owned()); }
        }
    }
    Ok(missing)
}

fn common_parent(paths: &[String]) -> Option<String> {
    let components: Vec<Vec<String>> = paths.iter().map(|p| std::path::Path::new(p)
        .components().map(|c| c.as_os_str().to_string_lossy().into_owned()).collect()).collect();
    let first = components.first()?;
    let mut prefix = Vec::new();
    for (index, part) in first.iter().enumerate() {
        if components.iter().all(|p| p.get(index) == Some(part)) { prefix.push(part.clone()); }
        else { break; }
    }
    if prefix.is_empty() { None } else {
        Some(prefix.join(std::path::MAIN_SEPARATOR_STR))
    }
}

pub fn check(conn: &Connection) -> Result<Vec<Value>> {
    let mut findings = Vec::new();

    let version_rows = query_json(conn, "SELECT version FROM schema_meta", [])?;
    let meta_ok = version_rows.len() == 1 && version_rows[0].get("version").and_then(Value::as_i64).is_some();
    if !meta_ok {
        findings.push(finding("SCHEMA-001", "error", "schema_meta",
            "the schema ledger is corrupt: expected exactly one integer version row",
            "restore the database from a backup; never hand-edit schema_meta."));
    }

    let mut previous = String::new();
    for event in query_json(conn, "SELECT * FROM event ORDER BY seq, id", [])? {
        let id = field(&event, "id");
        let stored = field(&event, "event_hash");
        if stored.is_empty() {
            previous.clear(); // pre-hash rows are grandfathered
            continue;
        }
        let prev = field(&event, "prev_hash");
        let reason = if prev != previous {
            Some("event does not link to its predecessor")
        } else {
            let expected = event_hash_for(
                &prev, &id, &field(&event, "at"), &field(&event, "research_id"),
                &field(&event, "kind"), &field(&event, "subject"), &field(&event, "detail"),
                &field(&event, "actor"), event.get("seq").and_then(Value::as_i64).unwrap_or(0),
                &field(&event, "root_id"), &field(&event, "parent_id"),
            );
            (expected != stored).then_some("stored digest does not match the event content")
        };
        if let Some(reason) = reason {
            findings.push(finding("LEDGER-001", "error", &id,
                format!("event ledger is broken: {reason}"),
                "restore the event row from a backup; never hand-edit the event log."));
        }
        previous = stored;
    }

    let sql = "SELECT * FROM claim WHERE kind='empirical' AND (source_id IS NULL OR trim(quote)='' OR trim(locator)='')";
    for row in query_json(conn, sql, [])? {
        findings.push(finding("PROV-001", "error", &field(&row, "id"),
            "empirical claim lacks a source, exact quote, or locator",
            "record the missing provenance, or reclassify the claim as derived/assumption."));
    }

    for row in query_json(conn, "SELECT * FROM source WHERE year IS NULL AND trim(doi)='' AND trim(url)=''", [])? {
        findings.push(finding("PROV-002", "error", &field(&row, "id"),
            "source has no year, DOI or URL", "add an identifier so the source can be found again."));
    }

    let sql = "SELECT * FROM claim WHERE status IN ('PROVEN','NUMERIC') AND (trim(kill_test)='' OR NOT EXISTS (SELECT 1 FROM verdict v WHERE v.subject_kind='claim' AND v.subject_id=claim.id AND v.status=claim.status AND trim(v.evidence)<>''))";
    for row in query_json(conn, sql, [])? {
        findings.push(finding("EVID-001", "error", &field(&row, "id"),
            "promoted claim has no kill test or no evidence-backed verdict",
            "record the kill test and the evidence path, or downgrade the claim."));
    }

    let sql = "SELECT c.* FROM claim c WHERE c.status='NUMERIC' AND NOT EXISTS (SELECT 1 FROM killtest t WHERE t.claim_id=c.id AND EXISTS (SELECT 1 FROM (SELECT run_group FROM test_run WHERE test_id=t.id AND role='main' GROUP BY run_group HAVING COUNT(*)>=2 AND SUM(passed)=COUNT(*) AND COUNT(DISTINCT exit_code||':'||stdout_sha256||':'||stderr_sha256)=1)))";
    for row in query_json(conn, sql, [])? {
        findings.push(finding("EVID-002", "error", &field(&row, "id"),
            "numeric claim has no test that passed twice with identical output",
            "bind a deterministic test and run `test verify`, or relabel the claim."));
    }

    let sql = "SELECT c.* FROM claim c WHERE c.status='UNKNOWN' AND NOT EXISTS (SELECT 1 FROM verdict v WHERE v.subject_kind='claim' AND v.subject_id=c.id AND v.status='UNKNOWN' AND trim(v.evidence)<>'')";
    for row in query_json(conn, sql, [])? {
        findings.push(finding("EVID-007", "warning", &field(&row, "id"),
            "UNKNOWN claim has no recorded reason for the missing evidence",
            "record what is missing with `claim verdict --status UNKNOWN --evidence ...`, or leave the claim UNVERIFIED."));
    }

    let sql = "SELECT id FROM killtest WHERE EXISTS (SELECT 1 FROM (SELECT run_group FROM test_run WHERE test_id=killtest.id AND role='main' GROUP BY run_group HAVING COUNT(*)>=2 AND SUM(passed)=COUNT(*) AND COUNT(DISTINCT exit_code||':'||stdout_sha256||':'||stderr_sha256)=1)) AND trim(control_command)=''";
    for row in query_json(conn, sql, [])? {
        findings.push(finding("EVID-008", "warning", &field(&row, "id"),
            "test produces verified evidence but declares no negative control, so vacuity is not excluded",
            "add `--control CMD` with a command that must fail, then re-verify."));
    }

    let sql = "SELECT c.id, s.id AS source_id, s.screening AS screening FROM claim c JOIN source s ON s.id=c.source_id WHERE s.screening IN ('screened_out','excluded') AND c.status NOT IN ('FALSIFIED','RETRACTED','INVALIDATED') ORDER BY c.id";
    for row in query_json(conn, sql, [])? {
        findings.push(finding("SCREEN-001", "warning", &field(&row, "id"),
            format!("claim cites source {} screened out of the review ({})", field(&row, "source_id"), field(&row, "screening")),
            "justify the inclusion, or replace the source and re-record the claim."));
    }

    let sql = "SELECT c.id, s.id AS source_id FROM claim c JOIN source s ON s.id=c.source_id WHERE s.status='retracted' AND c.status NOT IN ('FALSIFIED','RETRACTED','INVALIDATED') ORDER BY c.id";
    for row in query_json(conn, sql, [])? {
        findings.push(finding("PROV-003", "error", &field(&row, "id"),
            format!("claim cites retracted source {}", field(&row, "source_id")),
            "retract the claim (`source retract` does this) or replace the source."));
    }

    let sql = "SELECT c.id, s.id AS source_id FROM claim c JOIN source s ON s.id=c.source_id WHERE s.status='expression_of_concern' AND c.status NOT IN ('FALSIFIED','RETRACTED','INVALIDATED') ORDER BY c.id";
    for row in query_json(conn, sql, [])? {
        findings.push(finding("PROV-004", "warning", &field(&row, "id"),
            format!("claim cites source {} under an expression of concern", field(&row, "source_id")),
            "record the concern in the claim note, or replace the source."));
    }

    let sql = "SELECT c.* FROM claim c WHERE c.status IN ('FALSIFIED','RETRACTED','INVALIDATED') AND NOT EXISTS (SELECT 1 FROM verdict v WHERE v.subject_kind='claim' AND v.subject_id=c.id AND v.status=c.status AND trim(v.evidence)<>'')";
    for row in query_json(conn, sql, [])? {
        findings.push(finding("EVID-003", "error", &field(&row, "id"),
            format!("claim status {} has no verdict evidence", field(&row, "status")),
            "record the failing evidence, or return the claim to UNVERIFIED."));
    }

    let sql = "SELECT h.* FROM hypothesis h WHERE h.status IN ('SUPPORTED','REFUTED','INCONCLUSIVE') AND NOT EXISTS (SELECT 1 FROM verdict v WHERE v.subject_kind='hypothesis' AND v.subject_id=h.id AND v.status=h.status AND trim(v.evidence)<>'')";
    for row in query_json(conn, sql, [])? {
        findings.push(finding("EVID-004", "error", &field(&row, "id"),
            "hypothesis outcome has no evidence-backed verdict",
            "record the outcome evidence, or leave the hypothesis pre-registered."));
    }

    for cycle in cycles(conn, DEPENDENCY_RELATIONS) {
        findings.push(finding("GRAPH-001", "error", &cycle[0],
            format!("dependency cycle: {}", cycle.join(" -> ")),
            "remove one dependency edge so premises form a DAG."));
    }
    for cycle in cycles(conn, CORROBORATION_RELATIONS) {
        let unique: HashSet<&String> = cycle.iter().collect();
        if unique.len() < 2 { continue; }
        findings.push(finding("GRAPH-004", "warning", &cycle[0],
            format!("corroboration cycle: {}", cycle.join(" -> ")),
            "break the ring: mutual support is circular; keep the stronger direction or route both through shared evidence."));
    }

    for row in query_json(conn, "SELECT * FROM edge ORDER BY id", [])? {
        for (kind_key, id_key) in [("src_kind", "src_id"), ("dst_kind", "dst_id")] {
            let kind = field(&row, kind_key);
            let reference = field(&row, id_key);
            if !entity(conn, &kind, &reference) {
                findings.push(finding("GRAPH-002", "error", &field(&row, "id"),
                    format!("edge points to missing {kind} {reference}"),
                    "delete the dangling edge or restore the record."));
            }
        }
        if field(&row, "src_kind") == field(&row, "dst_kind") && field(&row, "src_id") == field(&row, "dst_id") {
            findings.push(finding("GRAPH-003", "error", &field(&row, "id"),
                "self edge", "delete the edge: a record cannot relate to itself."));
        }
    }

    let sql = "SELECT e.id, e.src_id, e.dst_id, src.status AS src_status, dst.status AS dst_status FROM edge e JOIN claim src ON src.id=e.src_id JOIN claim dst ON dst.id=e.dst_id WHERE e.src_kind='claim' AND e.dst_kind='claim' AND e.rel IN ('derived_from','depends_on') AND dst.status IN ('FALSIFIED','RETRACTED','INVALIDATED') AND src.status NOT IN ('FALSIFIED','RETRACTED','INVALIDATED')";
    for row in query_json(conn, sql, [])? {
        findings.push(finding("CASCADE-001", "error", &field(&row, "src_id"),
            format!("dependent is {} while premise {} is {}", field(&row, "src_status"), field(&row, "dst_id"), field(&row, "dst_status")),
            "run `claim invalidate` on the premise, or replace the failed premise."));
    }

    let sql = "SELECT t.id, t.claim_id, c.status FROM killtest t JOIN claim c ON c.id=t.claim_id WHERE c.status IN ('RETRACTED','INVALIDATED') ORDER BY t.id";
    for row in query_json(conn, sql, [])? {
        findings.push(finding("TEST-001", "warning", &field(&row, "id"),
            format!("test targets retired claim {} ({})", field(&row, "claim_id"), field(&row, "status")),
            "bind a test to the surviving claim, or record why the test is kept for history."));
    }

    let sql = "SELECT e.id, e.src_id, e.dst_id FROM edge e JOIN claim c ON c.id=e.dst_id WHERE e.src_kind='claim' AND e.dst_kind='claim' AND e.rel IN ('derived_from','depends_on') AND c.superseded_by IS NOT NULL ORDER BY e.id";
    for row in query_json(conn, sql, [])? {
        findings.push(finding("REV-001", "warning", &field(&row, "src_id"),
            format!("dependent still points at superseded claim {}", field(&row, "dst_id")),
            "re-link the dependent to the revision head, or record why the old link stands."));
    }

    let sql = "SELECT t.id, t.claim_id FROM killtest t JOIN claim c ON c.id=t.claim_id WHERE c.superseded_by IS NOT NULL ORDER BY t.id";
    for row in query_json(conn, sql, [])? {
        findings.push(finding("REV-002", "warning", &field(&row, "id"),
            format!("test targets superseded claim {}", field(&row, "claim_id")),
            "bind the test to the revision head, or record why the old test is kept."));
    }

    let sql = "SELECT q.* FROM question q WHERE q.status='open' AND NOT EXISTS (SELECT 1 FROM edge e WHERE e.dst_kind='question' AND e.dst_id=q.id AND e.src_kind='claim' AND e.rel IN ('supports','contradicts','answers'))";
    for row in query_json(conn, sql, [])? {
        findings.push(finding("GAP-001", "warning", &field(&row, "id"),
            "open question has no supporting or contradicting claim",
            "collect evidence, or close the question as out of scope."));
    }

    let sql = "SELECT c.* FROM claim c WHERE c.superseded_by IS NULL AND NOT EXISTS (SELECT 1 FROM edge e WHERE e.src_kind='claim' AND e.src_id=c.id AND e.dst_kind='question')";
    for row in query_json(conn, sql, [])? {
        findings.push(finding("GAP-002", "warning", &field(&row, "id"),
            "claim is not linked to any question",
            "link it with `claim link-question`, or record why it is standalone."));
    }

    let sql = "SELECT claim_id, MAX(at) AS data_at FROM observation GROUP BY claim_id ORDER BY claim_id";
    for row in query_json(conn, sql, [])? {
        let claim_id = field(&row, "claim_id");
        let analysis: String = query_json(conn,
            "SELECT MAX(at) AS last FROM event WHERE subject=?1 AND kind IN ('claim.stats','claim.trend')",
            params![claim_id])?
            .into_iter().next().map(|r| field(&r, "last")).unwrap_or_default();
        let observation_ids: Vec<String> = query_json(conn,
            "SELECT id FROM observation WHERE claim_id=?1 ORDER BY id", params![claim_id])?
            .into_iter().map(|r| field(&r, "id")).collect();
        let mut voided_at = String::new();
        for id in &observation_ids {
            let last: String = query_json(conn,
                "SELECT MAX(at) AS last FROM event WHERE kind='observation.void' AND subject=?1",
                params![id])?
                .into_iter().next().map(|r| field(&r, "last")).unwrap_or_default();
            if last > voided_at { voided_at = last; }
        }
        let live: i64 = conn.query_row(
            "SELECT COUNT(*) FROM observation WHERE claim_id=?1 AND voided=0",
            params![claim_id], |r| r.get(0)).unwrap_or(0);
        let data_at = field(&row, "data_at").max(voided_at);
        if (!analysis.is_empty() && analysis >= data_at) || (analysis.is_empty() && live == 0) {
            continue;
        }
        let message = if analysis.is_empty() {
            "claim has recorded observations but no statistics run"
        } else {
            "observations changed after the last statistics run"
        };
        findings.push(finding("OBS-001", "warning", &claim_id, message,
            "re-run `analysis stats CLAIM --baseline ... --treatment ...` before citing numbers."));
    }

    let sql = "SELECT id, claim_id FROM observation WHERE voided=0 AND (trim(instrument_id)='' OR trim(rater_id)='' OR trim(protocol_id)='') ORDER BY id";
    for row in query_json(conn, sql, [])? {
        findings.push(finding("OBS-002", "warning", &field(&row, "id"),
            format!("observation for {} has no measurement provenance", field(&row, "claim_id")),
            "record the instrument, rater and protocol together, or keep it as legacy data."));
    }
    let sql = "SELECT id, claim_id FROM observation WHERE voided=0 AND provenance_class='unclassified' ORDER BY id";
    for row in query_json(conn, sql, [])? {
        findings.push(finding("OBS-003", "warning", &field(&row, "id"),
            format!("observation for {} is not classified independent or self-reported", field(&row, "claim_id")),
            "pass --provenance-class when recording, or keep it as legacy data."));
    }
    let sql = "SELECT id, claim_id FROM observation WHERE voided=0 AND provenance_class='self_reported' ORDER BY id";
    for row in query_json(conn, sql, [])? {
        findings.push(finding("OBS-004", "warning", &field(&row, "id"),
            format!("self-reported measurement for {} is quarantined", field(&row, "claim_id")),
            "use an independent measurement for a comparative claim, or record a caveat."));
    }

    // DUP-001 — duplicate live claim text inside one program.
    let sql = "SELECT research_id, text, COUNT(*) AS n FROM claim WHERE \
               status NOT IN ('RETRACTED','INVALIDATED') AND superseded_by IS NULL \
               GROUP BY research_id, text HAVING n > 1 ORDER BY research_id";
    for row in query_json(conn, sql, [])? {
        findings.push(finding("DUP-001", "warning", &field(&row, "research_id"),
            format!("duplicate claim text appears {} times", row["n"].as_i64().unwrap_or(0)),
            "merge duplicates, or differentiate the assertions."));
    }

    // DUP-002 — sources sharing a normalized DOI or title.
    let sources = query_json(conn, "SELECT * FROM source ORDER BY id", [])?;
    if let Ok(groups) = crate::runtime_sources::duplicate_sources(&sources, None) {
        for group in groups.get("groups").and_then(Value::as_array).unwrap_or(&Vec::new()) {
            let ids: Vec<String> = group.get("sources").and_then(Value::as_array)
                .unwrap_or(&Vec::new()).iter().map(|s| field(s, "id")).collect();
            let key: String = field(group, "key").chars().take(120).collect();
            let detail = match field(group, "reason").as_str() {
                "doi" => format!("share DOI '{key}'"),
                "title_year" => format!("share the normalized title/year '{key}'"),
                _ => format!("share the normalized title '{key}'"),
            };
            findings.push(finding("DUP-002", "warning", &field(group, "keep"),
                format!("sources {} {detail}", ids.join(", ")),
                "keep one source, re-point its claims, and stop citing the duplicate."));
        }
    }

    // EMPTY-001 — research program with no claims.
    for row in query_json(conn, "SELECT r.id FROM research r WHERE NOT EXISTS \
        (SELECT 1 FROM claim c WHERE c.research_id = r.id) ORDER BY r.id", [])? {
        findings.push(finding("EMPTY-001", "warning", &field(&row, "id"),
            "research program has no claims yet", "add a claim, or remove the unused program."));
    }

    // PRE-001 — hypothesis outcome dated before its registration.
    let sql = "SELECT v.id, h.id AS hypothesis_id FROM verdict v JOIN hypothesis h \
               ON h.id = v.subject_id WHERE v.subject_kind='hypothesis' AND v.at < h.registered_at";
    for row in query_json(conn, sql, [])? {
        findings.push(finding("PRE-001", "error", &field(&row, "hypothesis_id"),
            format!("hypothesis outcome {} is dated before its registration", field(&row, "id")),
            "restore the chronological record; pre-registration must precede the outcome."));
    }

    // SCOPE-001 — edge crossing research programs.
    for row in query_json(conn, "SELECT * FROM edge ORDER BY id", [])? {
        let src = fetch_entity(conn, &field(&row, "src_kind"), &field(&row, "src_id"))?;
        let dst = fetch_entity(conn, &field(&row, "dst_kind"), &field(&row, "dst_id"))?;
        if let (Some(src), Some(dst)) = (src, dst) {
            if !field(&src, "research_id").is_empty() && !field(&dst, "research_id").is_empty()
                && field(&src, "research_id") != field(&dst, "research_id") {
                findings.push(finding("SCOPE-001", "error", &field(&row, "id"),
                    "edge crosses research programs",
                    "remove the edge or move both records into one program."));
            }
        }
    }

    // TEST-002 — a test created after another test on the same claim failed.
    let sql = "SELECT later.id AS test_id, earlier.id AS failed_test FROM killtest later \
               JOIN killtest earlier ON earlier.claim_id = later.claim_id AND earlier.id <> later.id \
               JOIN test_attempt failed ON failed.test_id = earlier.id \
               AND failed.outcome = 'subject_failed' WHERE later.created_at > failed.created_at \
               GROUP BY later.id ORDER BY later.id";
    for row in query_json(conn, sql, [])? {
        findings.push(finding("TEST-002", "warning", &field(&row, "test_id"),
            format!("test was created after {} failed on the same claim", field(&row, "failed_test")),
            "record why this is an independent test rather than a retry, or use the authoritative attempt."));
    }

    // EVID-010 — information-poor stored quote.
    let quote_rows = query_json(conn, "SELECT id, research_id, quote FROM claim WHERE \
        trim(quote) <> '' AND status NOT IN ('RETRACTED','INVALIDATED') ORDER BY id", [])?;
    let mut quotes_by_research: std::collections::BTreeMap<String, Vec<String>> =
        std::collections::BTreeMap::new();
    for row in &quote_rows {
        quotes_by_research.entry(field(row, "research_id")).or_default().push(field(row, "quote"));
    }
    let question_rows = query_json(conn, "SELECT e.src_id, q.text FROM edge e JOIN question q \
        ON q.id=e.dst_id WHERE e.src_kind='claim' AND e.dst_kind='question'", [])?;
    let mut questions_by_claim: std::collections::BTreeMap<String, Vec<String>> =
        std::collections::BTreeMap::new();
    for row in &question_rows {
        questions_by_claim.entry(field(row, "src_id")).or_default().push(field(row, "text"));
    }
    for row in &quote_rows {
        let claim_id = field(row, "id");
        let research_id = field(row, "research_id");
        let quote = field(row, "quote");
        let others: Vec<String> = quotes_by_research.get(&research_id).unwrap_or(&Vec::new())
            .iter().filter(|q| *q != &quote).cloned().collect();
        let classes = information_classes(&quote,
            questions_by_claim.get(&claim_id).unwrap_or(&Vec::new()), &others);
        if !classes.is_empty() {
            findings.push(finding("EVID-010", "warning", &claim_id,
                format!("claim quote is information-poor: {}", classes.join(", ")),
                "quote a passage that adds information beyond the question, or record why the repetition is necessary."));
        }
    }

    // EVID-009 — declared negative control never failed reproducibly.
    for row in query_json(conn, "SELECT id, claim_id FROM killtest ORDER BY id", [])? {
        let test_id = field(&row, "id");
        let test = crate::killtest::get_test(conn, &test_id)?;
        let verified = verified_groups_any(conn, &test_id)?;
        if verified.is_empty() || field(&test, "control_command").is_empty() { continue; }
        if !control_falsified(conn, &test_id, &verified[0])? {
            findings.push(finding("EVID-009", "error", &test_id,
                "the declared negative control never failed reproducibly, so the test has not shown it can fail",
                "make the control fail deterministically twice, then re-verify the test."));
        }
    }

    // EVID-005 / EVID-006 / EVID-011 — numeric evidence currency and missing volumes.
    let mut stale_volume: std::collections::BTreeMap<String, Vec<(String, Vec<String>)>> =
        std::collections::BTreeMap::new();
    for row in query_json(conn, "SELECT * FROM claim WHERE status='NUMERIC' ORDER BY id", [])? {
        let claim_id = field(&row, "id");
        let tests: Vec<Value> = query_json(conn, "SELECT * FROM killtest WHERE claim_id=?1 ORDER BY id",
            params![claim_id])?;
        if tests.is_empty() { continue; }
        if !tests.iter().any(|t| !verified_groups_any(conn, &field(t, "id")).unwrap_or_default().is_empty()) {
            continue;
        }
        let current = crate::killtest::claim_groups(conn, &claim_id)?;
        if current.is_empty() {
            let missing = missing_inputs(&tests)?;
            if !missing.is_empty() {
                stale_volume.entry(field(&row, "research_id")).or_default()
                    .push((claim_id, missing));
                continue;
            }
            emit_stale(&mut findings, &claim_id);
            continue;
        }
        let bound: String = query_json(conn,
            "SELECT evidence_group FROM verdict WHERE subject_kind='claim' AND subject_id=?1 \
             AND status='NUMERIC' ORDER BY id DESC LIMIT 1", params![claim_id])?
            .into_iter().next().map(|v| field(&v, "evidence_group")).unwrap_or_default();
        if !current.contains(&bound) {
            findings.push(finding("EVID-006", "error", &claim_id,
                format!("the promotion verdict is not tied to the authoritative current run (bound: {}; authoritative: {})",
                    if bound.is_empty() { "none".to_string() } else { bound }, current.join(", ")),
                "re-record the verdict against the authoritative group with `claim verdict --group`."));
        }
    }
    for (research_id, candidates) in stale_volume {
        if candidates.len() < 3 {
            for (claim_id, _) in candidates { emit_stale(&mut findings, &claim_id); }
            continue;
        }
        let mut all_paths: Vec<String> = Vec::new();
        for (_, paths) in &candidates { all_paths.extend(paths.iter().cloned()); }
        let common = common_parent(&all_paths);
        if common.is_none() {
            for (claim_id, _) in candidates { emit_stale(&mut findings, &claim_id); }
            continue;
        }
        let names: Vec<String> = candidates.iter().map(|(id, _)| id.clone()).collect();
        findings.push(finding("EVID-011", "error", &research_id,
            format!("evidence volume missing: {} leaves {} NUMERIC claims stale ({})",
                common.unwrap(), candidates.len(), names.join(", ")),
            "restore the folder, then re-run `test verify` for the affected tests."));
    }

    // AI-001 — unresolvable citation in a non-sweep AI artifact.
    for row in query_json(conn,
        "SELECT id, research_id, kind, cited_json FROM ai_artifact WHERE kind != 'sweep' ORDER BY id", [])? {
        let cited: Vec<Value> = serde_json::from_str(&field(&row, "cited_json")).unwrap_or_default();
        for entry in cited {
            let source_id = field(&entry, "source_id");
            let locator = field(&entry, "locator");
            let exists: i64 = conn.query_row(
                "SELECT COUNT(*) FROM source WHERE id=?1 AND research_id=?2",
                params![source_id, field(&row, "research_id")], |r| r.get(0)).unwrap_or(0);
            if locator.trim().is_empty() || exists == 0 {
                findings.push(finding("AI-001", "error", &field(&row, "id"),
                    format!("AI {} artifact cites unresolvable source {}", field(&row, "kind"),
                        if source_id.is_empty() { "(none)" } else { &source_id }),
                    "cite a source registered in this program with a locator, or leave the claim UNVERIFIED and unlinked."));
                break;
            }
        }
    }

    // AI-002 — AI-origin claim promoted without any test that ever verified.
    let sql = "SELECT c.id FROM claim c JOIN ai_artifact a ON a.claim_id=c.id \
               WHERE a.kind IN ('extraction','idea') AND c.status='PROVEN' ORDER BY c.id";
    for row in query_json(conn, sql, [])? {
        let claim_id = field(&row, "id");
        let tests = query_json(conn, "SELECT id FROM killtest WHERE claim_id=?1", params![claim_id])?;
        let historical = tests.iter().any(|t| {
            verified_groups_any(conn, &field(t, "id")).map(|g| !g.is_empty()).unwrap_or(false)
        });
        if !historical {
            findings.push(finding("AI-002", "error", &claim_id,
                "AI-origin claim is PROVEN with no test that ever passed twice",
                "bind a kill test, run `test verify`, and re-promote on the verified group, or downgrade the claim."));
        }
    }

    // AI-003 — AI-proposed test no longer matches its fixed probe template.
    let sql = "SELECT t.id, t.command, t.control_command FROM killtest t \
               JOIN ai_artifact a ON a.test_id=t.id ORDER BY t.id";
    for row in query_json(conn, sql, [])? {
        if !crate::ai::matches_template(&field(&row, "command"), &field(&row, "control_command"))? {
            findings.push(finding("AI-003", "error", &field(&row, "id"),
                "AI-proposed test no longer matches its fixed template",
                "re-propose the test from a template with `ai propose-test`, or record why the command was changed by hand."));
        }
    }

    Ok(findings)
}

fn emit_stale(findings: &mut Vec<Value>, claim_id: &str) {
    findings.push(finding("EVID-005", "error", claim_id,
        "numeric evidence is stale: no verified run matches the current code, inputs and command",
        "re-run `test verify` for the claim's test, or downgrade the claim."));
}

fn fetch_entity(conn: &Connection, kind: &str, id: &str) -> Result<Option<Value>> {
    let table = match kind { "claim" => "claim", "question" => "question",
        "hypothesis" => "hypothesis", "source" => "source", _ => return Ok(None) };
    Ok(query_json(conn, &format!("SELECT * FROM {table} WHERE id = ?1"), params![id])?
        .into_iter().next())
}

pub fn has_errors(findings: &[Value]) -> bool {
    findings.iter().any(|f| f.get("severity").and_then(Value::as_str) == Some("error"))
}

pub fn render_markdown(findings: &[Value]) -> String {
    let mut lines = vec![
        "# Integrity Report".to_string(),
        String::new(),
        "| Severity | Code | Subject | Message | Fix |".to_string(),
        "|---|---|---|---|---|".to_string(),
    ];
    for item in findings {
        let cell = |key: &str| field(item, key).replace('|', "\\|").replace('\n', " ");
        lines.push(format!("| {} | {} | {} | {} | {} |",
            cell("severity"), cell("code"), cell("subject"), cell("message"), cell("fix")));
    }
    if findings.is_empty() {
        lines.push("| — | — | — | no findings | — |".to_string());
    }
    lines.push(String::new());
    lines.join("\n")
}
