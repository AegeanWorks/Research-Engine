"""Run the full claim-verification workflow in separate processes.

This is the cross-platform equivalent of `make verify`:

1. regenerate the physics outputs,
2. run the independent audit as run1,
3. run the independent audit as run2 (separate process),
4. compare the two per-claim result sets and fingerprints.

The two audits are always separate processes, satisfying project rule G-001.

Run:

    python -m verification.verify
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Harness budget (ADR-055): run_all regenerates ~10 reports including the
# ~700 s widened ladder; a 600 s per-step cap aborts it before any physics
# check runs. 3600 s covers the full regeneration on current hardware while
# every individual simulation still enforces its own G-003 900 s cap.
TIMEOUT = 3600


def _run(module: str, *args: str) -> None:
    command = [sys.executable, "-m", module, *args]
    try:
        subprocess.run(command, cwd=ROOT, check=True, timeout=TIMEOUT)
    except subprocess.TimeoutExpired as error:
        raise RuntimeError(
            f"`{' '.join(command)}` exceeded {TIMEOUT}s. "
            "Why: a step hangs. Fix: run it alone and inspect the output."
        ) from error
    except subprocess.CalledProcessError as error:
        raise RuntimeError(
            f"`{' '.join(command)}` failed with exit code {error.returncode}. "
            "Why: a check failed or a required file is missing. "
            "Fix: read the output above, correct the cause, and rerun `python -m verification.verify`."
        ) from error


def main() -> int:
    try:
        _run("phenomenology.run_all")
        _run("verification.audit", "--tag", "run1")
        _run("verification.audit", "--tag", "run2")
        _run("verification.compare")
    except RuntimeError as error:
        print(error)
        return 1

    combined = json.loads((ROOT / "results" / "verification.json").read_text(encoding="utf-8"))
    meta = combined["meta"]
    print(
        f"accepted={meta['accepted']} per_claim={meta['claims_agree']} "
        f"details={meta['details_match']} fingerprints={meta['fingerprints_match']} "
        f"({combined['passed']}/{combined['total']})"
    )
    return 0 if meta["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
