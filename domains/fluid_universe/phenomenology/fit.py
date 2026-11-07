"""PDG pole-mass fit of the Hermitian circulant parametrisation.

The fit has three parameters (a, c, delta) for three masses and is therefore
exact by construction.  It is a consistency check of the algebra, not evidence
for Z3 and not a prediction of Q = 2/3.  Uncertainty propagation is a fixed-seed
Monte Carlo using the PDG 1-sigma errors.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from domains.fluid_universe.theory.circulant import fit_masses, koide_tau_prediction, q_masses

from .provenance import RESULTS_DIR, metadata, write_json, write_text_atomic

DATA_PATH = Path(__file__).resolve().parent / "data" / "pdg2024_leptons.csv"
KOIDE = 2.0 / 3.0
R_KOIDE = 1.0 / np.sqrt(2.0)


@dataclass(frozen=True)
class PoleMass:
    name: str
    value_MeV: float
    uncertainty_MeV: float
    definition: str
    source: str


def load_pole_masses(path: Path = DATA_PATH) -> list[PoleMass]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    masses = [
        PoleMass(
            name=row["name"],
            value_MeV=float(row["value_MeV"]),
            uncertainty_MeV=float(row["uncertainty_MeV"]),
            definition=row["definition"],
            source=row["source"],
        )
        for row in rows
    ]
    if len(masses) != 3:
        raise ValueError("expected exactly three charged leptons")
    return masses


def _summary(values: np.ndarray) -> dict[str, float]:
    values = np.asarray(values, dtype=float)
    return {
        "mean": float(np.mean(values)),
        "std": float(np.std(values, ddof=1)),
        "p16": float(np.percentile(values, 16.0)),
        "p84": float(np.percentile(values, 84.0)),
    }


def _circular_mean(angles: np.ndarray) -> float:
    return float(np.angle(np.mean(np.exp(1j * angles))) % (2.0 * np.pi))


def fit_point(masses_MeV: np.ndarray) -> dict[str, float]:
    fit = fit_masses(masses_MeV)
    fit["tau_prediction_MeV"] = koide_tau_prediction(
        float(masses_MeV[0]), float(masses_MeV[1])
    )
    fit["Q_minus_2_3"] = fit["Q"] - KOIDE
    fit["r_minus_1_sqrt2"] = fit["r"] - R_KOIDE
    # delta is defined only up to a cyclic relabeling, which shifts it by
    # 2*pi/3.  The minimal representative is the one comparable to Brannen's
    # delta ~ 0.2222.  The roots, Q, and r are invariant.
    fit["delta_mod_2pi_over_3"] = fit["delta"] % (2.0 * np.pi / 3.0)
    fit["delta_minus_2_over_9"] = fit["delta_mod_2pi_over_3"] - 2.0 / 9.0
    return fit


def run_fit(n_mc: int = 100_000, seed: int = 20261025, write: bool = True) -> dict:
    masses = load_pole_masses()
    central = np.array([m.value_MeV for m in masses])
    sigma = np.array([m.uncertainty_MeV for m in masses])
    point = fit_point(central)

    rng = np.random.default_rng(seed)
    draws = rng.normal(loc=central, scale=sigma, size=(n_mc, 3))
    # The errors are tiny compared with the masses; clipping is a safety net.
    draws = np.clip(draws, 1e-12, None)

    q_values = np.empty(n_mc)
    r_values = np.empty(n_mc)
    delta_values = np.empty(n_mc)
    a_values = np.empty(n_mc)
    c_values = np.empty(n_mc)
    tau_values = np.empty(n_mc)
    for i, m in enumerate(draws):
        fit = fit_masses(m)
        q_values[i] = fit["Q"]
        r_values[i] = fit["r"]
        delta_values[i] = fit["delta"]
        a_values[i] = fit["a"]
        c_values[i] = fit["c"]
        tau_values[i] = koide_tau_prediction(float(m[0]), float(m[1]))

    sigma_q = float(np.std(q_values, ddof=1))
    sigma_r = float(np.std(r_values, ddof=1))
    sigma_tau = float(np.std(tau_values, ddof=1))
    tau_measured = float(central[2])
    tau_pred = point["tau_prediction_MeV"]
    pull_tau = (tau_measured - tau_pred) / np.hypot(sigma_tau, sigma[2])

    payload = {
        "meta": metadata(
            {
                "n_mc": n_mc,
                "seed": seed,
                "inputs": [
                    {"name": m.name, "value_MeV": m.value_MeV, "sigma_MeV": m.uncertainty_MeV}
                    for m in masses
                ],
                "definitions": "pole masses",
                "koide_target": KOIDE,
                "r_target": R_KOIDE,
            }
        ),
        "inputs": [m.__dict__ for m in masses],
        "point": point,
        "monte_carlo": {
            "Q": _summary(q_values),
            "r": _summary(r_values),
            "delta": {**_summary(delta_values), "circular_mean": _circular_mean(delta_values)},
            "a_sqrt_MeV": _summary(a_values),
            "c_sqrt_MeV": _summary(c_values),
            "tau_prediction_MeV": _summary(tau_values),
        },
        "tests": {
            "Q_deviation_sigma": float((point["Q"] - KOIDE) / sigma_q),
            "r_deviation_sigma": float((point["r"] - R_KOIDE) / sigma_r),
            "tau_measured_minus_predicted_sigma": float(pull_tau),
        },
        "interpretation": {
            "fit_is_exact_by_construction": True,
            "free_parameters": 3,
            "data_points": 3,
            "predicts_Q": False,
            "note": "Q=2/3 is the independent condition r=1/sqrt(2), not a consequence of Z3.",
        },
    }

    if write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        write_json(RESULTS_DIR / "pdg_fit.json", payload)
        write_text_atomic(RESULTS_DIR / "pdg_fit.md", render_markdown(payload))
    return payload


def render_markdown(payload: dict) -> str:
    p = payload["point"]
    mc = payload["monte_carlo"]
    tests = payload["tests"]
    lines = [
        "# PDG pole-mass fit",
        "",
        "Generated by `python -m phenomenology.run_all`. Pole masses from PDG 2024.",
        "",
        "| quantity | value |",
        "|---|---:|",
        f"| a (MeV^1/2) | {p['a']:.9f} |",
        f"| c (MeV^1/2) | {p['c']:.9f} |",
        f"| delta (rad, branch) | {p['delta']:.12f} |",
        f"| delta mod 2*pi/3 (rad) | {p['delta_mod_2pi_over_3']:.12f} |",
        f"| delta - 2/9 (rad) | {p['delta_minus_2_over_9']:+.3e} |",
        f"| r = c/a | {p['r']:.12f} |",
        f"| Q | {p['Q']:.12f} |",
        f"| Q from 1/3+2c^2/(3a^2) | {p['Q_from_ac']:.12f} |",
        f"| max abs residual (MeV^1/2) | {p['max_abs_residual']:.3e} |",
        f"| m_tau predicted from Q=2/3 (MeV) | {p['tau_prediction_MeV']:.6f} |",
        "",
        "## Monte Carlo (PDG 1-sigma, fixed seed)",
        "",
        "| quantity | mean | std | 16th | 84th |",
        "|---|---:|---:|---:|---:|",
    ]
    for key, label in [
        ("Q", "Q"),
        ("r", "r"),
        ("delta", "delta (rad)"),
        ("a_sqrt_MeV", "a"),
        ("c_sqrt_MeV", "c"),
        ("tau_prediction_MeV", "m_tau pred (MeV)"),
    ]:
        s = mc[key]
        lines.append(
            f"| {label} | {s['mean']:.12g} | {s['std']:.3g} | {s['p16']:.12g} | {s['p84']:.12g} |"
        )
    lines += [
        "",
        "## Consistency tests",
        "",
        f"- (Q - 2/3)/sigma = {tests['Q_deviation_sigma']:+.3f}",
        f"- (r - 1/sqrt(2))/sigma = {tests['r_deviation_sigma']:+.3f}",
        f"- (m_tau(measured) - m_tau(predicted))/sigma = {tests['tau_measured_minus_predicted_sigma']:+.3f}",
        "",
        "**Interpretation.** The fit is exact by construction: three parameters, three masses. "
        "It neither derives nor predicts Q=2/3. The Koide value is the extra condition r=1/sqrt(2). "
        "The tau prediction is a post-hoc consistency check made with the measured electron and muon masses.",
        "",
        f"- Config SHA-256: `{payload['meta']['config_sha256']}`",
        f"- Git: `{payload['meta']['git']['commit']}` (dirty={payload['meta']['git']['dirty']})",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    payload = run_fit()
    p = payload["point"]
    print(f"Q = {p['Q']:.12f}  (2/3 = {KOIDE:.12f})")
    print(f"r = {p['r']:.12f}  (1/sqrt2 = {R_KOIDE:.12f})")
    print(f"delta = {p['delta']:.12f} rad")
    print(f"m_tau prediction = {p['tau_prediction_MeV']:.6f} MeV")


if __name__ == "__main__":
    main()
