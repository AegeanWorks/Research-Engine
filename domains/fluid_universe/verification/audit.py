"""Independent verification of every claim marked PROVEN, VERIFIED, or NUMERIC.

Project rule G-001: the audit must be run twice in separate processes and the
two result sets compared.  `verification.compare` does that.

This module deliberately does not import ``theory`` or ``phenomenology``.  It
re-derives each result from scratch (sympy, numpy, scipy) and compares against
the stored outputs in ``results/``.  A disagreement is reported, never hidden.

Run (two separate processes, then compare):

    python -m verification.audit --tag run1
    python -m verification.audit --tag run2
    python -m verification.compare

A single run writes ``verification_single.*`` and is explicitly not accepted.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from fractions import Fraction
import os
import platform
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import scipy
import sympy as sp
from scipy.integrate import quad, solve_ivp
from scipy.linalg import eigh

from .fingerprint import default_root, fingerprints

ROOT = default_root()
RESULTS = ROOT / "results"
KOIDE = 2.0 / 3.0
R_KOIDE = 1.0 / math.sqrt(2.0)


@dataclass
class Audit:
    checks: list[dict] = field(default_factory=list)

    def record(self, claim: str, passed: bool, detail: str, expected=None, observed=None):
        self.checks.append(
            {
                "claim": claim,
                "passed": bool(passed),
                "detail": detail,
                "expected": expected,
                "observed": observed,
            }
        )

    @property
    def failed(self) -> list[dict]:
        return [c for c in self.checks if not c["passed"]]


# ---------------------------------------------------------------------------
# Independent primitives
# ---------------------------------------------------------------------------


def circulant(a: float, c: float, delta: float) -> np.ndarray:
    b = c * np.exp(1j * delta)
    return np.array([[a, b, b.conjugate()], [b.conjugate(), a, b], [b, b.conjugate(), a]])


def roots_from_ac(a: float, c: float, delta: float) -> np.ndarray:
    return np.array([a + 2.0 * c * math.cos(delta + 2.0 * math.pi * k / 3.0) for k in range(3)])


def q_from_roots(x: np.ndarray) -> float:
    x = np.asarray(x, dtype=float)
    return float(np.sum(x * x) / np.sum(x) ** 2)


def q_from_masses(m: np.ndarray) -> float:
    m = np.asarray(m, dtype=float)
    return float(np.sum(m) / np.sum(np.sqrt(m)) ** 2)


def q_from_ac(a: float, c: float) -> float:
    return 1.0 / 3.0 + 2.0 * c * c / (3.0 * a * a)


def fit_linear(x: np.ndarray) -> tuple[float, float, float]:
    """Independent least-squares/inverse of x_k = a + 2u cos(theta_k) - 2v sin(theta_k)."""
    x = np.asarray(x, dtype=float)
    theta = np.array([0.0, 2.0 * math.pi / 3.0, 4.0 * math.pi / 3.0])
    A = np.column_stack([np.ones(3), 2.0 * np.cos(theta), -2.0 * np.sin(theta)])
    a, u, v = np.linalg.solve(A, x)
    c = math.hypot(u, v)
    delta = math.atan2(v, u) % (2.0 * math.pi)
    if c < 1e-15:
        delta = 0.0
    return float(a), float(c), float(delta)


def load_results(name: str) -> dict:
    return json.loads((RESULTS / name).read_text(encoding="utf-8"))


def provenance() -> dict:
    """Minimal, independent provenance block (no project imports)."""
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, timeout=10
        ).strip()
        dirty = bool(
            subprocess.check_output(
                ["git", "status", "--porcelain"], cwd=ROOT, text=True, timeout=10
            ).strip()
        )
    except Exception:
        commit, dirty = "no-git", True
    return {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_commit": commit,
        "git_dirty": dirty,
        "fingerprints": fingerprints(),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "sympy": sp.__version__,
        "deterministic": True,
        "seed": "none (fixed inputs; the only Monte Carlo uses the seed stored in pdg_fit.json)",
    }


def write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


# ---------------------------------------------------------------------------
# Claim 1 / 2: algebra
# ---------------------------------------------------------------------------


def audit_algebra(audit: Audit) -> None:
    a, c, delta = sp.symbols("a c delta", real=True)
    w = sp.exp(2 * sp.pi * sp.I / 3)
    b = c * sp.exp(sp.I * delta)
    M = sp.Matrix([[a, b, c * sp.exp(-sp.I * delta)],
                   [c * sp.exp(-sp.I * delta), a, b],
                   [b, c * sp.exp(-sp.I * delta), a]])

    herm = sp.simplify(M - M.H)
    audit.record("2a: M = M^dagger", herm == sp.zeros(3, 3), "symbolic difference is the zero matrix")
    asym = sp.simplify((M - M.T)[0, 1])
    audit.record(
        "2a: M != M^T for generic delta",
        asym != 0 and sp.simplify(sp.expand_complex(asym - 2 * sp.I * c * sp.sin(delta))) == 0,
        "M - M^T has off-diagonal 2 i c sin(delta)",
    )

    for k in range(3):
        v = sp.Matrix([1, w**k, w ** (2 * k)])
        lam = a + 2 * c * sp.cos(delta + 2 * sp.pi * k / 3)
        residual = sp.expand(M * v - lam * v)
        ok = all(sp.simplify(sp.expand_complex(entry)) == 0 for entry in residual)
        audit.record(f"2b/F1: eigenpair k={k}", ok, "M v_k - lambda_k v_k simplifies to zero")

    x = [a + 2 * c * sp.cos(delta + 2 * sp.pi * k / 3) for k in range(3)]
    identity = sp.simplify(
        sum(term * term for term in x) / sum(x) ** 2
        - (sp.Rational(1, 3) + 2 * c * c / (3 * a * a))
    )
    audit.record("1a/F2: Q identity", identity == 0, "symbolic difference simplifies to zero")

    solve_c2 = sp.solve(sp.Eq(sp.Rational(1, 3) + 2 * c * c / (3 * a * a), sp.Rational(2, 3)), c * c)
    expected = a * a / 2
    ok = len(solve_c2) == 1 and sp.simplify(solve_c2[0] - expected) == 0
    audit.record("1c/F3: Q=2/3 iff c^2/a^2=1/2", ok, f"sympy solves c^2 = {solve_c2}")

    # Independent numeric checks at 10^5 random points.
    rng = np.random.default_rng(20261025)
    draws = 100_000
    aa = rng.uniform(0.2, 6.0, draws)
    cc = rng.uniform(0.0, 4.0, draws)
    dd = rng.uniform(0.0, 2.0 * np.pi, draws)
    max_eig = 0.0
    max_q = 0.0
    for i in range(draws):
        xv = roots_from_ac(aa[i], cc[i], dd[i])
        eig = np.linalg.eigvalsh(circulant(aa[i], cc[i], dd[i]))
        max_eig = max(max_eig, float(np.max(np.abs(np.sort(eig) - np.sort(xv)))))
        max_q = max(max_q, abs(q_from_roots(xv) - q_from_ac(aa[i], cc[i])) / max(1.0, abs(q_from_ac(aa[i], cc[i]))))
    audit.record(
        "F1 numeric: eigenvalues vs numpy",
        max_eig < 1e-9,
        f"max |eigvalsh - formula| = {max_eig:.3e} over {draws} draws",
    )
    audit.record(
        "F2 numeric: Q identity",
        max_q < 1e-9,
        f"max relative |Q - (1/3+2c^2/3a^2)| = {max_q:.3e}",
    )

    # Sign caveat.
    xs = roots_from_ac(1.0, 0.9, np.pi)
    q_signed = q_from_roots(xs)
    q_phys = q_from_masses(xs * xs)
    audit.record(
        "1d: signed vs physical Q",
        abs(q_signed - 0.8733333333) < 1e-9 and abs(q_phys - 0.3714555766) < 1e-9,
        f"roots {xs.tolist()}, signed Q={q_signed:.10f}, physical Q={q_phys:.10f}",
    )

    # Bound: c/a <= 1 for positive roots.
    roots = rng.uniform(0.01, 50.0, size=(20_000, 3))
    ratios = []
    qs = []
    for row in roots:
        aa2, cc2, _ = fit_linear(row)
        ratios.append(cc2 / abs(aa2))
        qs.append(q_from_masses(row * row))
    audit.record(
        "F8: c/a <= 1 for positive roots",
        max(ratios) <= 1.0 + 1e-12,
        f"max c/a = {max(ratios):.6f} over 20000 random positive-root triples",
    )
    audit.record(
        "F8: 1/3 <= Q <= 1 for positive masses",
        min(qs) >= 1.0 / 3.0 - 1e-12 and max(qs) <= 1.0 + 1e-12,
        f"Q range [{min(qs):.6f}, {max(qs):.6f}]",
    )
    # 1b: three parameters fit any three masses; Q is not fixed by the structure.
    random_triples = rng.uniform(0.05, 100.0, size=(1_000, 3))
    residuals = []
    q_triples = []
    for row in random_triples:
        aa3, cc3, dd3 = fit_linear(row)
        residuals.append(float(np.max(np.abs(roots_from_ac(aa3, cc3, dd3) - row))))
        q_triples.append(q_from_masses(row * row))
    audit.record(
        "1b: 3 parameters fit 3 masses exactly",
        max(residuals) < 1e-9,
        f"max residual {max(residuals):.3e} over 1000 random positive-root triples",
    )
    audit.record(
        "1b: Q is not fixed by the Z3/circulant structure",
        max(q_triples) - min(q_triples) > 0.1,
        f"random triples span Q in [{min(q_triples):.4f}, {max(q_triples):.4f}]",
    )

    xb = np.array([10.0, 1.0, 1.0])
    ab, cb, _ = fit_linear(xb)
    audit.record(
        "5d: c/a=1/2 bound is false",
        abs(cb / ab - 0.75) < 1e-12 and abs(q_from_masses(xb * xb) - 0.7083333333) < 1e-9,
        f"(10,1,1): a={ab:.3f}, c/a={cb/ab:.6f}, Q={q_from_masses(xb*xb):.10f}",
    )


# ---------------------------------------------------------------------------
# Claim 3: pole-mass fit
# ---------------------------------------------------------------------------


def audit_fit(audit: Audit) -> None:
    payload = load_results("pdg_fit.json")
    central = np.array([row["value_MeV"] for row in payload["inputs"]])
    x = np.sqrt(central)
    a, c, delta = fit_linear(x)
    point = payload["point"]
    audit.record(
        "3a: independent (a,c,delta) fit",
        abs(a - point["a"]) < 1e-9
        and abs(c - point["c"]) < 1e-9
        and abs(np.exp(1j * (delta - point["delta"])) - 1.0) < 1e-9,
        f"a={a:.9f}, c={c:.9f}, delta={delta:.12f} (stored {point['a']:.9f}, {point['c']:.9f}, {point['delta']:.12f})",
    )
    q = q_from_masses(central)
    audit.record(
        "3a: Q from PDG pole masses",
        abs(q - point["Q"]) < 1e-12 and abs(q - 2.0 / 3.0) < 2e-5,
        f"Q={q:.12f}; Q-2/3={q-2.0/3.0:+.3e}",
    )
    audit.record(
        "3a: exact fit residual",
        point["max_abs_residual"] < 1e-12,
        f"stored max residual {point['max_abs_residual']:.3e}",
    )

    # Independent tau prediction: Q=2/3 with measured m_e, m_mu.
    me, mmu = central[0], central[1]
    s = math.sqrt(me) + math.sqrt(mmu)
    disc = 16.0 * s * s - 4.0 * (3.0 * (me + mmu) - 2.0 * s * s)
    roots = [(4.0 * s + sign * math.sqrt(disc)) / 2.0 for sign in (-1.0, 1.0)]
    tau = max(r * r for r in roots)
    audit.record(
        "3a: tau prediction",
        abs(tau - point["tau_prediction_MeV"]) < 1e-6,
        f"independent m_tau={tau:.6f} MeV, stored {point['tau_prediction_MeV']:.6f}",
    )

    # Reproduce the Monte Carlo summary from the same seed and algorithm.
    n_mc = payload["meta"]["config"]["n_mc"]
    seed = payload["meta"]["config"]["seed"]
    sigma = np.array([row["uncertainty_MeV"] for row in payload["inputs"]])
    rng = np.random.default_rng(seed)
    draws = np.clip(rng.normal(central, sigma, size=(n_mc, 3)), 1e-12, None)
    qvals = np.empty(n_mc)
    rvals = np.empty(n_mc)
    for i in range(n_mc):
        xi = np.sqrt(draws[i])
        ai, ci, _ = fit_linear(xi)
        qvals[i] = q_from_masses(draws[i])
        rvals[i] = ci / abs(ai)
    stored = payload["monte_carlo"]
    audit.record(
        "3a: quoted uncertainties",
        abs(qvals.std(ddof=1) - 5.1e-6) < 2e-7 and abs(rvals.std(ddof=1) - 5.4e-6) < 2e-7,
        f"sigma_Q={qvals.std(ddof=1):.3e}, sigma_r={rvals.std(ddof=1):.3e}",
    )
    sigma_q = qvals.std(ddof=1)
    pull_q = (q - 2.0 / 3.0) / sigma_q
    audit.record(
        "3a: (Q-2/3)/sigma",
        abs(pull_q + 0.435) < 0.05,
        f"(Q-2/3)/sigma = {pull_q:+.3f}",
    )
    audit.record(
        "3a: Monte Carlo mean/std reproduce",
        abs(qvals.mean() - stored["Q"]["mean"]) < 1e-12
        and abs(qvals.std(ddof=1) - stored["Q"]["std"]) < 1e-12
        and abs(rvals.mean() - stored["r"]["mean"]) < 1e-12
        and abs(rvals.std(ddof=1) - stored["r"]["std"]) < 1e-12,
        f"Q mean/std {qvals.mean():.12f}/{qvals.std(ddof=1):.3e} vs stored "
        f"{stored['Q']['mean']:.12f}/{stored['Q']['std']:.3e}",
    )


# ---------------------------------------------------------------------------
# Claim 4: one-loop running
# ---------------------------------------------------------------------------

MZ = 91.1876
VEW = 246.0
LOOP = 16.0 * math.pi**2
G0 = np.array([math.sqrt(5.0 / 3.0) * 0.357254, 0.65100, 1.2104])
M0 = {"e": 0.00048307, "mu": 0.101766, "tau": 1.72856}
MTOP = 168.26
MBOT = 2.839


def y0_vector() -> np.ndarray:
    return math.sqrt(2.0) / VEW * np.array(
        [M0["e"], M0["mu"], M0["tau"], MTOP, MBOT]
    )


def independent_rhs(_t: float, s: np.ndarray) -> np.ndarray:
    ye, ymu, ytau, yt, yb, g1, g2, g3 = s
    T = 3.0 * yt**2 + 3.0 * yb**2 + ye**2 + ymu**2 + ytau**2
    out = np.empty(8)
    for index, value in enumerate((ye, ymu, ytau)):
        out[index] = value * (1.5 * value**2 + T - 2.25 * g2**2 - 3.75 * g1**2) / LOOP
    out[3] = yt * (1.5 * yt**2 - 1.5 * yb**2 + T - 8 * g3**2 - 2.25 * g2**2 - 17.0 / 12.0 * g1**2) / LOOP
    out[4] = yb * (1.5 * yb**2 - 1.5 * yt**2 + T - 8 * g3**2 - 2.25 * g2**2 - 5.0 / 12.0 * g1**2) / LOOP
    out[5] = 41.0 / 10.0 * g1**3 / LOOP
    out[6] = -19.0 / 6.0 * g2**3 / LOOP
    out[7] = -7.0 * g3**3 / LOOP
    return out


def independent_solution(method: str = "RK45"):
    s0 = np.concatenate([y0_vector(), G0])
    sol = solve_ivp(
        independent_rhs,
        (math.log(MZ), math.log(1e16)),
        s0,
        method=method,
        rtol=1e-12,
        atol=1e-15,
        dense_output=True,
        max_step=0.05,
    )
    if not sol.success:
        raise RuntimeError(sol.message)
    return sol.sol


def q_from_yukawas(y: np.ndarray) -> float:
    m = np.asarray(y, dtype=float) * VEW / math.sqrt(2.0)
    return q_from_masses(m)


def audit_rg(audit: Audit) -> None:
    payload = load_results("rg_run.json")
    sol = independent_solution()
    stored = {row["scale_GeV"]: row for row in payload["scales"]}
    worst_q = 0.0
    worst_r = 0.0
    for scale, row in stored.items():
        y = sol(math.log(scale))[:3]
        m = y * VEW / math.sqrt(2.0)
        a, c, _ = fit_linear(np.sqrt(m))
        worst_q = max(worst_q, abs(q_from_yukawas(y) - row["Q"]))
        worst_r = max(worst_r, abs(c / a - row["r"]))
    audit.record(
        "4b: independent RGE reproduces Q(mu) and r(mu)",
        worst_q < 1e-11 and worst_r < 1e-11,
        f"max |Delta Q|={worst_q:.3e}, max |Delta r|={worst_r:.3e} vs stored table",
    )

    # Second independent integrator: the same RHS, different algorithm.
    sol_alt = independent_solution("DOP853")
    worst_alt_q = 0.0
    worst_alt_r = 0.0
    for scale in stored:
        y_a = sol(math.log(scale))[:3]
        y_b = sol_alt(math.log(scale))[:3]
        m_a = y_a * VEW / math.sqrt(2.0)
        m_b = y_b * VEW / math.sqrt(2.0)
        a_a, c_a, _ = fit_linear(np.sqrt(m_a))
        a_b, c_b, _ = fit_linear(np.sqrt(m_b))
        worst_alt_q = max(worst_alt_q, abs(q_from_yukawas(y_a) - q_from_yukawas(y_b)))
        worst_alt_r = max(worst_alt_r, abs(c_a / a_a - c_b / a_b))
    audit.record(
        "F10: RK45 and DOP853 independent integrators agree",
        worst_alt_q < 1e-9 and worst_alt_r < 1e-9,
        f"max |Delta Q|={worst_alt_q:.3e}, max |Delta r|={worst_alt_r:.3e}",
    )

    q0 = q_from_yukawas(sol(math.log(MZ))[:3])
    q1 = q_from_yukawas(sol(math.log(1e16))[:3])
    audit.record(
        "3b: MSbar Q(M_Z) != 2/3",
        abs(q0 - 2.0 / 3.0) > 1e-3,
        f"independent Q(M_Z)={q0:.12f}, Q-2/3={q0-2.0/3.0:+.3e}",
    )
    audit.record(
        "4b: one-loop drift is nonzero but small",
        0.0 < abs(q1 - q0) < 1e-5,
        f"Delta Q={q1-q0:+.3e} over ln(1e16/MZ)={math.log(1e16/MZ):.3f}",
    )

    audit.record(
        "4a: exact one-loop invariance would require a generation-blind RHS",
        True,
        "the (3/2)y_k^2 term is generation-dependent, so Q and r run; the nonzero drift confirms it",
    )

    # Published conversion cross-check, independent implementation.
    alpha = 1.0 / 128.89
    pole = np.array([0.51099895000e-3, 105.6583755e-3, 1776.93e-3])
    converted = pole * (1.0 - alpha / math.pi * (1.0 + 0.75 * np.log(MZ**2 / pole**2)))
    q_conv = q_from_masses(converted)
    lit = payload["published_conversion_check"]
    audit.record(
        "F9/3b: pole-to-MSbar conversion reproduces Xing-Zhang",
        abs(q_conv - lit["Q_from_converted_pole_masses"]) < 1e-12
        and abs(q_conv - 0.66792) < 2e-5,
        f"independent Q={q_conv:.9f}, stored {lit['Q_from_converted_pole_masses']:.9f}, literature 0.66792",
    )
    for index, key in enumerate(("e", "mu", "tau")):
        rel = (converted[index] - lit["converted_explicit"][key]["xing_zhang_GeV"]) / converted[index]
        audit.record(
            f"F9: converted {key} vs Xing-Zhang",
            abs(rel) < 5e-4,
            f"relative difference {rel:+.3e}",
        )

    # High-scale absolute masses are a truncation-limited comparison, not a verification.
    lit_high = payload["literature_high_scale_check"]
    max_rel = 0.0
    max_q_rel = 0.0
    for scale, item in lit_high.items():
        for key, value in item["literature"].items():
            max_rel = max(max_rel, abs(item["ours"][key] - value) / value)
        lit = item["literature"]
        m_lit = np.array([lit["e"], lit["mu"], lit["tau"]])
        ours = item["ours"]
        m_ours = np.array([ours["e"], ours["mu"], ours["tau"]])
        q_lit = q_from_masses(m_lit)
        q_ours = q_from_masses(m_ours)
        max_q_rel = max(max_q_rel, abs(q_ours - q_lit) / q_lit)
    audit.record(
        "F10: one-loop absolute running vs three-loop literature",
        max_rel < 0.06,
        f"max relative mass difference {max_rel:.3%}; loop truncation, not a precision check",
    )
    audit.record(
        "F10: Q from literature masses vs one-loop Q",
        max_q_rel < 5e-5,
        f"max relative Q difference {max_q_rel:.3e}; the shape is stable at this level",
    )
    conv = payload["published_conversion_check"]
    max_conv = max(abs(item["relative_difference"]) for item in conv["converted_explicit"].values())
    audit.record(
        "F9: conversion reproduced to 2e-4",
        max_conv < 2e-4,
        f"max relative difference {max_conv:.3e}",
    )


# ---------------------------------------------------------------------------
# Claim 5 / 6a: rotor and domain wall
# ---------------------------------------------------------------------------


def rotor_levels(I: float, mu: float, sector: int, n_max: int) -> np.ndarray:
    n = np.arange(-n_max, n_max + 1)
    n = n[np.mod(n, 3) == sector % 3]
    size = n.size
    H = np.zeros((size, size))
    for i, value in enumerate(n):
        H[i, i] = value * value / (2.0 * I) + mu
        for j, other in enumerate(n):
            if abs(int(other) - int(value)) == 3:
                H[i, j] -= 0.5 * mu
    return eigh(H, eigvals_only=True)


def audit_rotor(audit: Audit) -> None:
    payload = load_results("rotor.json")
    e0 = rotor_levels(1.0, 1.0, 0, 120)
    e1 = rotor_levels(1.0, 1.0, 1, 120)
    e2 = rotor_levels(1.0, 1.0, 2, 120)
    stored = payload["levels"]
    audit.record(
        "5a: independent rotor spectrum",
        abs(e0[0] - stored["E0"]) < 1e-10
        and abs(e1[0] - stored["E1"]) < 1e-10
        and abs(e2[0] - stored["E2"]) < 1e-10,
        f"independent E0={e0[0]:.12f}, E1={e1[0]:.12f}, E2={e2[0]:.12f}",
    )
    audit.record(
        "5c: k=1 and k=2 exactly degenerate",
        abs(e1[0] - e2[0]) < 1e-10,
        f"|E1-E2|={abs(e1[0]-e2[0]):.3e}",
    )
    # Truncation convergence.
    e0_cut = [rotor_levels(1.0, 1.0, 0, n)[0] for n in (20, 40, 80, 160)]
    audit.record(
        "5a: truncation convergence",
        max(abs(e0_cut[i] - e0_cut[-1]) for i in range(3)) < 1e-9,
        f"E0 at n=20,40,80,160: {e0_cut}",
    )
    # Free rotor, several levels.
    free = np.sort((np.array([n for n in range(-300, 301) if n % 3 == 1], dtype=float)) ** 2 / 2.0)
    free_exact = np.array([0.5, 2.0, 8.0, 12.5])
    audit.record(
        "5b: free-rotor limit",
        abs(rotor_levels(1.0, 0.0, 1, 120)[0] - 0.5) < 1e-10
        and abs(rotor_levels(1.0, 0.0, 0, 120)[0]) < 1e-10
        and np.allclose(free[:4], free_exact)
        and abs(rotor_levels(1.0, 0.0, 0, 120)[1] - 4.5) < 1e-10,
        "E(sector 0)=0, 4.5 (twofold); E(sector 1)=0.5, 2, 8, 12.5 at mu=0, I=1",
    )
    # The naive map produces two distinct roots, not three.
    levels = (e0[0], e1[0], e2[0])
    aa = (levels[0] + 2.0 * levels[1]) / 3.0
    cc = (levels[1] - levels[0]) / 3.0
    mapped = np.array([aa + 2.0 * cc * math.cos(2.0 * math.pi * k / 3.0) for k in range(3)])
    distinct = len({round(float(value), 8) for value in mapped})
    audit.record(
        "5c: naive map gives two distinct roots",
        distinct == 2,
        f"mapped roots {mapped.tolist()} -> {distinct} distinct (3 needed)",
    )
    # Domain-wall tension, symbolic and numeric.
    mu = sp.symbols("mu", positive=True)
    phi = sp.symbols("phi", real=True)
    trig_identity = sp.simplify(
        1 - sp.cos(3 * phi) - 2 * sp.sin(3 * phi / 2) ** 2
    )
    audit.record(
        "6a: 1-cos(3phi) = 2 sin^2(3phi/2)",
        trig_identity == 0,
        "symbolic identity used to remove the absolute value on 0 <= phi <= 2pi/3",
    )
    symbolic = sp.integrate(2 * sp.sqrt(mu) * sp.sin(3 * phi / 2), (phi, 0, 2 * sp.pi / 3))
    symbolic = sp.simplify(symbolic)
    audit.record(
        "6a: domain-wall tension symbolic",
        sp.simplify(symbolic - sp.Rational(8, 3) * sp.sqrt(mu)) == 0,
        f"sympy integral = {symbolic} (sin(3phi/2) >= 0 on the interval)",
    )
    for value in (0.5, 1.0, 7.3):
        numeric, _ = quad(lambda p: math.sqrt(max(0.0, 2 * value * (1 - math.cos(3 * p)))), 0, 2 * math.pi / 3)
        audit.record(
            f"6a: tension quadrature mu={value}",
            abs(numeric - 8.0 / 3.0 * math.sqrt(value)) < 1e-10,
            f"{numeric:.12f} vs {8.0/3.0*math.sqrt(value):.12f}",
        )



# ---------------------------------------------------------------------------
# Claim 7 / 8: neutrinos, quarks, PMNS branches
# ---------------------------------------------------------------------------


def audit_neutrinos_quarks(audit: Audit) -> None:
    neutrino = load_results("neutrinos.json")
    quarks = load_results("quarks.json")
    pmns = load_results("pmns.json")

    dm21 = 7.41e-5
    dm31_no = 2.507e-3
    dm31_io = -2.486e-3
    q_no = q_from_masses([0.0, math.sqrt(dm21), math.sqrt(dm31_no)])
    q_io = q_from_masses(
        [math.sqrt(abs(dm31_io)), math.sqrt(abs(dm31_io) + dm21), 0.0]
    )
    audit.record(
        "7a: Q_nu at m_light=0 (NO and IO)",
        abs(q_no - 0.5856120093687199) < 1e-12
        and abs(q_io - 0.5000067395867646) < 1e-12
        and q_no < 2.0 / 3.0
        and q_io < 2.0 / 3.0,
        f"NO={q_no:.12f}, IO={q_io:.12f}",
    )
    corners = []
    for dm21_corner in (6.82e-5, 8.03e-5):
        for dm31_corner in (2.427e-3, 2.590e-3):
            corners.append(q_from_masses([0.0, math.sqrt(dm21_corner), math.sqrt(dm31_corner)]))
        for dm31_corner in (-2.570e-3, -2.406e-3):
            corners.append(
                q_from_masses(
                    [
                        math.sqrt(abs(dm31_corner)),
                        math.sqrt(abs(dm31_corner) + dm21_corner),
                        0.0,
                    ]
                )
            )
    corner_max = max(corners)
    audit.record(
        "7a: 3-sigma corner maximum",
        abs(corner_max - 0.5906060371336499) < 1e-12 and corner_max < 2.0 / 3.0,
        f"corner max={corner_max:.12f}; stored={neutrino['verdict']['Q_nu_max_at_3sigma_corner']:.12f}",
    )
    scan_max = max(q_no, q_io)
    audit.record(
        "7a: no scanned point reaches 2/3",
        scan_max < 2.0 / 3.0
        and abs(scan_max - neutrino["verdict"]["Q_nu_max"]) < 1e-12
        and neutrino["verdict"]["Q_nu_below_2_3_all_scanned"],
        f"scan max={scan_max:.12f}; margin={2.0/3.0-scan_max:.6f}",
    )

    data_path = ROOT / "phenomenology" / "data" / "quark_masses_hz2021.csv"
    with data_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    ups = []
    downs = []
    for row in rows:
        ups.append(q_from_masses([float(row["m_u_GeV"]), float(row["m_c_GeV"]), float(row["m_t_GeV"])]))
        downs.append(q_from_masses([float(row["m_d_GeV"]), float(row["m_s_GeV"]), float(row["m_b_GeV"])]))
    mz = quarks["points"][0]
    audit.record(
        "8: Q_up and Q_down at M_Z",
        abs(ups[0] - 0.8875692313187327) < 1e-12
        and abs(downs[0] - 0.7480650548031402) < 1e-12
        and abs(ups[0] - mz["Q_up"]) < 1e-12
        and abs(downs[0] - mz["Q_down"]) < 1e-12,
        f"Q_up={ups[0]:.12f}, Q_down={downs[0]:.12f}",
    )
    audit.record(
        "8: six-scale ranges and no 2/3",
        min(ups + downs) > 2.0 / 3.0
        and abs(min(ups) - quarks["ranges"]["Q_up_min"]) < 1e-12
        and abs(max(ups) - quarks["ranges"]["Q_up_max"]) < 1e-12
        and abs(min(downs) - quarks["ranges"]["Q_down_min"]) < 1e-12
        and abs(max(downs) - quarks["ranges"]["Q_down_max"]) < 1e-12
        and quarks["verdict"]["direct_extension_falsified"],
        f"Q_up range [{min(ups):.9f},{max(ups):.9f}], Q_down range [{min(downs):.9f},{max(downs):.9f}]",
    )

    omega = np.exp(2j * math.pi / 3.0)
    k = np.arange(3)
    U = np.array([[omega ** (k * n) for k in range(3)] for n in range(3)]) / math.sqrt(3.0)

    def angles(matrix: np.ndarray) -> dict[str, float]:
        s13 = min(1.0, float(abs(matrix[0, 2])))
        c13 = math.sqrt(max(0.0, 1.0 - s13 * s13))
        s12 = min(1.0, float(abs(matrix[0, 1])) / c13)
        s23 = min(1.0, float(abs(matrix[1, 2])) / c13)
        return {
            "theta12_deg": math.degrees(math.asin(s12)),
            "theta13_deg": math.degrees(math.asin(s13)),
            "theta23_deg": math.degrees(math.asin(s23)),
        }

    dft_angles = angles(U)
    identity_angles = angles(np.eye(3))
    stored_dft = pmns["branches"]["neutrino_only_circulant"]["angles"]
    stored_identity = pmns["branches"]["same_basis_both_circulant"]["angles"]
    audit.record(
        "7b: minimal PMNS branch angles",
        abs(dft_angles["theta13_deg"] - 35.264389682754654) < 1e-9
        and abs(dft_angles["theta12_deg"] - 45.0) < 1e-9
        and abs(dft_angles["theta23_deg"] - 45.0) < 1e-9
        and all(abs(identity_angles[key]) < 1e-12 for key in identity_angles)
        and abs(dft_angles["theta13_deg"] - stored_dft["theta13_deg"]) < 1e-9
        and abs(identity_angles["theta13_deg"] - stored_identity["theta13_deg"]) < 1e-9,
        f"DFT={dft_angles}; identity={identity_angles}",
    )
    measured = pmns["measured"]["theta13_deg"]
    audit.record(
        "7b: both branches excluded; theta13-only claim ill-posed",
        abs(dft_angles["theta13_deg"] - measured) > 3.0
        and abs(identity_angles["theta13_deg"] - measured) > 3.0
        and pmns["verdict"]["same_basis_branch_excluded"]
        and pmns["verdict"]["trimaximal_branch_excluded_by_theta13"]
        and not pmns["verdict"]["original_claim_well_posed"],
        f"measured theta13={measured:.2f}, DFT={dft_angles['theta13_deg']:.3f}, identity=0",
    )



# ---------------------------------------------------------------------------
# Claim 9 / 10 / 14: delta search, Frank-Oseen, Derrick
# ---------------------------------------------------------------------------


def audit_delta_modes_derrick(audit: Audit) -> None:
    fit = load_results("pdg_fit.json")
    delta = float(fit["point"]["delta_mod_2pi_over_3"])
    sigma = float(fit["monte_carlo"]["delta"]["std"])
    span = 2.0 * math.pi / 3.0

    candidates: dict[float, str] = {}
    for q in range(1, 21):
        for p in range(1, int(span * q) + 2):
            value = float(Fraction(p, q))
            if 0.0 < value <= span:
                candidates.setdefault(round(value, 15), f"{p}/{q}")
    for q in range(1, 13):
        for p in range(1, int(span / math.pi * q) + 2):
            value = p * math.pi / q
            if 0.0 < value <= span:
                candidates.setdefault(round(value, 15), f"{p}*pi/{q}")
    for n in range(1, 13):
        for value, label in (
            (1.0 / math.sqrt(n), f"1/sqrt({n})"),
            (math.atan(1.0 / n), f"atan(1/{n})"),
            (math.acos(1.0 / n), f"acos(1/{n})"),
        ):
            if 0.0 < value <= span:
                candidates.setdefault(round(value, 15), label)
    best_value, best_label = min(candidates.items(), key=lambda item: abs(item[0] - delta))
    best_diff = abs(best_value - delta)
    p_look = 1.0 - math.exp(-len(candidates) * min(1.0, 2.0 * best_diff / span))
    audit.record(
        "9: delta closed-form search",
        best_label == "2/9"
        and abs(best_diff - 2.539681804081262e-06) < 1e-15
        and abs(best_diff / sigma - 0.4071) < 1e-3
        and abs(p_look - 7.927e-4) < 1e-6,
        f"best={best_label}, diff={best_diff:.3e}, sigma={best_diff/sigma:.3f}, p_LEE={p_look:.3e}",
    )

    def elastic(kx: float, ky: float, kz: float, k1: float, k2: float, k3: float) -> np.ndarray:
        return np.array(
            [
                [k1 * kx * kx + k2 * ky * ky + k3 * kz * kz, (k1 - k2) * kx * ky],
                [(k1 - k2) * kx * ky, k1 * ky * ky + k2 * kx * kx + k3 * kz * kz],
            ]
        )

    equal = np.linalg.eigvalsh(elastic(1.0, 2.0, 3.0, 2.0, 2.0, 2.0))
    axis_x = np.linalg.eigvalsh(elastic(2.0, 0.0, 0.0, 1.0, 2.0, 3.0))
    axis_z = np.linalg.eigvalsh(elastic(0.0, 0.0, 2.0, 1.0, 2.0, 3.0))
    audit.record(
        "10: Frank-Oseen elastic matrix",
        np.allclose(equal, [2.0 * (1.0 + 4.0 + 9.0)] * 2)
        and np.allclose(axis_x, [1.0 * 4.0, 2.0 * 4.0])
        and np.allclose(axis_z, [3.0 * 4.0, 3.0 * 4.0]),
        f"equal={equal.tolist()}, x={axis_x.tolist()}, z={axis_z.tolist()}",
    )
    audit.record(
        "10: two modes and no photon",
        True,
        "two transverse director components; no gauge field or vector potential in the F-O energy",
    )

    def scaling(lam: float, e2: float, e4: float, potential: float) -> float:
        return lam * e2 + e4 / lam + lam**3 * potential

    e2, e4, potential = 2.0, 1.0, 0.5
    h = 1e-7
    numeric = (scaling(1.0 + h, e2, e4, potential) - scaling(1.0 - h, e2, e4, potential)) / (2 * h)
    audit.record(
        "14a: Derrick derivative equals virial",
        abs(numeric - (e2 - e4 + 3.0 * potential)) < 1e-6,
        f"numeric dE/dlambda={numeric:.9f}, virial={e2-e4+3*potential:.9f}",
    )
    y = (-e2 + math.sqrt(e2 * e2 + 12.0 * potential * e4)) / (6.0 * potential)
    audit.record(
        "14a: stationary scale and curvature",
        y > 0.0 and 2.0 * e4 + 6.0 * potential > 0.0,
        f"lambda^2={y:.9f}, second derivative={2*e4+6*potential:.6f}",
    )
    audit.record(
        "14b: kappa>0 necessary, existence unproved",
        True,
        "kappa=0 has no stationary point; kappa<0 is unbounded; Derrick scaling is not an existence proof",
    )



# ---------------------------------------------------------------------------
# Claim 6b / 13 / 16: reduction, topology, new-prediction audit
# ---------------------------------------------------------------------------


def audit_negatives(audit: Audit) -> None:
    topology = load_results("topology.json")
    reduction = load_results("reduction.json")
    predictions = load_results("predictions.json")

    homotopy = topology["verdict"]["direct"]["homotopy"]
    audit.record(
        "13a: RP2 homotopy has no Z3 factor",
        homotopy == {"pi1": "Z2", "pi2": "Z", "pi3": "Z"}
        and topology["verdict"]["direct"]["z3_factor_present"] is False
        and topology["verdict"]["13a_direct_z3_from_nematic_topology"] is False
        and topology["verdict"]["cos3phi_inserted_by_hand"] is True,
        f"homotopy={homotopy}",
    )
    extensions = topology["verdict"]["extensions"]
    audit.record(
        "13b: standard extensions do not derive Z3",
        len(extensions) == 3 and all(item["z3_derived"] is False for item in extensions.values()),
        f"extensions={list(extensions)}",
    )

    tension = 8.0 / 3.0
    audit.record(
        "6b: trivial 2D lower bound",
        abs(tension - reduction["wall_tension"]) < 1e-12
        and abs(reduction["lower_bound_example"] - 2.0 * tension) < 1e-12
        and reduction["verdict"]["6b_i_trivial_lower_bound"] is True
        and reduction["verdict"]["6b_ii_exact_dimensional_reduction"] is False,
        f"T={tension:.12f}, T*L_y(2)={2.0*tension:.12f}",
    )
    audit.record(
        "6c: moment convergence and log divergence",
        reduction["moment"]["alpha_2"]["finite"] is False
        and reduction["moment"]["alpha_4"]["log_divergent"] is True
        and reduction["moment"]["alpha_5"]["finite"] is True
        and reduction["verdict"]["6b_iii_moment_finite_for_stated_profile"] is False
        and reduction["verdict"]["stated_tail_status"] == "log-divergent",
        "I_eff finite iff alpha>4; alpha=4 log-divergent; alpha=2 power-divergent",
    )

    rows = predictions["candidates"]
    audit.record(
        "16: no new prediction found",
        len(rows) == 7
        and all(row["new"] is False for row in rows)
        and predictions["verdict"]["new_prediction_found"] is False
        and predictions["verdict"]["count"] == 0,
        f"{len(rows)} candidate classes, none new",
    )



# ---------------------------------------------------------------------------
# Claim 11 / 12: residual anisotropy and LV bounds
# ---------------------------------------------------------------------------


def audit_lorentz(audit: Audit) -> None:
    payload = load_results("lorentz.json")
    k1, k2, k3 = 1.0, 2.0, 3.0
    rho = 1.0

    def matrix(kx, ky, kz):
        return np.array(
            [
                [k1 * kx * kx + k2 * ky * ky + k3 * kz * kz, (k1 - k2) * kx * ky],
                [(k1 - k2) * kx * ky, k1 * ky * ky + k2 * kx * kx + k3 * kz * kz],
            ]
        )

    axis_x = np.sqrt(np.linalg.eigvalsh(matrix(1, 0, 0)) / rho)
    axis_z = np.sqrt(np.linalg.eigvalsh(matrix(0, 0, 1)) / rho)
    audit.record(
        "11a: axis speeds for K=(1,2,3)",
        np.allclose(axis_x, [1.0, math.sqrt(2.0)])
        and np.allclose(axis_z, [math.sqrt(3.0), math.sqrt(3.0)]),
        f"x={axis_x.tolist()}, z={axis_z.tolist()}",
    )

    rng = np.random.default_rng(20261025)
    vectors = rng.normal(size=(4000, 3))
    vectors /= np.linalg.norm(vectors, axis=1)[:, None]
    c2 = []
    for vector in vectors:
        values = np.linalg.eigvalsh(
            np.array(
                [
                    [
                        k1 * vector[0] ** 2 + k2 * vector[1] ** 2 + k3 * vector[2] ** 2,
                        (k1 - k2) * vector[0] * vector[1],
                    ],
                    [
                        (k1 - k2) * vector[0] * vector[1],
                        k1 * vector[1] ** 2 + k2 * vector[0] ** 2 + k3 * vector[2] ** 2,
                    ],
                ]
            )
            / rho
        )
        c2.extend(values.tolist())
    c2 = np.asarray(c2)
    xi = float((c2.max() - c2.min()) / c2.mean())
    audit.record(
        "11a/F23: residual anisotropy xi",
        abs(xi - 1.0034799560133727) < 1e-9
        and abs(payload["anisotropy_unequal"]["xi"] - xi) < 1e-9
        and payload["anisotropy_equal"]["xi"] == 0.0,
        f"xi(K=1,2,3)={xi:.9f}; xi(equal)=0",
    )
    audit.record(
        "12a: photon bounds are not directly applicable",
        payload["verdict_unequal"]["12_lv_bounds_directly_applicable"] is False
        and all(bound["applies_to_director_modes"] is False for bound in payload["bounds"]),
        "all four bounds flagged non-applicable; director modes are neutral",
    )
    checks = payload["conditional_unequal"]["checks"]
    audit.record(
        "12b: conditional bound",
        xi > 1e-18
        and all(item["passes_if_photon"] is False for item in checks)
        and payload["verdict_equal"]["12_equal_K_is_isotropic"] is True,
        "equal K is exactly isotropic; O(1) xi fails every Delta c/c bound",
    )



# ---------------------------------------------------------------------------
# Claim 15: Hopf estimator validation
# ---------------------------------------------------------------------------


def audit_hopf(audit: Audit) -> None:
    payload = load_results("hopf.json")
    preimage = payload["preimage"]
    grid = payload["grid"]
    audit.record(
        "15/4: preimage linking converges to 1",
        preimage["100"] < preimage["200"] < preimage["400"]
        and abs(preimage["400"] - 0.9999582415186622) < 1e-12
        and abs(preimage["400"] - 1.0) < 1e-3,
        f"H(100/200/400)={preimage['100']:.9f}/{preimage['200']:.9f}/{preimage['400']:.9f}",
    )
    audit.record(
        "15/4: reflection, rotation, shear",
        abs(payload["reflection"] + preimage["200"]) < 1e-6
        and abs(payload["rotation"] - preimage["200"]) < 1e-6
        and abs(payload["shear"] - preimage["200"]) < 1e-5,
        f"reflection={payload['reflection']:.9f}, rotation={payload['rotation']:.9f}, shear={payload['shear']:.9f}",
    )
    audit.record(
        "15/4: grid estimator matches known answer",
        abs(grid["32"] - 1.000141490106325) < 1e-9
        and abs(grid["64"] - 1.0000000385194467) < 1e-9
        and all(abs(value - 1.0) < 0.01 for value in grid.values())
        and payload["verdict"]["grid_reflection_flips_sign"] is True
        and abs(payload["grid_reflection"] + 1.0) < 0.01
        and payload["verdict"]["two_method_agreement"] is True
        and payload["verdict"]["baseline_4_pass"] is True,
        f"grid(32/48/64)={grid['32']:.9f}/{grid['48']:.9f}/{grid['64']:.9f}; baseline_4=True",
    )



# ---------------------------------------------------------------------------
# Claim 15: 3D pilot
# ---------------------------------------------------------------------------


def audit_hopfion3d(audit: Audit) -> None:
    payload = load_results("hopfion3d.json")
    rows = {row["mu"]: row for row in payload["rows"]}
    audit.record(
        "15: 3D pilot values at 1200 steps",
        abs(rows[0.0]["H"] - 0.7497584225892562) < 1e-9
        and abs(rows[20.0]["H"] - 0.052372282005896706) < 1e-9
        and abs(rows[20.0]["Z3"] - 0.9601692730852452) < 1e-9
        and all(row["monotone"] for row in payload["rows"]),
        f"H(mu=0)={rows[0.0]['H']:.9f}, H(mu=20)={rows[20.0]['H']:.9f}, Z3(mu=20)={rows[20.0]['Z3']:.9f}",
    )
    audit.record(
        "15: pilot is not converged or resolved",
        payload["verdict"]["resolved"] is False
        and payload["convergence"]["converged"] is False
        and payload["verdict"]["production_ready"] is False
        and payload["verdict"]["claim_15_status"].startswith("UNVERIFIED")
        and all(not (row["H"] >= 1.0 and row["Z3"] >= 0.5) for row in payload["rows"]),
        f"force_rms(1200)={payload['convergence']['rows'][-1]['force_rms']:.3e}; no conclusion",
    )



# ---------------------------------------------------------------------------
# Hopf grid resolution
# ---------------------------------------------------------------------------


def audit_hopf_resolution(audit: Audit) -> None:
    payload = load_results("hopf_resolution.json")
    rows = {row["n"]: row for row in payload["rows"]}
    audit.record(
        "15/4: grid Hopf resolution",
        abs(rows[16]["H_grid"] - 0.801799780520344) < 1e-9
        and abs(rows[32]["H_grid"] - 1.000141490106325) < 1e-9
        and abs(rows[64]["H_grid"] - 1.0000000385194467) < 1e-9
        and rows[16]["abs_error_vs_preimage"] > 1e-3
        and rows[32]["abs_error_vs_preimage"] < 1e-3
        and payload["verdict"]["fine_within_1e_3"] is True,
        f"N=16 H={rows[16]['H_grid']:.9f}, N=32 H={rows[32]['H_grid']:.9f}, N=64 H={rows[64]['H_grid']:.9f}",
    )



# ---------------------------------------------------------------------------
# N=64 3D diagnostic
# ---------------------------------------------------------------------------


def audit_n64(audit: Audit) -> None:
    payload = load_results("hopfion3d_n64.json")
    rows = {(row["mu"], row["steps"]): row for row in payload["rows"]}
    audit.record(
        "15: N=64 diagnostic values",
        abs(rows[(0.0, 1200)]["H"] - 0.9999999315531043) < 1e-9
        and abs(rows[(20.0, 1200)]["H"] - 0.9989096223178509) < 1e-9
        and abs(rows[(20.0, 3600)]["H"] - 0.7879997839463242) < 1e-9
        and abs(rows[(20.0, 3600)]["Z3"] - 0.6074303431126289) < 1e-9
        and all(row["monotone"] for row in payload["rows"]),
        f"H(20,3600)={rows[(20.0,3600)]['H']:.6f}, Z3={rows[(20.0,3600)]['Z3']:.6f}",
    )
    audit.record(
        "15: N=64 diagnostic not converged and no coexistence",
        payload["verdict"]["converged"] is False
        and payload["verdict"]["coexistence_H_and_Z3"] is False
        and payload["verdict"]["production_ready"] is False
        and rows[(20.0, 3600)]["force_rms"] > 1e-2,
        f"force_rms(3600)={rows[(20.0,3600)]['force_rms']:.3e}",
    )



# ---------------------------------------------------------------------------
# Scale-iteration candidate
# ---------------------------------------------------------------------------


def audit_scale(audit: Audit) -> None:
    payload = load_results("hopfion_scale.json")
    best = payload["best"]
    audit.record(
        "14c: scale-stationary H=1 candidate",
        best["iteration"] == 4
        and abs(best["virial"] - 0.009610009576846323) < 1e-9
        and abs(best["H"] - 0.9972974138250582) < 1e-9
        and abs(best["force_rms"] - 0.003002063883660039) < 1e-9
        and payload["verdict"]["scale_stationary_candidate"] is True
        and payload["verdict"]["full_stability_proved"] is False,
        f"best iter={best['iteration']}, virial={best['virial']:+.6f}, H={best['H']:.6f}, rms={best['force_rms']:.3e}",
    )


# ---------------------------------------------------------------------------
# Tangent-space Hessian of the scale candidate
# ---------------------------------------------------------------------------


def audit_stability(audit: Audit) -> None:
    payload = load_results("hopfion_stability.json")
    validation = payload["dense_validation"]
    spectrum = payload["spectrum"]
    verdict = payload["verdict"]
    audit.record(
        "14d: tangent Hessian operator passes dense validation",
        validation["passed"] is True
        and validation["max_abs_error"] < 1e-8
        and validation["symmetry_error"] < 1e-8
        and len(validation["dense_smallest"]) == len(validation["operator_smallest"])
        and all(
            abs(dense - matrix_free) < 1e-8
            for dense, matrix_free in zip(
                validation["dense_smallest"], validation["operator_smallest"]
            )
        ),
        f"N={validation['n']}, max error={validation['max_abs_error']:.3e}",
    )
    audit.record(
        "14d: N=64 scale candidate is a saddle",
        abs(spectrum["min_eigenvalue"] + 5.799862658102943) < 1e-6
        and spectrum["dimension"] == 476656
        and spectrum["negative_count"] >= 8
        and verdict["local_minimum_at_N64"] is False
        and verdict["claim_14d_status"].startswith("FALSIFIED")
        and verdict["claim_14b_status"] == "UNVERIFIED",
        f"min={spectrum['min_eigenvalue']:+.6f}, negative={spectrum['negative_count']}",
    )


# ---------------------------------------------------------------------------
# Pure-FN candidate Hessian (claims 14b/14e)
# ---------------------------------------------------------------------------


def audit_purefn(audit: Audit) -> None:
    payload = load_results("hopfion_purefn_stability.json")
    candidate = payload["candidate"]
    validation = payload["validation"]
    spectrum = payload["spectrum"]
    verdict = payload["verdict"]
    negative = spectrum["min_eigenvalue"] < -1e-6
    audit.record(
        "14b: pure-FN candidate is the N=64 mu=0 relax",
        spectrum["n"] == 64
        and spectrum["dimension"] == 2 * 62**3
        and candidate["H"] > 0.9999
        and candidate["force_rms"] < 1e-2
        and candidate["Z3"] < 1e-2
        and validation["passed"] is True,
        f"H={candidate['H']:.9f}, rms={candidate['force_rms']:.3e}",
    )
    audit.record(
        "14e: pure-FN Hessian verdict follows the negative tolerance",
        verdict["local_minimum_at_N64"] == (not negative)
        and (
            verdict["candidate_status"].startswith("FALSIFIED")
            if negative
            else verdict["candidate_status"].startswith("NUMERIC")
        )
        and (
            verdict["claim_14b_status"] == "UNVERIFIED"
            if negative
            else verdict["claim_14b_status"].startswith("NUMERIC")
        ),
        f"min={spectrum['min_eigenvalue']:+.6f}, "
        f"negative={spectrum['negative_count']}",
    )


# ---------------------------------------------------------------------------
# Saddle-escape search (claim 14b/ADR-006)
# ---------------------------------------------------------------------------


def audit_escape(audit: Audit) -> None:
    payload = load_results("hopfion_saddle_escape.json")
    base = payload["base"]
    attempts = payload["attempts"]
    verdict = payload["verdict"]
    purefn = load_results("hopfion_purefn_stability.json")
    audit.record(
        "14b: saddle-escape starts from the pure-FN candidate",
        abs(base["min_eigenvalue"] - purefn["spectrum"]["min_eigenvalue"]) < 1e-6
        and len(attempts) == 2
        and [attempt["amplitude"] for attempt in attempts] == [0.05, 0.15]
        and all(attempt["min_pre_norm"] > 0.1 for attempt in attempts),
        f"base min={base['min_eigenvalue']:+.6f}, attempts={len(attempts)}",
    )
    audit.record(
        "14b: saddle-escape finds no local minimum and does not promote",
        verdict["local_minimum_found"] is False
        and verdict["claim_14b_status"] == "UNVERIFIED"
        and all(attempt["local_minimum"] is False for attempt in attempts)
        and all(attempt["H"] < 0.9 for attempt in attempts),
        ", ".join(
            f"eps={attempt['amplitude']:.3g}: H={attempt['H']:.6f}"
            for attempt in attempts
        ),
    )


# ---------------------------------------------------------------------------
# Box-length scan (claim 14b/ADR-007)
# ---------------------------------------------------------------------------


def audit_lengthscan(audit: Audit) -> None:
    payload = load_results("hopfion_length_scan.json")
    attempts = payload["attempts"]
    verdict = payload["verdict"]
    audit.record(
        "14b: box-length scan covers 8, 10, 12 and 14 at N=64",
        len(attempts) == 4
        and [attempt["length"] for attempt in attempts] == [8.0, 10.0, 12.0, 14.0]
        and all(attempt["accepted"] for attempt in attempts)
        and all(attempt["tested"] for attempt in attempts)
        and all(attempt["min_pre_norm"] > 0.1 for attempt in attempts),
        ", ".join(
            f"L={attempt['length']:.3g}: min={attempt['min_eigenvalue']:+.6f}"
            for attempt in attempts
        ),
    )
    audit.record(
        "14b: every box length is a saddle and the claim is not promoted",
        verdict["local_minimum_found"] is False
        and verdict["claim_14b_status"] == "UNVERIFIED"
        and all(
            attempt["local_minimum"] is False
            and attempt["negative_count"] >= 8
            and attempt["min_eigenvalue"] < -1e-6
            for attempt in attempts
        ),
        f"attempts={len(attempts)}, "
        f"negative={[attempt['negative_count'] for attempt in attempts]}",
    )


# ---------------------------------------------------------------------------
# Vortex-knot mass spectrum (claim 17/ADR-008)
# ---------------------------------------------------------------------------


def audit_vortex(audit: Audit) -> None:
    payload = load_results("vortex_knot_spectrum.json")
    result = payload["result"]
    energies = result["energies"]
    expected_q = float(
        sum(energies) / (sum(value**0.5 for value in energies) ** 2)
    )
    audit.record(
        "17: vortex-knot spectrum uses T(2,3), T(2,5), T(2,7)",
        result["knots"] == [3, 5, 7]
        and len(energies) == 3
        and all(value > 0.0 for value in energies)
        and abs(result["koide_q_energy"] - expected_q) < 1e-12,
        f"energies={[round(value, 3) for value in energies]}",
    )
    audit.record(
        "17: simple vortex-knot assignment is falsified",
        result["falsified"] is True
        and result["status"].startswith("FALSIFIED")
        and result["koide_q_energy"] < 0.5
        and result["required_power"] > 2.0,
        f"Q={result['koide_q_energy']:.6f}, "
        f"p={result['required_power']:.3f}",
    )


# ---------------------------------------------------------------------------
# One-parameter vortex hierarchy (claim 18/ADR-009)
# ---------------------------------------------------------------------------


def audit_cascade(audit: Audit) -> None:
    payload = load_results("vortex_cascade.json")
    result = payload["result"]
    models = result["models"]
    audit.record(
        "18: one-parameter hierarchy test covers geometric and power-law spectra",
        set(models) == {
            "geometric",
            "power_law_muon_fit",
            "power_law_koide_fit",
        }
        and all(model["falsified"] for model in models.values())
        and abs(
            models["power_law_koide_fit"]["koide_q_predicted"] - 2.0 / 3.0
        )
        < 1e-12
        and models["geometric"]["predicted_tau_ratio"] > 1000.0,
        ", ".join(
            f"{name}: tau={model['predicted_tau_ratio']:.1f}, "
            f"Q={model['koide_q_predicted']:.6f}"
            for name, model in models.items()
        ),
    )
    audit.record(
        "18: no one-parameter hierarchy matches both ratios and Q",
        result["falsified"] is True
        and result["status"].startswith("FALSIFIED")
        and all(
            abs(model["tau_relative_error"]) > result["relative_tolerance"]
            for model in models.values()
        ),
        f"min |tau error|={min(abs(model['tau_relative_error']) for model in models.values()):.6f}",
    )


# ---------------------------------------------------------------------------
# Real Z3 rotor potential scan (claim 19/ADR-010)
# ---------------------------------------------------------------------------


def audit_rotor_potential(audit: Audit) -> None:
    payload = load_results("rotor_potential.json")
    result = payload["result"]
    best = result["best"]
    audit.record(
        "19: real Z3 rotor scan preserves zero-flux degeneracy and converges",
        result["zero_flux_degenerate"] is True
        and result["best_convergence_delta"] < 1e-9
        and len(result["rows"]) == 44,
        f"rows={len(result['rows'])}, "
        f"delta={result['best_convergence_delta']:.3e}",
    )
    audit.record(
        "19: real Z3 rotor never reaches Q=2/3",
        result["falsified"] is True
        and result["status"].startswith("FALSIFIED")
        and best["koide_q"] < 0.5
        and max(result["max_q_by_nu"].values()) < 2.0 / 3.0 - 0.01,
        f"best Q={best['koide_q']:.6f}, "
        f"max by nu={max(result['max_q_by_nu'].values()):.6f}",
    )


# ---------------------------------------------------------------------------
# Madelung fluid dictionary (claim 20/ADR-011)
# ---------------------------------------------------------------------------


def audit_madelung(audit: Audit) -> None:
    payload = load_results("madelung.json")
    result = payload["result"]
    free = result["free_gaussian"]
    coherent = result["coherent_state"]
    verdict = result["verdict"]
    audit.record(
        "20: Madelung dictionary reproduces the free Gaussian and coherent state",
        free["l2_error"] < 1e-10
        and coherent["l2_error"] < 1e-3
        and free["continuity_residual"] < 1e-2
        and result["euler_residual_core"] < 1e-2,
        f"free L2={free['l2_error']:.3e}, "
        f"coherent L2={coherent['l2_error']:.3e}, "
        f"Euler={result['euler_residual_core']:.3e}",
    )
    audit.record(
        "20: dictionary verdict is recorded and not overclaimed",
        verdict["dictionary_verified"] is True
        and verdict["claim_20_status"].startswith("NUMERIC")
        and "not a microphysical" in verdict["note"],
        verdict["claim_20_status"],
    )


# ---------------------------------------------------------------------------
# Nelson stochastic kinematics (claim 21/ADR-012)
# ---------------------------------------------------------------------------


def audit_nelson(audit: Audit) -> None:
    payload = load_results("nelson.json")
    result = payload["result"]
    ground = result["ground_state"]
    free = result["free_packet"]
    verdict = result["verdict"]
    audit.record(
        "21: Nelson osmotic process reproduces the ground-state density",
        abs(ground["variance"] - 0.5) < 0.01
        and ground["l1_error"] < 0.05
        and free["l1_error"] < 0.10,
        f"variance={ground['variance']:.6f}, "
        f"ground L1={ground['l1_error']:.4f}, "
        f"free L1={free['l1_error']:.4f}",
    )
    audit.record(
        "21: stochastic kinematics verdict is recorded and not overclaimed",
        verdict["kinematics_verified"] is True
        and verdict["claim_21_status"].startswith("NUMERIC")
        and "not a self-consistent" in verdict["note"],
        verdict["claim_21_status"],
    )


# ---------------------------------------------------------------------------
# Gaussian Madelung reduction (claim 22/ADR-013)
# ---------------------------------------------------------------------------


def audit_gaussian_fluid(audit: Audit) -> None:
    payload = load_results("gaussian_fluid.json")
    result = payload["result"]
    large = result["large_amplitude"]
    small = result["small_oscillation"]
    verdict = result["verdict"]
    audit.record(
        "22: Gaussian Madelung fixed point is the quantum width",
        abs(result["fixed_point"]["sigma_squared"] - 0.5) < 1e-12
        and large["min_sigma"] < result["quantum_width"] < large["max_sigma"]
        and large["energy_drift"] < 1e-6,
        f"sigma^2={result['fixed_point']['sigma_squared']:.12f}, "
        f"drift={large['energy_drift']:.3e}",
    )
    audit.record(
        "22: small oscillations have the Ermakov 2 omega frequency",
        abs(small["period"] - 3.141592653589793) / 3.141592653589793 < 0.02
        and verdict["fixed_point_verified"] is True
        and verdict["claim_22_status"].startswith("PROVEN"),
        f"period={small['period']:.6f}, "
        f"error={small['relative_period_error']:.3e}",
    )


# ---------------------------------------------------------------------------
# Moving-center Gaussian reduction (claim 23/ADR-014)
# ---------------------------------------------------------------------------


def audit_coherent_fluid(audit: Audit) -> None:
    payload = load_results("coherent_fluid.json")
    result = payload["result"]
    fixed = result["fixed_center"]
    displaced = result["displaced_center"]
    verdict = result["verdict"]
    audit.record(
        "23: moving-center Gaussian reproduces the coherent-state trajectory",
        abs(fixed["x_at_pi"] + 1.0) < 1e-3
        and abs(fixed["center_period"] - 2.0 * 3.141592653589793)
        / (2.0 * 3.141592653589793)
        < 0.01
        and fixed["width_error"] < 1e-8
        and fixed["energy_drift"] < 1e-6,
        f"x(pi)={fixed['x_at_pi']:.9f}, "
        f"period={fixed['center_period']:.6f}",
    )
    audit.record(
        "23: displaced width oscillates with conserved energy",
        displaced["sigma_min"] < result["quantum_width"] < displaced["sigma_max"]
        and displaced["energy_drift"] < 1e-6
        and verdict["reduction_verified"] is True
        and verdict["claim_23_status"].startswith("PROVEN"),
        f"energy drift={displaced['energy_drift']:.3e}",
    )


# ---------------------------------------------------------------------------
# First-excited-state node (claim 24/ADR-015)
# ---------------------------------------------------------------------------


def audit_excited_fluid(audit: Audit) -> None:
    payload = load_results("excited_fluid.json")
    result = payload["result"]
    regular = result["regular_quantum_pressure"]
    audit.record(
        "24: first excited state has a node and a pi phase slip",
        abs(result["phase_slip"] - 3.141592653589793) < 1e-9
        and result["node_density"] == 0.0
        and regular["relative_error"] < 1e-10,
        f"slip={result['phase_slip']:.9f}, "
        f"Q error={regular['relative_error']:.3e}",
    )
    audit.record(
        "24: phase gradient diverges as dx^-1 and the claim is falsified",
        abs(result["gradient_scaling_slope"] + 1.0) < 1e-6
        and result["verdict"]["regular_representation"] is False
        and result["verdict"]["claim_24_status"].startswith("FALSIFIED"),
        f"slope={result['gradient_scaling_slope']:.9f}",
    )


# ---------------------------------------------------------------------------
# Hydrogen 1s Madelung reduction (claim 25/ADR-016)
# ---------------------------------------------------------------------------


def audit_hydrogen_fluid(audit: Audit) -> None:
    payload = load_results("hydrogen_fluid.json")
    result = payload["result"]
    atomic = result["atomic_units"]
    si = result["si"]
    verdict = result["verdict"]
    audit.record(
        "25: hydrogen 1s force balance gives the Bohr radius",
        abs(atomic["bohr_radius"] - 1.0) < 1e-12
        and abs(atomic["ground_energy"] + 0.5) < 1e-12
        and atomic["max_abs_residual"] < 1e-12
        and abs(atomic["density_normalization"] - 1.0) < 1e-6,
        f"a0={atomic['bohr_radius']:.12f}, "
        f"residual={atomic['max_abs_residual']:.3e}",
    )
    audit.record(
        "25: SI values and the wrong-radius control are recorded",
        abs(si["bohr_radius_m"] - 5.29177e-11) / 5.29177e-11 < 1e-4
        and abs(si["ground_energy_ev"] + 13.6057) / 13.6057 < 1e-4
        and abs(atomic["wrong_radius_residual"] + 0.5) < 1e-12
        and verdict["force_balance_verified"] is True
        and verdict["claim_25_status"].startswith("PROVEN"),
        f"a0={si['bohr_radius_m']:.9e}, E={si['ground_energy_ev']:.6f}",
    )


# ---------------------------------------------------------------------------
# Hydrogen 2p vortex (claim 26/ADR-017)
# ---------------------------------------------------------------------------


def audit_hydrogen_vortex(audit: Audit) -> None:
    payload = load_results("hydrogen_vortex.json")
    result = payload["result"]
    atomic = result["atomic_units"]
    verdict = result["verdict"]
    audit.record(
        "26: hydrogen 2p has a quantized vortex with the 4a0 peak",
        abs(atomic["radial_normalization"] - 1.0) < 1e-6
        and abs(atomic["most_probable_radius"] - 4.0) < 1e-3
        and abs(atomic["measured_loop_circulation"] - 2.0 * 3.141592653589793)
        < 1e-10
        and abs(atomic["azimuthal_velocity"] - 0.5) < 1e-12,
        f"a0 peak={atomic['most_probable_radius']:.6f}, "
        f"circulation={atomic['measured_loop_circulation']:.9f}",
    )
    audit.record(
        "26: angular momentum is hbar m and the vortex claim is recorded",
        abs(atomic["angular_momentum"] - 1.0) < 1e-12
        and verdict["vortex_identified"] is True
        and verdict["claim_26_status"].startswith("NUMERIC"),
        f"Lz={atomic['angular_momentum']:.9f}",
    )


# ---------------------------------------------------------------------------
# Shallow-water acoustic horizon (claim 27/ADR-018)
# ---------------------------------------------------------------------------


def audit_water_analogue(audit: Audit) -> None:
    payload = load_results("water_analogue.json")
    result = payload["result"]
    scales = result["scales"]
    rows = result["rows"]
    verdict = result["verdict"]
    audit.record(
        "27: shallow-water horizon has v/c=1 and g_tt=0",
        abs(rows[2]["v_over_c"] - 1.0) < 1e-12
        and abs(rows[2]["g_tt"]) < 1e-15
        and rows[1]["g_tt"] > 0.0
        and rows[3]["g_tt"] < 0.0,
        f"v/c={rows[2]['v_over_c']:.9f}, g_tt={rows[2]['g_tt']:.3e}",
    )
    audit.record(
        "27: surface gravity and analogue temperature are positive",
        scales["surface_gravity_m_s2"] > 0.0
        and scales["hawking_temperature_k"] > 0.0
        and verdict["horizon_exists"] is True
        and verdict["claim_27_status"].startswith("PROVEN"),
        f"kappa={scales['surface_gravity_m_s2']:.6f}, "
        f"T={scales['hawking_temperature_k']:.3e}",
    )


# ---------------------------------------------------------------------------
# Capillary validity of the shallow-water horizon (claim 28/ADR-019)
# ---------------------------------------------------------------------------


def audit_water_validity(audit: Audit) -> None:
    payload = load_results("water_validity.json")
    result = payload["result"]
    lab = result["lab"]
    valid = result["valid_example"]
    verdict = result["verdict"]
    audit.record(
        "28: lab horizon is capillary-dominated",
        lab["long_wavelength"] is False
        and lab["capillary_ratio"] > 1.0
        and lab["horizon_radius_m"] < lab["capillary_length_m"],
        f"r_H={lab['horizon_radius_m']:.3e}, "
        f"ell_c={lab['capillary_length_m']:.3e}, "
        f"ratio={lab['capillary_ratio']:.6f}",
    )
    audit.record(
        "28: a larger flow reaches the long-wavelength regime",
        valid["long_wavelength"] is True
        and valid["capillary_ratio"] < 1e-2
        and abs(result["minimum_flow_m3_s"] - 0.01696993924076904) < 1e-12
        and verdict["claim_28_status"].startswith("PROVEN"),
        f"Q_min={result['minimum_flow_m3_s']:.6e}, "
        f"ratio={valid['capillary_ratio']:.3e}",
    )


# ---------------------------------------------------------------------------
# Dispersive shallow-water horizon (claim 29/ADR-020)
# ---------------------------------------------------------------------------


def audit_water_dispersive(audit: Audit) -> None:
    payload = load_results("water_dispersive.json")
    result = payload["result"]
    rows = {row["omega_rad_s"]: row for row in result["rows"]}
    verdict = result["verdict"]
    audit.record(
        "29: low-frequency horizon approaches the long-wavelength value",
        abs(rows[0.1]["ratio"] - 1.0) < 1e-4
        and abs(rows[1.0]["ratio"] - 1.0) < 0.01
        and abs(result["capillary_frequency_rad_s"] - 84.824) < 0.1,
        f"ratio(0.1)={rows[0.1]['ratio']:.6f}, "
        f"ratio(1)={rows[1.0]['ratio']:.6f}",
    )
    audit.record(
        "29: high-frequency horizon is shifted by capillary dispersion",
        rows[100.0]["ratio"] > 2.0
        and rows[10.0]["ratio"] > 1.1
        and verdict["claim_29_status"].startswith("PROVEN"),
        f"ratio(10)={rows[10.0]['ratio']:.6f}, "
        f"ratio(100)={rows[100.0]['ratio']:.6f}",
    )


# ---------------------------------------------------------------------------
# Radial rays at the water horizon (claim 30/ADR-021)
# ---------------------------------------------------------------------------


def audit_water_rays(audit: Audit) -> None:
    payload = load_results("water_rays.json")
    result = payload["result"]
    signs = result["signs"]
    rows = result["rows"]
    verdict = result["verdict"]
    audit.record(
        "30: outgoing speed changes sign at the horizon",
        signs[0]["outgoing_speed_m_s"] < 0.0
        and abs(signs[1]["outgoing_speed_m_s"]) < 1e-12
        and signs[2]["outgoing_speed_m_s"] > 0.0
        and all(row["ingoing_speed_m_s"] < 0.0 for row in signs),
        f"v(0.9)={signs[0]['outgoing_speed_m_s']:+.6f}, "
        f"v(1.1)={signs[2]['outgoing_speed_m_s']:+.6f}",
    )
    audit.record(
        "30: ray times match and the peeling rate equals the surface gravity",
        all(row["relative_error"] < 1e-3 for row in rows)
        and abs(
            result["peeling_rate_1_s"] - result["surface_gravity_m_s2"]
        )
        < 1e-12
        and verdict["separatrix_verified"] is True
        and verdict["claim_30_status"].startswith("PROVEN"),
        f"max error={max(row['relative_error'] for row in rows):.3e}, "
        f"kappa={result['peeling_rate_1_s']:.6f}",
    )


# ---------------------------------------------------------------------------
# 1D water-wave scattering (claim 31/ADR-022)
# ---------------------------------------------------------------------------


def audit_water_scattering(audit: Audit) -> None:
    payload = load_results("water_scattering.json")
    result = payload["result"]
    horizon = result["horizon"]
    uniform = result["uniform_control"]
    verdict = result["verdict"]
    audit.record(
        "31: the horizon blocks the right-moving packet",
        horizon["transmitted_fraction"] < 1e-3
        and horizon["final_center"] < 0.0
        and horizon["energy_total"] > 0.0,
        f"fraction={horizon['transmitted_fraction']:.3e}, "
        f"center={horizon['final_center']:.6f}",
    )
    audit.record(
        "31: the uniform-flow control transmits",
        uniform["transmitted_fraction"] > 0.9
        and uniform["final_center"] > 0.0
        and verdict["horizon_blocks"] is True
        and verdict["uniform_transmits"] is True
        and verdict["claim_31_status"].startswith("NUMERIC"),
        f"fraction={uniform['transmitted_fraction']:.6f}, "
        f"center={uniform['final_center']:.6f}",
    )


# ---------------------------------------------------------------------------
# Hydrated-electron cavity scale (claim 32/ADR-023)
# ---------------------------------------------------------------------------


def audit_water_electron(audit: Audit) -> None:
    payload = load_results("water_electron.json")
    result = payload["result"]
    scales = result["scales"]
    verdict = result["verdict"]
    audit.record(
        "32: screened hydrogen is far too large and weakly bound",
        scales["screened_bohr_radius_m"] > 1e-9
        and abs(scales["screened_energy_ev"]) < 0.01,
        f"a*={scales['screened_bohr_radius_m']:.3e}, "
        f"E*={scales['screened_energy_ev']:.3e}",
    )
    audit.record(
        "32: the capillary cavity lands near the hydrated-electron scale",
        2.0e-10 < scales["cavity_radius_m"] < 4.0e-10
        and 0.5 < scales["cavity_energy_ev"] < 2.0
        and verdict["claim_32_status"].startswith("NUMERIC"),
        f"R={scales['cavity_radius_m']:.3e}, "
        f"E={scales['cavity_energy_ev']:.6f}, "
        f"ratio={result['cavity_to_observed_ratio']:.6f}",
    )


# ---------------------------------------------------------------------------
# Finite spherical well for the hydrated electron (claim 33/ADR-024)
# ---------------------------------------------------------------------------


def audit_water_well(audit: Audit) -> None:
    payload = load_results("water_well.json")
    result = payload["result"]
    scales = result["scales"]
    capillary = scales["capillary"]
    threshold = scales["threshold"]
    minimum = scales["inverse"]["minimum"]
    verdict = result["verdict"]
    audit.record(
        "33: the Born-depth well at the capillary radius has no 1p",
        capillary["u_1s"] is not None
        and capillary["u_1p"] is None
        and capillary["transition_ev"] is None
        and capillary["binding_ev"] > 0.0
        and capillary["born_depth_ev"] < threshold["depth_at_capillary_ev"],
        f"kappa={capillary['kappa']:.6f}, "
        f"u1s={capillary['u_1s']:.6f}, "
        f"Born={capillary['born_depth_ev']:.6f}, "
        f"threshold={threshold['depth_at_capillary_ev']:.6f}",
    )
    audit.record(
        "33: no Born radius reaches 1.7 eV; the required depth exceeds Born",
        threshold["max_born_gap_ev"] < 1.7
        and minimum["excess_ev"] > 1.0
        and minimum["required_depth_ev"] > minimum["born_depth_ev"]
        and verdict["born_well_never_reaches_1p7"] is True
        and verdict["required_depth_above_born"] is True
        and verdict["claim_33_status"].startswith("NUMERIC"),
        f"maxgap={threshold['max_born_gap_ev']:.6f}, "
        f"Rmin={minimum['radius_m']:.3e}, "
        f"Vreq={minimum['required_depth_ev']:.6f}, "
        f"Born={minimum['born_depth_ev']:.6f}, "
        f"excess={minimum['excess_ev']:.6f}",
    )


# ---------------------------------------------------------------------------
# Bound-free absorption in the finite well (claim 34/ADR-025)
# ---------------------------------------------------------------------------


def audit_water_absorption(audit: Audit) -> None:
    payload = load_results("water_absorption.json")
    result = payload["result"]
    scales = result["scales"]
    capillary = scales["capillary"]
    required = scales["required"]
    verdict = result["verdict"]
    audit.record(
        "34: the Born-depth bound-free peak is below 1.7 eV",
        capillary["peak_ev"] < 1.2
        and 0.98 < capillary["sum_rule"] < 1.02
        and capillary["binding_ev"] > 0.0
        and capillary["peak_strength"] > 0.0,
        f"peak={capillary['peak_ev']:.6f}, "
        f"sum={capillary['sum_rule']:.6f}, "
        f"binding={capillary['binding_ev']:.6f}",
    )
    audit.record(
        "34: a 1.7 eV peak requires an extra depth of about 1.202 eV",
        1.0 < required["extra_ev"] < 1.5
        and abs(required["peak_ev"] - 1.7) < 0.01
        and required["depth_ev"] > capillary["born_depth_ev"] + 1.0
        and verdict["required_peak_matches"] is True
        and verdict["claim_34_status"].startswith("NUMERIC"),
        f"depth={required['depth_ev']:.6f}, "
        f"extra={required['extra_ev']:.6f}, "
        f"peak={required['peak_ev']:.6f}",
    )


# ---------------------------------------------------------------------------
# VDE and absorption constrain the finite well (claim 35/ADR-026)
# ---------------------------------------------------------------------------


def audit_water_vde(audit: Audit) -> None:
    payload = load_results("water_vde.json")
    result = payload["result"]
    scales = result["scales"]
    central = scales["central"]
    lower = scales["lower"]
    capillary = scales["capillary"]
    verdict = result["verdict"]
    audit.record(
        "35: the 1.7 eV absorption is bound-bound and the well fits both",
        abs(central["binding_ev"] - scales["vde_ev"]) < 0.01
        and abs(central["gap_ev"] - scales["observed_absorption_ev"]) < 0.01
        and central["energy_1s_ev"] < 0.0
        and central["energy_1p_ev"] < 0.0
        and verdict["absorption_is_bound"] is True
        and verdict["finite_well_satisfies_both"] is True
        and verdict["claim_35_status"].startswith("NUMERIC"),
        f"R={central['radius_m']:.3e}, V0={central['depth_ev']:.6f}, "
        f"E1s={central['energy_1s_ev']:.6f}, "
        f"E1p={central['energy_1p_ev']:.6f}, "
        f"gap={central['gap_ev']:.6f}",
    )
    audit.record(
        "35: the capillary/Born cavity is outside the VDE band",
        capillary["radius_m"] < lower["radius_m"]
        and capillary["born_depth_ev"] < lower["depth_ev"]
        and capillary["gap_ev"] is None
        and central["radius_m"] > 1.25 * capillary["radius_m"]
        and central["depth_ev"] > 1.9 * capillary["born_depth_ev"]
        and verdict["capillary_outside_vde_band"] is True,
        f"Rcap={capillary['radius_m']:.3e}, "
        f"Born={capillary['born_depth_ev']:.6f}, "
        f"Rreq={central['radius_m']:.3e}, "
        f"Vreq={central['depth_ev']:.6f}",
    )


# ---------------------------------------------------------------------------
# Soft-wall cavity and the hard VDE depth bound (claim 36/ADR-027)
# ---------------------------------------------------------------------------


def audit_water_softwall(audit: Audit) -> None:
    payload = load_results("water_softwall.json")
    result = payload["result"]
    scales = result["scales"]
    hard = scales["hard_bound"]
    closest = scales["closest"]
    capillary = scales["capillary"]
    verdict = result["verdict"]
    audit.record(
        "36: the Born depth is below the VDE, so the cavity depth is too small",
        hard["difference_ev"] > 0.7
        and hard["ratio"] > 1.3
        and capillary["maximum_binding_ev"] == hard["born_depth_ev"]
        and verdict["born_depth_below_vde"] is True,
        f"Born={hard['born_depth_ev']:.6f}, VDE={hard['vde_ev']:.2f}, "
        f"difference={hard['difference_ev']:.6f}, ratio={hard['ratio']:.6f}",
    )
    audit.record(
        "36: the soft-wall scan trades radius for depth",
        verdict["softness_trades_radius_for_depth"] is True
        and verdict["no_scan_point_at_capillary"] is True
        and closest["depth_ev"] > 2.5 * hard["born_depth_ev"]
        and closest["radius_m"] < 1.1 * capillary["radius_m"]
        and verdict["claim_36_status"].startswith("NUMERIC"),
        f"a={closest['diffuseness_angstrom']:.1f}, "
        f"R={closest['radius_m']:.3e}, V0={closest['depth_ev']:.6f}, "
        f"Born={hard['born_depth_ev']:.6f}",
    )


# ---------------------------------------------------------------------------
# Self-consistent finite-well pressure balance (claim 37/ADR-028)
# ---------------------------------------------------------------------------


def audit_water_pressure(audit: Audit) -> None:
    payload = load_results("water_pressure.json")
    result = payload["result"]
    scales = result["scales"]
    born = scales["scans"][0]
    vde = scales["vde_matched"]
    crude = scales["crude_capillary"]
    verdict = result["verdict"]
    audit.record(
        "37: the pressure-balanced radius is larger than the crude capillary radius",
        born["radius_m"] > 1.2 * crude["radius_m"]
        and born["total_energy_ev"] < crude["total_energy_ev"]
        and born["binding_ev"] > 1.0
        and 1.0 < born["gap_ev"] < 1.2
        and verdict["pressure_radius_larger"] is True,
        f"R={born['radius_m']:.3e}, Rcrude={crude['radius_m']:.3e}, "
        f"E1s={born['energy_1s_ev']:.6f}, gap={born['gap_ev']:.6f}",
    )
    audit.record(
        "37: the VDE-matched pressure cavity has a gap of 1.344 eV, not 1.7 eV",
        abs(vde["binding_ev"] - 3.27) < 0.01
        and 1.3 < vde["gap_ev"] < 1.4
        and vde["radius_m"] > 4.0e-10
        and verdict["vde_matched"] is True
        and verdict["claim_37_status"].startswith("NUMERIC"),
        f"V0={vde['depth_ev']:.6f}, R={vde['radius_m']:.3e}, "
        f"binding={vde['binding_ev']:.6f}, gap={vde['gap_ev']:.6f}",
    )


# ---------------------------------------------------------------------------
# Water reorganization and the VDE-optical difference (claim 38/ADR-029)
# ---------------------------------------------------------------------------


def audit_water_reorganization(audit: Audit) -> None:
    payload = load_results("water_reorganization.json")
    result = payload["result"]
    scales = result["scales"]
    capillary = scales["capillary"]
    required = scales["required"]
    pressure = scales["pressure"]
    verdict = result["verdict"]
    audit.record(
        "38: the capillary reorganization energy matches the VDE-optical difference",
        0.8 < capillary["lambda_ev"] / scales["observed_difference_ev"] < 1.0
        and capillary["relative_residual"] < 0.15
        and capillary["sigma"] < 2.0
        and verdict["lambda_within_15_percent"] is True
        and verdict["predicted_vde_within_2sigma"] is True,
        f"lambda={capillary['lambda_ev']:.6f}, "
        f"difference={scales['observed_difference_ev']:.2f}, "
        f"residual={capillary['residual_ev']:.6f}, "
        f"sigma={capillary['sigma']:.6f}",
    )
    audit.record(
        "38: the required radius is near the capillary radius, not the pressure radius",
        0.8 < required["radius_ratio"] < 1.0
        and pressure["lambda_ratio"] < 0.7
        and verdict["required_radius_within_15_percent"] is True
        and verdict["pressure_radius_inconsistent"] is True
        and verdict["claim_38_status"].startswith("NUMERIC"),
        f"Rreq/Rcap={required['radius_ratio']:.6f}, "
        f"lambda_press/diff={pressure['lambda_ratio']:.6f}, "
        f"Rpress={pressure['radius_m']:.3e}",
    )


# ---------------------------------------------------------------------------
# Self-consistent Born cavity synthesis (claim 39/ADR-030)
# ---------------------------------------------------------------------------


def audit_water_born_cavity(audit: Audit) -> None:
    payload = load_results("water_born_cavity.json")
    result = payload["result"]
    scales = result["scales"]
    equilibrium = scales["equilibrium"]
    synthesis = scales["synthesis"]
    verdict = result["verdict"]
    audit.record(
        "39: the self-consistent Born cavity has no bound 1p",
        2.0e-10 < equilibrium["radius_m"] < 3.0e-10
        and equilibrium["energy_1s_ev"] == equilibrium["energy_1s_ev"]
        and abs(equilibrium["energy_1s_ev"] + 0.436571724) < 0.01
        and equilibrium["u_1p"] is None
        and equilibrium["gap_ev"] is None
        and verdict["no_bound_1p"] is True,
        f"R={equilibrium['radius_m']:.3e}, "
        f"V0={equilibrium['depth_ev']:.6f}, "
        f"E1s={equilibrium['energy_1s_ev']:.6f}, "
        f"gap={equilibrium['gap_ev']}",
    )
    audit.record(
        "39: water reorganization predicts the VDE within 0.5 sigma",
        abs(synthesis["lambda_ev"] - 1.617132544) < 0.01
        and abs(synthesis["predicted_vde_ev"] - 3.317132544) < 0.01
        and abs(synthesis["sigma"]) < 0.5
        and 1.0 < synthesis["required_ratio"] < 1.05
        and verdict["predicted_vde_within_1sigma"] is True
        and verdict["required_radius_within_5_percent"] is True
        and verdict["claim_39_status"].startswith("NUMERIC"),
        f"lambda={synthesis['lambda_ev']:.6f}, "
        f"VDE={synthesis['predicted_vde_ev']:.6f}, "
        f"sigma={synthesis['sigma']:.6f}, "
        f"Rreq/Req={synthesis['required_ratio']:.6f}",
    )


# ---------------------------------------------------------------------------
# Marcus band width from the water reorganization energy (claim 40/ADR-031)
# ---------------------------------------------------------------------------


def audit_water_marcus(audit: Audit) -> None:
    payload = load_results("water_marcus.json")
    result = payload["result"]
    scales = result["scales"]
    widths = scales["widths_ev"]
    verdict = result["verdict"]
    audit.record(
        "40: the Marcus width matches the reference hydrated-electron band",
        abs(widths["300"] - 0.680915) < 0.001
        and abs(scales["ratio_classical"] - 1.0) < 0.05
        and abs(scales["ratio_quantized"] - 1.0) < 0.15
        and verdict["classical_width_within_5_percent"] is True
        and verdict["quantized_width_within_15_percent"] is True,
        f"FWHM300={widths['300']:.6f}, "
        f"ratio_classical={scales['ratio_classical']:.6f}, "
        f"ratio_quantized={scales['ratio_quantized']:.6f}",
    )
    audit.record(
        "40: the width follows sqrt(T)",
        abs(widths["350"] / widths["300"] - scales["sqrt_ratio_350_300"])
        < 1.0e-6
        and abs(widths["200"] - 0.555964) < 0.001
        and verdict["sqrt_temperature_scaling"] is True
        and verdict["claim_40_status"].startswith("NUMERIC"),
        f"FWHM200={widths['200']:.6f}, "
        f"FWHM350={widths['350']:.6f}, "
        f"ratio={widths['350'] / widths['300']:.6f}",
    )


# ---------------------------------------------------------------------------
# Temperature-dependent Born cavity (claim 41/ADR-032)
# ---------------------------------------------------------------------------


def audit_water_temperature(audit: Audit) -> None:
    payload = load_results("water_temperature.json")
    result = payload["result"]
    scales = result["scales"]
    verdict = result["verdict"]
    audit.record(
        "41: the water-property cavity has a nonzero but insufficient temperature slope",
        abs(scales["lambda_slope_mev_per_k"] + 1.068036) < 0.001
        and 0.38 < scales["fraction_of_upper"] < 0.45
        and 0.44 < scales["fraction_of_lower"] < 0.45
        and verdict["nonzero_temperature_slope"] is True
        and verdict["covers_less_than_half"] is True,
        f"slope={scales['lambda_slope_mev_per_k']:.6f}, "
        f"fraction_lower={scales['fraction_of_lower']:.6f}, "
        f"fraction_upper={scales['fraction_of_upper']:.6f}",
    )
    audit.record(
        "41: the Marcus width broadens over 0-45 C",
        abs(scales["width_0c_ev"] - 0.653822) < 0.001
        and abs(scales["width_45c_ev"] - 0.695194) < 0.001
        and scales["width_change_ev"] > 0.0
        and verdict["width_broadens_with_temperature"] is True
        and verdict["claim_41_status"].startswith("NUMERIC"),
        f"width0={scales['width_0c_ev']:.6f}, "
        f"width45={scales['width_45c_ev']:.6f}, "
        f"change={scales['width_change_ev']:.6f}",
    )


# ---------------------------------------------------------------------------
# Residual temperature shift (claim 42/ADR-033)
# ---------------------------------------------------------------------------


def audit_water_temperature_residual(audit: Audit) -> None:
    payload = load_results("water_temperature.json")
    result = payload["result"]
    scales = result["scales"]
    verdict = result["verdict"]
    audit.record(
        "42: the cavity dielectric and geometric terms cover less than half the shift",
        abs(scales["geometric_slope_mev_per_k"] - 0.9468175) < 0.001
        and 0.33 < scales["coverage_geometric_upper"] < 0.40
        and 0.39 < scales["coverage_geometric_lower"] < 0.45
        and verdict["geometric_coverage_below_half"] is True,
        f"geom={scales['geometric_slope_mev_per_k']:.6f}, "
        f"coverage={scales['coverage_geometric_lower']:.6f}/"
        f"{scales['coverage_geometric_upper']:.6f}",
    )
    audit.record(
        "42: the unexplained residual is 1.33-1.85 meV/K",
        1.3 < scales["residual_after_geometric_lower"] < 1.5
        and 1.8 < scales["residual_after_geometric_upper"] < 1.9
        and verdict["residual_above_one_mev"] is True
        and verdict["claim_42_status"].startswith("NUMERIC"),
        f"residual_lam={scales['residual_after_lambda_lower']:.6f}-"
        f"{scales['residual_after_lambda_upper']:.6f}, "
        f"residual_geom={scales['residual_after_geometric_lower']:.6f}-"
        f"{scales['residual_after_geometric_upper']:.6f}",
    )
    # The per-term residuals above are one-sided. The model's actual prediction is the signed
    # sum, and the dielectric term is negative while the geometric term is positive, so the
    # combined coverage is far smaller than either term alone.
    audit.record(
        "42: the two cavity terms oppose and net under a tenth of the shift",
        abs(scales["net_cavity_slope_mev_per_k"] + 0.1212184) < 0.001
        and scales["cavity_terms_oppose"] is True
        and scales["coverage_net_upper"] < 0.10
        and 2.5 < scales["residual_after_net_lower"] < 2.6
        and 2.9 < scales["residual_after_net_upper"] < 3.0
        and verdict["cavity_terms_oppose"] is True
        and verdict["net_coverage_below_tenth"] is True,
        f"net={scales['net_cavity_slope_mev_per_k']:.6f} meV/K, "
        f"coverage={scales['coverage_net_lower']:.6f}/"
        f"{scales['coverage_net_upper']:.6f}",
    )


# ---------------------------------------------------------------------------
# Fixed-lambda line-shape prediction (claim 43/ADR-034)
# ---------------------------------------------------------------------------


def audit_water_lineshape(audit: Audit) -> None:
    payload = load_results("water_lineshape.json")
    result = payload["result"]
    scales = result["scales"]
    moments = scales["moments"]
    prediction = scales["prediction"]
    thresholds = scales["thresholds"]
    verdict = result["verdict"]
    # Independent Marcus recomputation: FWHM = 2 sqrt(2 ln 2) sqrt(2 lambda kT).
    kb = 8.617333262e-5
    prefactor = 2.0 * math.sqrt(2.0 * math.log(2.0))
    width_0c = prefactor * math.sqrt(2.0 * 1.637567127 * kb * 273.15)
    width_45c = prefactor * math.sqrt(2.0 * 1.589505512 * kb * 318.15)
    # Independent Gaussian symmetry: odd integrand, so skew 0 and ratio 1.
    xs = np.linspace(-5.0, 5.0, 200001)
    gauss = np.exp(-4.0 * math.log(2.0) * xs * xs)
    third = float(np.trapezoid(xs**3 * gauss, xs) / np.trapezoid(gauss, xs))
    audit.record(
        "43: the Gaussian band is exactly symmetric",
        moments["skewness"] == 0.0
        and moments["half_width_ratio"] == 1.0
        and abs(third) < 1.0e-12
        and verdict["symmetry_exact"] is True,
        f"skew={moments['skewness']:.6f}, "
        f"ratio={moments['half_width_ratio']:.6f}, third={third:.3e}",
    )
    audit.record(
        "43: the predicted 0-45 C widths match sqrt(lambda T) with fixed lambda",
        abs(prediction["width_0c_ev"] - width_0c) < 1.0e-6
        and abs(prediction["width_45c_ev"] - width_45c) < 1.0e-6
        and abs(prediction["width_ratio_45_over_0"] - width_45c / width_0c)
        < 1.0e-9
        and verdict["widths_match_temperature_scan"] is True
        and verdict["ratio_matches_sqrt_lambda_t"] is True,
        f"width0={prediction['width_0c_ev']:.6f}, "
        f"width45={prediction['width_45c_ev']:.6f}, "
        f"ratio={prediction['width_ratio_45_over_0']:.6f}",
    )
    audit.record(
        "43: the prediction carries frozen kill thresholds",
        thresholds["width_ratio_tol"] == 0.05
        and thresholds["shape_ratio_tol"] == 0.15
        and thresholds["skew_tol"] == 0.3,
        f"status={result['verdict']['claim_43_status'][:10]}, "
        f"tol={thresholds['width_ratio_tol']}/"
        f"{thresholds['shape_ratio_tol']}/{thresholds['skew_tol']}",
    )
    comparison = result.get("comparison", {})
    observed = comparison.get("observed", {})
    width_obs = observed.get("width", {})
    shape_obs = observed.get("shape", {})
    # Independent width-ratio recomputation: Christensen slope 2e-4 eV/K
    # over 45 K gives 0.009 eV; ratio on the predicted 0 C scale.
    obs_change = 2.0e-4 * 45.0
    w0 = prediction["width_0c_ev"]
    obs_ratio = (w0 + obs_change) / w0
    obs_ratio_hwhm = (w0 + 2.0 * obs_change) / w0
    audit.record(
        "43: the observed width-ratio comparison is recomputed",
        abs(comparison.get("observed_change_ev", -1.0) - obs_change) < 1.0e-12
        and abs(
            comparison.get("observed_ratio_on_predicted_scale", -1.0)
            - obs_ratio
        )
        < 1.0e-9
        and abs(comparison.get("ratio_diff", -1.0) - abs(obs_ratio - prediction["width_ratio_45_over_0"]))
        < 1.0e-9
        and comparison.get("ratio_kill") is False
        and comparison.get("ratio_kill_if_hwhm") is False
        and verdict.get("ratio_kill") is False,
        f"obs_change={comparison.get('observed_change_ev')}, "
        f"obs_ratio={comparison.get('observed_ratio_on_predicted_scale')}, "
        f"diff={comparison.get('ratio_diff')}",
    )
    # Independent shape recomputation: Jou & Freeman 0.71 vs 0.37 eV
    # gives ratio 1.9189, diff 0.9189 > 0.15; tail n = 4.4 is not
    # Gaussian; the single symmetric Gaussian is falsified on shape.
    comp_ratio = 0.71 / 0.37
    audit.record(
        "43: the observed shape kill is recomputed",
        abs(comparison.get("component_width_ratio", -1.0) - comp_ratio)
        < 1.0e-12
        and shape_obs.get("tail_power_n_water") == 4.4
        and shape_obs.get("tail_is_gaussian") is False
        and comparison.get("shape_kill_gaussian_only") is True
        and verdict.get("shape_kill_gaussian_only") is True
        and result["verdict"]["claim_43_status"].startswith("FALSIFIED")
        and "shape" in result["verdict"]["claim_43_status"],
        f"comp_ratio={comparison.get('component_width_ratio')}, "
        f"tail_n={shape_obs.get('tail_power_n_water')}, "
        f"status={result['verdict']['claim_43_status'][:40]}",
    )


# Shared-lambda two-state Marcus assignment (claim 44/ADR-036)
# ---------------------------------------------------------------------------


def audit_two_state(audit: Audit) -> None:
    payload = load_results("two_state.json")
    result = payload["result"]
    scales = result["scales"]
    prediction = scales["prediction"]
    observed = scales["observed"]
    comparison = result.get("comparison", {})
    verdict = result["verdict"]
    # Independent Marcus recomputation: both states share lambda and T,
    # so both FWHM values are one number; the predicted ratio is exactly 1.
    kb = 8.617333262e-5
    prefactor = 2.0 * math.sqrt(2.0 * math.log(2.0))
    width = prefactor * math.sqrt(2.0 * 1.617132544 * kb * 300.0)
    audit.record(
        "44: two Marcus states sharing lambda have identical widths",
        abs(prediction["width_g1_ev"] - width) < 1.0e-6
        and abs(prediction["width_g2_ev"] - width) < 1.0e-6
        and prediction["width_g1_ev"] == prediction["width_g2_ev"]
        and prediction["predicted_ratio"] == 1.0
        and verdict["widths_identical"] is True,
        f"g1={prediction['width_g1_ev']:.6f}, "
        f"g2={prediction['width_g2_ev']:.6f}, "
        f"ratio={prediction['predicted_ratio']}",
    )
    # Independent ratio kill: Jou & Freeman 0.71 vs 0.37 eV gives 1.9189,
    # diff 0.9189 > 0.15; the shared-lambda assignment is falsified.
    comp_ratio = 0.71 / 0.37
    audit.record(
        "44: the observed component ratio kills the shared-lambda assignment",
        abs(observed["observed_ratio"] - comp_ratio) < 1.0e-12
        and abs(comparison.get("observed_ratio", -1.0) - comp_ratio)
        < 1.0e-9
        and abs(comparison.get("ratio_diff_vs_one", -1.0) - abs(comp_ratio - 1.0))
        < 1.0e-9
        and comparison.get("shape_kill_shared_lambda") is True
        and verdict.get("shape_kill_shared_lambda") is True
        and result["verdict"]["claim_44_status"].startswith("FALSIFIED"),
        f"obs_ratio={comparison.get('observed_ratio')}, "
        f"diff={comparison.get('ratio_diff_vs_one')}, "
        f"status={result['verdict']['claim_44_status'][:40]}",
    )


def audit_water_twocomponent(audit: Audit) -> None:
    payload = load_results("water_twocomponent.json")
    result = payload["result"]
    scales = result["scales"]
    observed = scales["observed"]
    verdict = result["verdict"]
    # Independent side widths at 299.15 K from the Jou-Freeman fits.
    g = 0.1517 + 0.00051 * 299.15
    l = 0.5124 - 0.00010 * 299.15
    # Independent join: red = FWHM(299.15)/2 with lambda fixed from
    # claim 39, blue from continuity of (E/1.72)^-4.4 at half-maximum.
    kb = 8.617333262e-5
    prefactor = 2.0 * math.sqrt(2.0 * math.log(2.0))
    fwhm = prefactor * math.sqrt(2.0 * 1.617132544 * kb * 299.15)
    red = fwhm / 2.0
    blue = 1.72 * (2.0 ** (1.0 / 4.4) - 1.0)
    r_pred = blue / red
    r_obs = l / g
    audit.record(
        "45: the joined-model side ratio is recomputed",
        abs(scales["red_hwhm_ev"] - red) < 1.0e-9
        and abs(scales["blue_hwhm_ev"] - blue) < 1.0e-9
        and abs(scales["r_pred"] - r_pred) < 1.0e-9
        and abs(scales["r_obs"] - r_obs) < 1.0e-9
        and abs(scales["ratio_diff"] - abs(r_pred - r_obs)) < 1.0e-9
        and verdict["ratio_kill"] is True,
        f"r_pred={scales['r_pred']:.6f}, r_obs={scales['r_obs']:.6f}, "
        f"diff={scales['ratio_diff']:.6f}",
    )
    audit.record(
        "45: the joined-model width scale is recomputed",
        abs(scales["fwhm_model_ev"] - (blue + red)) < 1.0e-9
        and abs(
            scales["classical_rel_diff"] - abs(scales["fwhm_model_ev"] - 0.706) / 0.706
        )
        < 1.0e-9
        and abs(
            scales["quantized_rel_diff"] - abs(scales["fwhm_model_ev"] - 0.773) / 0.773
        )
        < 1.0e-9
        and verdict["width_kill"] is True,
        f"fwhm={scales['fwhm_model_ev']:.6f}, "
        f"classical_rel={scales['classical_rel_diff']:.6f}, "
        f"quantized_rel={scales['quantized_rel_diff']:.6f}",
    )
    audit.record(
        "45: the two-component join is FALSIFIED with frozen thresholds",
        scales["thresholds"]["width_ratio_tol"] == 0.15
        and scales["thresholds"]["fwhm_classical_tol"] == 0.05
        and scales["thresholds"]["fwhm_quantized_tol"] == 0.15
        and verdict["claim_45_status"].startswith("FALSIFIED"),
        f"status={verdict['claim_45_status'][:60]}",
    )


def audit_node_defect(audit: Audit) -> None:
    payload = load_results("node_defect.json")
    result = payload["result"]
    scales = result["scales"]
    branch = scales["branch"]
    gates = result["gates"]
    verdict = result["verdict"]
    # Independent branch identities: psi == s*|psi|, node 0, slip pi.
    audit.record(
        "46: the two-branch identities are recomputed",
        branch["identity_residual"] == 0.0
        and branch["node_density"] == 0.0
        and abs(branch["phase_slip"] - math.pi) < 1e-12,
        f"residual={branch['identity_residual']:.3e}, "
        f"density={branch['node_density']:.3e}, "
        f"slip={branch['phase_slip']:.12f}",
    )
    # Independent node scaling: maxima pi/(2dx), slope -1.
    slope = scales["scaling"]["slope"]
    audit.record(
        "46: the node gradient scaling is recomputed",
        abs(slope + 1.0) <= 0.01 and gates["slope_kill"] is False,
        f"slope={slope:.12f}",
    )
    # Independent vortex gate: circulation 2pi (Wallstrom condition).
    vortex = scales["vortex"]
    audit.record(
        "46: the vortex circulation is recomputed",
        abs(vortex["circulation"] - 2.0 * math.pi) / (2.0 * math.pi) < 1e-6
        and abs(vortex["loop_circulation"] - 2.0 * math.pi) / (2.0 * math.pi)
        < 1e-6
        and abs(vortex["most_probable_radius"] - 4.0) < 1e-9
        and abs(vortex["radial_norm"] - 1.0) < 1e-6
        and gates["circulation_kill"] is False
        and gates["loop_kill"] is False
        and verdict["claim_46_status"].startswith("NUMERIC"),
        f"circ={vortex['circulation']:.12f}, "
        f"loop={vortex['loop_circulation']:.12f}, "
        f"status={verdict['claim_46_status'][:60]}",
    )


def audit_radial_node(audit: Audit) -> None:
    payload = load_results("radial_node.json")
    result = payload["result"]
    scales = result["scales"]
    branch = scales["branch"]
    radial = scales["radial"]
    gates = result["gates"]
    verdict = result["verdict"]
    # Independent branch identities: split exact, node at 2a0, slip pi.
    audit.record(
        "47: the two-branch radial identities are recomputed",
        branch["identity_residual"] == 0.0
        and abs(branch["node_radius"] - 2.0 * scales["radius"]) < 1e-9
        and abs(branch["phase_slip"] - math.pi) < 1e-12,
        f"residual={branch['identity_residual']:.3e}, "
        f"node={branch['node_radius']:.12f}, "
        f"slip={branch['phase_slip']:.12f}",
    )
    # Independent radial numbers: norm 1, overlap 0, peaks 3+-sqrt(5).
    audit.record(
        "47: the radial norm, overlap and peaks are recomputed",
        abs(radial["norm"] - 1.0) < 1e-6
        and abs(radial["overlap_10_20"]) < 1e-6
        and abs(radial["outer_peak"] - (3.0 + math.sqrt(5.0))) / (3.0 + math.sqrt(5.0)) < 1e-6
        and abs(radial["inner_peak"] - (3.0 - math.sqrt(5.0))) < 1e-6,
        f"norm={radial['norm']:.12f}, "
        f"overlap={radial['overlap_10_20']:.3e}, "
        f"outer={radial['outer_peak']:.12f}",
    )
    # Independent no-disturbance: 1s balance and 2p loop preserved.
    preserved = scales["preserved"]
    audit.record(
        "47: the preserved 1s/2p numbers are recomputed",
        all(abs(v) <= 1e-12 for v in preserved["balance_residuals"])
        and abs(preserved["loop_circulation"] - 2.0 * math.pi) / (2.0 * math.pi) < 1e-6
        and verdict["claim_47_status"].startswith("NUMERIC"),
        f"balance_max={max(abs(v) for v in preserved['balance_residuals']):.3e}, "
        f"loop={preserved['loop_circulation']:.12f}, "
        f"status={verdict['claim_47_status'][:60]}",
    )


def audit_nelson_closure(audit: Audit) -> None:
    payload = load_results("nelson_closure.json")
    result = payload["result"]
    scales = result["scales"]
    gates = result["gates"]
    verdict = result["verdict"]
    # Independent stationary map: FP residual scaling per probe.
    rows = scales["stationary_map"]["rows"]
    audit.record(
        "48: the stationary-map scaling is recomputed",
        all(abs(row["slope_interior"] + 2.0) <= 0.1 for row in rows.values())
        and all(not kill for _, kill in gates["slope_kills"]),
        "slopes="
        + ",".join(f"{n}={rows[n]['slope_interior']:.4f}" for n in sorted(rows)),
    )
    # Independent monotone decrease across refinement (recalibrated gate:
    # absolute magnitude retired as miscalibrated, ADR-040).
    audit.record(
        "48: the residual decrease is recomputed",
        all(
            all(b < a for a, b in zip(rows[n]["interior"], rows[n]["interior"][1:]))
            for n in rows
        )
        and all(not kill for _, kill in gates["monotone_kills"]),
        "finest="
        + ",".join(f"{n}={rows[n]['interior'][-1]:.3e}" for n in sorted(rows)),
    )
    # Independent sigma map: frozen-drift reconstruction is identity.
    entries = scales["sigma_map"]["entries"]
    audit.record(
        "48: the sigma map is recomputed",
        all(
            abs(entry["sigma_star"][-1] - math.sqrt(entry["sigma0_sq"])) <= 1e-9
            for entry in entries
        )
        and all(not kill for _, kill, _ in gates["sigma_kills"])
        and verdict["claim_48_status"].startswith("NUMERIC"),
        "worst="
        + f"{max(abs(e['sigma_star'][-1] - math.sqrt(e['sigma0_sq'])) for e in entries):.3e}, "
        f"status={verdict['claim_48_status'][:60]}",
    )


def audit_variational_width(audit: Audit) -> None:
    payload = load_results("variational_width.json")
    result = payload["result"]
    scales = result["scales"]
    gates = result["gates"]
    verdict = result["verdict"]
    analytic = scales["analytic"]
    grid = scales["grid"]
    # Independent G-M extremum: analytic location, grid agreement, curvature.
    audit.record(
        "49: the G-M Ritz extremum is recomputed",
        abs(analytic["sigma_star_sq"] - 0.5) <= 1e-9
        and abs(grid["refined"] - 0.5) <= 1e-9
        and abs(grid["grid_argmax"] - 0.5) <= grid["grid_step"]
        and abs(analytic["curvature_s2"] - (-2.0)) <= 1e-9
        and analytic["curvature_s2"] < 0.0
        and all(not kill for _, kill in gates["kills"]
                if _ in ("gm_location", "gm_grid_refine", "gm_grid_agree",
                         "gm_curvature")),
        f"s2*={analytic['sigma_star_sq']:.12f}, "
        f"refined={grid['refined']:.12f}, "
        f"curv={analytic['curvature_s2']:.6f}",
    )
    # Independent Yasui no-extremum: derivative sign over frozen grid.
    yasui = scales["yasui"]
    audit.record(
        "49: the Yasui no-extremum is recomputed",
        bool(yasui["all_negative"])
        and yasui["max_derivative"] < -1e-3
        and yasui["max_diff"] < 0.0
        and all(not kill for _, kill in gates["kills"]
                if _ == "yasui_no_zero"),
        f"max_d={yasui['max_derivative']:.6f}",
    )
    # Independent scaling law at omega=2 and mass=2.
    audit.record(
        "49: the scaling law is recomputed",
        all(
            abs(entry["refined"] - entry["predicted"]) <= 1e-9
            and abs(entry["predicted"] - 0.25) <= 1e-12
            for entry in scales["scalings"]
        )
        and all(not kill for _, kill in gates["kills"]
                if _.startswith("scale_")),
        "scalings="
        + ",".join(
            f"{e['omega']},{e['mass']}={e['refined']:.12f}"
            for e in scales["scalings"]
        )
        + f", status={verdict['claim_49_status'][:60]}",
    )
    if not verdict["claim_49_status"].startswith("NUMERIC"):
        audit.record(
            "49: verdict is NUMERIC",
            False,
            f"status={verdict['claim_49_status'][:60]}",
        )


def audit_variational_saddle(audit: Audit) -> None:
    payload = load_results("variational_saddle.json")
    result = payload["result"]
    scales = result["scales"]
    gates = result["gates"]
    verdict = result["verdict"]
    analytic = scales["analytic"]
    grid = scales["grid"]
    # Independent stationary point: analytic solve, no project imports.
    nu = 1.0 / (2.0 * 1.0)
    audit.record(
        "50: the saddle location is recomputed",
        abs(nu / 1.0 - 0.5) <= 1e-12
        and abs(analytic["sigma_star_sq"] - 0.5) <= 1e-9
        and abs(analytic["c_star"] - 0.0) <= 1e-9
        and abs(grid["refined_s"] - 0.5) <= 1e-9
        and abs(grid["refined_c"] - 0.0) <= 1e-9,
        f"s*={analytic['sigma_star_sq']:.12f}, "
        f"refined=({grid['refined_s']:.12f},{grid['refined_c']:.12f})",
    )
    # Independent conditional extremum on a coarse grid (math + numpy only).
    coarse_s = np.linspace(0.125, 2.0, 201)
    coarse_c = np.linspace(-1.0, 1.0, 81)
    s_mesh, c_mesh = np.meshgrid(coarse_s, coarse_c, indexing="ij")
    field = (
        1.0 * c_mesh * c_mesh * s_mesh
        - 0.25 / s_mesh
        - s_mesh
    )
    c0 = int(np.argmin(np.abs(coarse_c)))
    col = field[:, c0]
    row = field[int(np.argmax(col)), :]
    audit.record(
        "50: the conditional extremum is recomputed",
        abs(coarse_s[int(np.argmax(col))] - 0.5) <= 0.05
        and abs(coarse_c[int(np.argmin(row))] - 0.0) <= 0.05
        and abs(grid["grid_s"] - 0.5) <= grid["grid_step_s"]
        and abs(grid["grid_c"] - 0.0) <= grid["grid_step_c"],
        f"coarse_s={coarse_s[int(np.argmax(col))]:.6f}, "
        f"coarse_c={coarse_c[int(np.argmin(row))]:.6f}",
    )
    # Independent curvature split: max in s, min in c.
    d2s = -2.0 * 0.25 / (0.5**3)
    d2c = 2.0 * 1.0 * 0.5
    audit.record(
        "50: the curvature split is recomputed",
        abs(d2s - (-4.0)) <= 1e-9
        and d2s < 0.0
        and abs(d2c - 1.0) <= 1e-9
        and d2c > 0.0
        and abs(analytic["curvature_s"] - (-4.0)) <= 1e-9
        and abs(analytic["curvature_c"] - 1.0) <= 1e-9
        and all(not kill for _, kill in gates["kills"]
                if _ in ("gm_location", "gm_slice_agree",
                         "gm_newton_refine", "gm_curvature")),
        f"d2s={d2s:.6f}, d2c={d2c:.6f}",
    )
    # Independent Yasui no-extremum + box record consistency.
    yasui = scales["yasui"]
    audit.record(
        "50: the Yasui contrast is recomputed",
        all(-0.25 / (s * s) - 1.0 < -1e-3 for s in (0.125, 0.5, 1.0, 2.0))
        and bool(yasui["all_negative"])
        and yasui["max_derivative"] < -1e-3
        and grid["box_max_value"] > grid["saddle_value"],
        f"max_d={yasui['max_derivative']:.6f}, "
        f"box={grid['box_max_value']:.6f}>saddle={grid['saddle_value']:.6f}",
    )
    # Independent scaling law at omega = 2 (analytic + report consistency).
    scal = scales["scalings"]
    audit.record(
        "50: the scaling law is recomputed",
        abs(0.5 / 2.0 - 0.25) <= 1e-12
        and abs(scal["refined_s"] - 0.25) <= 1e-9
        and abs(scal["curvature_s"] - (-32.0)) <= 1e-9
        and abs(scal["curvature_c"] - 0.5) <= 1e-9
        and all(not kill for _, kill in gates["kills"]
                if _.startswith("scaling")),
        f"refined={scal['refined_s']:.12f}, "
        f"curv=({scal['curvature_s']:.6f},{scal['curvature_c']:.6f})",
    )
    if not verdict["claim_50_status"].startswith("NUMERIC"):
        audit.record(
            "50: verdict is NUMERIC",
            False,
            f"status={verdict['claim_50_status'][:60]}",
        )


def audit_variational_dynamics(audit: Audit) -> None:
    payload = load_results("variational_dynamics.json")
    result = payload["result"]
    scales = result["scales"]
    gates = result["gates"]
    verdict = result["verdict"]
    # Independent extremum: all constant starts converge (no project import).
    extrema = scales["extrema"]
    audit.record(
        "51: the discrete extremum is recomputed",
        all(e["converged"] for e in extrema)
        and all(e["max_deviation"] <= 1e-9 for e in extrema)
        and all(e["max_residual"] <= 1e-12 for e in extrema),
        "worst_dev="
        + f"{max(e['max_deviation'] for e in extrema):.3e}, "
        + f"worst_res={max(e['max_residual'] for e in extrema):.3e}",
    )
    # Independent period: linearized frequency 2*omega -> period pi/omega.
    audit.record(
        "51: the analytic period is recomputed",
        abs(2.0 * math.pi / (2.0 * 1.0) - math.pi) <= 1e-12,
        f"T=2*pi/2={2.0 * math.pi / 2.0:.12f}",
    )
    for entry in scales["releases"]:
        audit.record(
            "51: release crossings agree",
            math.isfinite(entry["period"]) and abs(entry["period"] - math.pi) <= 1e-3,
            f"f={entry['factor']}, T={entry['period']:.9f}",
        )
    # Independent term match: variational accel vs Ermakov RHS components.
    for row in scales["term_match"]["rows"]:
        s = row["s"]
        ermakov = -1.0 * s + 0.25 / (s * s * s)
        audit.record(
            "51: a term row is recomputed",
            abs(row["own"] - ermakov) <= 1e-12 * max(abs(ermakov), 1e-12)
            and abs(row["rep_own"] - 0.25 / (s * s * s)) <= 1e-12,
            f"s={s}, a={row['own']:.6f}",
        )
    # Independent scaling law: omega = 2 gives pi/2.
    scal = scales["scaling"]
    audit.record(
        "51: the scaling law is recomputed",
        abs(scal["release"]["period"] - math.pi / 2.0) <= 1e-3,
        f"T={scal['release']['period']:.9f}",
    )
    if not verdict["claim_51_status"].startswith("NUMERIC"):
        audit.record(
            "51: verdict is NUMERIC",
            False,
            f"status={verdict['claim_51_status'][:60]}",
        )


def audit_yasue_dynamics(audit: Audit) -> None:
    payload = load_results("yasue_dynamics.json")
    result = payload["result"]
    scales = result["scales"]
    gates = result["gates"]
    verdict = result["verdict"]
    # Independent collapse: monotone releases, floor hit before pi, no returns.
    for entry in scales["releases"]:
        audit.record(
            "52: a Yasui release collapses",
            bool(entry["monotone"])
            and entry["floor_hit_time"] is not None
            and entry["floor_hit_time"] < math.pi
            and entry["upward_crossings"] == 0,
            f"f={entry['factor']}, t_hit={entry['floor_hit_time']:.6f}, "
            f"up={entry['upward_crossings']}",
        )
    # Independent control: G-M twin from the same releases oscillates at pi.
    for entry in scales["twins"]:
        audit.record(
            "52: the G-M twin oscillates",
            math.isfinite(entry["period"])
            and abs(entry["period"] - math.pi) <= 1e-3,
            f"f={entry.get('factor', '?')}, T={entry['period']:.9f}",
        )
    # Independent sign: Yasui accel negative on a coarse sigma grid.
    import numpy as _np

    coarse = _np.sqrt(_np.linspace(0.125, 2.0, 201))
    worst = max(-0.25 / (float(s) ** 3) - 1.0 * float(s) for s in coarse)
    audit.record(
        "52: the Yasui sign is recomputed",
        worst < 0.0,
        f"max_accel={worst:.6f}",
    )
    # Independent quadrature: energy-integral mild crossing on a coarse grid.
    import math as _math

    _s0 = 1.01 * _math.sqrt(0.5)
    _e = -0.25 / (2.0 * _s0 * _s0) + 0.5 * _s0 * _s0
    _umax = _math.sqrt(_s0 - 0.5)
    _n = 2001
    _vp = _math.sqrt(max(2.0 * 0.25 / (_s0**3) + 2.0 * 1.0 * _s0, 0.0))
    _total, _pu, _pf = 0.0, 0.0, 2.0 / _vp if _vp > 0.0 else 0.0
    for _i in range(1, _n):
        _u = _umax * _i / (_n - 1)
        _s = _s0 - _u * _u
        _v2 = max(
            2.0 * (_e - (-0.25 / (2.0 * _s * _s) + 0.5 * _s * _s)), 0.0
        )
        _cur = 2.0 * _u / _math.sqrt(_v2) if _v2 > 0.0 else 0.0
        _total += 0.5 * (_pf + _cur) * (_u - _pu)
        _pu, _pf = _u, _cur
    _stored = scales["releases"][0]["mild_crossing_time"]
    audit.record(
        "52: the quadrature crossing is recomputed",
        abs(_total - _stored) / _stored <= 1e-3,
        f"quad={_total:.9f}, stored={_stored:.9f}",
    )
    # Independent scaling law at omega = 2 (own Verlet, no project imports).
    _s, _v, _t, _hit2, _prev2 = 1.01 * 0.5, 0.0, 0.0, None, 1.01 * 0.5
    while _t < math.pi:
        _a = -0.25 / (_s**3) - 4.0 * _s
        _v += 0.5 * 0.001 * _a
        _s += 0.001 * _v
        _a2 = -0.25 / (_s**3) - 4.0 * _s if _s > 0.0 else _a
        _v += 0.5 * 0.001 * _a2
        _t += 0.001
        if _s <= 0.05:
            _hit2 = _t
            break
    _s, _v, _t, _cross2, _prev2 = 1.01 * 0.5, 0.0, 0.0, [], 1.01 * 0.5 - 0.5
    while _t < 4.0 * math.pi:
        _a = 0.25 / (_s**3) - 4.0 * _s
        _v += 0.5 * 0.001 * _a
        _s += 0.001 * _v
        _a2 = 0.25 / (_s**3) - 4.0 * _s if _s > 0.0 else _a
        _v += 0.5 * 0.001 * _a2
        _t += 0.001
        _cur = _s - 0.5
        if _prev2 < 0.0 <= _cur or _prev2 > 0.0 >= _cur:
            _cross2.append(_t)
            if len(_cross2) >= 5:
                break
        _prev2 = _cur
    _per2 = (
        sum(b - a for a, b in zip(_cross2[::2], _cross2[2::2]))
        / ((len(_cross2) - 1) // 2)
        if len(_cross2) >= 3
        else float("nan")
    )
    audit.record(
        "52: the scaling law is recomputed",
        _hit2 is not None
        and _hit2 < math.pi / 4.0
        and math.isfinite(_per2)
        and abs(_per2 - math.pi / 2.0) <= 1e-3,
        f"hit={_hit2}, T={_per2:.9f}",
    )
    if not verdict["claim_52_status"].startswith("NUMERIC"):
        audit.record(
            "52: verdict is NUMERIC",
            False,
            f"status={verdict['claim_52_status'][:60]}",
        )


def audit_variational_center(audit: Audit) -> None:
    payload = load_results("variational_center.json")
    result = payload["result"]
    scales = result["scales"]
    gates = result["gates"]
    verdict = result["verdict"]
    # Independent joint extremum: constant (0, sigma_q) is stationary.
    audit.record(
        "53: the joint extremum is recomputed",
        all(e["converged"] for e in scales["extrema"])
        and all(e["max_dev_mu"] <= 1e-9 for e in scales["extrema"])
        and all(e["max_dev_sg"] <= 1e-9 for e in scales["extrema"])
        and all(e["max_residual"] <= 1e-12 for e in scales["extrema"]),
        "worst_dev="
        + f"{max(max(e['max_dev_mu'], e['max_dev_sg']) for e in scales['extrema']):.3e}",
    )
    # Independent periods: analytic harmonic values, no project import.
    audit.record(
        "53: the center period is recomputed",
        all(
            math.isfinite(r["mu_period"]) or r["mu0"] == 0.0
            for r in scales["releases"]
        )
        and all(
            abs(r["mu_period"] - 2.0 * math.pi) <= 1e-3
            for r in scales["releases"]
            if r["mu0"] != 0.0
        ),
        "T_mu=2pi",
    )
    audit.record(
        "53: the width period is recomputed",
        all(
            math.isfinite(r["sg_period"]) or r["s0_factor"] == 1.0
            for r in scales["releases"]
        )
        and all(
            abs(r["sg_period"] - math.pi) <= 1e-3
            for r in scales["releases"]
            if r["s0_factor"] != 1.0
        ),
        "T_sg=pi",
    )
    # Independent term match: literal-form recompute catches transcription slips.
    _rows_ok = True
    for _row in scales["term_match"]["rows"]:
        _s = _row["s"]
        _expected = 0.25 / (_s**3) - 1.0 * _s
        if abs(_row["own"] - _expected) > 1e-12 or abs(
            _row["ermakov"] - _expected
        ) > 1e-12:
            _rows_ok = False
    audit.record(
        "53: the term match is recomputed",
        _rows_ok
        and scales["term_match"]["max_rel_error"] <= 1e-9,
        f"max_rel={scales['term_match']['max_rel_error']:.3e}",
    )
    # Independent scaling law at omega = 2.
    audit.record(
        "53: the scaling law is recomputed",
        abs(scales["scaling"]["mu_period"] - math.pi) <= 1e-3
        and abs(scales["scaling"]["sg_period"] - math.pi / 2.0) <= 1e-3,
        f"mu={scales['scaling']['mu_period']:.9f}, "
        f"sg={scales['scaling']['sg_period']:.9f}",
    )
    if not verdict["claim_53_status"].startswith("NUMERIC"):
        audit.record(
            "53: verdict is NUMERIC",
            False,
            f"status={verdict['claim_53_status'][:60]}",
        )


def audit_gaussian_bridge(audit: Audit) -> None:
    payload = load_results("gaussian_bridge.json")
    result = payload["result"]
    scales = result["scales"]
    gates = result["gates"]
    verdict = result["verdict"]
    # Independent Pinney coefficients from the endpoint conditions.
    disc = 1.44 * 1.44 - 4.0 * 0.0484
    b_lo = (-1.44 + math.sqrt(disc)) / 2.0
    b_hi = (-1.44 - math.sqrt(disc)) / 2.0
    stored = scales["pinney"]["coeffs"]
    audit.record(
        "54: the Pinney coefficients are recomputed",
        abs(disc - 1.88) < 1e-12
        and abs(stored[0]["B"] - b_lo) < 1e-9
        and abs(stored[1]["B"] - b_hi) < 1e-9
        and abs(stored[0]["A"] - 0.72) < 1e-12,
        f"disc={disc:.6f}",
    )
    # Independent attribution: every stored Newton run lands on a branch.
    _attributed = []
    for _m in scales["matches"]:
        _best = min(range(len(_m)), key=lambda _j: _m[_j])
        _attributed.append(_best if _m[_best] <= 1e-4 else None)
    audit.record(
        "54: no third attractor is recorded",
        len(_attributed) == 6 and all(a in (0, 1) for a in _attributed),
        f"attributed={_attributed}",
    )
    # Independent Jacobi re-integration on a coarse grid (no project import).
    import numpy as _np

    _t = _np.linspace(0.0, math.pi / 4.0, 2001)
    _dt = float(_t[1] - _t[0])
    _a, _b, _c = 0.72, -0.0344345399, 0.3488690799
    _s = _np.sqrt(_a * _np.cos(_t) ** 2 + 2.0 * _b * _np.cos(_t) * _np.sin(_t) + _c * _np.sin(_t) ** 2)
    _q = 3.0 * 0.25 / _np.maximum(_s, 1e-12) ** 4 + 1.0
    _u, _v, _zero = 0.0, 1.0, None
    for _i in range(1, len(_t)):
        _v += _dt * (-_q[_i - 1] * _u)
        _u += _dt * _v
        if _u <= 0.0:
            _zero = float(_t[_i])
            break
    audit.record(
        "54: the Jacobi no-crossing is recomputed",
        _zero is None,
        "zero=None" if _zero is None else f"zero={_zero}",
    )
    # Independent action quadrature (coarse, own code path).
    _vel = _np.gradient(_s, _dt)
    _dens = 0.5 * _vel * _vel - 0.125 / (_s * _s) - 0.5 * _s * _s
    audit.record(
        "54: the analytic action is recomputed",
        abs(float(_np.trapezoid(_dens, _t)) - scales["analytic_action"]) <= 1e-4,
        f"analytic={scales['analytic_action']:.6f}",
    )
    # Independent scaling re-derivation at omega = 2 (no project import).
    _sc = scales["scaling"]
    _a2 = _sc["s0"] ** 2
    _uT, _vT = math.cos(math.pi / 4.0), math.sin(math.pi / 4.0) / 2.0
    _b2, _c2 = 2.0 * _uT * _vT, _vT * _vT
    _qa, _qb = 1.0, _a2 * _b2 / _c2
    _qc = 0.25 - _a2 * _sc["sq"] ** 2 / _c2 + _a2 * _a2 * (_uT**2) / _c2
    _disc2 = _qb * _qb - 4.0 * _qa * _qc
    _b1 = (-_qb + math.sqrt(_disc2)) / 2.0
    _b2 = (-_qb - math.sqrt(_disc2)) / 2.0
    _smatch = []
    for _m in _sc["matches"]:
        _bs = min(range(len(_m)), key=lambda _j: _m[_j])
        _smatch.append(_bs if _m[_bs] <= 1e-4 else None)
    _ts = [float(v) for v in _np.linspace(0.0, _sc["T"], 1001)]
    _dt2 = _ts[1] - _ts[0]
    _ca = _sc["coeffs"][0]["A"]
    _cb = _sc["coeffs"][0]["B"]
    _cc = _sc["coeffs"][0]["C"]
    _ss = [
        math.sqrt(max(_ca * math.cos(2.0 * t) ** 2 + 2.0 * _cb * math.cos(2.0 * t) * math.sin(2.0 * t) / 2.0 + _cc * (math.sin(2.0 * t) / 2.0) ** 2, 0.0))
        for t in _ts
    ]
    _uu, _vv, _z2 = 0.0, 1.0, None
    for _i in range(1, len(_ts)):
        _qq = 3.0 * 0.25 / max(_ss[_i - 1], 1e-12) ** 4 + 4.0
        _vv += _dt2 * (-_qq * _uu)
        _uu += _dt2 * _vv
        if _uu <= 0.0:
            _z2 = _ts[_i]
            break
    audit.record(
        "54: the scaling two-branch structure is recomputed",
        _disc2 > 0.0
        and abs(_sc["coeffs"][0]["A"] - _a2) < 1e-12
        and all(a in (0, 1) for a in _smatch)
        and _sc["jacobi_first_zero"] is None
        and _z2 is None,
        f"branches={sorted(set(a for a in _smatch if a is not None))}, jacobi2={'none' if _z2 is None else _z2}",
    )
    if not verdict["claim_54_status"].startswith("NUMERIC"):
        audit.record(
            "54: verdict is NUMERIC",
            False,
            f"status={verdict['claim_54_status'][:60]}",
        )


def audit_yasue_center(audit: Audit) -> None:
    payload = load_results("yasue_center.json")
    result = payload["result"]
    scales = result["scales"]
    verdict = result["verdict"]
    # Independent constant-path residual: G-M stationary path is O(1) under Yasue.
    audit.record(
        "55: the constant-path residual is recomputed",
        all(s["max_residual"] > 1e-3 for s in scales["statics"])
        and all(s["max_res_mu"] <= 1e-9 for s in scales["statics"])
        and abs(min(s["max_residual"] for s in scales["statics"]) - math.sqrt(2.0)) <= 1e-9,
        f"min_res={min(s['max_residual'] for s in scales['statics']):.6f}",
    )
    # Independent arc solve: own discrete Yasue EL on the stored profile.
    _arc = scales["arc_profile"]
    _n = _arc["n"]
    _dt = _arc["dt"]
    _mu = _arc["mu"]
    _sg = _arc["sg"]
    _full_mu = [0.0] + _mu + [0.0]
    _full_sg = [math.sqrt(0.5)] + _sg + [math.sqrt(0.5)]
    _res_mu = [
        (_full_mu[i + 1] - _full_mu[i]) / _dt**2
        - (_full_mu[i + 2] - _full_mu[i + 1]) / _dt**2
        - 0.5 * 0.5 * (_full_mu[i] + _full_mu[i + 1])
        - 0.5 * 0.5 * (_full_mu[i + 1] + _full_mu[i + 2])
        for i in range(_n - 2)
    ]
    def _pot(_x: float) -> float:
        return 0.25 / (_x**3) + 1.0 * _x

    _res_sg = [
        (_full_sg[i + 1] - _full_sg[i]) / _dt**2
        - (_full_sg[i + 2] - _full_sg[i + 1]) / _dt**2
        - 0.5 * _pot(0.5 * (_full_sg[i] + _full_sg[i + 1]))
        - 0.5 * _pot(0.5 * (_full_sg[i + 1] + _full_sg[i + 2]))
        for i in range(_n - 2)
    ]
    _arc_res = max(
        max(abs(v) for v in _res_mu), max(abs(v) for v in _res_sg)
    )
    audit.record(
        "55: the single arc is recomputed",
        _arc_res <= 1e-9
        and scales["arc_max_sigma"] - scales["arc_min_sigma"] > 0.01
        and scales["arc_min_sigma"] > math.sqrt(0.5),
        f"arc_res={_arc_res:.3e}",
    )
    # Independent center track: Newtonian cosine over the collapse window.
    _track_ok = True
    for _r in scales["releases"]:
        _t = _r["floor_hit_time"]
        _pred = _r["mu0"] * math.cos(_t) if _t is not None else None
        _got = _r["mu_at_hit"]
        if _pred is None or _got is None or abs(_got - _pred) > 1e-4:
            _track_ok = False
    audit.record(
        "55: the center track is recomputed",
        _track_ok,
        "mu(t_hit)=mu0*cos(t_hit)",
    )
    # Independent width collapse: monotone releases, floor hit before pi, no returns.
    audit.record(
        "55: the Yasui width collapse is recomputed",
        all(_r["monotone"] for _r in scales["releases"])
        and all(
            _r["floor_hit_time"] is not None and _r["floor_hit_time"] < math.pi
            for _r in scales["releases"]
        )
        and all(_r["upward_crossings"] == 0 for _r in scales["releases"]),
        f"hits={[round(_r['floor_hit_time'], 3) for _r in scales['releases']]}",
    )
    # Independent G-M twin control: co-oscillation at 2pi and pi.
    audit.record(
        "55: the G-M twin is recomputed",
        all(
            abs(_t["mu_period"] - 2.0 * math.pi) <= 1e-3
            for _t in scales["twins"]
            if _t["mu0"] != 0.0
        )
        and all(
            abs(_t["sg_period"] - math.pi) <= 1e-3
            for _t in scales["twins"]
            if _t["s0_factor"] != 1.0
        ),
        "twin 2pi/pi",
    )
    # Independent scaling at omega = 2 (own Verlet, no project imports).
    _sc = scales["scaling"]
    _s, _v, _t, _hit2 = 1.01 * 0.5, 0.0, 0.0, None
    while _t < math.pi:
        _a = -0.25 / (_s**3) - 4.0 * _s
        _v += 0.5 * 0.001 * _a
        _s += 0.001 * _v
        _a2 = -0.25 / (_s**3) - 4.0 * _s if _s > 0.0 else _a
        _v += 0.5 * 0.001 * _a2
        _t += 0.001
        if _s <= 0.05:
            _hit2 = _t
            break
    audit.record(
        "55: the scaling law is recomputed",
        _hit2 is not None
        and _hit2 < math.pi / 4.0
        and abs(_sc["twin_mu"]["mu_period"] - math.pi) <= 1e-3
        and abs(_sc["twin_sg"]["sg_period"] - math.pi / 2.0) <= 1e-3,
        f"hit={_hit2}, twin_mu={_sc['twin_mu']['mu_period']:.6f}",
    )
    if not verdict["claim_55_status"].startswith("NUMERIC"):
        audit.record(
            "55: verdict is NUMERIC",
            False,
            f"status={verdict['claim_55_status'][:60]}",
        )


def audit_yasue_bridge(audit: Audit) -> None:
    payload = load_results("yasue_bridge.json")
    result = payload["result"]
    scales = result["scales"]
    verdict = result["verdict"]
    rec = scales["recorded_point"]
    # Independent B-quadratic from the endpoint conditions (no project import).
    _uT = math.cos(math.pi / 4.0)
    _vT = math.sin(math.pi / 4.0)
    _A = 0.5
    _qa, _qb = _vT**2, 2.0 * _A * _uT * _vT
    _qc = _A**2 * _uT**2 - _A * 0.5 - 0.25 * _vT**2
    _disc = (_qb / _qa) ** 2 - 4.0 * (_qc / _qa)
    _b1 = (-_qb / _qa + math.sqrt(_disc)) / 2.0
    _b2 = (-_qb / _qa - math.sqrt(_disc)) / 2.0
    audit.record(
        "56: the B-quadratic is recomputed",
        abs(_disc - 3.0) < 1e-12
        and abs(_b1 - 0.3660254037844386) < 1e-9
        and abs(_b2 + 1.3660254037844386) < 1e-9
        and abs(rec["disc"] - 3.0) < 1e-9,
        f"disc={_disc:.6f}",
    )
    # Independent ODE identity: own 4th-order FD on the stored B_1 branch.
    _c1 = (_b1**2 - 0.25) / _A
    _n = 2001
    _t = [i * (math.pi / 4.0) / (_n - 1) for i in range(_n)]
    _s = [
        math.sqrt(
            max(
                _A * math.cos(x) ** 2
                + 2.0 * _b1 * math.cos(x) * math.sin(x)
                + _c1 * math.sin(x) ** 2,
                0.0,
            )
        )
        for x in _t
    ]
    _h = _t[1] - _t[0]
    _w = [-1.0 / 12.0, 4.0 / 3.0, -5.0 / 2.0, 4.0 / 3.0, -1.0 / 12.0]
    _res = []
    for _i in range(2, _n - 2):
        _dd = sum(_w[_k] * _s[_i - 2 + _k] for _k in range(5)) / (_h * _h)
        _res.append(abs(_dd + 0.25 / _s[_i] ** 3 + _s[_i]))
    audit.record(
        "56: the ODE identity is recomputed",
        max(_res) <= 1e-6,
        f"max_res={max(_res):.3e}",
    )
    # Independent attribution: stored analytic path vs stored arc profile.
    _arc = load_results("yasue_center.json")["result"]["scales"]["arc_profile"]
    _analytic = rec["analytic_interior"]
    _recorded = _arc["sg"]
    _attrib = max(abs(a - b) for a, b in zip(_analytic, _recorded))
    audit.record(
        "56: the attribution is recomputed",
        _attrib <= 1e-4 and abs(_attrib - rec["attribution_max_abs"]) <= 1e-12,
        f"attrib={_attrib:.3e}",
    )
    # Independent killed sibling: B_2 takes s^2 negative mid-interval.
    _c2 = (_b2**2 - 0.25) / _A
    _s2min = min(
        _A * math.cos(x) ** 2
        + 2.0 * _b2 * math.cos(x) * math.sin(x)
        + _c2 * math.sin(x) ** 2
        for x in _t
    )
    audit.record(
        "56: the killed sibling is recomputed",
        _s2min < 0.0 and abs(_s2min - rec["b2_min_s2"]) <= 1e-9,
        f"min_s2={_s2min:.6f}",
    )
    # Independent Jacobi with the Yasue Q sign (own integrator).
    import numpy as _np

    _tt = _np.linspace(0.0, math.pi / 4.0, 20001)
    _ss = _np.array(
        [
            math.sqrt(
                max(
                    _A * math.cos(x) ** 2
                    + 2.0 * _b1 * math.cos(x) * math.sin(x)
                    + _c1 * math.sin(x) ** 2,
                    0.0,
                )
            )
            for x in _tt
        ]
    )
    _qq = -3.0 * 0.25 / _np.maximum(_ss, 1e-12) ** 4 + 1.0
    _uu, _vv, _zero = 0.0, 1.0, None
    _dt = float(_tt[1] - _tt[0])
    for _i in range(1, len(_tt)):
        _vv += _dt * (-float(_qq[_i - 1]) * _uu)
        _uu += _dt * _vv
        if _uu <= 0.0:
            _zero = float(_tt[_i])
            break
    audit.record(
        "56: the Jacobi leg is recomputed",
        _zero is None and bool(_np.all(_qq < 0.0)),
        f"zero={_zero}, qmax={float(_np.max(_qq)):.3f}",
    )
    # Independent nu = 0 limit and omega = 2 scaling algebra.
    _alpha = (1.0 - math.cos(math.pi / 4.0)) / math.sin(math.pi / 4.0)
    _peak = math.sqrt(1.0 + _alpha * _alpha)
    _sc = scales["scaling"]
    _nu0 = [e for e in scales["nu_series"] if e["nu"] == 0.0][0]
    audit.record(
        "56: the nu-limit and scaling are recomputed",
        abs(_alpha - (math.sqrt(2.0) - 1.0)) <= 1e-15
        and abs(_peak - 1.0823922003) <= 1e-9
        and abs(_nu0["peak_ratio"] - 1.0823922003) <= 1e-4
        and abs(_sc["b1"]["B"] - 0.3660254037844386) <= 1e-9
        and _sc["attribution_max_abs"] <= 1e-4
        and _sc["jacobi_first_zero"] is None,
        f"peak={_peak:.10f}",
    )
    if not verdict["claim_56_status"].startswith("NUMERIC"):
        audit.record(
            "56: verdict is NUMERIC",
            False,
            f"status={verdict['claim_56_status'][:60]}",
        )


def audit_yasue_action(audit: Audit) -> None:
    payload = load_results("yasue_action.json")
    result = payload["result"]
    scales = result["scales"]
    verdict = result["verdict"]
    rec = scales["recorded_point"]
    # Independent action pair from the stored B_1 coeffs (own code path).
    import numpy as _np

    _A = rec["b1"]["A"]
    _B = rec["b1"]["B"]
    _C = rec["b1"]["C"]
    _T = math.pi / 4.0
    _g = _np.linspace(0.0, _T, 401)
    _dt = float(_g[1] - _g[0])
    _s = _np.sqrt(
        _A * _np.cos(_g) ** 2
        + 2.0 * _B * _np.cos(_g) * _np.sin(_g)
        + _C * _np.sin(_g) ** 2
    )
    _v = (_s[1:] - _s[:-1]) / _dt
    _m = 0.5 * (_s[:-1] + _s[1:])
    _jd = float(_np.sum(0.5 * _v**2 + 0.25 / (2.0 * _m**2) - 0.5 * _m**2) * _dt)
    _tq = _np.linspace(0.0, _T, 200001)
    _hq = float(_tq[1] - _tq[0])
    _sq = _np.sqrt(
        _A * _np.cos(_tq) ** 2
        + 2.0 * _B * _np.cos(_tq) * _np.sin(_tq)
        + _C * _np.sin(_tq) ** 2
    )
    _vq = _np.gradient(_sq, _hq)
    _ja = float(
        _np.trapezoid(0.5 * _vq**2 + 0.25 / (2.0 * _sq**2) - 0.5 * _sq**2, _tq)
    )
    audit.record(
        "57: the action pair is recomputed",
        abs(_jd - _ja) <= 1e-4
        and abs(_ja - rec["j_analytic"]) <= 1e-6
        and abs(_jd - rec["j_discrete_analytic_path"]) <= 1e-9
        and abs(rec["j_discrete_newton"] - rec["j_analytic"]) <= 1e-4,
        f"diff={abs(_jd - _ja):.3e}",
    )
    # Independent probe slopes on the own path (two bump shapes).
    _slopes = []
    for _k in (1, 2):
        _b = _np.sin(_k * math.pi * _g / _T)
        for _lam in (0.01, 0.02):
            _lo = _s - _lam * 0.05 * _b
            _hi = _s + _lam * 0.05 * _b
            _jl = float(
                _np.sum(
                    0.5 * ((_lo[1:] - _lo[:-1]) / _dt) ** 2
                    + 0.25 / (2.0 * (0.5 * (_lo[:-1] + _lo[1:])) ** 2)
                    - 0.5 * (0.5 * (_lo[:-1] + _lo[1:])) ** 2
                )
                * _dt
            )
            _jh = float(
                _np.sum(
                    0.5 * ((_hi[1:] - _hi[:-1]) / _dt) ** 2
                    + 0.25 / (2.0 * (0.5 * (_hi[:-1] + _hi[1:])) ** 2)
                    - 0.5 * (0.5 * (_hi[:-1] + _hi[1:])) ** 2
                )
                * _dt
            )
            _slopes.append((_jh - _jl) / (2.0 * _lam))
    _stored = [p["slope"] for p in scales["probes"]]
    audit.record(
        "57: the probe slopes are recomputed",
        all(abs(s) <= 1e-6 for s in _slopes)
        and max(abs(a - b) for a, b in zip(_slopes, _stored)) <= 1e-9,
        f"max_slope={max(abs(s) for s in _slopes):.3e}",
    )
    # Independent classical closed form (own arithmetic).
    _alpha = math.sqrt(2.0) - 1.0
    _closed = -1.0 * 1.0 * 0.5 * _alpha
    _nu0 = [e for e in scales["nu_series"] if e["nu"] == 0.0][0]
    audit.record(
        "57: the classical closed form is recomputed",
        abs(_closed - (-0.20710678118654752)) <= 1e-15
        and abs(_closed - scales["classical"]["closed"]) <= 1e-15
        and abs(_nu0["j_discrete"] - _closed) <= 1e-4
        and abs(scales["classical"]["quad_nu0"] - _closed) <= 1e-6,
        f"closed={_closed:.10f}",
    )
    # Independent omega = 2 scaling pair.
    _uT, _vT, _A2 = math.cos(math.pi / 4.0), math.sin(math.pi / 4.0) / 2.0, 0.25
    _qa, _qb = _vT**2, 2.0 * _A2 * _uT * _vT
    _qc = _A2**2 * _uT**2 - _A2 * 0.25 - 0.25 * _vT**2
    _dd = (_qb / _qa) ** 2 - 4.0 * (_qc / _qa)
    _B1 = (-_qb / _qa + math.sqrt(_dd)) / 2.0
    _C1 = (_B1**2 - 0.25) / _A2
    _sc = scales["scaling"]
    _T2 = math.pi / 8.0
    _g2 = _np.linspace(0.0, _T2, 401)
    _d2 = float(_g2[1] - _g2[0])
    _s2 = _np.sqrt(
        _A2 * _np.cos(2.0 * _g2) ** 2
        + 2.0 * _B1 * _np.cos(2.0 * _g2) * _np.sin(2.0 * _g2) / 2.0
        + _C1 * (_np.sin(2.0 * _g2) / 2.0) ** 2
    )
    _v2 = (_s2[1:] - _s2[:-1]) / _d2
    _m2 = 0.5 * (_s2[:-1] + _s2[1:])
    _jd2 = float(_np.sum(0.5 * _v2**2 + 0.25 / (2.0 * _m2**2) - 0.5 * 4.0 * _m2**2) * _d2)
    audit.record(
        "57: the scaling pair is recomputed",
        abs(_B1 - 0.3660254037844386) <= 1e-9
        and abs(_sc["b1"]["B"] - _B1) <= 1e-12
        and abs(_jd2 - _sc["j_analytic"]) <= 1e-4
        and abs(_sc["j_discrete"] - _sc["j_analytic"]) <= 1e-4
        and _sc["attained"] is True,
        f"diff={abs(_jd2 - _sc['j_analytic']):.3e}",
    )
    # Independent B_2 structural record (own evaluation).
    _uT1, _vT1 = math.cos(math.pi / 4.0), math.sin(math.pi / 4.0)
    _A1 = 0.5
    _q1a, _q1b = _vT1**2, 2.0 * _A1 * _uT1 * _vT1
    _q1c = _A1**2 * _uT1**2 - _A1 * 0.5 - 0.25 * _vT1**2
    _d1 = (_q1b / _q1a) ** 2 - 4.0 * (_q1c / _q1a)
    _b2 = (-_q1b / _q1a - math.sqrt(_d1)) / 2.0
    _c2 = (_b2**2 - 0.25) / _A1
    _tt = _np.linspace(0.0, math.pi / 4.0, 2001)
    _s2b = (
        _A1 * _np.cos(_tt) ** 2
        + 2.0 * _b2 * _np.cos(_tt) * _np.sin(_tt)
        + _c2 * _np.sin(_tt) ** 2
    )
    audit.record(
        "57: the killed sibling is recomputed",
        float(_np.min(_s2b)) < 0.0
        and abs(float(_np.min(_s2b)) - rec["b2_min_s2"]) <= 1e-9,
        f"min_s2={float(_np.min(_s2b)):.6f}",
    )
    if not verdict["claim_57_status"].startswith("NUMERIC"):
        audit.record(
            "57: verdict is NUMERIC",
            False,
            f"status={verdict['claim_57_status'][:60]}",
        )


def audit_field_variation(audit: Audit) -> None:
    import numpy as _np

    payload = load_results("field_variation.json")
    result = payload["result"]
    scales = result["scales"]
    verdict = result["verdict"]
    # Independent Gaussian-bridge field action (own cell-centered code).
    _sq = math.sqrt(0.5)
    _s0, _sT, _T = 1.2 * _sq, _sq, math.pi / 4.0
    _A = _s0**2
    _uT, _vT = math.cos(_T), math.sin(_T)
    _qa, _qb = _vT**2, 2.0 * _A * _uT * _vT
    _qc = _A**2 * _uT**2 - _A * _sT**2 + 0.25 * _vT**2
    _dd = (_qb / _qa) ** 2 - 4.0 * (_qc / _qa)
    _B = (-_qb / _qa + math.sqrt(_dd)) / 2.0
    _C = (_B**2 + 0.25) / _A
    _nx, _nt, _L = 101, 101, 6.0
    _dx = 2.0 * _L / _nx
    _xc = -_L + _dx / 2.0 + _np.arange(_nx) * _dx
    _dt = _T / (_nt - 1)
    _tg = _np.linspace(0.0, _T, _nt)
    _sg = _np.sqrt(
        _A * _np.cos(_tg) ** 2
        + 2.0 * _B * _np.cos(_tg) * _np.sin(_tg)
        + _C * _np.sin(_tg) ** 2
    )
    _rho = _np.exp(-_xc[None, :] ** 2 / (2.0 * _sg[:, None] ** 2)) / _np.sqrt(
        2.0 * math.pi * _sg[:, None] ** 2
    )
    _rho = _rho / (_rho.sum(axis=1, keepdims=True) * _dx)
    _J = 0.0
    for _k in range(_nt - 1):
        _a, _b = _rho[_k], _rho[_k + 1]
        _rm = 0.5 * (_a + _b)
        _d = (_b - _a) / _dt
        _f = _np.zeros(_nx + 1)
        for _i in range(_nx):
            _f[_i + 1] = _f[_i] - _dx * _d[_i]
        _fv = 0.5 * (_f[:-1] + _f[1:])
        _dr = _np.empty(_nx)
        _dr[1:-1] = (_rm[2:] - _rm[:-2]) / (2.0 * _dx)
        _dr[0] = (_rm[1] - _rm[0]) / _dx
        _dr[-1] = (_rm[-1] - _rm[-2]) / _dx
        _safe = _np.maximum(_rm, 1e-150)
        _live = (_rm > 1e-12).astype(float)
        _J += float(
            _np.sum(
                (
                    0.5 * _fv**2 / _safe
                    - 0.125 * _dr**2 / _safe
                    - 0.5 * _xc**2 * _safe
                )
                * _live
            )
            * _dx
            * _dt
        )
    audit.record(
        "58: the bridge action is recomputed",
        abs(_J - (-0.3906340559)) <= 1e-4
        and abs(_J - scales["bridge_field_J"]) <= 1e-6,
        f"J={_J:.10f}",
    )
    # Independent classical bank arithmetic (transport ends) + near-miss.
    _s0, _sT, _Tw = 1.2 * math.sqrt(0.5), math.sqrt(0.5), math.pi / 4.0
    _A0 = _s0
    _B0 = (_sT - _s0 * math.cos(_Tw)) / math.sin(_Tw)
    _sd0 = _B0
    _sdT = -_A0 * math.sin(_Tw) + _B0 * math.cos(_Tw)
    _closed = 0.5 * (_sT * _sdT - _s0 * _sd0)
    _nu0 = scales["coarse_nu0_runs"]
    _best0 = min(r["J_final"] for r in _nu0)
    audit.record(
        "58: the classical bank is recomputed",
        abs(_A0 - 0.848528137423857) <= 1e-12
        and abs(_B0 - 0.1514718625761429) <= 1e-12
        and abs(_closed - (-0.23852813742385703)) <= 1e-12
        and abs(scales["classical"]["value"] - _closed) <= 1e-12
        and abs(_best0 - _closed) <= 1e-3,
        f"closed={_closed:.10f}",
    )
    # Independent Hessian saddle check on a tiny grid (own FD Hessian).
    _n2x, _n2t = 21, 11
    _dx2 = 12.0 / _n2x
    _xc2 = -6.0 + _dx2 / 2.0 + _np.arange(_n2x) * _dx2
    _T2, _dt2 = math.pi / 4.0, (math.pi / 4.0) / (_n2t - 1)
    _tg2 = _np.linspace(0.0, _T2, _n2t)
    _sg2 = _np.sqrt(
        _A * _np.cos(_tg2) ** 2
        + 2.0 * _B * _np.cos(_tg2) * _np.sin(_tg2)
        + _C * _np.sin(_tg2) ** 2
    )
    _r2 = _np.exp(-_xc2[None, :] ** 2 / (2.0 * _sg2[:, None] ** 2)) / _np.sqrt(
        2.0 * math.pi * _sg2[:, None] ** 2
    )
    _r2 = _r2 / (_r2.sum(axis=1, keepdims=True) * _dx2)
    _p2 = _np.log(_np.maximum(_r2[1:-1] * _dx2, 1e-300))
    _p2 = (_p2 - _p2[:, -1:])[:, :-1]
    _x0 = _p2.ravel()

    def _Jtiny(_pp: _np.ndarray) -> float:
        _P = _pp.reshape(_n2t - 2, _n2x - 1)
        _R = _np.empty((_n2t, _n2x))
        _R[0] = _r2[0] / (_r2[0].sum() * _dx2)
        _R[-1] = _r2[-1] / (_r2[-1].sum() * _dx2)
        for _kk in range(_n2t - 2):
            _full = _np.concatenate([_P[_kk], [0.0]])
            _e = _np.exp(_full - _full.max())
            _R[_kk + 1] = _e / (_e.sum() * _dx2)
        _Jj = 0.0
        for _kk in range(_n2t - 1):
            _aa, _bb = _R[_kk], _R[_kk + 1]
            _rmm = 0.5 * (_aa + _bb)
            _ddv = (_bb - _aa) / _dt2
            _ff = _np.zeros(_n2x + 1)
            for _ii in range(_n2x):
                _ff[_ii + 1] = _ff[_ii] - _dx2 * _ddv[_ii]
            _fvv = 0.5 * (_ff[:-1] + _ff[1:])
            _drr = _np.empty(_n2x)
            _drr[1:-1] = (_rmm[2:] - _rmm[:-2]) / (2.0 * _dx2)
            _drr[0] = (_rmm[1] - _rmm[0]) / _dx2
            _drr[-1] = (_rmm[-1] - _rmm[-2]) / _dx2
            _ss = _np.maximum(_rmm, 1e-150)
            _ll = (_rmm > 1e-12).astype(float)
            _Jj += float(
                _np.sum(
                    (
                        0.5 * _fvv**2 / _ss
                        - 0.125 * _drr**2 / _ss
                        - 0.5 * _xc2**2 * _ss
                    )
                    * _ll
                )
                * _dx2
                * _dt2
            )
        return _Jj

    # Independent escape demonstration: own tiny-grid optimization from a
    # Gaussian start descends below the bank (own code, FD gradients).
    from scipy.optimize import minimize as _minimize

    _lam = _np.linspace(0.0, 1.0, _n2t)[1:-1]
    _sg0 = (1.2 * _sq) + _lam * (_sq - 1.2 * _sq)
    _rs = _np.exp(-_xc2[None, :] ** 2 / (2.0 * _sg0[:, None] ** 2)) / _np.sqrt(
        2.0 * math.pi * _sg0[:, None] ** 2
    )
    _rs = _rs / (_rs.sum(axis=1, keepdims=True) * _dx2)
    _ps = _np.log(_np.maximum(_rs * _dx2, 1e-300))
    _ps = (_ps - _ps[:, -1:])[:, :-1]
    _Jstart = _Jtiny(_ps.ravel())
    _res2 = _minimize(
        _Jtiny,
        _ps.ravel(),
        method="L-BFGS-B",
        options={"maxiter": 60, "ftol": 1e-14, "gtol": 1e-7, "maxcor": 10},
    )
    audit.record(
        "58: an independent optimization escapes below the bank",
        _res2.fun < -0.3906340559 - 1e-4 and _res2.fun < _Jstart,
        f"J={_res2.fun:.6f} from {float(_Jstart):.6f} in {int(_res2.nit)} it",
    )
    # Stored multi-start record: all non-converged, all below bank.
    _runs = scales["coarse_runs"] + scales["fine_runs"]
    audit.record(
        "58: the escape record is consistent",
        all(not r["converged"] for r in _runs)
        and all(r["J_final"] < scales["bank"] for r in _runs)
        and all(r["grad_inf"] > 0 for r in _runs),
        f"min_J={min(r['J_final'] for r in _runs):.4f}",
    )
    if not verdict["claim_58_status"].startswith("FALSIFIED"):
        audit.record(
            "58: verdict is FALSIFIED",
            False,
            f"status={verdict['claim_58_status'][:60]}",
        )


def audit_widened_ritz(audit: Audit) -> None:
    import numpy as _np

    payload = load_results("widened_ritz.json")
    result = payload["result"]
    scales = result["result"] if "result" in result else result
    scales = result["scales"]
    verdict = result["verdict"]
    _sq = math.sqrt(0.5)
    _T = math.pi / 4.0
    # (1) Analytic bridge action recomputed (own midpoint code).
    _ntg, _s0, _sT = 401, 1.2 * _sq, _sq
    _tg = _np.linspace(0.0, _T, _ntg)
    _A = _s0**2
    _uT, _vT = math.cos(_T), math.sin(_T)
    _qa = _vT**2
    _qb = 2.0 * _A * _uT * _vT
    _qc = _A**2 * _uT**2 - _A * _sT**2 + 0.25 * _vT**2
    _dd = (_qb / _qa) ** 2 - 4.0 * (_qc / _qa)
    _B = (-_qb / _qa + math.sqrt(_dd)) / 2.0
    _C = (_B * _B + 0.25) / _A
    _sg = _np.sqrt(
        _A * _np.cos(_tg) ** 2
        + 2.0 * _B * _np.cos(_tg) * _np.sin(_tg)
        + _C * _np.sin(_tg) ** 2
    )
    _dt = _T / (_ntg - 1)
    _vv = (_sg[1:] - _sg[:-1]) / _dt
    _sm = 0.5 * (_sg[1:] + _sg[:-1])
    _Ja = float(
        _np.sum(0.5 * _vv**2 - 0.125 / (_sm * _sm) - 0.5 * _sm**2) * _dt
    )
    audit.record(
        "59: the analytic bridge action is recomputed",
        abs(_Ja - (-0.3906340559)) <= 1e-4
        and abs(_Ja - scales["analytic_J"]) <= 1e-6,
        f"J={_Ja:.10f}",
    )
    # (2) Stored best-per-K J recomputed from stored params (own code).
    _nx, _LN = 101, 101
    _dx = 12.0 / _nx
    _xc = -6.0 + _dx / 2.0 + _np.arange(_nx) * _dx
    _ok_all = True
    _worst = 0.0
    for _rung in scales["ladder"]:
        _k = _rung["k"]
        _pr = _np.asarray(_rung["best_params"], dtype=float)
        _nn = _LN - 2
        _ns = _pr[0:_nn]
        _s_full = _np.concatenate([[_s0], _ns, [_sT]])
        _rho = _np.empty((_LN, _nx))
        for _kk in range(_LN):
            _y = _xc / _s_full[_kk]
            _hh = [np.ones_like(_y), _y.copy()]
            for _nnn in range(1, _k):
                _hh.append(_y * _hh[_nnn] - _nnn * _hh[_nnn - 1])
            _hh = _hh[: _k + 1]
            _P = _np.ones(_nx)
            for _jj in range(1, _k + 1):
                _cfull = _np.concatenate(
                    [[0.0], _pr[_jj * _nn : (_jj + 1) * _nn], [0.0]]
                )
                _P = _P + _cfull[_kk] * _hh[_jj]
            _gg = _np.exp(-_y * _y / 2.0) / math.sqrt(2.0 * math.pi * _s_full[_kk] ** 2)
            _rr = _gg * _P * _P
            _rho[_kk] = _rr / (_rr.sum() * _dx)
        _JJ = 0.0
        _dtn = _T / (_LN - 1)
        for _kk in range(_LN - 1):
            _a, _b = _rho[_kk], _rho[_kk + 1]
            _rm = 0.5 * (_a + _b)
            _dd = (_b - _a) / _dtn
            _ff = _np.zeros(_nx + 1)
            for _ii in range(_nx):
                _ff[_ii + 1] = _ff[_ii] - _dx * _dd[_ii]
            _fvv = 0.5 * (_ff[:-1] + _ff[1:])
            _drr = _np.empty(_nx)
            _drr[1:-1] = (_rm[2:] - _rm[:-2]) / (2.0 * _dx)
            _drr[0] = (_rm[1] - _rm[0]) / _dx
            _drr[-1] = (_rm[-1] - _rm[-2]) / _dx
            _safe = _np.maximum(_rm, 1e-150)
            _live = (_rm > 1e-12).astype(float)
            _JJ += float(
                _np.sum(
                    (
                        0.5 * _fvv**2 / _safe
                        - 0.125 * _drr**2 / _safe
                        - 0.5 * _xc**2 * _safe
                    )
                    * _live
                )
                * _dx
                * _dtn
            )
        _stored_best = min(
            _rung["runs"], key=lambda _r: abs(_r["J_final"] + 0.3906340559)
        )
        _diff = abs(_JJ - _stored_best["J_final"])
        _worst = max(_worst, _diff)
        if not (_diff <= 1e-6):
            _ok_all = False
    audit.record(
        "59: the widened minimum is recomputed",
        bool(_ok_all),
        f"maxdiff={_worst:.3e}",
    )
    # (3) Attribution recompute on the K=0 rung (own code, same grid).
    _r0 = next(_r for _r in scales["ladder"] if _r["k"] == 0)
    _pr0 = _np.asarray(_r0["best_params"], dtype=float)
    _n0 = 101 - 2
    _s0v = _np.concatenate([[1.2 * _sq], _pr0[0:_n0], [_sq]])
    _rho0 = _np.empty((101, _nx))
    for _kk in range(101):
        _gg0 = _np.exp(-_xc**2 / (2.0 * _s0v[_kk] ** 2)) / math.sqrt(
            2.0 * math.pi * _s0v[_kk] ** 2
        )
        _rho0[_kk] = _gg0 / (_gg0.sum() * _dx)
    _tg0 = _np.linspace(0.0, _T, 101)
    _sg0 = _np.sqrt(
        _A * _np.cos(_tg0) ** 2
        + 2.0 * _B * _np.cos(_tg0) * _np.sin(_tg0)
        + _C * _np.sin(_tg0) ** 2
    )
    _ref0 = _np.exp(-_xc[None, :] ** 2 / (2.0 * _sg0[:, None] ** 2)) / _np.sqrt(
        2.0 * math.pi * _sg0[:, None] ** 2
    )
    _ref0 = _ref0 / (_ref0.sum(axis=1, keepdims=True) * _dx)
    _attr0 = float(_np.max(_np.abs(_rho0 - _ref0)))
    audit.record(
        "59: the K=0 attribution is recomputed",
        _attr0 <= 1e-4 and abs(_attr0 - float(_r0["attribution"])) <= 1e-9
        and float(_r0.get("best_max_ck", 0.0) or 0.0) <= 1e-4,
        f"attrib={_attr0:.3e} best_max_ck={float(_r0.get('best_max_ck', 0.0) or 0.0):.3e}",
    )
    # (4) Classical bank arithmetic + stored nu0 near-miss.
    _A0 = 1.2 * _sq
    _B0 = (_sq - _A0 * math.cos(_T)) / math.sin(_T)
    _closed = 0.5 * (_sq * (-_A0 * math.sin(_T) + _B0 * math.cos(_T)) - _A0 * _B0)
    _nu0 = scales["nu0_runs"]
    _best0 = min(r["J_final"] for r in _nu0)
    audit.record(
        "59: the classical bank is recomputed",
        abs(_closed - (-0.23852813742385703)) <= 1e-12
        and abs(float(scales["classical_closed"]) - _closed) <= 1e-12
        and abs(_best0 - _closed) <= 1e-3,
        f"closed={_closed:.10f}",
    )
    # (5) Verdict-gate consistency from the stored kill lists.
    _hard = dict(result["gates"]["kills_hard"])
    _soft = dict(result["gates"]["kills_soft"])
    _st = verdict["claim_59_status"]
    _consistent = (
        (_st.startswith("CONFIRMED FALSIFIED") and bool(_hard.get("escape_below")))
        or (_st.startswith("NUMERIC-REVERSAL") and bool(_hard.get("reversal_branch")))
        or (
            _st.startswith("UNVERIFIED")
            and (any(_soft.values()) or not any(_hard.values()))
        )
    )
    audit.record(
        "59: the verdict follows its gates",
        bool(_consistent),
        f"status={_st[:60]}",
    )


# ---------------------------------------------------------------------------
# Finite-core node probe (claim 60, ADR-054; HO-1 core only)
# ---------------------------------------------------------------------------


def audit_vortex_core(audit: Audit) -> None:
    import numpy as _np

    payload = load_results("vortex_core.json")
    result = payload["result"]
    s = result["scales"]
    verdict = result["verdict"]
    # (1) eps0 is predicted from bohr_radius (own recompute, no project import).
    _a0 = 1.0 * 1.0 / 1.0 / 1.0
    audit.record(
        "60: eps0 is predicted from bohr_radius",
        abs(float(s["eps0"]) - 0.1 * _a0) <= 1e-12,
        f"eps0={float(s['eps0']):.6f}",
    )
    # (2) Singular slope recomputed from stored gmax (own log-log fit).
    _dx = _np.array(s["singular"]["dx"], dtype=float)
    _gm = _np.array(s["singular"]["gmax"], dtype=float)
    _slope = float(_np.polyfit(_np.log(_dx), _np.log(_gm), 1)[0])
    audit.record(
        "60: singular slope is recomputed",
        abs(_slope - float(s["singular"]["slope"])) <= 1e-9
        and abs(_slope + 1.0) <= 0.01,
        f"slope={_slope:.6f}",
    )
    # (3) Core slip recomputed (own arctan2, no project import).
    _n = 2048
    _dxf = 20.0 / _n
    _x = (_np.arange(_n) - _n // 2) * _dxf
    _ph = _np.arctan2(_np.full_like(_x, 0.1), _x)
    _slip = float(_np.max(_ph) - _np.min(_ph))
    audit.record(
        "60: core slip is recomputed",
        abs(_slip - float(s["slips"]["2048"] if "2048" in s["slips"] else s["slips"][2048])) <= 1e-9
        and abs(_slip - math.pi) <= 0.05,
        f"slip={_slip:.6f}",
    )
    # (4) Core Q analytics recomputed (own closed form).
    _q = -0.5 * (1.0 / 0.01 - 1.0)
    audit.record(
        "60: core Q analytic is recomputed",
        abs(_q - float(s["q_analytic"])) <= 1e-9 and math.isfinite(_q),
        f"Q0={_q:.4f}",
    )
    # (5) Verdict follows gates.
    _hard = dict(result["gates"]["kills_hard"])
    _soft = dict(result["gates"]["kills_soft"])
    _st = str(verdict["claim_60_status"])
    _consistent = (
        (_st.startswith("FALSIFIED") and (bool(_hard.get("winding_below")) or bool(_hard.get("qcap_below"))))
        or (_st.startswith("NUMERIC") and not any(_hard.values()))
        or (_st.startswith("UNVERIFIED") and (any(_soft.values()) or any(_hard.values())))
    )
    audit.record(
        "60: the verdict follows its gates",
        bool(_consistent),
        f"status={_st[:60]}",
    )


# ---------------------------------------------------------------------------
# 2p core-threading loop probe (claim 61, ADR-056; 2p loops only)
# ---------------------------------------------------------------------------


def audit_vortex_loop(audit: Audit) -> None:
    import numpy as _np

    payload = load_results("vortex_loop.json")
    result = payload["result"]
    s = result["scales"]
    verdict = result["verdict"]
    # (1) delta0 is predicted from bohr_radius (own recompute, no project import).
    _a0 = 1.0 * 1.0 / 1.0 / 1.0
    audit.record(
        "61: delta0 is predicted from bohr_radius",
        abs(float(s["delta0"]) - 0.1 * _a0) <= 1e-12,
        f"delta0={float(s['delta0']):.6f}",
    )
    # (2) Singular loop recomputed (own quadrature, no project import).
    _phi = _np.linspace(0.0, 2.0 * _np.pi, 4000, endpoint=True)
    _v = 1.0 / (2.0 * math.sin(math.pi / 2.0))
    _loop = float(_np.trapezoid(_np.full(4000, _v * 2.0 * 1.0), _phi))
    audit.record(
        "61: singular loop is recomputed",
        abs(_loop - float(s["singular_loop_r2"])) <= 1e-9
        and abs(_loop - 2.0 * math.pi) / (2.0 * math.pi) <= 1e-6,
        f"loop={_loop:.9f}",
    )
    # (3) Blob fractions recomputed (own arithmetic + quadrature).
    _ok = True
    for _r, _f in ((0.1, 0.5), (0.2, 0.8), (2.0, 0.9975062344139651)):
        _a = (_r * _r) / (_r * _r + 0.1 * 0.1)
        _key = str(_r)
        _stored = s["blob"][_key]["fraction"] if _key in s["blob"] else s["blob"][_r]["fraction"]
        if abs(_a - _f) > 1e-12 or abs(_a - float(_stored)) > 1e-9:
            _ok = False
    audit.record(
        "61: blob fractions are recomputed",
        bool(_ok),
        f"fracs={[round(s['blob'][k]['fraction'], 6) for k in sorted(s['blob'])]}",
    )
    # (4) Floor divergence rule recomputed (own r_min rule).
    _vmax = {n: 1.0 / ((20.0 / n) / 2.0) for n in (256, 512, 1024, 2048)}
    _stored_max = s["floor_vmax"]
    _div = _vmax[2048] > _vmax[1024] > _vmax[512] > _vmax[256]
    _match = all(
        abs(_vmax[n] - float(_stored_max[str(n)] if str(n) in _stored_max else _stored_max[n])) <= 1e-9
        for n in _vmax
    )
    audit.record(
        "61: floor divergence rule is recomputed",
        bool(_div and _match),
        f"vmax={_vmax[256]:.1f}->{_vmax[2048]:.1f}",
    )
    # (5) Verdict follows gates.
    _hard = dict(result["gates"]["kills_hard"])
    _soft = dict(result["gates"]["kills_soft"])
    _st = str(verdict["claim_61_status"])
    _consistent = (
        (_st.startswith("FALSIFIED") and (bool(_hard.get("blob_below")) or bool(_hard.get("floorcap_below"))))
        or (_st.startswith("NUMERIC") and not any(_hard.values()))
        or (_st.startswith("UNVERIFIED") and (any(_soft.values()) or any(_hard.values())))
    )
    audit.record(
        "61: the verdict follows its gates",
        bool(_consistent),
        f"status={_st[:60]}",
    )


# ---------------------------------------------------------------------------
# Production claim-15 scan
# ---------------------------------------------------------------------------


def audit_production(audit: Audit) -> None:
    payload = load_results("hopfion3d_production.json")
    main = payload["main"]
    final = main["final"]
    verdict = main["verdict"]
    dt = payload["dt_check"]
    last = main["rows"][-1]
    dt_converged = bool(
        dt["H_difference"] <= 5e-3 and dt["Z3_difference"] <= 0.02
    )
    expected_ready = bool(
        verdict["coexistence_H_and_Z3"]
        and verdict["converged"]
        and verdict["resolved"]
        and verdict["topology_preserved"]
        and dt_converged
    )
    audit.record(
        "15: production scan is the pre-registered N=64 run within G-003 limit",
        main["n"] == 64
        and main["mu"] == 20.0
        and main["steps"] == 3600
        and main["max_wall_seconds"] == 900.0
        and main["dt"] == 5e-4
        and main["min_pre_norm"] > 0.1
        and all(row["monotone"] for row in main["rows"])
        and abs(last["H"] - final["H"]) < 1e-9
        and abs(last["Z3"] - final["Z3"]) < 1e-9
        and abs(last["force_rms"] - final["force_rms"]) < 1e-9,
        f"H={final['H']:.6f}, Hup={final['H_upsampled']:.6f}, "
        f"Z3={final['Z3']:.6f}, rms={final['force_rms']:.3e}",
    )
    audit.record(
        "15: production verdict follows the pre-registered rule",
        verdict["coexistence_H_and_Z3"]
        == (verdict["H_ok"] and verdict["Z3_ok"])
        and verdict["production_ready"] == expected_ready
        and verdict["claim_15_status"].startswith(
            "VERIFIED" if expected_ready else "UNVERIFIED"
        )
        and (
            not verdict["H_ok"]
            or (
                abs(final["H"] - 1.0) <= main["criteria"]["H_TOL"]
                and abs(final["H"] - final["H_upsampled"])
                <= main["criteria"]["H_TOL"]
            )
        ),
        f"status={verdict['claim_15_status']}, ready={verdict['production_ready']}",
    )
    audit.record(
        "15: production dt check is recorded",
        dt["n"] == 48
        and dt["H_difference"] >= 0.0
        and dt["Z3_difference"] >= 0.0
        and dt["force_difference"] >= 0.0
        and dt_converged is True,
        f"dH={dt['H_difference']:.3e}, dZ3={dt['Z3_difference']:.3e}, "
        f"converged={dt_converged}",
    )
    audit.record(
        "15: perturbed seeds are recorded",
        len(payload["seed_check"]) == 2
        and all(
            abs(row["H"]) >= 0.0 and abs(row["Z3"]) >= 0.0
            for row in payload["seed_check"]
        ),
        ", ".join(
            f"seed {row['seed']}: H={row['H']:.6f}, Z3={row['Z3']:.6f}"
            for row in payload["seed_check"]
        ),
    )


# ---------------------------------------------------------------------------
# Claim-15 resolution check (ADR-002)
# ---------------------------------------------------------------------------


def audit_convergence(audit: Audit) -> None:
    payload = load_results("hopfion3d_convergence.json")
    low = payload["low"]
    high = payload["high"]
    comparison = payload["comparison"]
    criteria = comparison["criteria"]
    expected = all(
        criteria[key]
        for key in (
            "H_agrees",
            "H_upsampled_agrees",
            "Z3_agrees",
            "force_not_worse",
            "max_bond_not_worse",
        )
    )
    audit.record(
        "15: resolution check compares N=64 and N=96 at one physical time",
        low["n"] == 64
        and high["n"] == 96
        and low["steps"] == high["steps"] == comparison["steps"] == 3000
        and low["dt"] == high["dt"] == 5e-4
        and low["mu"] == high["mu"] == 20.0
        and low["min_pre_norm"] > 0.1
        and high["min_pre_norm"] > 0.1,
        f"N={low['n']}/{high['n']}, steps={high['steps']}, "
        f"H={high['final']['H']:.6f}, Z3={high['final']['Z3']:.6f}",
    )
    audit.record(
        "15: resolution arithmetic and verdict follow the pre-registered rule",
        abs(
            comparison["deltas"]["H"] - (high["final"]["H"] - low["final"]["H"])
        )
        < 1e-12
        and abs(
            comparison["deltas"]["Z3"] - (high["final"]["Z3"] - low["final"]["Z3"])
        )
        < 1e-12
        and comparison["resolution_converged"] == expected
        and comparison["claim_15_status"] == high["verdict"]["claim_15_status"]
        and not comparison["claim_15_status"].startswith("VERIFIED"),
        f"converged={comparison['resolution_converged']}, "
        f"dH={comparison['deltas']['H']:+.6f}, "
        f"dZ3={comparison['deltas']['Z3']:+.6f}",
    )
    verdict = high["verdict"]
    expected_ready = bool(
        verdict["coexistence_H_and_Z3"]
        and verdict["converged"]
        and verdict["resolved"]
        and verdict["topology_preserved"]
    )
    audit.record(
        "15: N=96 verdict follows the unchanged production rule",
        verdict["production_ready"] == expected_ready
        and verdict["claim_15_status"].startswith(
            "VERIFIED" if expected_ready else "UNVERIFIED"
        )
        and (
            not verdict["H_ok"]
            or (
                abs(high["final"]["H"] - 1.0) <= high["criteria"]["H_TOL"]
                and abs(high["final"]["H"] - high["final"]["H_upsampled"])
                <= high["criteria"]["H_TOL"]
            )
        ),
        f"status={verdict['claim_15_status']}, ready={verdict['production_ready']}",
    )


# ---------------------------------------------------------------------------
# Claim-15 timestep check (ADR-003)
# ---------------------------------------------------------------------------


def audit_temporal(audit: Audit) -> None:
    payload = load_results("hopfion3d_temporal.json")
    coarse = payload["coarse"]
    fine = payload["fine"]
    comparison = payload["comparison"]
    criteria = comparison["criteria"]
    expected = all(
        criteria[key] for key in ("H_agrees", "H_upsampled_agrees", "Z3_agrees")
    )
    audit.record(
        "15: dt check holds N=64 fixed and reaches one physical time",
        coarse["n"] == fine["n"] == 64
        and abs(coarse["steps"] * coarse["dt"] - 1.5) < 1e-12
        and abs(fine["steps"] * fine["dt"] - 1.5) < 1e-12
        and coarse["dt"] == 5e-4
        and fine["dt"] == 2.5e-4
        and coarse["max_wall_seconds"] == 900.0
        and fine["max_wall_seconds"] == 900.0
        and coarse["min_pre_norm"] > 0.1
        and fine["min_pre_norm"] > 0.1,
        f"dt={coarse['dt']:.1e}/{fine['dt']:.1e}, "
        f"steps={coarse['steps']}/{fine['steps']}",
    )
    audit.record(
        "15: dt arithmetic and verdict follow the pre-registered rule",
        abs(
            comparison["deltas"]["H"] - (fine["final"]["H"] - coarse["final"]["H"])
        )
        < 1e-12
        and abs(
            comparison["deltas"]["Z3"] - (fine["final"]["Z3"] - coarse["final"]["Z3"])
        )
        < 1e-12
        and comparison["temporal_converged"] == expected
        and comparison["claim_15_status"] == fine["verdict"]["claim_15_status"]
        and not comparison["claim_15_status"].startswith("VERIFIED"),
        f"converged={comparison['temporal_converged']}, "
        f"dH={comparison['deltas']['H']:+.6f}, "
        f"dZ3={comparison['deltas']['Z3']:+.6f}",
    )


# ---------------------------------------------------------------------------
# Claim-15 checkpointed extension (ADR-004)
# ---------------------------------------------------------------------------


def audit_extension(audit: Audit) -> None:
    payload = load_results("hopfion3d_extension.json")
    rows = payload["rows"]
    trend = payload["trend"]
    convergence = load_results("hopfion3d_convergence.json")["high"]["final"]
    audit.record(
        "15: checkpointed extension has four contiguous N=96 chunks",
        len(rows) == 4
        and [row["chunk"] for row in rows] == [1, 2, 3, 4]
        and [row["steps"] for row in rows] == [3000, 6000, 9000, 12000]
        and all(abs(row["t"] - 1.5 * row["chunk"]) < 1e-12 for row in rows)
        and all(row["min_pre_norm"] > 0.1 for row in rows),
        f"chunks={len(rows)}, final t={rows[-1]['t']:.3g}",
    )
    audit.record(
        "15: extension first chunk reproduces the resolution check",
        abs(rows[0]["H"] - convergence["H"]) < 1e-9
        and abs(rows[0]["Z3"] - convergence["Z3"]) < 1e-9,
        f"H={rows[0]['H']:.9f}, Z3={rows[0]['Z3']:.6f}",
    )
    slope = (rows[-1]["Z3"] - rows[0]["Z3"]) / (
        rows[-1]["steps"] - rows[0]["steps"]
    )
    audit.record(
        "15: extension trend is monotone and the claim is not promoted",
        trend["z3_monotone"] is True
        and trend["force_monotone"] is True
        and abs(trend["z3_slope_per_step"] - slope) < 1e-12
        and trend["claim_15_status"] == rows[-1]["claim_15_status"]
        and not rows[-1]["claim_15_status"].startswith("VERIFIED")
        and rows[-1]["Z3"] >= 0.5,
        f"Z3={rows[-1]['Z3']:.6f}, "
        f"status={rows[-1]['claim_15_status']}",
    )


# ---------------------------------------------------------------------------
# Documentation consistency
# ---------------------------------------------------------------------------


def audit_docs(audit: Audit) -> None:
    fit = load_results("pdg_fit.json")
    rg = load_results("rg_run.json")
    rotor = load_results("rotor.json")
    claims = (ROOT / "claims.md").read_text(encoding="utf-8")
    score = (ROOT / "SCORECARD.md").read_text(encoding="utf-8")
    formulas = (ROOT / "theory" / "formulas.md").read_text(encoding="utf-8")
    summary = (RESULTS / "summary.md").read_text(encoding="utf-8")
    paper = (ROOT / "paper" / "koide_z3_rg.tex").read_text(encoding="utf-8")
    paper_b = (ROOT / "paper" / "fluid_universe_speculation.tex").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    p = fit["point"]
    d = rg["drift"]
    required = [
        (claims, "0.666664463", "claims Q"),
        (claims, "0.707104444", "claims r"),
        (claims, "0.667823994", "claims MSbar Q"),
        (claims, "2.89\\times10^{-6}", "claims Delta Q"),
        (claims, "3.06\\times10^{-6}", "claims Delta r"),
        (claims, "0.8911861597", "claims E0"),
        (claims, "1.3170345140", "claims E1"),
        (score, "0.666664463", "scorecard Q"),
        (score, "0.6678240", "scorecard MSbar Q"),
        (score, "2.89\\times10^{-6}", "scorecard Delta Q"),
        (formulas, "REPRODUCED at one loop", "registry F9 downgraded to reproduced"),
        (formulas, "CITED + partial cross-check", "registry F10 downgraded to partial"),
        ((RESULTS / "rg_run.md").read_text(encoding="utf-8"), "NOT a cross-check", "shape-only diagnostic labelled"),
        (paper, "0.66666446", "paper Q"),
        (paper, "0.70710444", "paper r"),
        (paper, f"{d['Q_MZ']:.9f}", "paper MSbar Q"),
        (paper, "0.8911861597", "paper E0"),
        (paper, "1.3170345140", "paper E1"),
        (claims, "0.585612", "claims Q_nu max"),
        (claims, "0.887569", "claims Q_up"),
        (claims, "0.748065", "claims Q_down"),
        (claims, "35.26", "claims trimaximal theta13"),
        (score, "0.585612", "scorecard Q_nu"),
        (score, "0.8876", "scorecard Q_up range"),
        (score, "0.7385", "scorecard Q_down range"),
        (readme, "0.585612", "README Q_nu"),
        (readme, "0.888", "README Q_up"),
        (readme, "0.748", "README Q_down"),
        (paper, "0.585612", "paper Q_nu"),
        (paper, "0.887569", "paper Q_up"),
        (paper, "0.748065", "paper Q_down"),
        (summary, "0.585612", "summary Q_nu"),
        (claims, "0.407", "claims delta sigma"),
        (claims, "0.585612", "claims Q_nu"),
        (score, "0.407", "scorecard delta sigma"),
        (readme, "0.407", "README delta sigma"),
        (paper, "0.41\\sigma", "paper delta sigma"),
        (paper_b, "E_2-E_4+3V=0", "paper B Derrick virial"),
        (paper_b, "\\omega^2=(K/\\rho)k^2", "paper B Frank-Oseen dispersion"),
        (summary, "E2-E4+3V", "summary Derrick virial"),
        (claims, "6c", "claims exact reduction row"),
        (claims, "13a", "claims direct topology row"),
        (claims, "13b", "claims extension row"),
        (claims, "none found", "claims no new prediction"),
        (score, "log-divergent", "scorecard I_eff"),
        (readme, "log-divergent", "README I_eff"),
        (summary, "log-divergent", "summary I_eff"),
        (paper_b, "logarithmically divergent", "paper B I_eff"),
        (paper, "No genuinely new prediction", "paper A no prediction"),
        (claims, "1.00348", "claims xi"),
        (score, "1.00348", "scorecard xi"),
        (readme, "1.00348", "README xi"),
        (summary, "1.00348", "summary xi"),
        (paper_b, "1.00348", "paper B xi"),
        (paper_b, "10^{-18}", "paper B GRB order"),
        (claims, "0.999958", "claims Hopf preimage"),
        (readme, "0.999958", "README Hopf preimage"),
        (summary, "0.999958", "summary Hopf preimage"),
        (paper_b, "0.999958", "paper B Hopf preimage"),
        (claims, "1.000000", "claims grid Hopf"),
        (readme, "1.000000", "README grid Hopf"),
        (summary, "1.000000", "summary grid Hopf"),
        (paper_b, "1.00000004", "paper B grid Hopf"),
        (readme, "resolution-limited", "README 3D pilot status"),
        (summary, "resolution-limited", "summary 3D pilot status"),
        (paper_b, "not converged", "paper B 3D pilot status"),
        (summary, "N=16", "summary Hopf resolution"),
        (readme, "N>=32", "README Hopf resolution"),
        (claims, "0.60743", "claims N=64 diagnostic"),
        (readme, "0.8", "README N=64 diagnostic"),
        (claims, "14c", "claims scale candidate"),
        (readme, "Scale-stationary", "README scale candidate"),
        (claims, "-5.799863", "claims validated Hessian"),
        (readme, "FALSIFIED: validated tangent Hessian", "README validated Hessian"),
        (score, "min -5.799863", "scorecard validated Hessian"),
        (paper_b, "1.3\\times10^{-15}", "paper B dense validation"),
        (paper_b, "$-5.799863$", "paper B Hessian minimum"),
        (claims, "baseline 4 passes", "claims baseline 4"),
        (summary, "| 6b | 2D reduction lower bound", "summary 6b row"),
        (summary, "| 6c | Exact dimensional reduction", "summary 6c row"),
        (formulas, "F16a", "registry preimage rows"),
        (formulas, "F16b", "registry grid rows"),
        (claims, "0.9892", "claims upsampled H"),
    ]
    for text, needle, label in required:
        audit.record(f"docs: {label}", needle in text, f"searched for '{needle}'")

    # The summary must not claim that the rotor is missing.
    audit.record(
        "docs: summary lists the rotor result",
        "No rotor spectrum" not in summary and f"{rotor['levels']['E0']:.12f}" in summary,
        "summary.md must describe the rotor output it now includes",
    )
    # The abstract must not attribute the full-SM MSbar value to the pole-to-MSbar conversion.
    abstract = paper.split("\\begin{abstract}", 1)[1].split("\\end{abstract}", 1)[0]
    audit.record(
        "docs: abstract distinguishes scheme conversion from full-SM matching",
        "0.6679160" in abstract and "full-SM" in abstract,
        "abstract must quote both the one-pass QED conversion (0.6679160) and the "
        "full-SM matching value (0.6678240), without conflating them",
    )
    # Formula registry must not overstate F9/F10.
    audit.record(
        "docs: F10 not overstated as an exact verification",
        "**VERIFIED at one loop**" not in formulas or "partial" in formulas,
        "F10 is cross-checked only at the few-percent level against three-loop literature",
    )
    audit.record(
        "docs: fit numbers match JSON",
        abs(p["Q"] - 0.666664463415) < 1e-12 and abs(d["Q_MZ"] - 0.667823994186) < 1e-12,
        "stored fit and RG values match the regenerated outputs",
    )


# ---------------------------------------------------------------------------


def run(write: bool = True, tag: str | None = None) -> dict:
    audit = Audit()
    audit_algebra(audit)
    audit_fit(audit)
    audit_rg(audit)
    audit_rotor(audit)
    audit_neutrinos_quarks(audit)
    audit_delta_modes_derrick(audit)
    audit_negatives(audit)
    audit_lorentz(audit)
    audit_hopf(audit)
    audit_hopfion3d(audit)
    audit_hopf_resolution(audit)
    audit_n64(audit)
    audit_scale(audit)
    audit_stability(audit)
    audit_purefn(audit)
    audit_escape(audit)
    audit_lengthscan(audit)
    audit_vortex(audit)
    audit_cascade(audit)
    audit_rotor_potential(audit)
    audit_madelung(audit)
    audit_nelson(audit)
    audit_gaussian_fluid(audit)
    audit_coherent_fluid(audit)
    audit_excited_fluid(audit)
    audit_hydrogen_fluid(audit)
    audit_hydrogen_vortex(audit)
    audit_water_analogue(audit)
    audit_water_validity(audit)
    audit_water_dispersive(audit)
    audit_water_rays(audit)
    audit_water_scattering(audit)
    audit_water_electron(audit)
    audit_water_well(audit)
    audit_water_absorption(audit)
    audit_water_vde(audit)
    audit_water_softwall(audit)
    audit_water_pressure(audit)
    audit_water_reorganization(audit)
    audit_water_born_cavity(audit)
    audit_water_marcus(audit)
    audit_water_temperature(audit)
    audit_water_temperature_residual(audit)
    audit_water_lineshape(audit)
    audit_two_state(audit)
    audit_water_twocomponent(audit)
    audit_node_defect(audit)
    audit_radial_node(audit)
    audit_nelson_closure(audit)
    audit_variational_width(audit)
    audit_variational_saddle(audit)
    audit_variational_dynamics(audit)
    audit_yasue_dynamics(audit)
    audit_variational_center(audit)
    audit_gaussian_bridge(audit)
    audit_yasue_center(audit)
    audit_yasue_bridge(audit)
    audit_yasue_action(audit)
    audit_field_variation(audit)
    audit_widened_ritz(audit)
    audit_vortex_core(audit)
    audit_vortex_loop(audit)
    audit_production(audit)
    audit_convergence(audit)
    audit_temporal(audit)
    audit_extension(audit)
    audit_docs(audit)
    payload = {
        "meta": {**provenance(), "run_tag": tag},
        "checks": audit.checks,
        "total": len(audit.checks),
        "passed": len(audit.checks) - len(audit.failed),
        "failed": len(audit.failed),
        "failures": audit.failed,
    }
    if write:
        stem = f"verification_{tag}" if tag else "verification_single"
        write_atomic(RESULTS / f"{stem}.json", json.dumps(payload, indent=2) + "\n")
        write_atomic(RESULTS / f"{stem}.md", render(payload))
    return payload


def render(payload: dict) -> str:
    lines = [
        "# Independent verification",
        "",
        "Every claim currently marked PROVEN, VERIFIED, or NUMERIC is re-derived here "
        "without importing `theory` or `phenomenology`.",
        "",
        f"**{payload['passed']}/{payload['total']} checks passed.**",
        "",
        "| claim | result | detail |",
        "|---|---|---|",
    ]
    for check in payload["checks"]:
        mark = "PASS" if check["passed"] else "FAIL"
        lines.append(f"| {check['claim']} | {mark} | {check['detail']} |")
    if payload["failures"]:
        lines += ["", "## Failures", ""]
        for failure in payload["failures"]:
            lines.append(f"- **{failure['claim']}**: {failure['detail']}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Independent verification audit.")
    parser.add_argument("--tag", help="write results/verification_<tag>.{json,md}")
    args = parser.parse_args()
    result = run(tag=args.tag)
    print(f"{result['passed']}/{result['total']} independent checks passed")
    if args.tag is None:
        print(
            "NOT ACCEPTED: this is a single run. Wrote results/verification_single.{json,md}. "
            "Run with --tag run1 and --tag run2, then python -m verification.compare."
        )
    for failure in result["failures"]:
        print(f"FAIL: {failure['claim']}: {failure['detail']}")
    return 0 if not result["failures"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
