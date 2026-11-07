"""Result payloads for the topology, reduction, and prediction negatives."""

from __future__ import annotations

from domains.fluid_universe.theory.reduction import (
    moment_finite,
    moment_log_divergent,
    moment_power,
    render_markdown as render_reduction_markdown,
    verdict as reduction_verdict,
    wall_lower_bound_2d,
    wall_tension,
)
from domains.fluid_universe.theory.topology import (
    HOMOTOPY,
    render_markdown as render_topology_markdown,
    verdict as topology_verdict,
)

from .predictions import run_prediction_audit
from .provenance import RESULTS_DIR, metadata, write_json, write_text_atomic


def run_topology_check(write: bool = True) -> dict:
    payload = {
        "meta": metadata({"source": "standard homotopy groups of RP^2", "homotopy": HOMOTOPY}),
        "verdict": topology_verdict(),
    }
    if write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        write_json(RESULTS_DIR / "topology.json", payload)
        write_text_atomic(RESULTS_DIR / "topology.md", render_topology_markdown(payload))
    return payload


def run_reduction_check(write: bool = True) -> dict:
    argued_alpha = 4.0
    payload = {
        "meta": metadata(
            {
                "wall_tension_mu": 1.0,
                "stated_tail_alpha": argued_alpha,
                "moment_integrand_power": moment_power(argued_alpha),
                "moment_definition": "2*pi int rho(r) r^3 dr",
            }
        ),
        "wall_tension": wall_tension(1.0),
        "lower_bound_example": wall_lower_bound_2d(1.0, 2.0),
        "moment": {
            "alpha_2": {"finite": moment_finite(2.0), "power": moment_power(2.0)},
            "alpha_4": {"finite": moment_finite(4.0), "log_divergent": moment_log_divergent(4.0)},
            "alpha_5": {"finite": moment_finite(5.0), "power": moment_power(5.0)},
        },
        "verdict": reduction_verdict(argued_alpha),
    }
    if write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        write_json(RESULTS_DIR / "reduction.json", payload)
        write_text_atomic(RESULTS_DIR / "reduction.md", render_reduction_markdown(payload))
    return payload


__all__ = ["run_topology_check", "run_reduction_check", "run_prediction_audit"]
