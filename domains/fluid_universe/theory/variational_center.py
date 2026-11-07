"""Co-emergence of Newtonian center and Ermakov width (claim 53, ADR-045).

Zero free parameters, no full-field claims. For the time-dependent
2D-path Gaussian trial (center mu(t), width sigma(t)) the drift
v = mudot + (sigmadot/sigma)(x - mu) gives, with rho = N(mu, sigma^2):

    E[v^2] = mudot^2 + sigmadot^2     (cross term dies: E[x - mu] = 0)
    E[V]   = m*w^2*(sigma^2 + mu^2)/2

so the G-M action splits additively, J[mu,sigma] = J_mu[mu] + J_sg[sg],
with J_mu the classical HO action and J_sg the span-51 width action.
The stationary path is (0, sigma_q); small oscillations decouple:
mu at omega (period 2*pi) and sigma at 2*omega (period pi).

Units convention: STARTS entries are (mu0 absolute, sigma0 as a
multiple of the fixed width). Releases likewise carry absolute mu0.
The frozen horizon T = pi/(4*omega) is governed by the tighter
(width) leg: first conjugate zero at pi/(2*omega) vs pi/omega for
the center. Weak-local-positivity only; no global claims.
Yasui center dynamics and the full control problem stay untested.
"""

from __future__ import annotations

import math

import numpy as np

GRID_N = 401
HORIZON_FRACTION = 0.25
BASE = {"omega": 1.0, "hbar": 1.0, "mass": 1.0}
STARTS = ((0.0, 1.0), (0.0, 1.05), (0.0, 0.95), (0.5, 1.0), (-0.5, 1.0))
RELEASES = ((0.1, 1.0), (0.0, 1.01), (0.3, 1.2))
TEST_SIGMAS = (0.5, 0.7071067811865476, 1.0, 1.5)
SCALING_OMEGA = 2.0


def diffusivity(hbar: float, mass: float) -> float:
    if hbar <= 0.0 or mass <= 0.0:
        raise ValueError("hbar and mass must be positive")
    return hbar / (2.0 * mass)


def horizon(omega: float) -> float:
    if omega <= 0.0:
        raise ValueError("omega must be positive")
    return math.pi / (4.0 * omega)


def width_fixed_point(omega: float, hbar: float, mass: float) -> float:
    nu = diffusivity(hbar, mass)
    return math.sqrt(nu / omega)


def mu_acceleration(mu: float, omega: float) -> float:
    return -omega * omega * mu


def sigma_acceleration(s: float, omega: float, hbar: float, mass: float) -> float:
    if s <= 0.0:
        raise ValueError("s must be positive")
    nu = diffusivity(hbar, mass)
    return nu * nu / (s * s * s) - omega * omega * s


def discrete_el_system(
    interior: np.ndarray,
    omega: float,
    hbar: float,
    mass: float,
    dt: float,
    mu_end: float,
    s_end: float,
) -> np.ndarray:
    """Discrete Euler-Lagrange residuals for the (mu, sigma) pair."""
    interior = np.asarray(interior, dtype=float)
    n2 = len(interior) // 2
    mu = np.concatenate([[mu_end], interior[:n2], [mu_end]])
    sg = np.concatenate([[s_end], interior[n2:], [s_end]])
    nu = diffusivity(hbar, mass)
    res_mu = (
        mass * (mu[1:-1] - mu[:-2]) / dt**2
        - mass * (mu[2:] - mu[1:-1]) / dt**2
        - 0.5 * mass * omega * omega * 0.5 * (mu[:-2] + mu[1:-1])
        - 0.5 * mass * omega * omega * 0.5 * (mu[1:-1] + mu[2:])
    )

    def _pot_prime(x: np.ndarray) -> np.ndarray:
        return -mass * nu * nu / (x * x * x) + mass * omega * omega * x

    mid_l = 0.5 * (sg[:-2] + sg[1:-1])
    mid_r = 0.5 * (sg[1:-1] + sg[2:])
    res_sg = (
        mass * (sg[1:-1] - sg[:-2]) / dt**2
        - mass * (sg[2:] - sg[1:-1]) / dt**2
        - 0.5 * _pot_prime(mid_l)
        - 0.5 * _pot_prime(mid_r)
    )
    return np.concatenate([res_mu, res_sg])


def newton_pair(
    mu0: float,
    s0_factor: float,
    omega: float = 1.0,
    hbar: float = 1.0,
    mass: float = 1.0,
    n: int = GRID_N,
    steps: int = 12,
) -> dict:
    """Joint Newton solve on the discrete EL system from a constant start."""
    from domains.fluid_universe.theory.gaussian_fluid import quantum_width

    width = quantum_width(omega, hbar, mass)
    dt = horizon(omega) / (n - 1)
    sg0 = s0_factor * width
    interior = np.concatenate(
        [np.full(n - 2, mu0), np.full(n - 2, sg0)]
    )
    converged = True
    try:
        for _ in range(steps):
            residual = discrete_el_system(
                interior, omega, hbar, mass, dt, 0.0, width
            )
            if float(np.max(np.abs(residual))) < 1e-12:
                break
            h = 1e-7
            cols = []
            for j in range(len(interior)):
                pert = np.zeros_like(interior)
                pert[j] = h
                columns = (
                    discrete_el_system(
                        interior + pert, omega, hbar, mass, dt, 0.0, width
                    )
                    - residual
                ) / h
                cols.append(columns)
            jacobian = np.column_stack(cols)
            interior = interior - np.linalg.solve(jacobian, residual)
    except np.linalg.LinAlgError:
        converged = False
    n2 = n - 2
    final = discrete_el_system(interior, omega, hbar, mass, dt, 0.0, width)
    return {
        "mu0": mu0,
        "s0_factor": s0_factor,
        "max_dev_mu": float(np.max(np.abs(interior[:n2] - 0.0))),
        "max_dev_sg": float(np.max(np.abs(interior[n2:] - width))),
        "max_residual": float(np.max(np.abs(final))),
        "converged": bool(converged),
        "dt": dt,
    }


def _period_from_crossings(times: list) -> float:
    same = times[::2]
    if len(same) < 2:
        return float("nan")
    diffs = [b - a for a, b in zip(same, same[1:])]
    return sum(diffs) / len(diffs)


def release_pair(
    mu0: float,
    s0_factor: float,
    omega: float = 1.0,
    hbar: float = 1.0,
    mass: float = 1.0,
    dt: float = 0.001,
    t_end: float = 4.0 * math.pi,
) -> dict:
    """Joint Verlet release; per-leg zero crossings give both periods."""
    from domains.fluid_universe.theory.gaussian_fluid import quantum_width

    width = quantum_width(omega, hbar, mass)
    mu, sg, vmu, vsg, t = mu0, s0_factor * width, 0.0, 0.0, 0.0
    mu_prev, sg_prev = mu - 0.0, sg - width
    mu_cross, sg_cross = [], []
    while t < t_end:
        vmu += 0.5 * dt * mu_acceleration(mu, omega)
        vsg += 0.5 * dt * sigma_acceleration(sg, omega, hbar, mass)
        mu += dt * vmu
        sg = max(sg + dt * vsg, 1e-9)
        vmu += 0.5 * dt * mu_acceleration(mu, omega)
        vsg += 0.5 * dt * sigma_acceleration(sg, omega, hbar, mass)
        t += dt
        cur_mu, cur_sg = mu - 0.0, sg - width
        if mu_prev < 0.0 <= cur_mu or mu_prev > 0.0 >= cur_mu:
            mu_cross.append(
                t - dt + dt * mu_prev / (mu_prev - cur_mu)
                if cur_mu != mu_prev
                else t
            )
        if sg_prev < 0.0 <= cur_sg or sg_prev > 0.0 >= cur_sg:
            sg_cross.append(
                t - dt + dt * sg_prev / (sg_prev - cur_sg)
                if cur_sg != sg_prev
                else t
            )
        mu_prev, sg_prev = cur_mu, cur_sg
    return {
        "mu0": mu0,
        "s0_factor": s0_factor,
        "mu_period": _period_from_crossings(mu_cross),
        "sg_period": _period_from_crossings(sg_cross),
        "n_mu_crossings": len(mu_cross),
        "n_sg_crossings": len(sg_cross),
    }


def term_match() -> dict:
    """Sigma-leg term match vs ermakov_rhs; mu-leg analytic identity."""
    from domains.fluid_universe.theory.gaussian_fluid import ermakov_rhs

    rows = []
    for s in TEST_SIGMAS:
        own = sigma_acceleration(s, 1.0, 1.0, 1.0)
        _, ermakov = ermakov_rhs(s, 0.0, 1.0, 1.0)
        rows.append(
            {
                "s": s,
                "own": own,
                "ermakov": float(ermakov),
                "abs": abs(own - float(ermakov)),
                "rel": abs(own - float(ermakov)) / max(abs(float(ermakov)), 1e-300),
            }
        )
    mus = [0.0, 0.25, -0.4]
    mu_rows = [
        {"mu": m, "own": mu_acceleration(m, 1.0), "newton": -1.0 * m}
        for m in mus
    ]
    return {
        "rows": rows,
        "mu_rows": mu_rows,
        "max_rel_error": max(r["rel"] for r in rows),
    }


def dynamics_scales() -> dict:
    """Collect the co-emergence bundle (no verdict)."""
    extrema = [newton_pair(mu0, s0) for mu0, s0 in STARTS]
    releases = [release_pair(mu0, s0) for mu0, s0 in RELEASES]
    term = term_match()
    scaling = {
        "omega": 2.0,
        "mu_period": release_pair(0.05, 1.0, omega=2.0)["mu_period"],
        "sg_period": release_pair(0.0, 1.01, omega=2.0)["sg_period"],
    }
    return {
        "grids": {"n": GRID_N, "horizon_fraction": HORIZON_FRACTION},
        "base": {"omega": 1.0, "hbar": 1.0, "mass": 1.0},
        "starts": [list(s) for s in STARTS],
        "releases": releases,
        "extrema": extrema,
        "term_match": term,
        "scaling": scaling,
    }
