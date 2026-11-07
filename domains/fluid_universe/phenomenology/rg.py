"""One-loop Standard-Model running of charged-lepton Yukawa couplings.

The charged-lepton RGE is

    16 pi^2 d ln y_k / dt = (3/2) y_k^2 + T - (9/4) g_2^2 - (15/4) g_1^2,

with g_1 SU(5)-normalised and T = Tr(3 Y_u^dagger Y_u + 3 Y_d^dagger Y_d +
Y_e^dagger Y_e).  The gauge and T terms are generation-blind.  Only the
(3/2) y_k^2 term differentiates the three leptons, so Q and r are not exactly
RG-invariant.  The numerical drift is tiny because y_tau^2 is small.

Initial conditions at M_Z are the full-SM MS-bar masses of Huang & Zhou
(PRD 103, 016010 (2021), Table 3), not pole masses.  Pole masses give
Q = 2/3 at the few-10^-6 level; the MS-bar threshold conversion moves Q by
about 0.18%, which is much larger than the subsequent RG drift.  Those two
effects must not be conflated.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.integrate import solve_ivp

from domains.fluid_universe.theory.circulant import extract_ac_delta, q_masses

from .provenance import RESULTS_DIR, metadata, write_json, write_text_atomic

M_Z = 91.1876  # GeV
V_EW = 246.0  # GeV, effective Higgs VEV used by Huang & Zhou
M_TOP = 168.26  # GeV, m_t(M_Z), full SM, Huang & Zhou Table 2
M_BOTTOM = 2.839  # GeV, m_b(M_Z), full SM, Huang & Zhou Table 2
G1_MZ = math.sqrt(5.0 / 3.0) * 0.357254  # SU(5)-normalised g_1 = sqrt(5/3) g'
G2_MZ = 0.65100
G3_MZ = 1.2104

# Full-SM MS-bar charged-lepton masses at M_Z (GeV), Huang & Zhou Table 3.
MSBAR_MZ = {
    "e": 0.00048307,
    "mu": 0.101766,
    "tau": 1.72856,
}
# Published full-SM values for the cross-check (GeV), Huang & Zhou Table 3.
LITERATURE = {
    1.0e8: {"e": 0.00049691, "mu": 0.104681, "tau": 1.77852},
    1.0e12: {"e": 0.00048388, "mu": 0.101936, "tau": 1.73194},
}

SCALES = [M_Z, 1.0e3, 1.0e6, 1.0e9, 1.0e12, 1.0e15, 1.0e16]
KOIDE = 2.0 / 3.0
R_KOIDE = 1.0 / math.sqrt(2.0)
LOOP = 16.0 * math.pi**2


@dataclass(frozen=True)
class InitialState:
    y_e: float
    y_mu: float
    y_tau: float
    y_t: float
    y_b: float
    g1: float
    g2: float
    g3: float

    def vector(self) -> np.ndarray:
        return np.log(
            np.array(
                [self.y_e, self.y_mu, self.y_tau, self.y_t, self.y_b]
                + [self.g1, self.g2, self.g3],
                dtype=float,
            )
        )


def yukawa_from_mass(mass_GeV: float, v_GeV: float = V_EW) -> float:
    return math.sqrt(2.0) * mass_GeV / v_GeV


def initial_state(
    masses_GeV: dict[str, float] | None = None,
    m_top_GeV: float = M_TOP,
    m_bottom_GeV: float = M_BOTTOM,
) -> InitialState:
    masses = masses_GeV or MSBAR_MZ
    return InitialState(
        y_e=yukawa_from_mass(masses["e"]),
        y_mu=yukawa_from_mass(masses["mu"]),
        y_tau=yukawa_from_mass(masses["tau"]),
        y_t=yukawa_from_mass(m_top_GeV),
        y_b=yukawa_from_mass(m_bottom_GeV),
        g1=G1_MZ,
        g2=G2_MZ,
        g3=G3_MZ,
    )


def _split(state: np.ndarray) -> tuple[float, float, float, float, float, float, float, float]:
    """Return y_e, y_mu, y_tau, y_t, y_b, g1, g2, g3 from log-state."""
    ye, ymu, ytau, yt, yb, g1, g2, g3 = np.exp(state)
    return ye, ymu, ytau, yt, yb, g1, g2, g3


def rhs(_t: float, state: np.ndarray) -> np.ndarray:
    """One-loop SM RHS for log(yukawas) and log(gauge couplings).

    The state is logarithmic, so every returned component is d ln(quantity)/dt.
    For a gauge coupling, beta_g = c g^3 implies d ln g/dt = c g^2.
    """
    ye, ymu, ytau, yt, yb, g1, g2, g3 = _split(state)
    T = 3.0 * yt**2 + 3.0 * yb**2 + ye**2 + ymu**2 + ytau**2
    d_le = (1.5 * ye**2 + T - 2.25 * g2**2 - 3.75 * g1**2) / LOOP
    d_lmu = (1.5 * ymu**2 + T - 2.25 * g2**2 - 3.75 * g1**2) / LOOP
    d_ltau = (1.5 * ytau**2 + T - 2.25 * g2**2 - 3.75 * g1**2) / LOOP
    d_lt = (
        1.5 * yt**2
        - 1.5 * yb**2
        + T
        - 8.0 * g3**2
        - 2.25 * g2**2
        - (17.0 / 12.0) * g1**2
    ) / LOOP
    d_lb = (
        1.5 * yb**2
        - 1.5 * yt**2
        + T
        - 8.0 * g3**2
        - 2.25 * g2**2
        - (5.0 / 12.0) * g1**2
    ) / LOOP
    d_g1 = (41.0 / 10.0) * g1**2 / LOOP
    d_g2 = (-19.0 / 6.0) * g2**2 / LOOP
    d_g3 = (-7.0) * g3**2 / LOOP
    return np.array([d_le, d_lmu, d_ltau, d_lt, d_lb, d_g1, d_g2, d_g3])


def _rhs_ratio_only(_t: float, state: np.ndarray) -> np.ndarray:
    """RHS with only the generation-dependent (3/2) y_k^2 term."""
    ye, ymu, ytau = np.exp(state[:3])
    return np.array(
        [
            1.5 * ye**2 / LOOP,
            1.5 * ymu**2 / LOOP,
            1.5 * ytau**2 / LOOP,
        ]
    )


def run_system(
    initial: InitialState | None = None,
    scale_max: float = 1.0e16,
    rtol: float = 1e-11,
    atol: float = 1e-13,
) -> tuple[np.ndarray, callable]:
    initial = initial or initial_state()
    t0, t1 = math.log(M_Z), math.log(scale_max)
    sol = solve_ivp(
        rhs,
        (t0, t1),
        initial.vector(),
        method="DOP853",
        rtol=rtol,
        atol=atol,
        dense_output=True,
        max_step=0.25,
    )
    if not sol.success:
        raise RuntimeError(f"RGE integration failed: {sol.message}")
    return sol.t, sol.sol


def run_ratio_only(
    initial: InitialState | None = None,
    scale_max: float = 1.0e16,
) -> callable:
    initial = initial or initial_state()
    sol = solve_ivp(
        _rhs_ratio_only,
        (math.log(M_Z), math.log(scale_max)),
        np.log(np.array([initial.y_e, initial.y_mu, initial.y_tau])),
        method="DOP853",
        rtol=1e-12,
        atol=1e-14,
        dense_output=True,
        max_step=0.25,
    )
    if not sol.success:
        raise RuntimeError(f"ratio-only integration failed: {sol.message}")
    return sol.sol


def observables_from_yukawas(y: np.ndarray) -> dict[str, float]:
    """Q, r, delta and masses from the three positive Yukawa eigenvalues.

    The circulant matrix acts on sqrt(m), not on the Yukawa eigenvalues.  With
    m_k = y_k v / sqrt(2), the signed roots are x_k = sqrt(m_k).
    """
    y = np.asarray(y, dtype=float)
    if np.any(y <= 0.0):
        raise ValueError("Yukawa eigenvalues must be positive")
    masses = y * V_EW / math.sqrt(2.0)
    roots = np.sqrt(masses)
    Q = float(q_masses(masses))
    a, c, delta = extract_ac_delta(roots)
    return {
        "Q": Q,
        "r": c / a,
        "a_sqrt_GeV": a,
        "c_sqrt_GeV": c,
        "delta": delta,
        "delta_mod_2pi_over_3": delta % (2.0 * math.pi / 3.0),
        "m_e_GeV": float(masses[0]),
        "m_mu_GeV": float(masses[1]),
        "m_tau_GeV": float(masses[2]),
        "all_yukawas_positive": bool(np.all(y > 0.0)),
    }


def convert_pole_to_msbar_explicit(
    m_pole_GeV: float, mu_GeV: float, alpha_mu: float
) -> float:
    """Published one-pass QED conversion used by Xing & Zhang (2006).

    m(mu) = m_pole [1 - (alpha/pi)(1 + (3/4) ln(mu^2/m_pole^2))].
    """
    delta = (alpha_mu / math.pi) * (
        1.0 + 0.75 * math.log(mu_GeV**2 / m_pole_GeV**2)
    )
    return m_pole_GeV * (1.0 - delta)


def convert_pole_to_msbar(m_pole_GeV: float, mu_GeV: float, alpha_mu: float) -> float:
    """Self-consistent one-loop QED pole-to-MSbar conversion by fixed point.

    m_pole = m(mu) * [1 + (alpha/pi)(1 + (3/4) ln(mu^2/m(mu)^2))].
    """
    m = m_pole_GeV
    for _ in range(100):
        delta = (alpha_mu / math.pi) * (
            1.0 + 0.75 * math.log(mu_GeV**2 / m**2)
        )
        m_new = m_pole_GeV / (1.0 + delta)
        if abs(m_new - m) <= 1e-16 * abs(m_new):
            return m_new
        m = m_new
    return m


def _literature_check(sol: callable) -> dict:
    out: dict[str, dict[str, float]] = {}
    for scale, values in LITERATURE.items():
        state = sol(math.log(scale))
        ye, ymu, ytau = np.exp(state[:3])
        got = {
            "e": float(ye * V_EW / math.sqrt(2.0)),
            "mu": float(ymu * V_EW / math.sqrt(2.0)),
            "tau": float(ytau * V_EW / math.sqrt(2.0)),
        }
        out[str(scale)] = {
            "ours": got,
            "literature": values,
            "relative_difference": {
                key: (got[key] - values[key]) / values[key] for key in values
            },
        }
    return out


def run_rg(write: bool = True) -> dict:
    initial = initial_state()
    _t, sol = run_system(initial)
    ratio_sol = run_ratio_only(initial)

    rows = []
    for scale in SCALES:
        state = sol(math.log(scale))
        ye, ymu, ytau, yt, yb, g1, g2, g3 = _split(state)
        obs = observables_from_yukawas(np.array([ye, ymu, ytau]))
        obs["scale_GeV"] = scale
        obs["y_t"] = float(yt)
        obs["y_b"] = float(yb)
        obs["g1"] = float(g1)
        obs["g2"] = float(g2)
        obs["g3"] = float(g3)
        rows.append(obs)

    # Cross-check: the full RHS and the ratio-only RHS must give the same Q and r.
    cross = []
    for scale in SCALES:
        y_full = np.exp(sol(math.log(scale))[:3])
        y_ratio = np.exp(ratio_sol(math.log(scale)))
        # Ratio-only has an arbitrary common normalisation; Q and r are scale-free.
        cross.append(
            {
                "scale_GeV": scale,
                "delta_Q": abs(
                    observables_from_yukawas(y_full)["Q"]
                    - observables_from_yukawas(y_ratio)["Q"]
                ),
                "delta_r": abs(
                    observables_from_yukawas(y_full)["r"]
                    - observables_from_yukawas(y_ratio)["r"]
                ),
            }
        )

    first, last = rows[0], rows[-1]
    q_drift = last["Q"] - first["Q"]
    r_drift = last["r"] - first["r"]

    # Pole-to-MSbar cross-check against Xing & Zhang (2006), alpha(M_Z)=1/128.89.
    pole = {"e": 0.51099895000e-3, "mu": 105.6583755e-3, "tau": 1776.93e-3}
    alpha_xing = 1.0 / 128.89
    converted = {}
    self_consistent = {}
    for name, pole_mass in pole.items():
        converted[name] = convert_pole_to_msbar_explicit(pole_mass, M_Z, alpha_xing)
        self_consistent[name] = convert_pole_to_msbar(pole_mass, M_Z, alpha_xing)
    xing = {"e": 0.486755106e-3, "mu": 102.740394e-3, "tau": 1746.56e-3}
    conversion_check = {}
    for name in pole:
        conversion_check[name] = {
            "ours_GeV": converted[name],
            "xing_zhang_GeV": xing[name],
            "relative_difference": (converted[name] - xing[name]) / xing[name],
        }
    converted_masses = np.array([converted["e"], converted["mu"], converted["tau"]])
    converted_Q = q_masses(converted_masses)
    converted_a, converted_c, _ = extract_ac_delta(np.sqrt(converted_masses))
    sc_masses = np.array([self_consistent["e"], self_consistent["mu"], self_consistent["tau"]])
    sc_a, sc_c, _ = extract_ac_delta(np.sqrt(sc_masses))
    sc_Q = q_masses(sc_masses)

    payload = {
        "meta": metadata(
            {
                "initial_conditions": "full-SM MSbar masses at M_Z, Huang & Zhou (2021) Table 3",
                "M_Z_GeV": M_Z,
                "v_GeV": V_EW,
                "m_top_MZ_GeV": M_TOP,
                "m_bottom_MZ_GeV": M_BOTTOM,
                "g1_MZ": G1_MZ,
                "g2_MZ": G2_MZ,
                "g3_MZ": G3_MZ,
                "scales_GeV": SCALES,
                "rtol": 1e-11,
                "atol": 1e-13,
                "loops": 1,
            }
        ),
        "initial": {
            "y_e": initial.y_e,
            "y_mu": initial.y_mu,
            "y_tau": initial.y_tau,
            "y_t": initial.y_t,
            "y_b": initial.y_b,
            "m_e_GeV": MSBAR_MZ["e"],
            "m_mu_GeV": MSBAR_MZ["mu"],
            "m_tau_GeV": MSBAR_MZ["tau"],
            "mass_source": "Huang & Zhou, PRD 103, 016010 (2021), Table 3",
        },
        "scales": rows,
        "drift": {
            "Q_MZ": first["Q"],
            "Q_1e16": last["Q"],
            "Q_change": q_drift,
            "Q_relative_change": q_drift / first["Q"],
            "r_MZ": first["r"],
            "r_1e16": last["r"],
            "r_change": r_drift,
            "r_relative_change": r_drift / first["r"],
            "n_e_folds": math.log(1.0e16 / M_Z),
            "Q_change_per_e_fold": q_drift / math.log(1.0e16 / M_Z),
            "r_change_per_e_fold": r_drift / math.log(1.0e16 / M_Z),
        },
        "shape_only_approximation": {
            "max_abs_delta_Q": max(row["delta_Q"] for row in cross),
            "max_abs_delta_r": max(row["delta_r"] for row in cross),
            "rows": cross,
        },
        "published_conversion_check": {
            "alpha_MZ": alpha_xing,
            "converted_explicit": conversion_check,
            "converted_self_consistent": self_consistent,
            "Q_from_converted_pole_masses": converted_Q,
            "r_from_converted_pole_masses": converted_c / converted_a,
            "Q_self_consistent": sc_Q,
            "r_self_consistent": sc_c / sc_a,
            "xing_zhang_Q_MZ": 0.66792,
        },
        "literature_high_scale_check": _literature_check(sol),
        "verdict": {
            "exact_rg_invariance_of_r": False,
            "numerical_drift_is_negligible": bool(abs(r_drift) < 1e-5),
            "Q_MZ_is_2_3": bool(abs(first["Q"] - KOIDE) < 1e-4),
            "note": (
                "The 0.18% difference between pole and MS-bar Q(M_Z) is a scheme/threshold "
                "effect, not RG running. The one-loop RG drift from M_Z to 1e16 GeV is tiny."
            ),
        },
    }

    if write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        write_json(RESULTS_DIR / "rg_run.json", payload)
        write_text_atomic(RESULTS_DIR / "rg_run.md", render_markdown(payload))
    return payload


def render_markdown(payload: dict) -> str:
    d = payload["drift"]
    lines = [
        "# One-loop SM running of the charged-lepton Koide parameters",
        "",
        "Initial conditions: full-SM MS-bar masses at M_Z from Huang & Zhou (2021), Table 3. "
        "One-loop RGE, `scipy.solve_ivp` DOP853, rtol=1e-11.",
        "",
        "| mu (GeV) | m_e (MeV) | m_mu (MeV) | m_tau (MeV) | Q | r | delta mod 2pi/3 |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in payload["scales"]:
        lines.append(
            f"| {row['scale_GeV']:.6g} | {row['m_e_GeV']*1e3:.9g} | "
            f"{row['m_mu_GeV']*1e3:.9g} | {row['m_tau_GeV']*1e3:.9g} | "
            f"{row['Q']:.12f} | {row['r']:.12f} | {row['delta_mod_2pi_over_3']:.12f} |"
        )
    lines += [
        "",
        "## Drift",
        "",
        f"- Q(M_Z) = {d['Q_MZ']:.12f}",
        f"- Q(1e16 GeV) = {d['Q_1e16']:.12f}",
        f"- Delta Q = {d['Q_change']:+.3e} ({d['Q_relative_change']:+.3e} relative)",
        f"- r(M_Z) = {d['r_MZ']:.12f}",
        f"- r(1e16 GeV) = {d['r_1e16']:.12f}",
        f"- Delta r = {d['r_change']:+.3e} ({d['r_relative_change']:+.3e} relative)",
        f"- over {d['n_e_folds']:.2f} e-folds",
        "",
        "**Interpretation.** The exact one-loop invariance claim is false: the (3/2)y_k^2 term "
        "differentiates the generations. For charged leptons the effect is a few parts in 10^6 over "
        "16 decades, so the numerical stability is real but is not an invariance theorem.",
        "",
        "## Cross-checks",
        "",
        f"- Shape-only diagnostic (NOT a cross-check): max |Delta Q| = {payload['shape_only_approximation']['max_abs_delta_Q']:.3e}, "
        f"max |Delta r| = {payload['shape_only_approximation']['max_abs_delta_r']:.3e}. "
        "The difference is a few percent of the drift because the (3/2)y_k^2 term scales with the absolute Yukawa normalisation.",
        f"- Pole-to-MSbar conversion vs Xing & Zhang (2006): "
        + ", ".join(
            f"{k}: {v['relative_difference']:+.2e}"
            for k, v in payload["published_conversion_check"]["converted_explicit"].items()
        )
        + ".",
        "",
        "## Literature high-scale check (Huang & Zhou 2021, Table 3)",
        "",
        "| mu (GeV) | ours m_e | lit m_e | ours m_mu | lit m_mu | ours m_tau | lit m_tau |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for scale, item in payload["literature_high_scale_check"].items():
        o, l = item["ours"], item["literature"]
        lines.append(
            f"| {float(scale):.0e} | {o['e']*1e3:.6g} | {l['e']*1e3:.6g} | "
            f"{o['mu']*1e3:.6g} | {l['mu']*1e3:.6g} | {o['tau']*1e3:.6g} | {l['tau']*1e3:.6g} |"
        )
    lines += [
        "",
        "The absolute mass scale at high energies is sensitive to the near-cancellation between the "
        "top-Yukawa term and the gauge terms, so the one-loop truncation differs from the three-loop "
        "literature by up to a few percent at 1e8 GeV. Only the dimensionless ratios Q and r are used "
        "for any claim; they are stable at the 10^-6 level.",
        "",
        f"- Config SHA-256: `{payload['meta']['config_sha256']}`",
        f"- Git: `{payload['meta']['git']['commit']}` (dirty={payload['meta']['git']['dirty']})",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    payload = run_rg()
    d = payload["drift"]
    print(f"Q(M_Z)      = {d['Q_MZ']:.12f}")
    print(f"Q(1e16)     = {d['Q_1e16']:.12f}")
    print(f"Delta Q     = {d['Q_change']:+.3e}")
    print(f"r(M_Z)      = {d['r_MZ']:.12f}")
    print(f"r(1e16)     = {d['r_1e16']:.12f}")
    print(f"Delta r     = {d['r_change']:+.3e}")
    print("conversion check:", payload["published_conversion_check"]["converted_explicit"])


if __name__ == "__main__":
    main()
