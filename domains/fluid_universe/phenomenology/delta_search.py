"""Search for a closed form of the circulant phase delta, with a stated prior.

This is a post-hoc search: the phase delta = 0.22222476 rad (mod 2*pi/3) is
already known to be near 2/9.  The point of this module is to quantify the
look-elsewhere effect instead of promoting the near-miss.

Prior: uniform over the enumerated candidate set
  * reduced rationals p/q in (0, 2*pi/3] with q <= 20,
  * rational multiples p*pi/q with q <= 12,
  * 1/sqrt(n), arctan(1/n), arccos(1/n) for n <= 12.
The candidate set includes 2/9, so the resulting p-value is a lower bound on a
fully honest pre-registered search.  No candidate is marked established.
"""

from __future__ import annotations

import math
from fractions import Fraction
from pathlib import Path

from .provenance import RESULTS_DIR, metadata, write_json, write_text_atomic

FIT_PATH = RESULTS_DIR / "pdg_fit.json"
UPPER = 2.0 * math.pi / 3.0
QMAX = 20
PI_QMAX = 12
SIMPLE_NMAX = 12


def rational_candidates() -> dict[float, str]:
    out: dict[float, str] = {}
    for q in range(1, QMAX + 1):
        for p in range(1, int(UPPER * q) + 2):
            value = float(Fraction(p, q))
            if 0.0 < value <= UPPER:
                out.setdefault(round(value, 15), f"{p}/{q}")
    return out


def pi_candidates() -> dict[float, str]:
    out: dict[float, str] = {}
    for q in range(1, PI_QMAX + 1):
        for p in range(1, int(UPPER / math.pi * q) + 2):
            value = p * math.pi / q
            if 0.0 < value <= UPPER:
                out.setdefault(round(value, 15), f"{p}*pi/{q}")
    return out


def simple_candidates() -> dict[float, str]:
    out: dict[float, str] = {}
    for n in range(1, SIMPLE_NMAX + 1):
        for value, label in (
            (1.0 / math.sqrt(n), f"1/sqrt({n})"),
            (math.atan(1.0 / n), f"atan(1/{n})"),
            (math.acos(1.0 / n), f"acos(1/{n})"),
        ):
            if 0.0 < value <= UPPER:
                out.setdefault(round(value, 15), label)
    return out


def all_candidates() -> dict[float, str]:
    merged: dict[float, str] = {}
    for family in (rational_candidates(), pi_candidates(), simple_candidates()):
        for value, label in family.items():
            merged.setdefault(value, label)
    return merged


def search(delta: float, sigma: float) -> dict:
    candidates = all_candidates()
    rows = []
    for value, label in candidates.items():
        diff = abs(value - delta)
        rows.append(
            {
                "value": value,
                "label": label,
                "abs_diff": diff,
                "sigma_diff": diff / sigma if sigma > 0 else float("inf"),
            }
        )
    rows.sort(key=lambda row: row["abs_diff"])
    best = rows[0]
    n_candidates = len(rows)
    span = UPPER
    p_single = min(1.0, 2.0 * best["abs_diff"] / span) if span > 0 else 1.0
    expected = min(n_candidates, n_candidates * p_single)
    p_look_elsewhere = 1.0 - math.exp(-expected)
    return {
        "n_candidates": n_candidates,
        "best": best,
        "top10": rows[:10],
        "prior": {
            "rationals_qmax": QMAX,
            "pi_multiples_qmax": PI_QMAX,
            "simple_nmax": SIMPLE_NMAX,
            "span": span,
            "uniform_over": "enumerated candidate set",
        },
        "look_elsewhere": {
            "p_single_candidate": p_single,
            "expected_candidates_within_best_distance": expected,
            "p_look_elsewhere": p_look_elsewhere,
        },
        "promoted": False,
        "verdict": (
            "No closed form is established. The closest candidate is "
            f"{best['label']} at {best['sigma_diff']:.3f} sigma; the post-hoc "
            f"look-elsewhere p-value over the stated prior is {p_look_elsewhere:.3e}. "
            "This is a recorded near-miss, not evidence."
        ),
    }


def run_delta_search(write: bool = True) -> dict:
    import json

    fit = json.loads(FIT_PATH.read_text(encoding="utf-8"))
    delta = float(fit["point"]["delta_mod_2pi_over_3"])
    sigma = float(fit["monte_carlo"]["delta"]["std"])
    result = search(delta, sigma)
    payload = {
        "meta": metadata(
            {
                "delta_rad": delta,
                "delta_mod": "2*pi/3",
                "sigma_delta_rad": sigma,
                "source_fit": "results/pdg_fit.json",
                "prior": result["prior"],
            }
        ),
        **result,
    }
    if write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        write_json(RESULTS_DIR / "delta_search.json", payload)
        write_text_atomic(RESULTS_DIR / "delta_search.md", render_markdown(payload))
    return payload


def render_markdown(payload: dict) -> str:
    best = payload["best"]
    le = payload["look_elsewhere"]
    lines = [
        "# Delta closed-form search (claim 9)",
        "",
        "Post-hoc search, not a prediction. "
        f"delta = {payload['meta']['config']['delta_rad']:.12f} rad mod 2*pi/3, "
        f"sigma_delta = {payload['meta']['config']['sigma_delta_rad']:.3e} rad.",
        "",
        f"Prior: {payload['prior']['rationals_qmax']} rational denominators, "
        f"{payload['prior']['pi_multiples_qmax']} pi-multiple denominators, "
        f"{payload['prior']['simple_nmax']} simple forms; {payload['n_candidates']} candidates.",
        "",
        "| rank | candidate | value | |diff| | sigma |",
        "|---:|---|---:|---:|---:|",
    ]
    for rank, row in enumerate(payload["top10"], 1):
        lines.append(
            f"| {rank} | {row['label']} | {row['value']:.12f} | "
            f"{row['abs_diff']:.3e} | {row['sigma_diff']:.3f} |"
        )
    lines += [
        "",
        f"Best: **{best['label']}**, {best['sigma_diff']:.3f} sigma.",
        f"Single-candidate p = {le['p_single_candidate']:.3e}; "
        f"expected candidates within the best distance = "
        f"{le['expected_candidates_within_best_distance']:.3e}; "
        f"look-elsewhere p = {le['p_look_elsewhere']:.3e}.",
        "",
        "**Verdict:** no candidate is promoted. The 2/9 near-miss is recorded with its prior "
        "and look-elsewhere penalty; it is not evidence for a closed form.",
        "",
        f"- Config SHA-256: `{payload['meta']['config_sha256']}`",
        f"- Git: `{payload['meta']['git']['commit']}` (dirty={payload['meta']['git']['dirty']})",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    result = run_delta_search()
    print(result["verdict"])
