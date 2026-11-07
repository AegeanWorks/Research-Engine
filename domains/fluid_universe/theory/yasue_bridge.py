"""Pinned-endpoint Yasue bridge: the c<0 Pinney analytic family (claim 56, ADR-048).

Zero free parameters, no full-field claims. The Yasue width ODE

    s_ddot = -nu^2/s^3 - omega^2*s

is the Pinney equation with NEGATIVE coefficient c = -nu^2. Its
stationary paths have the Pinney FORM s^2 = A*u^2 + 2*B*u*v + C*v^2
(u = cos(omega*t), v = sin(omega*t)/omega, Wronskian 1) with the
ODE-imposed constraint A*C - B^2 = -nu^2 (not fitted). Endpoint
pinning s(0) = s0, s(T) = sT selects the admissible positive
branches algebraically. At the recorded point (s0 = sT = sigma_q,
T = pi/4, omega = 1) the quadratic gives disc = 3 with
B_1 = 0.3660254038 (admissible: the recorded claim-55 arc) and
B_2 = -1.3660254038 (inadmissible: s^2 < 0 mid-interval, reported
as the killed sibling, never hidden).

The omega = 2 scaling preserves the branch structure exactly (same
monic B equation, same normalized bulge). The nu -> 0 limit with
fixed endpoints is the oscillator bridge
s(t) = a*(cos(wt) + alpha*sin(wt)), alpha = sqrt(2)-1, whose
max = midpoint = 1.0823922003*a is the classical bank.

Trial-class BVP analysis only. No analytic stability proof beyond
the Jacobi leg, no full-field claim.
"""

from __future__ import annotations

import math

import numpy as np

GRID_N = 401
RESID_TOL = 1e-9
FD_TOL = 1e-6
ATTRIB_TOL = 1e-4
BASE = {"omega": 1.0, "hbar": 1.0, "mass": 1.0}
RECORDED_S0_FACTOR = 1.0
NU_SERIES = (0.5, 0.25, 0.125, 0.0)
FIXED_A = math.sqrt(0.5)
S1_S0_FACTORS = (1.0, 1.1, 1.2)
S1_HORIZON_FACTORS = (2.0 / 3.0, 1.0, 4.0 / 3.0)
WIDTH_STARTS = ("const_s0", "const_sT", "linear", "bump")
BUMP_AMP = 0.3

# 8th-order central second-derivative weights / h^2.
_FD8 = (
    -1.0 / 560.0,
    8.0 / 315.0,
    -1.0 / 5.0,
    8.0 / 5.0,
    -205.0 / 72.0,
    8.0 / 5.0,
    -1.0 / 5.0,
    8.0 / 315.0,
    -1.0 / 560.0,
)


def diffusivity(hbar: float, mass: float) -> float:
    if hbar <= 0.0 or mass <= 0.0:
        raise ValueError("hbar and mass must be positive")
    return hbar / (2.0 * mass)


def horizon(omega: float) -> float:
    if omega <= 0.0:
        raise ValueError("omega must be positive")
    return math.pi / (4.0 * omega)


def pinney_coeffs_yasue(
    s0: float,
    sT: float,
    horizon_T: float,
    omega: float,
    hbar: float,
    mass: float,
    nu: float | None = None,
) -> tuple:
    """Solve the c<0 endpoint algebra. Returns (branches, disc_norm).

    Each branch is {"A","B","C","admissible","min_s2"}. From
    A*(sT^2-A*a2-B*b2)/c2 - B^2 = -nu^2 with a2 = uT^2,
    b2 = 2*uT*vT, c2 = vT^2, the monic quadratic in B is
    B^2 + (qb/qa)*B + qc/qa = 0 with qa = vT^2, qb = 2*A*uT*vT,
    qc = A^2*uT^2 - A*sT^2 - nu^2*vT^2 (same form as the G-M
    span-54 elimination; the -nu^2 enters through the constraint).
    """
    if nu is None:
        nu = diffusivity(hbar, mass)
    uT = math.cos(omega * horizon_T)
    vT = math.sin(omega * horizon_T) / omega
    A = s0 * s0
    qa = vT * vT
    if abs(qa) < 1e-15:
        raise ValueError("degenerate endpoint basis (vT == 0)")
    qb = 2.0 * A * uT * vT
    qc = A * A * uT * uT - A * sT * sT - nu * nu * vT * vT
    disc = (qb / qa) * (qb / qa) - 4.0 * (qc / qa)
    if disc < 0.0:
        return [], disc
    out = []
    for sgn in (1.0, -1.0):
        bval = (-qb / qa + sgn * math.sqrt(disc)) / 2.0
        cval = (bval * bval - nu * nu) / A
        out.append({"A": A, "B": bval, "C": cval})
    t = np.linspace(0.0, horizon_T, 2001)
    u = np.cos(omega * t)
    v = np.sin(omega * t) / omega
    for branch in out:
        s2 = (
            branch["A"] * u * u
            + 2.0 * branch["B"] * u * v
            + branch["C"] * v * v
        )
        branch["min_s2"] = float(np.min(s2))
        branch["admissible"] = bool(branch["min_s2"] > 0.0)
    out.sort(key=lambda d: (not d["admissible"], abs(d["B"])))
    return out, disc


def pinney_path(coeffs: dict, t_values: np.ndarray, omega: float) -> np.ndarray:
    from domains.fluid_universe.theory.gaussian_bridge import pinney_path as _pinney

    return _pinney(coeffs, t_values, omega)


def fd_ode_residual(
    coeffs: dict,
    omega: float,
    hbar: float,
    mass: float,
    horizon_T: float,
    nu: float | None = None,
    n: int = 2001,
) -> dict:
    """8th-order finite-difference check of s_ddot + nu^2/s^3 + w^2 s = 0."""
    if nu is None:
        nu = diffusivity(hbar, mass)
    t = np.linspace(0.0, horizon_T, n)
    h = float(t[1] - t[0])
    s = pinney_path(coeffs, t, omega)
    kernel = np.array(_FD8) / (h * h)
    s_ddot = np.convolve(s, kernel, mode="valid")
    s_int = s[4:-4]
    residual = s_ddot + nu * nu / (s_int**3) + omega * omega * s_int
    return {
        "max_abs": float(np.max(np.abs(residual))),
        "rms": float(np.sqrt(np.mean(residual**2))),
    }


def _discrete_residual_width(
    interior: np.ndarray,
    omega: float,
    hbar: float,
    mass: float,
    nu: float,
    dt: float,
    s0: float,
    sT: float,
) -> np.ndarray:
    interior = np.asarray(interior, dtype=float)
    full = np.concatenate([[s0], interior, [sT]])
    left, mid, right = full[:-2], full[1:-1], full[2:]

    def _pot(x: np.ndarray) -> np.ndarray:
        return mass * nu * nu / (x * x * x) + mass * omega * omega * x

    return (
        mass * (mid - left) / dt**2
        - mass * (right - mid) / dt**2
        - 0.5 * _pot(0.5 * (left + mid))
        - 0.5 * _pot(0.5 * (mid + right))
    )


def newton_width(
    s0: float,
    sT: float,
    horizon_T: float,
    omega: float = 1.0,
    hbar: float = 1.0,
    mass: float = 1.0,
    nu: float | None = None,
    n: int = GRID_N,
    steps: int = 12,
    starts: tuple = WIDTH_STARTS,
) -> list:
    """Width-only BVP Newton solves from the given starts (Yasue sign)."""
    if nu is None:
        nu = diffusivity(hbar, mass)
    dt = horizon_T / (n - 1)
    grid = np.linspace(dt / horizon_T, 1.0 - dt / horizon_T, n - 2)
    base = s0 + (sT - s0) * grid
    inits = {
        "const_s0": np.full(n - 2, s0),
        "const_sT": np.full(n - 2, sT),
        "linear": base.copy(),
        "bump": base + BUMP_AMP * np.sin(math.pi * grid),
    }
    out = []
    for name in starts:
        interior = inits[name].copy()
        converged = True
        try:
            for _ in range(steps):
                residual = _discrete_residual_width(
                    interior, omega, hbar, mass, nu, dt, s0, sT
                )
                if float(np.max(np.abs(residual))) < RESID_TOL:
                    break
                h = 1e-7
                cols = []
                for j in range(len(interior)):
                    pert = np.zeros_like(interior)
                    pert[j] = h
                    cols.append(
                        (
                            _discrete_residual_width(
                                interior + pert,
                                omega,
                                hbar,
                                mass,
                                nu,
                                dt,
                                s0,
                                sT,
                            )
                            - residual
                        )
                        / h
                    )
                interior = interior - np.linalg.solve(
                    np.column_stack(cols), residual
                )
        except np.linalg.LinAlgError:
            converged = False
        final = _discrete_residual_width(
            interior, omega, hbar, mass, nu, dt, s0, sT
        )
        if float(np.max(np.abs(final))) > RESID_TOL:
            converged = False
        out.append(
            {
                "start": name,
                "interior": [float(v) for v in interior],
                "max_residual": float(np.max(np.abs(final))),
                "converged": bool(converged),
                "max_sigma": float(np.max(interior)),
                "min_sigma": float(np.min(interior)),
            }
        )
    return out


def attribution_diff(analytic: list, recorded: list) -> float:
    a = np.asarray(analytic, dtype=float)
    b = np.asarray(recorded, dtype=float)
    return float(np.max(np.abs(a - b)))


def jacobi_first_zero_yasue(
    t_values: np.ndarray,
    s_values: np.ndarray,
    omega: float,
    nu: float,
    n: int = 20001,
) -> float | None:
    """First conjugate zero of u'' + Q u = 0 with Yasue Q = -3nu^2/s^4 + w^2.

    Same integrator structure as the span-54 Jacobi leg; the Q sign is
    the load-bearing difference (never reuse the G-M function here).
    """
    t = np.linspace(float(t_values[0]), float(t_values[-1]), n)
    dt = float(t[1] - t[0])
    s = np.interp(t, np.asarray(t_values, dtype=float), np.asarray(s_values, dtype=float))
    u_prev, v_prev = 0.0, 1.0
    for i in range(1, n):
        q = -3.0 * nu * nu / max(float(s[i - 1]), 1e-12) ** 4 + omega * omega
        v_new = v_prev + dt * (-q * u_prev)
        u_new = u_prev + dt * v_new
        if u_new == 0.0 or (u_prev < 0.0) != (u_new < 0.0):
            return float(t[i])
        u_prev, v_prev = u_new, v_new
    return None


def nu_limit_bridge(alpha_T: float = math.pi / 4.0) -> dict:
    """Closed-form nu=0 fixed-endpoint bridge (classical bank).

    s(t) = a*(cos(wt) + alpha*sin(wt)), alpha = (1-cos wT)/sin wT.
    """
    alpha = (1.0 - math.cos(alpha_T)) / math.sin(alpha_T)
    peak = math.sqrt(1.0 + alpha * alpha)
    return {"alpha": alpha, "peak_ratio": peak, "wT": alpha_T}
