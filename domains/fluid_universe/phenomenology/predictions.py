"""Search for a genuinely new prediction beyond Q=2/3 (claim 16).

Each row is a candidate class, what the framework currently says, and whether
that statement is a new falsifiable prediction.  A row is "new" only if it is
not the built-in Koide value and is not already excluded by existing data.
"""

from __future__ import annotations

from .provenance import RESULTS_DIR, metadata, write_json, write_text_atomic

CANDIDATES = [
    {
        "class": "mass relation",
        "current_statement": "Q = 2/3 (Koide) for pole masses",
        "new": False,
        "reason": "Built in; the three-parameter fit accommodates any three masses.",
    },
    {
        "class": "mass relation (extra)",
        "current_statement": "none beyond Q = 2/3",
        "new": False,
        "reason": "No second relation survives; the fit has three parameters for three masses.",
    },
    {
        "class": "mixing relation",
        "current_statement": "minimal circulant branches predict no mixing or trimaximal mixing",
        "new": False,
        "reason": "Both branches are excluded by measured angles; no viable prediction.",
    },
    {
        "class": "dispersion deviation",
        "current_statement": "equal-K Frank-Oseen gives omega^2 = (K/rho) k^2",
        "new": False,
        "reason": "No physical calibration of K, rho, or the UV scale; no numerical deviation.",
    },
    {
        "class": "defect-spectrum count",
        "current_statement": "no validated simulation",
        "new": False,
        "reason": "No Hopfion solution or validated core; no count to compare.",
    },
    {
        "class": "RG signature",
        "current_statement": "Q and r drift by about 3e-6 over 16 decades",
        "new": False,
        "reason": "Far below experimental reach and consistent with the SM; not a discriminator.",
    },
    {
        "class": "neutrino prediction",
        "current_statement": "Q_nu never reaches 2/3",
        "new": False,
        "reason": "A negative result about a Koide extension, not a new positive prediction.",
    },
]


def run_prediction_audit(write: bool = True) -> dict:
    new_rows = [row for row in CANDIDATES if row["new"]]
    payload = {
        "meta": metadata(
            {
                "candidates": len(CANDIDATES),
                "source": "claims.md 1-16 and results/",
            }
        ),
        "candidates": CANDIDATES,
        "verdict": {
            "new_prediction_found": bool(new_rows),
            "count": len(new_rows),
            "note": (
                "No genuinely new falsifiable prediction beyond Q=2/3 was found. "
                "The mass fit is a reparametrisation, the minimal mixing branches are "
                "excluded, the dispersion has no calibration, and the defect spectrum "
                "has no validated simulation."
            ),
        },
    }
    if write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        write_json(RESULTS_DIR / "predictions.json", payload)
        write_text_atomic(RESULTS_DIR / "predictions.md", render_markdown(payload))
    return payload


def render_markdown(payload: dict) -> str:
    v = payload["verdict"]
    lines = [
        "# New-prediction audit (claim 16)",
        "",
        "| class | current statement | new? | reason |",
        "|---|---|---|---|",
    ]
    for row in payload["candidates"]:
        lines.append(
            f"| {row['class']} | {row['current_statement']} | {row['new']} | {row['reason']} |"
        )
    lines += [
        "",
        f"**Verdict:** new prediction found: **{v['new_prediction_found']}** (count {v['count']}).",
        "",
        v["note"],
        "",
        f"- Config SHA-256: `{payload['meta']['config_sha256']}`",
        f"- Git: `{payload['meta']['git']['commit']}` (dirty={payload['meta']['git']['dirty']})",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    print(run_prediction_audit()["verdict"])
