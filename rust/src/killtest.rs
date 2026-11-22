//! Executable kill tests: two agreeing runs, bound to code, inputs and command.

use rusqlite::{params, Connection};
use serde_json::{json, Value};

use crate::core::{get_claim, get_hypothesis, get_research};
use crate::db::{next_id, utc_now};
use crate::error::{EngineError, Result};
use crate::provenance::{self, fingerprint};
use crate::util::{query_json, sha256_text};
use crate::vocab::{ATTEMPT_OUTCOMES, REPLACEABLE_ATTEMPT_OUTCOMES};

const MIN_BINDING_RUNS: i64 = 2;
const MAX_CAPTURE: usize = 2000;

fn field(value: &Value, name: &str) -> String {
    value.get(name).and_then(Value::as_str).unwrap_or("").to_string()
}

pub fn get_test(conn: &Connection, reference: &str) -> Result<Value> {
    let rows = query_json(conn, "SELECT * FROM killtest WHERE id=?1", params![reference])?;
    rows.into_iter().next().ok_or_else(|| EngineError::not_found("test", reference))
}

pub fn list_tests(conn: &Connection, research_ref: Option<&str>) -> Result<Vec<Value>> {
    if let Some(reference) = research_ref {
        let research = get_research(conn, reference)?;
        query_json(conn, "SELECT * FROM killtest WHERE research_id=?1 ORDER BY id", params![field(&research, "id")])
    } else {
        query_json(conn, "SELECT * FROM killtest ORDER BY id", [])
    }
}

#[allow(clippy::too_many_arguments)]
pub fn add_test(
    conn: &Connection,
    research_ref: &str,
    name: &str,
    command: &str,
    claim_ref: Option<&str>,
    hypothesis_ref: Option<&str>,
    expect_exit: i64,
    timeout: i64,
    inputs: &[String],
    control: &str,
) -> Result<Value> {
    let research = get_research(conn, research_ref)?;
    if name.trim().is_empty() || command.trim().is_empty() {
        return Err(EngineError::new("test needs a name and a command",
            "a kill test is runnable.", "pass --name and --command."));
    }
    if claim_ref.is_none() && hypothesis_ref.is_none() {
        return Err(EngineError::new("test is not bound to a claim or hypothesis",
            "an unbound test cannot serve as evidence.", "pass --claim or --hypothesis."));
    }
    let mut claim_id = None;
    if let Some(reference) = claim_ref {
        let claim = get_claim(conn, reference)?;
        if !field(&claim, "superseded_by").is_empty() {
            return Err(EngineError::new(
                format!("claim {} is superseded by {}", field(&claim, "id"), field(&claim, "superseded_by")),
                "a test on history cannot produce evidence for the live graph.",
                "bind the test to the current head.",
            ));
        }
        if field(&claim, "research_id") != field(&research, "id") {
            return Err(EngineError::new("claim belongs to another research program",
                "tests and targets must share a program.", "bind the test inside the claim's program."));
        }
        claim_id = Some(field(&claim, "id"));
    }
    let mut hypothesis_id = None;
    if let Some(reference) = hypothesis_ref {
        let hypothesis = get_hypothesis(conn, reference)?;
        if field(&hypothesis, "research_id") != field(&research, "id") {
            return Err(EngineError::new("hypothesis belongs to another research program",
                "tests and targets must share a program.", "bind the test inside the hypothesis's program."));
        }
        hypothesis_id = Some(field(&hypothesis, "id"));
    }
    if timeout < 1 {
        return Err(EngineError::new("timeout must be positive",
            "a test needs a bounded run time.", "pass --timeout 120."));
    }
    let declared = provenance::resolve_inputs(inputs)?;
    let tx = conn.unchecked_transaction()?;
    let id = next_id(&tx, "t")?;
    tx.execute(
        "INSERT INTO killtest(id, research_id, claim_id, hypothesis_id, name, command, expect_exit, timeout_seconds, created_at, inputs_json, control_command) VALUES (?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11)",
        params![id, field(&research, "id"), claim_id, hypothesis_id, name.trim(), command.trim(),
            expect_exit, timeout, utc_now(), serde_json::to_string(&declared)?, control.trim()],
    )?;
    tx.commit()?;
    get_test(conn, &id)
}

/// The identity a run must carry to count as evidence now.
pub fn binding(test: &Value) -> Result<Value> {
    let declared: Vec<String> = serde_json::from_str(
        test.get("inputs_json").and_then(Value::as_str).unwrap_or("[]")
    ).unwrap_or_default();
    let fp = fingerprint(&declared)?;
    let command_payload = format!(
        "{}\n--control--\n{}\n--expect-exit--\n{}\n--timeout--\n{}",
        field(test, "command"), field(test, "control_command"),
        test.get("expect_exit").and_then(Value::as_i64).unwrap_or(0),
        test.get("timeout_seconds").and_then(Value::as_i64).unwrap_or(120),
    );
    Ok(json!({
        "command_sha256": sha256_text(&command_payload),
        "code_sha256": fp.code_sha256,
        "inputs_sha256": fp.inputs_sha256,
    }))
}

struct RunOutcome {
    exit_code: i64,
    timed_out: bool,
    duration_ms: i64,
    stdout: String,
    stderr: String,
}

fn run_once(command: &str, timeout_seconds: i64) -> RunOutcome {
    use std::process::Stdio;
    use std::time::{Duration, Instant};

    let started = Instant::now();
    let mut child = {
        #[cfg(windows)]
        {
            std::process::Command::new("cmd").args(["/C", command])
                .stdout(Stdio::piped()).stderr(Stdio::piped()).spawn()
        }
        #[cfg(not(windows))]
        {
            std::process::Command::new("sh").args(["-c", command])
                .stdout(Stdio::piped()).stderr(Stdio::piped()).spawn()
        }
    };
    let mut child = match child {
        Ok(child) => child,
        Err(_) => return RunOutcome {
            exit_code: -1, timed_out: true, duration_ms: started.elapsed().as_millis() as i64,
            stdout: String::new(), stderr: "command could not be spawned".to_string(),
        },
    };
    let deadline = Duration::from_secs(timeout_seconds.max(1) as u64);
    let mut timed_out = false;
    loop {
        match child.try_wait() {
            Ok(Some(_)) => break,
            Ok(None) if started.elapsed() >= deadline => {
                timed_out = true;
                #[cfg(windows)]
                {
                    let _ = std::process::Command::new("taskkill")
                        .args(["/PID", &child.id().to_string(), "/T", "/F"]).output();
                }
                #[cfg(not(windows))]
                {
                    let _ = child.kill();
                }
                let _ = child.wait();
                break;
            }
            Ok(None) => std::thread::sleep(Duration::from_millis(10)),
            Err(_) => {
                timed_out = true;
                let _ = child.kill();
                let _ = child.wait();
                break;
            }
        }
    }
    let output = child.wait_with_output().ok();
    match output {
        Some(output) => RunOutcome {
            exit_code: if timed_out { -1 } else { i64::from(output.status.code().unwrap_or(-1)) },
            timed_out,
            duration_ms: started.elapsed().as_millis() as i64,
            stdout: String::from_utf8_lossy(&output.stdout).into_owned(),
            stderr: String::from_utf8_lossy(&output.stderr).into_owned(),
        },
        None => RunOutcome {
            exit_code: -1, timed_out: true, duration_ms: started.elapsed().as_millis() as i64,
            stdout: String::new(), stderr: "command output could not be captured".to_string(),
        },
    }
}

fn execute(
    conn: &Connection,
    test: &Value,
    command: &str,
    group: &str,
    runs: i64,
    role: &str,
    tag_prefix: &str,
    current: &Value,
    commit: &str,
    dirty: bool,
) -> Result<Vec<Value>> {
    let expect_exit = test.get("expect_exit").and_then(Value::as_i64).unwrap_or(0);
    let timeout = test.get("timeout_seconds").and_then(Value::as_i64).unwrap_or(120);
    let tx = conn.unchecked_transaction()?;
    let mut results = Vec::new();
    for index in 0..runs {
        let outcome = run_once(command, timeout);
        let passed = !outcome.timed_out && outcome.exit_code == expect_exit;
        let stdout_hash = sha256_text(&outcome.stdout);
        let stderr_hash = sha256_text(&outcome.stderr);
        let tail: String = format!("{}{}", outcome.stdout, outcome.stderr)
            .chars().rev().take(MAX_CAPTURE).collect::<Vec<_>>().into_iter().rev().collect();
        let record = json!({
            "run_tag": format!("{tag_prefix}{}", index + 1),
            "role": role,
            "exit_code": outcome.exit_code,
            "passed": passed,
            "stdout_sha256": stdout_hash,
            "stderr_sha256": stderr_hash,
        });
        let id = next_id(&tx, "u")?;
        tx.execute(
            "INSERT INTO test_run(id, test_id, run_group, run_tag, started_at, duration_ms, exit_code, passed, stdout_sha256, stderr_sha256, output_tail, command_sha256, code_sha256, inputs_sha256, git_commit, git_dirty, python_version, platform, role) VALUES (?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?12,?13,?14,?15,?16,?17,?18,?19)",
            params![id, field(test, "id"), group, record["run_tag"].as_str().unwrap_or(""),
                utc_now(), outcome.duration_ms, outcome.exit_code, i64::from(passed), stdout_hash,
                stderr_hash, tail, field(current, "command_sha256"), field(current, "code_sha256"),
                field(current, "inputs_sha256"), commit, i64::from(dirty), "rust",
                std::env::consts::OS, role],
        )?;
        results.push(record);
    }
    tx.commit()?;
    Ok(results)
}

fn fingerprints_unique(results: &[Value]) -> bool {
    let mut seen = std::collections::HashSet::new();
    for item in results {
        seen.insert((item.get("exit_code").and_then(Value::as_i64),
            item.get("stdout_sha256").and_then(Value::as_str),
            item.get("stderr_sha256").and_then(Value::as_str)));
    }
    seen.len() == 1
}

pub fn run_test(conn: &Connection, reference: &str, runs: i64) -> Result<Value> {
    let test = get_test(conn, reference)?;
    if !(1..=5).contains(&runs) {
        return Err(EngineError::new(format!("unsupported run count: {runs}"),
            "the engine records between one and five runs per invocation.",
            "pass --runs 2 for the independent verification standard."));
    }
    let current = binding(&test)?;
    let group = next_id(conn, "g")?;
    let (commit, dirty) = provenance::git_state();
    let results = execute(conn, &test, &field(&test, "command"), &group, runs,
        "main", "run", &current, &commit, dirty)?;
    let mut control = Value::Null;
    let control_ok = if !field(&test, "control_command").is_empty() {
        let control_results = execute(conn, &test, &field(&test, "control_command"), &group, runs,
            "control", "control", &current, &commit, dirty)?;
        let falsified = control_results.len() as i64 >= MIN_BINDING_RUNS
            && control_results.iter().all(|r| r.get("passed").and_then(Value::as_bool) == Some(false))
            && fingerprints_unique(&control_results);
        control = json!({
            "runs": control_results.len(),
            "falsified": falsified,
            "reproducible": control_results.len() as i64 >= MIN_BINDING_RUNS && fingerprints_unique(&control_results),
        });
        falsified
    } else {
        true
    };
    let all_passed = results.iter().all(|r| r.get("passed").and_then(Value::as_bool) == Some(true));
    let reproducible = fingerprints_unique(&results);
    let outcome = if runs < MIN_BINDING_RUNS {
        "indeterminate"
    } else if results.iter().any(|r| r.get("exit_code").and_then(Value::as_i64) == Some(-1)) {
        "infra_failed"
    } else if !reproducible || !control_ok {
        "indeterminate"
    } else if !all_passed {
        "subject_failed"
    } else {
        "completed"
    };
    let reason = match outcome {
        "indeterminate" if runs < MIN_BINDING_RUNS => "insufficient_runs",
        "indeterminate" if !reproducible => "non_reproducible",
        "indeterminate" if !control_ok => "control_not_falsified",
        "subject_failed" => "expected_exit_mismatch",
        "infra_failed" => "timeout",
        _ => "",
    };
    let attempt_no: i64 = conn.query_row(
        "SELECT COALESCE(MAX(attempt_no), 0) + 1 FROM test_attempt WHERE test_id=?1",
        params![field(&test, "id")], |r| r.get(0))?;
    let attempt_id = next_id(conn, "a")?;
    conn.execute(
        "INSERT INTO test_attempt(id, test_id, attempt_no, run_group, outcome, reason, created_at) VALUES (?1,?2,?3,?4,?5,?6,?7)",
        params![attempt_id, field(&test, "id"), attempt_no, group, outcome, reason, utc_now()],
    )?;
    let verification_complete = runs >= MIN_BINDING_RUNS && all_passed && reproducible && control_ok;
    Ok(json!({
        "test": field(&test, "id"),
        "run_group": group,
        "runs": results,
        "control": control,
        "binding": current,
        "attempt": {"id": attempt_id, "attempt_no": attempt_no, "outcome": outcome, "reason": reason},
        "passed": all_passed && reproducible && control_ok,
        "reproducible": reproducible,
        "verification_complete": verification_complete,
        "required_runs": MIN_BINDING_RUNS,
    }))
}

/// Currently valid verified groups for a test, newest first.
pub fn current_verified_groups(conn: &Connection, test: &Value) -> Result<Vec<String>> {
    let current = binding(test)?;
    let rows = query_json(conn,
        "SELECT run_group FROM test_run WHERE test_id=?1 AND role='main' AND command_sha256=?2 AND code_sha256=?3 AND inputs_sha256=?4 GROUP BY run_group HAVING COUNT(*)>=2 AND SUM(passed)=COUNT(*) AND COUNT(DISTINCT exit_code||':'||stdout_sha256||':'||stderr_sha256)=1 ORDER BY MAX(id) DESC",
        params![field(test, "id"), field(&current, "command_sha256"),
            field(&current, "code_sha256"), field(&current, "inputs_sha256")])?;
    Ok(rows.iter().map(|r| field(r, "run_group")).collect())
}

/// The authoritative group is the earliest non-replaceable completed attempt
/// whose group is still currently verified.
pub fn authoritative_group(conn: &Connection, test: &Value) -> Result<Option<String>> {
    let current = binding(test)?;
    let attempt = query_json(conn,
        "SELECT * FROM test_attempt WHERE test_id=?1 ORDER BY attempt_no LIMIT 1",
        params![field(test, "id")])?.into_iter().next();
    let attempt = match attempt { Some(a) => a, None => return Ok(None) };
    let outcome = field(&attempt, "outcome");
    if REPLACEABLE_ATTEMPT_OUTCOMES.contains(&outcome.as_str()) {
        // A replaceable attempt is skipped; find the next non-replaceable one.
        let next = query_json(conn,
            "SELECT * FROM test_attempt WHERE test_id=?1 AND outcome NOT IN ('infra_failed','indeterminate') ORDER BY attempt_no LIMIT 1",
            params![field(test, "id")])?.into_iter().next();
        if let Some(next) = next {
            return authoritative_from(conn, test, &current, &next);
        }
        return Ok(None);
    }
    authoritative_from(conn, test, &current, &attempt)
}

fn authoritative_from(conn: &Connection, test: &Value, current: &Value, attempt: &Value) -> Result<Option<String>> {
    if field(attempt, "outcome") != "completed" { return Ok(None); }
    let group = field(attempt, "run_group");
    let valid = current_verified_groups(conn, test)?;
    if !valid.contains(&group) { return Ok(None); }
    let _ = current;
    Ok(Some(group))
}

/// Groups across every test bound to a claim that currently carry evidence.
pub fn claim_groups(conn: &Connection, claim_id: &str) -> Result<Vec<String>> {
    let tests = query_json(conn, "SELECT * FROM killtest WHERE claim_id=?1 ORDER BY id", params![claim_id])?;
    let mut groups = Vec::new();
    for test in &tests {
        if let Some(group) = authoritative_group(conn, test)? {
            if !groups.contains(&group) { groups.push(group); }
        }
    }
    Ok(groups)
}

/// G-003: a NUMERIC promotion needs an authoritative, currently valid run group.
pub fn numeric_gate(conn: &Connection, claim_id: &str) -> Result<()> {
    let groups = claim_groups(conn, claim_id)?;
    if groups.is_empty() {
        return Err(EngineError::new(
            "NUMERIC verdict has no authoritative verified test group",
            "a numeric verdict requires two separate runs that agree on exit code and output hashes, bound to the current code, inputs and command.",
            "run `test verify` on a test bound to this claim, then record `claim verdict --status NUMERIC --group <run_group>`.",
        ));
    }
    Ok(())
}

pub fn list_runs(conn: &Connection, reference: Option<&str>, limit: i64) -> Result<Vec<Value>> {
    if let Some(reference) = reference {
        query_json(conn, "SELECT * FROM test_run WHERE test_id=?1 ORDER BY id DESC LIMIT ?2", params![reference, limit])
    } else {
        query_json(conn, "SELECT * FROM test_run ORDER BY id DESC LIMIT ?1", params![limit])
    }
}

pub fn list_attempts(conn: &Connection, reference: Option<&str>, limit: i64) -> Result<Vec<Value>> {
    if let Some(reference) = reference {
        query_json(conn, "SELECT * FROM test_attempt WHERE test_id=?1 ORDER BY attempt_no DESC LIMIT ?2", params![reference, limit])
    } else {
        query_json(conn, "SELECT * FROM test_attempt ORDER BY id DESC LIMIT ?1", params![limit])
    }
}

pub fn is_replaceable(outcome: &str) -> bool {
    ATTEMPT_OUTCOMES.contains(&outcome) && REPLACEABLE_ATTEMPT_OUTCOMES.contains(&outcome)
}
