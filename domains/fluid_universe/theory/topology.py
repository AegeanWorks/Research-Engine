"""Topology of a nematic director and the Z3 question.

A nematic director is headless: n ~ -n, so the order-parameter space is RP^2.
Its low homotopy groups are

    pi1(RP^2) = Z2,  pi2(RP^2) = Z,  pi3(RP^2) = Z.

None contains a Z3 factor.  The cos(3 phi) potential used in the rotor model is
therefore inserted by hand unless an additional structure is specified.

This module records the direct result and audits three "natural" extensions.
It does not prove that no conceivable extension can produce Z3; it records that
none of the three standard ones does so without inserting the symmetry.
"""

from __future__ import annotations

HOMOTOPY = {"pi1": "Z2", "pi2": "Z", "pi3": "Z"}


def has_z3_factor() -> bool:
    """True only if one of the listed homotopy groups has a Z3 factor."""
    return any("Z3" in value or "Z_3" in value for value in HOMOTOPY.values())


def direct_result() -> dict:
    return {
        "order_parameter_space": "RP^2",
        "homotopy": dict(HOMOTOPY),
        "z3_factor_present": has_z3_factor(),
        "cos3phi_inserted_by_hand": True,
        "direct_claim": "Z3 is derived from nematic topology alone",
        "direct_claim_falsified": True,
        "reason": (
            "The listed homotopy groups contain Z2 and Z, not Z3. A three-fold "
            "sector cannot be read off the RP^2 topology without extra structure."
        ),
    }


def extensions() -> dict:
    return {
        "rank_three_order_parameter": {
            "z3_derived": False,
            "requires": (
                "An explicit rank-3 tensor with a three-fold symmetric invariant. "
                "The Z3 is a property of the chosen invariant, not of RP^2."
            ),
        },
        "three_coupled_nematics": {
            "z3_derived": False,
            "requires": (
                "An S3 permutation symmetry of the three fields. Its Z3 subgroup "
                "is imposed by the coupling, so the symmetry is inserted."
            ),
        },
        "three_fold_lattice": {
            "z3_derived": False,
            "requires": (
                "A lattice with a three-fold axis. The lattice breaks continuous "
                "rotation and supplies the Z3 label; nematic topology alone does not."
            ),
        },
    }


def verdict() -> dict:
    direct = direct_result()
    ext = extensions()
    return {
        "13a_direct_z3_from_nematic_topology": False,
        "13b_natural_extension_yields_z3_without_insertion": False,
        "direct_claim_status": "FALSIFIED",
        "extensions_status": "UNVERIFIED (null for the three standard extensions)",
        "cos3phi_inserted_by_hand": True,
        "note": (
            "The strong claim is false: RP^2 has no Z3 factor and the cos(3 phi) "
            "term is inserted. None of the three standard extensions produces Z3 "
            "without an explicit three-fold structure. A different, specified "
            "extension is not excluded, but it would have to be constructed and "
            "tested explicitly."
        ),
        "direct": direct,
        "extensions": ext,
    }


def render_markdown(payload: dict) -> str:
    v = payload["verdict"]
    lines = [
        "# Nematic topology and Z3 (claim 13)",
        "",
        f"Order-parameter space: {v['direct']['order_parameter_space']}. "
        f"Homotopy: {v['direct']['homotopy']}.",
        "",
        "| extension | Z3 derived? | what it would require |",
        "|---|---|---|",
    ]
    for name, item in v["extensions"].items():
        lines.append(f"| {name} | {item['z3_derived']} | {item['requires']} |")
    lines += [
        "",
        f"**Verdict:** direct Z3 from nematic topology: **{v['13a_direct_z3_from_nematic_topology']}**; "
        f"standard extensions: **{v['13b_natural_extension_yields_z3_without_insertion']}**. "
        f"`cos(3 phi)` inserted by hand: **{v['cos3phi_inserted_by_hand']}**.",
        "",
        v["note"],
        "",
        f"- Config SHA-256: `{payload['meta']['config_sha256']}`",
        f"- Git: `{payload['meta']['git']['commit']}` (dirty={payload['meta']['git']['dirty']})",
        "",
    ]
    return "\n".join(lines)
