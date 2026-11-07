"""Variational dynamics reproduces Ermakov (claim 51, ADR-043).

Zero free parameters, no full-field dynamics asserted. For the
time-dependent Gaussian trial (rho = N(0, sigma(t)^2),
v = (sigma_dot/sigma) x) with nu = hbar/(2*m), the path action is

    J[sigma] = int_0^T [m*sdot^2/2 - m*nu^2/(2*s^2) - m*omega^2*s^2/2] dt,

whose Euler-Lagrange equation is exactly the Ermakov equation
sddot = nu^2/s^3 - omega^2*s (nu^2 = hbar^2/(4*m^2)). Linearized at
s_q^2 = nu/omega the Jacobi frequency is 2*omega (period pi/omega);
the first conjugate point is at pi/(2*omega), so the frozen horizon
T = pi/4 carries no conjugate ambiguity (Jacobi hypothesis
satisfied; weak-local-positivity regime — global uniqueness is probed
empirically via multi-start Newton, never asserted).

The discrete action uses the midpoint Lagrangian with N = 401 nodes
(dt = T/400); Dirichlet ends are pinned. Newton targets discrete-EL
roots (not descent minima). The static Ritz maximum vs dynamic
stability subtlety is decided by Jacobi, never by curvature signs;
no global stability is claimed.
"""

from __future__ import annotations

import math

import numpy as np

GRID_N = 401
HORIZON_FRACTION = 0.25  # T = pi/4 = half the first conjugate time pi/2
START_FACTORS = (1.0, 1.05, 0.95, 1.5)


GRID_N = 401
HORIZON_FRACTION = 0.25
BASE = {"omega": 1.0, "hbar": 1.0, "mass": 1.0}
START_FACTORS = (1.0, 1.05, 0.95, 1.5)
TEST_SIGMAS = (0.5, 0.7071067811865476, 1.0, 1.5)
RELEASE_FACTORS = (1.01, 0.99, 1.1)


def diffusivity(hbar: float, mass: float) -> float:
    if hbar <= 0.0 or mass <= 0.0:
        raise ValueError("hbar and mass must be positive")
    return hbar / (2.0 * mass)


def horizon(omega: float) -> float:
    if omega <= 0.0:
        raise ValueError("omega must be positive")
    return math.pi / (4.0 * omega)


def grid(n: int = GRID_N, omega: float = 1.0) -> np.ndarray:
    if n < 3:
        raise ValueError("need at least 3 grid points")
    return np.linspace(0.0, horizon(omega), n)


def acceleration(s: float, omega: float, hbar: float, mass: float) -> float:
    """Ermakov acceleration nu^2/s^3 - omega^2*s (V1 re-derives)."""
    if s <= 0.0 or omega <= 0.0:
        raise ValueError("s and omega must be positive")
    nu = diffusivity(hbar, mass)
    return nu * nu / (s * s * s) - omega * omega * s


def repulsion_term(s: float, omega: float, hbar: float, mass: float) -> float:
    nu = diffusivity(hbar, mass)
    return nu * nu / (s * s * s)


def confining_term(s: float, omega: float, hbar: float, mass: float) -> float:
    return -omega * omega * s


def discrete_el_residual(
    interior: np.ndarray,
    omega: float,
    hbar: float,
    mass: float,
    dt: float,
    endpoint: float = 0.0,
) -> np.ndarray:
    """Discrete Euler-Lagrange residuals (midpoint Lagrangian).

    ``endpoint`` is the pinned Dirichlet value at both ends; pass the
    fixed width sigma_q (never zero: the action is singular there).
    """
    interior = np.asarray(interior, dtype=float)
    nu = diffusivity(hbar, mass)
    full = np.concatenate([[endpoint], interior, [endpoint]])
    left = full[:-2]
    mid = full[1:-1]
    right = full[2:]
    # Midpoint discrete Lagrangian:
    # Ld(a,b) = [m*((b-a)/dt)^2/2 - U((a+b)/2)] * dt,
    # U(s) = m*nu^2/(2*s^2) + m*omega^2*s^2/2.
    def potential(q: np.ndarray) -> np.ndarray:
        return (
            mass * nu * nu / (2.0 * q * q) + 0.5 * mass * omega * omega * q * q
        )

    def potential_prime(q: np.ndarray) -> np.ndarray:
        return -mass * nu * nu / (q * q * q) + mass * omega * omega * q

    mid_left = 0.5 * (left + mid)
    mid_right = 0.5 * (mid + right)
    residual = (
        mass * (mid - left) / (dt * dt)
        - mass * (right - mid) / (dt * dt)
        - 0.5 * potential_prime(mid_left)
        - 0.5 * potential_prime(mid_right)
    )
    return residual


def newton_extremum(
    start_factor: float,
    omega: float = 1.0,
    hbar: float = 1.0,
    mass: float = 1.0,
    n: int = GRID_N,
    steps: int = 12,
) -> dict:
    """Newton on the discrete EL system from a constant-path start."""
    from domains.fluid_universe.theory.gaussian_fluid import quantum_width

    width = quantum_width(omega, hbar, mass)
    t = grid(n, omega)
    dt = float(t[1] - t[0])
    fixed = width
    interior = np.full(n - 2, fixed * start_factor)
    converged = True
    try:
        for _ in range(steps):
            residual = discrete_el_residual(
                interior, omega, hbar, mass, dt, endpoint=fixed
            )
            if float(np.max(np.abs(residual))) < 1e-12:
                break
            h = 1e-7
            columns = []
            for j in range(len(interior)):
                pert = np.zeros_like(interior)
                pert[j] = h
                columns.append(
                    (discrete_el_residual(
                        interior + pert, omega, hbar, mass, dt, endpoint=fixed
                    ) - residual) / h
                )
            jacobian = np.column_stack(columns)
            interior = interior - np.linalg.solve(jacobian, residual)
    except np.linalg.LinAlgError:
        converged = False
    final_residual = discrete_el_residual(
        interior, omega, hbar, mass, dt, endpoint=fixed
    )
    return {
        "start_factor": start_factor,
        "interior": [float(v) for v in interior],
        "max_deviation": float(np.max(np.abs(interior - fixed))),
        "max_residual": float(np.max(np.abs(final_residual))),
        "converged": bool(converged),
        "grid_n": n,
        "dt": dt,
    }


def release_period(
    factor: float,
    omega: float = 1.0,
    hbar: float = 1.0,
    mass: float = 1.0,
) -> dict:
    """Verlet release from width*factor; interpolated zero-crossing period."""
    from domains.fluid_universe.theory.gaussian_fluid import quantum_width

    width = quantum_width(omega, hbar, mass)
    dt = 0.001
    steps = int(8.0 * math.pi / dt) + 1
    s = width * factor
    v = 0.0
    crossings = []
    previous = s - width
    t = 0.0
    for _ in range(steps):
        acc = acceleration(s, omega, hbar, mass)
        v += 0.5 * dt * acc
        s += dt * v
        acc = acceleration(s, omega, hbar, mass)
        v += 0.5 * dt * acc
        t += dt
        current = s - width
        if previous < 0.0 <= current or previous > 0.0 >= current:
            frac = previous / (previous - current) if current != previous else 0.0
            crossings.append(t - dt + frac * dt)
            if len(crossings) >= 3:
                break
        previous = current
    period = crossings[-1] - crossings[0] if len(crossings) >= 3 else float("nan")
    return {"factor": factor, "crossings": crossings, "period": period}


TEST_SIGMAS = (0.5, 0.7071067811865476, 1.0, 1.5)
RELEASE_FACTORS = (1.01, 0.99, 1.1)


def term_match() -> dict:
    """Variational acceleration vs Ermakov RHS, whole and per-term."""
    from domains.fluid_universe.theory.gaussian_fluid import ermakov_rhs

    omega, hbar, mass = BASE["omega"], BASE["hbar"], BASE["mass"]
    rows = []
    for s in TEST_SIGMAS:
        own = acceleration(s, omega, hbar, mass)
        _, ermakov = ermakov_rhs(s, 0.0, omega, hbar, mass)
        rep_own = repulsion_term(s, omega, hbar, mass)
        rep_ermakov = hbar * hbar / (4.0 * mass * mass * s * s * s)
        conf = confining_term(s, omega, hbar, mass)
        rows.append(
            {
                "s": s,
                "own": own,
                "ermakov": float(ermakov),
                "abs": abs(own - float(ermakov)),
                "rel": abs(own - float(ermakov)) / max(abs(float(ermakov)), 1e-300),
                "rep_own": rep_own,
                "rep_ermakov": rep_ermakov,
                "rep_rel": abs(rep_own - rep_ermakov) / rep_ermakov,
                "conf": conf,
            }
        )
    max_abs = max(r["abs"] for r in rows)
    max_rel = max(r["rel"] for r in rows)
    max_rep_rel = max(r["rep_rel"] for r in rows)
    return {
        "rows": rows,
        "max_abs_error": max_abs,
        "max_rel_error": max_rel,
        "max_rep_rel_error": max_rep_rel,
    }


def dynamics_scales() -> dict:
    """Collect the dynamics correspondence bundle (no verdict)."""
    from domains.fluid_universe.theory.gaussian_fluid import quantum_width

    width = quantum_width(1.0)
    extrema = [
        newton_extremum(factor) for factor in START_FACTORS
    ]
    releases = [release_period(factor) for factor in RELEASE_FACTORS]
    omega2 = 2.0
    width2 = quantum_width(omega2)
    release2 = release_period(1.01, omega=omega2)
    return {
        "grids": {"n": GRID_N, "horizon_fraction": HORIZON_FRACTION},
        "base": dict(BASE),
        "starts": list(START_FACTORS),
        "width": width,
        "extrema": extrema,
        "releases": releases,
        "term_match": term_match(),
        "scaling": {
            "omega": omega2,
            "width": width2,
            "release": release2,
        },
    }
