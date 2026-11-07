"""What a minimal circulant lepton sector predicts for PMNS mixing.

Two assumptions are possible once only one sector is specified:

* both charged-lepton and neutrino mass matrices are Hermitian circulants in
  the same flavour basis: they share the DFT eigenvectors, so U_PMNS is a
  diagonal phase matrix (no mixing);
* only the neutrino mass matrix is circulant and the charged-lepton matrix is
  diagonal: U_PMNS is the DFT, i.e. trimaximal mixing |U_alpha i| = 1/sqrt(3).

Both branches are incompatible with the measured angles.  The original claim
"circulant PMNS is ruled out by theta13" is therefore not well-posed as stated:
the same-basis branch is excluded by all three angles, while the trimaximal
branch is excluded by theta13 (and the others).
"""

from __future__ import annotations

import math

import numpy as np

from .neutrinos import load_parameters
from .provenance import RESULTS_DIR, metadata, write_json, write_text_atomic


def dft_matrix() -> np.ndarray:
    omega = np.exp(2j * math.pi / 3.0)
    k = np.arange(3)
    return np.array([[omega ** (k * n) for k in range(3)] for n in range(3)]) / math.sqrt(3.0)


def angles_from_pmns(U: np.ndarray) -> dict[str, float]:
    """Standard three-neutrino angles in degrees from |U|."""
    U = np.asarray(U, dtype=complex)
    s13 = float(abs(U[0, 2]))
    s13 = min(1.0, s13)
    c13 = math.sqrt(max(0.0, 1.0 - s13 * s13))
    if c13 == 0.0:
        raise ValueError("theta13 = 90 degrees: theta12 and theta23 are undefined")
    s12 = min(1.0, float(abs(U[0, 1])) / c13)
    s23 = min(1.0, float(abs(U[1, 2])) / c13)
    return {
        "theta12_deg": math.degrees(math.asin(s12)),
        "theta13_deg": math.degrees(math.asin(s13)),
        "theta23_deg": math.degrees(math.asin(s23)),
    }


def run_pmns_check(write: bool = True) -> dict:
    measured = load_parameters()
    measured_angles = {
        "theta12_deg": measured.theta12_deg,
        "theta13_deg": measured.theta13_deg,
        "theta23_deg": measured.theta23_deg,
    }
    identity = np.eye(3, dtype=complex)
    dft = dft_matrix()
    branches = {
        "same_basis_both_circulant": {
            "U": "identity (up to diagonal phases and permutations)",
            "angles": angles_from_pmns(identity),
        },
        "neutrino_only_circulant": {
            "U": "DFT (trimaximal, |U_alpha i| = 1/sqrt(3))",
            "angles": angles_from_pmns(dft),
        },
    }
    for branch in branches.values():
        branch["delta_vs_measured"] = {
            key: branch["angles"][key] - measured_angles[key] for key in measured_angles
        }
    theta13_measured = measured_angles["theta13_deg"]
    theta13_identity = branches["same_basis_both_circulant"]["angles"]["theta13_deg"]
    theta13_dft = branches["neutrino_only_circulant"]["angles"]["theta13_deg"]
    payload = {
        "meta": metadata(
            {
                "source": "NuFit 5.2 (2022) with SK-atm; DFT basis for a Hermitian circulant",
                "measured_angles_deg": measured_angles,
            }
        ),
        "measured": measured_angles,
        "branches": branches,
        "verdict": {
            "same_basis_branch_excluded": bool(
                abs(theta13_identity - theta13_measured) > 3.0
                or abs(branches["same_basis_both_circulant"]["angles"]["theta12_deg"] - measured_angles["theta12_deg"]) > 3.0
            ),
            "trimaximal_branch_excluded_by_theta13": bool(abs(theta13_dft - theta13_measured) > 3.0),
            "original_claim_well_posed": False,
            "note": (
                "A circulant PMNS is not a single model. If both mass matrices are circulant "
                "in the same basis the prediction is no mixing; if only the neutrino matrix is "
                "circulant the prediction is trimaximal mixing. Both are excluded, but only the "
                "second is specifically a theta13 statement."
            ),
        },
    }
    if write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        write_json(RESULTS_DIR / "pmns.json", payload)
        write_text_atomic(RESULTS_DIR / "pmns.md", render_markdown(payload))
    return payload


def render_markdown(payload: dict) -> str:
    v = payload["verdict"]
    lines = [
        "# Circulant PMNS branches",
        "",
        "Measured angles (NuFit 5.2 with SK-atm, NO): "
        f"theta12={payload['measured']['theta12_deg']:.2f} deg, "
        f"theta13={payload['measured']['theta13_deg']:.2f} deg, "
        f"theta23={payload['measured']['theta23_deg']:.2f} deg.",
        "",
        "| branch | U | theta12 | theta13 | theta23 |",
        "|---|---|---:|---:|---:|",
    ]
    for name, branch in payload["branches"].items():
        angles = branch["angles"]
        lines.append(
            f"| {name} | {branch['U']} | {angles['theta12_deg']:.6f} | "
            f"{angles['theta13_deg']:.6f} | {angles['theta23_deg']:.6f} |"
        )
    lines += [
        "",
        f"**Verdict:** same-basis branch excluded: **{v['same_basis_branch_excluded']}**. "
        f"Trimaximal branch excluded by theta13: **{v['trimaximal_branch_excluded_by_theta13']}**. "
        f"Original theta13-only claim well-posed: **{v['original_claim_well_posed']}**.",
        "",
        v["note"],
        "",
        f"- Config SHA-256: `{payload['meta']['config_sha256']}`",
        f"- Git: `{payload['meta']['git']['commit']}` (dirty={payload['meta']['git']['dirty']})",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    result = run_pmns_check()
    print(result["verdict"])
