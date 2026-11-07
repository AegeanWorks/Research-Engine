"""Reproducible UV-track checks: Frank-Oseen modes and Derrick scaling.

These are structural calculations, not evidence for the nematic-fluid UV
picture.  They are kept separate from the Z3/Koide phenomenology.
"""

from __future__ import annotations

from .provenance import RESULTS_DIR, metadata, write_json, write_text_atomic
from domains.fluid_universe.theory.derrick import (
    exponents,
    scaling_minimum,
    stable_region,
    stationary_scale_squared,
    symbolic_virial,
    virial,
)
from domains.fluid_universe.theory.frank_oseen import anisotropy, dispersion, modes, symbolic_matches_numeric


def run_frank_oseen_check(write: bool = True) -> dict:
    k = 1.0
    equal = dispersion(k, 0.0, 0.0, 2.0, 2.0, 2.0)
    axis_x = dispersion(k, 0.0, 0.0, 1.0, 2.0, 3.0)
    axis_z = dispersion(0.0, 0.0, k, 1.0, 2.0, 3.0)
    payload = {
        "meta": metadata(
            {
                "k": k,
                "rho": 1.0,
                "equal_K": 2.0,
                "unequal_K": [1.0, 2.0, 3.0],
            }
        ),
        "equal_K_dispersion": {
            "omega2_x": [float(x) for x in equal],
            "omega2_along_x": [float(x) for x in axis_x],
            "omega2_along_z": [float(x) for x in axis_z],
        },
        "anisotropy": {
            "equal_K_direction_111": anisotropy((1, 1, 1), 2.0, 2.0, 2.0),
            "unequal_K_direction_x": anisotropy((1, 0, 0), 1.0, 2.0, 3.0),
        },
        "modes": modes(),
        "symbolic_matrix_matches": symbolic_matches_numeric(),
        "verdict": {
            "equal_K_dispersion_proven": True,
            "propagating_modes": 2,
            "photon_candidate": False,
            "emergent_lorentz_invariance": False,
            "note": (
                "K1=K2=K3 gives omega^2=(K/rho)k^2 for the two transverse modes. "
                "The background n0 selects a preferred frame, and no gauge field is present."
            ),
        },
    }
    if write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        write_json(RESULTS_DIR / "frank_oseen.json", payload)
        write_text_atomic(RESULTS_DIR / "frank_oseen.md", render_frank_oseen(payload))
    return payload


def render_frank_oseen(payload: dict) -> str:
    v = payload["verdict"]
    equal = payload["equal_K_dispersion"]
    lines = [
        "# Frank-Oseen linearised modes (claim 10)",
        "",
        "Background n0 = z, plane wave, kinetic term (rho/2)(dt n)^2. "
        "The elastic matrix is the Hessian of the quadratic director energy.",
        "",
        f"- K1=K2=K3=2, k=1: omega^2 = {equal['omega2_x']} (two degenerate modes).",
        f"- Unequal K=(1,2,3), k along x: omega^2 = {equal['omega2_along_x']}.",
        f"- Unequal K=(1,2,3), k along z: omega^2 = {equal['omega2_along_z']}.",
        f"- Symbolic Hessian equals the numeric matrix: **{payload['symbolic_matrix_matches']}**.",
        "",
        "## Modes",
        "",
        f"- Propagating modes: {payload['modes']['propagating_modes']}.",
        f"- Polarisation: {payload['modes']['polarisations']}.",
        f"- Gauge field / vector potential: {payload['modes']['gauge_field']} / {payload['modes']['vector_potential']}.",
        f"- Can be a photon: **{payload['modes']['can_be_photon']}**. {payload['modes']['reason']}",
        "",
        f"**Verdict:** equal-K dispersion proven: **{v['equal_K_dispersion_proven']}**; "
        f"emergent Lorentz invariance: **{v['emergent_lorentz_invariance']}**.",
        "",
        v["note"],
        "",
        f"- Config SHA-256: `{payload['meta']['config_sha256']}`",
        f"- Git: `{payload['meta']['git']['commit']}` (dirty={payload['meta']['git']['dirty']})",
        "",
    ]
    return "\n".join(lines)


def run_derrick_check(write: bool = True) -> dict:
    e2, e4, potential = 2.0, 1.0, 0.5
    payload = {
        "meta": metadata(
            {
                "d": 3,
                "example_E2": e2,
                "example_E4": e4,
                "example_V": potential,
                "symbolic_virial": symbolic_virial(),
            }
        ),
        "exponents": exponents(3),
        "virial_example": virial(e2, e4, potential, 3),
        "second_derivative_example": 2.0 * e4 + 6.0 * potential,
        "minimum_no_potential": {
            "E2": 2.0,
            "E4": 8.0,
            "lambda_squared": stationary_scale_squared(2.0, 8.0, 0.0),
            "details": scaling_minimum(2.0, 8.0, 0.0),
        },
        "minimum_with_potential": {
            "E2": 2.0,
            "E4": 8.0,
            "V": 0.5,
            "lambda_squared": stationary_scale_squared(2.0, 8.0, 0.5),
            "details": scaling_minimum(2.0, 8.0, 0.5),
        },
        "regions": {
            "kappa_negative": stable_region(1.0, -1.0, 0.5),
            "kappa_zero": stable_region(1.0, 0.0, 0.5),
            "kappa_positive": stable_region(1.0, 1.0, 0.5),
        },
        "verdict": {
            "scaling_exponents_proven": True,
            "virial_relation_proven": True,
            "stable_scaling_region": "K>0, kappa>0, mu>=0",
            "hopfion_existence_proved": False,
            "note": (
                "Derrick scaling gives a necessary condition, not an existence proof. "
                "No Hopfion solution is claimed."
            ),
        },
    }
    if write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        write_json(RESULTS_DIR / "derrick.json", payload)
        write_text_atomic(RESULTS_DIR / "derrick.md", render_derrick(payload))
    return payload


def render_derrick(payload: dict) -> str:
    v = payload["verdict"]
    lines = [
        "# Derrick scaling (claim 14)",
        "",
        "d=3: E(lambda) = lambda E2 + lambda^-1 E4 + lambda^3 V.",
        f"Exponents: {payload['exponents']}.",
        f"Virial example (E2=2, E4=1, V=0.5): E2 - E4 + 3V = {payload['virial_example']}.",
        f"Second derivative at lambda=1: 2 E4 + 6 V = {payload['second_derivative_example']}.",
        "",
        "## Minima",
        "",
        f"- V=0: lambda^2 = {payload['minimum_no_potential']['lambda_squared']:.6f}, "
        f"minimum = {payload['minimum_no_potential']['details']}.",
        f"- V=0.5: lambda^2 = {payload['minimum_with_potential']['lambda_squared']:.6f}, "
        f"minimum = {payload['minimum_with_potential']['details']}.",
        "",
        "## Parameter region (necessary conditions)",
        "",
        "| case | bounded below | scaling minimum |",
        "|---|---|---|",
    ]
    for name, region in payload["regions"].items():
        lines.append(
            f"| {name} | {region['energy_bounded_below']} | {region['scaling_minimum_exists']} |"
        )
    lines += [
        "",
        f"**Verdict:** scaling exponents and virial relation proven: "
        f"**{v['scaling_exponents_proven']} / {v['virial_relation_proven']}**. "
        f"Necessary region: **{v['stable_scaling_region']}**. "
        f"Hopfion existence proved: **{v['hopfion_existence_proved']}**.",
        "",
        v["note"],
        "",
        f"- Config SHA-256: `{payload['meta']['config_sha256']}`",
        f"- Git: `{payload['meta']['git']['commit']}` (dirty={payload['meta']['git']['dirty']})",
        "",
    ]
    return "\n".join(lines)
