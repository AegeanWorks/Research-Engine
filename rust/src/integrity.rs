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

    Ok(findings)
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
