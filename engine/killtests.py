"""Executable kill tests: two agreeing runs, bound to code, inputs and command."""

from __future__ import annotations

import json
import os
import signal
import sqlite3
import subprocess
import time
from typing import Dict, List, Optional, Sequence, Tuple

from engine.artifacts import sha256_text, utc_now
from engine.claims import get_claim
from engine.database import next_id, transaction
from engine.errors import EngineError, NotFound
from engine.evidence import (
    MIN_BINDING_RUNS,
    binding,
    current_verified_group,
    current_verified_groups,
    test_inputs,
    verified_groups,
)
from engine.hypotheses import get_hypothesis
from engine.models import KillTest, TestRun
from engine.provenance import PROJECT_ROOT, environment, fingerprint, git_state, resolve_inputs
from engine.researches import get_research

MAX_CAPTURE = 2000
MIN_BINDING_RUNS = 2


def _to_test(row: sqlite3.Row) -> KillTest:
    return KillTest(**{key: row[key] for key in KillTest.__dataclass_fields__})


def _to_run(row: sqlite3.Row) -> TestRun:
    values = {key: row[key] for key in TestRun.__dataclass_fields__}
    values["passed"] = bool(values["passed"])
    values["git_dirty"] = bool(values["git_dirty"])
    return TestRun(**values)


def add_test(
    conn: sqlite3.Connection,
    research_ref: str,
    name: str,
    command: str,
    claim_ref: Optional[str] = None,
    hypothesis_ref: Optional[str] = None,
    expect_exit: int = 0,
    timeout_seconds: int = 120,
    inputs: Sequence[str] = (),
    control_command: str = "",
) -> KillTest:
    """Register an executable test bound to a claim, a hypothesis, its inputs and a control.

    `control_command` is a negative control: a command that must NOT satisfy the expectation. A
    test without one cannot show that it is capable of failing, so its passing result is weaker
    evidence. The control is optional because existing tests predate it, but integrity reports the
    gap for every NUMERIC claim.
    """
    research = get_research(conn, research_ref)
    if not name.strip() or not command.strip():
        raise EngineError("test needs a name and a command", "a kill test is runnable.", "pass --name and --command.")
    if not claim_ref and not hypothesis_ref:
        raise EngineError(
            "test is not bound to a claim or hypothesis",
            "an unbound test cannot serve as evidence.",
            "pass --claim or --hypothesis.",
        )
    claim_id = None
    if claim_ref:
        claim = get_claim(conn, claim_ref)
        if claim.research_id != research.id:
            raise EngineError(
                "claim belongs to another research program",
                "tests and targets must share a program.",
                "bind the test inside the claim's program.",
            )
        claim_id = claim.id
    hypothesis_id = None
    if hypothesis_ref:
        hypothesis = get_hypothesis(conn, hypothesis_ref)
        if hypothesis.research_id != research.id:
            raise EngineError(
                "hypothesis belongs to another research program",
                "tests and targets must share a program.",
                "bind the test inside the hypothesis's program.",
            )
        hypothesis_id = hypothesis.id
    if timeout_seconds < 1:
        raise EngineError("timeout must be positive", "a test needs a bounded run time.", "pass --timeout 120.")
    declared = resolve_inputs(inputs)
    with transaction(conn):
        record = KillTest(
            id=next_id(conn, "t"),
            research_id=research.id,
            claim_id=claim_id,
            hypothesis_id=hypothesis_id,
            name=name.strip(),
            command=command.strip(),
            expect_exit=int(expect_exit),
            timeout_seconds=int(timeout_seconds),
            created_at=utc_now(),
            inputs_json=json.dumps(list(declared)),
            control_command=control_command.strip(),
        )
        conn.execute(
            "INSERT INTO killtest(id, research_id, claim_id, hypothesis_id, name, command,"
            " expect_exit, timeout_seconds, created_at, inputs_json, control_command)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                record.id,
                record.research_id,
                record.claim_id,
                record.hypothesis_id,
                record.name,
                record.command,
                record.expect_exit,
                record.timeout_seconds,
                record.created_at,
                record.inputs_json,
                record.control_command,
            ),
        )
    return record


def get_test(conn: sqlite3.Connection, ref: str) -> KillTest:
    """Fetch one test by identifier."""
    row = conn.execute("SELECT * FROM killtest WHERE id = ?", (ref,)).fetchone()
    if row is None:
        raise NotFound("test", ref)
    return _to_test(row)


def list_tests(
    conn: sqlite3.Connection, research_ref: str | None = None
) -> List[KillTest]:
    """List tests, optionally filtered by program."""
    if research_ref:
        research = get_research(conn, research_ref)
        rows = conn.execute(
            "SELECT * FROM killtest WHERE research_id = ? ORDER BY id", (research.id,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM killtest ORDER BY id").fetchall()
    return [_to_test(row) for row in rows]

def _terminate_tree(process: subprocess.Popen) -> None:
    """Kill the process and its children without leaking a detached tree."""
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            capture_output=True,
            check=False,
            timeout=10,
        )
        return
    try:
        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        process.kill()


def _run_once(command: str, timeout_seconds: int) -> dict:
    """Run one command in the project root and capture a deterministic fingerprint."""
    kwargs: Dict[str, object] = {}
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    started = time.monotonic()
    # hygiene: allow tests are user-authored shell commands by design, bounded by timeout.
    process = subprocess.Popen(
        command,
        shell=True,
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        **kwargs,
    )
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        _terminate_tree(process)
        stdout, stderr = process.communicate()
    duration_ms = int((time.monotonic() - started) * 1000)
    return {
        "exit_code": -1 if timed_out else int(process.returncode),
        "timed_out": timed_out,
        "duration_ms": duration_ms,
        "stdout": stdout or "",
        "stderr": stderr or "",
    }


def run_test(
    conn: sqlite3.Connection,
    test_ref: str,
    runs: int = 1,
) -> dict:
    """Run a test one or more times, plus its negative control, recording each run's identity.

    The control runs in its own group and must fail on every repetition. When a control is
    declared, verification is complete only if the main command passed twice and the control
    failed twice with identical output.
    """
    test = get_test(conn, test_ref)
    if runs < 1 or runs > 5:
        raise EngineError(
            f"unsupported run count: {runs}",
            "the engine records between one and five runs per invocation.",
            "pass --runs 2 for the independent verification standard.",
        )
    current = binding(test)
    before = fingerprint(test_inputs(test))
    group = next_id(conn, "g")
    results = _execute(conn, test, test.command, group, runs, "main", "run", current)
    control = None
    if test.control_command:
        control_results = _execute(
            conn, test, test.control_command, group, runs, "control", "control", current
        )
        control = _summarise_control(control_results, test.expect_exit)
    after = fingerprint(test_inputs(test))
    fingerprints = {
        (item["exit_code"], item["stdout_sha256"], item["stderr_sha256"]) for item in results
    }
    all_passed = all(item["passed"] for item in results)
    reproducible = len(fingerprints) == 1
    stable = before == after
    control_ok = control is None or bool(control["falsified"])
    return {
        "test": test.id,
        "name": test.name,
        "run_group": group,
        "runs": results,
        "control": control,
        "binding": current,
        "workspace_changed_during_runs": not stable,
        "passed": all_passed and reproducible and stable and control_ok,
        "reproducible": reproducible,
        "control_declared": bool(test.control_command),
        "control_falsified": control_ok,
        "required_runs": MIN_BINDING_RUNS,
        "verification_complete": (
            runs >= MIN_BINDING_RUNS and all_passed and reproducible and stable and control_ok
        ),
    }


def _execute(
    conn: sqlite3.Connection,
    test: KillTest,
    command: str,
    group: str,
    runs: int,
    role: str,
    tag_prefix: str,
    current: dict,
) -> list:
    """Execute one command `runs` times and persist every run under its role."""
    commit, dirty = git_state()
    runtime = environment()
    results = []
    for index in range(runs):
        outcome = _run_once(command, test.timeout_seconds)
        passed = (not outcome["timed_out"]) and outcome["exit_code"] == test.expect_exit
        results.append(
            {
                "run_tag": f"{tag_prefix}{index + 1}",
                "role": role,
                "started_at": utc_now(),
                "duration_ms": outcome["duration_ms"],
                "exit_code": outcome["exit_code"],
                "passed": passed,
                "stdout_sha256": sha256_text(outcome["stdout"]),
                "stderr_sha256": sha256_text(outcome["stderr"]),
                "output_tail": (outcome["stdout"] + outcome["stderr"])[-MAX_CAPTURE:],
            }
        )
        with transaction(conn):
            conn.execute(
                "INSERT INTO test_run(id, test_id, run_group, run_tag, started_at, duration_ms,"
                " exit_code, passed, stdout_sha256, stderr_sha256, output_tail,"
                " command_sha256, code_sha256, inputs_sha256, git_commit, git_dirty,"
                " python_version, platform, role)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    next_id(conn, "u"),
                    test.id,
                    group,
                    results[-1]["run_tag"],
                    results[-1]["started_at"],
                    results[-1]["duration_ms"],
                    results[-1]["exit_code"],
                    int(passed),
                    results[-1]["stdout_sha256"],
                    results[-1]["stderr_sha256"],
                    results[-1]["output_tail"],
                    current["command_sha256"],
                    current["code_sha256"],
                    current["inputs_sha256"],
                    commit,
                    int(dirty),
                    runtime["python"],
                    runtime["platform"],
                    role,
                ),
            )
    return results


def _summarise_control(results: list, expect_exit: int) -> dict:
    """A control is falsified when every repetition fails the expectation identically."""
    fingerprints = {
        (item["exit_code"], item["stdout_sha256"], item["stderr_sha256"]) for item in results
    }
    return {
        "runs": results,
        "reproducible": len(fingerprints) == 1,
        "expected_exit": expect_exit,
        "falsified": all(not item["passed"] for item in results) and len(fingerprints) == 1,
    }


def verify_test(conn: sqlite3.Connection, test_ref: str) -> dict:
    """Run a test twice in separate processes; disagreement or drift is a failure."""
    return run_test(conn, test_ref, runs=MIN_BINDING_RUNS)


def list_runs(
    conn: sqlite3.Connection, test_ref: str | None = None, limit: int = 50
) -> List[TestRun]:
    """List recent runs, optionally for one test."""
    if test_ref:
        test = get_test(conn, test_ref)
        rows = conn.execute(
            "SELECT * FROM test_run WHERE test_id = ? ORDER BY id DESC LIMIT ?",
            (test.id, limit),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM test_run ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [_to_run(row) for row in rows]
