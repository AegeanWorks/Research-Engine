"""Yasue center-width discriminator: collapse under Yasue, co-emergence under G-M (claim 55, ADR-047).

Zero free parameters, no full-field claims. For the time-dependent
2-path Gaussian trial (center mu(t), width sigma(t)) the drift
v = mudot + (sigmadot/sigma)(x - mu) gives, with rho = N(mu, sigma^2):

    E[v^2] = mudot^2 + sigmadot^2     (cross term dies: E[x - mu] = 0)
    E[V]   = m*w^2*(sigma^2 + mu^2)/2

for BOTH actions: the kinetic and trap terms are action-independent.
The G-M and Yasue Lagrangians differ only in the osmotic-potential
sign, which depends on sigma alone:

    L_G = m*mudot^2/2 + m*sdot^2/2 + m*nu^2/(2*s^2) - m*w^2*(mu^2+s^2)/2  (G-M)
    L_Y = m*mudot^2/2 + m*sdot^2/2 - m*nu^2/(2*s^2) - m*w^2*(mu^2+s^2)/2  (Yasue)

Hence the center Euler-Lagrange equation is the classical HO in BOTH:

    mu_ddot = -omega^2*mu          (shared center control)

while the width equations discriminate:

    s_ddot = +nu^2/s^3 - omega^2*s   (G-M Ermakov, oscillates at pi)
    s_ddot = -nu^2/s^3 - omega^2*s   (Yasue, negative everywhere: collapse)

The frozen horizon T = pi/(4*omega) is governed by the tighter
(width) leg: first conjugate zero at pi/(2*omega) vs pi/omega for the
center. Weak-local-positivity only; no global claims. The full control
problem stays untested. Spelling: the literature name is Yasue
(K. Yasue 1981); old modules keep their names untouched.

Predicted pattern (H55-rev): under Yasue the center leg stays
Newtonian (mu tracks mu0*cos(omega*t) over the collapse window) while
the width leg collapses (monotone to the floor, zero upward crossings,
floor-hit < pi); the identical G-M twin co-oscillates (2*pi and pi).
The kill leg is the WIDTH leg conditioned on an intact center control:
a Yasue width oscillation at pi falsifies the discriminator; a center
that leaves the Newtonian track breaks the split assumption
(UNVERIFIED + theory revision, not a win).

Two measurement facts shape the gates. First, the joint release ends
when the width hits the floor (t < 1), before the center completes a
period — so the center is gated on its analytic track over the window,
not on a measured full period (the 2*pi period itself is analytic
inference from the shared EL, flagged as such). Second, the Yasue
fixed-endpoint BVP admits a single non-constant stationary arc (an
upward bulge, max about +14% above sigma_q, attained from every start
to the finite-difference floor): the constant path is not stationary
(residual O(1)), but "no root" is false and is not gated. The arc is
recorded, not claimed; an analytic arc family plus Jacobi is future
work.
"""

from __future__ import annotations

import math

import numpy as np

GRID_N = 401
HORIZON_FRACTION = 0.25
BASE = {"omega": 1.0, "hbar": 1.0, "mass": 1.0}
STARTS = ((0.0, 1.0), (0.0, 1.05), (0.0, 0.95), (0.5, 1.0), (-0.5, 1.0))
RELEASES = ((0.1, 1.0), (0.0, 1.01), (0.3, 1.2))
YASUE_FLOORS = (0.05, 0.02)
DT = 0.001
T_END = 4.0 * math.pi
MILD_SIGMA = 0.5
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
    from domains.fluid_universe.theory.gaussian_fluid import quantum_width

    return quantum_width(omega, hbar, mass)


def mu_acceleration(mu: float, omega: float) -> float:
    return -omega * omega * mu


def sigma_acceleration_gm(s: float, omega: float, hbar: float, mass: float) -> float:
    if s <= 0.0:
        raise ValueError("s must be positive")
    nu = diffusivity(hbar, mass)
    return nu * nu / (s * s * s) - omega * omega * s


def yasue_acceleration(s: float, omega: float, hbar: float, mass: float) -> float:
    """Yasue width acceleration: -nu^2/s^3 - omega^2*s < 0 for all s > 0."""
    if s <= 0.0 or omega <= 0.0:
        raise ValueError("s and omega must be positive")
    nu = diffusivity(hbar, mass)
    return -nu * nu / (s * s * s) - omega * omega * s


def sigma_acceleration_yasue(s: float, omega: float, hbar: float, mass: float) -> float:
    return yasue_acceleration(s, omega, hbar, mass)


def discrete_el_system_yasue(
    interior: np.ndarray,
    omega: float,
    hbar: float,
    mass: float,
    dt: float,
    mu_end: float,
    s_end: float,
) -> np.ndarray:
    """Discrete Euler-Lagrange residuals for the (mu, sigma) pair under Yasue.

    Identical to the G-M system except the osmotic potential prime flips
    sign: +m*nu^2/x^3 + m*w^2*x (Yasue) vs -m*nu^2/x^3 + m*w^2*x (G-M).
    The center leg is byte-identical to G-M.
    """
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

    def _pot_prime_yasue(x: np.ndarray) -> np.ndarray:
        return mass * nu * nu / (x * x * x) + mass * omega * omega * x

    mid_l = 0.5 * (sg[:-2] + sg[1:-1])
    mid_r = 0.5 * (sg[1:-1] + sg[2:])
    res_sg = (
        mass * (sg[1:-1] - sg[:-2]) / dt**2
        - mass * (sg[2:] - sg[1:-1]) / dt**2
        - 0.5 * _pot_prime_yasue(mid_l)
        - 0.5 * _pot_prime_yasue(mid_r)
    )
    return np.concatenate([res_mu, res_sg])


def static_residuals(
    omega: float = 1.0,
    hbar: float = 1.0,
    mass: float = 1.0,
    n: int = GRID_N,
) -> list:
    """Discrete Yasue EL residual at the G-M stationary path (0, sigma_q).

    Under G-M this residual is <= 1e-12 (claim 53); under Yasue it must
    be O(1) — the constant path is NOT stationary, the static leg of
    the discriminator (complement to the span-50 saddle result).
    """
    from domains.fluid_universe.theory.gaussian_fluid import quantum_width

    width = quantum_width(omega, hbar, mass)
    dt = horizon(omega) / (n - 1)
    out = []
    for mu0, s0_factor in STARTS:
        interior = np.concatenate(
            [np.full(n - 2, 0.0), np.full(n - 2, width)]
        )
        residual = discrete_el_system_yasue(
            interior, omega, hbar, mass, dt, 0.0, width
        )
        n2 = n - 2
        out.append(
            {
                "mu0": mu0,
                "s0_factor": s0_factor,
                "max_residual": float(np.max(np.abs(residual))),
                "max_res_mu": float(np.max(np.abs(residual[:n2]))),
                "max_res_sg": float(np.max(np.abs(residual[n2:]))),
            }
        )
    return out


def newton_attempt_yasue(
    mu0: float,
    s0_factor: float,
    omega: float = 1.0,
    hbar: float = 1.0,
    mass: float = 1.0,
    n: int = GRID_N,
    steps: int = 12,
) -> dict:
    """Bounded Newton solve on the Yasue discrete EL system.

    Attainment gate is 1e-9 (finite-difference Jacobian floor, ADR-046
    precedent: floor eps*s/dt^2 ~= 4e-11). Every start attains the same
    single upward-bulge arc (projectile-like: endpoints pinned, interior
    above sigma_q). Attained = residual <= 1e-9; single attractor =
    identical min/max sigma across starts. The arc is recorded, not
    claimed; no analytic family or Jacobi exists here.
    """
    from domains.fluid_universe.theory.gaussian_fluid import quantum_width

    width = quantum_width(omega, hbar, mass)
    dt = horizon(omega) / (n - 1)
    sg0 = s0_factor * width
    interior = np.concatenate(
        [np.full(n - 2, mu0), np.full(n - 2, sg0)]
    )
    attained = False
    diverged = False
    try:
        for _ in range(steps):
            residual = discrete_el_system_yasue(
                interior, omega, hbar, mass, dt, 0.0, width
            )
            if float(np.max(np.abs(residual))) < 1e-9:
                attained = True
                break
            n2 = n - 2
            if float(np.min(interior[n2:])) <= 1e-12:
                diverged = True
                break
            h = 1e-7
            cols = []
            for j in range(len(interior)):
                pert = np.zeros_like(interior)
                pert[j] = h
                columns = (
                    discrete_el_system_yasue(
                        interior + pert, omega, hbar, mass, dt, 0.0, width
                    )
                    - residual
                ) / h
                cols.append(columns)
            jacobian = np.column_stack(cols)
            interior = interior - np.linalg.solve(jacobian, residual)
    except np.linalg.LinAlgError:
        diverged = True
    final = discrete_el_system_yasue(interior, omega, hbar, mass, dt, 0.0, width)
    n2 = n - 2
    return {
        "mu0": mu0,
        "s0_factor": s0_factor,
        "max_residual": float(np.max(np.abs(final))),
        "attained": bool(attained),
        "converged": bool(attained),
        "diverged": bool(diverged),
        "min_sigma": float(np.min(interior[n2:])),
        "max_sigma": float(np.max(interior[n2:])),
        "max_dev_mu": float(np.max(np.abs(interior[:n2] - 0.0))),
        "interior_mu": [float(v) for v in interior[:n2]],
        "interior_sg": [float(v) for v in interior[n2:]],
        "dt": dt,
    }


def _period_from_crossings(times: list) -> float:
    same = times[::2]
    if len(same) < 2:
        return float("nan")
    diffs = [b - a for a, b in zip(same, same[1:])]
    return sum(diffs) / len(diffs)


def release_pair_yasue(
    mu0: float,
    s0_factor: float,
    omega: float = 1.0,
    hbar: float = 1.0,
    mass: float = 1.0,
    dt: float = DT,
    t_end: float = T_END,
    floor: float = 0.05,
) -> dict:
    """Joint Verlet release under Yasue: classical center, collapsing width.

    mu uses the shared HO acceleration; sigma uses the Yasue acceleration
    with a floor stop. The center must oscillate at 2*pi/omega; the width
    must fall monotonically to the floor with zero upward crossings.
    """
    from domains.fluid_universe.theory.gaussian_fluid import quantum_width

    width = quantum_width(omega, hbar, mass)
    mu, sg, vmu, vsg, t = mu0, s0_factor * width, 0.0, 0.0, 0.0
    mu_prev, sg_prev = mu - 0.0, sg - width
    mu_cross: list = []
    sg_cross: list = []
    sg_diffs: list = []
    upward = 0
    mild_time = 0.0 if sg <= MILD_SIGMA else None
    prev_sg = sg
    hit_time = None
    min_sigma = sg
    mu_track_max_dev = 0.0
    mu_at_hit = None
    while t < t_end and sg > floor:
        vmu += 0.5 * dt * mu_acceleration(mu, omega)
        vsg += 0.5 * dt * yasue_acceleration(sg, omega, hbar, mass)
        mu += dt * vmu
        sg_new = sg + dt * vsg
        vmu += 0.5 * dt * mu_acceleration(mu, omega)
        if sg_new > 0.0:
            vsg += 0.5 * dt * yasue_acceleration(sg_new, omega, hbar, mass)
        else:
            vsg += 0.5 * dt * yasue_acceleration(max(sg, 1e-12), omega, hbar, mass)
        t += dt
        mu_track_max_dev = max(
            mu_track_max_dev, abs(mu - mu0 * math.cos(omega * t))
        )
        sg_diffs.append(sg_new - sg)
        if mild_time is None and sg > MILD_SIGMA >= sg_new:
            frac = (sg - MILD_SIGMA) / (sg - sg_new) if sg != sg_new else 0.0
            mild_time = t - dt + frac * dt
        cur_mu, cur_sg = mu - 0.0, sg_new - width
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
            if sg_prev < 0.0 <= cur_sg:
                upward += 1
        mu_prev, sg_prev = cur_mu, cur_sg
        sg = sg_new
        min_sigma = min(min_sigma, sg)
        if sg <= floor:
            hit_time = t
            mu_at_hit = float(mu)
            break
    return {
        "mu0": mu0,
        "s0_factor": s0_factor,
        "mu_period": _period_from_crossings(mu_cross),
        "sg_period": _period_from_crossings(sg_cross),
        "n_mu_crossings": len(mu_cross),
        "n_sg_crossings": len(sg_cross),
        "mu_track_max_dev": float(mu_track_max_dev),
        "mu_at_hit": mu_at_hit,
        "monotone": bool(all(d < 0.0 for d in sg_diffs)) if sg_diffs else True,
        "floor_hit_time": hit_time,
        "upward_crossings": upward,
        "mild_crossing_time": mild_time,
        "min_sigma": float(min_sigma),
        "floor": floor,
    }


def term_match() -> dict:
    """Width-leg sign split + shared center leg, term by term.

    mu rows: own vs -omega^2*mu (shared classical leg, both actions).
    sg rows: Yasue own vs -nu^2/s^3 - omega^2*s (must be exact, and < 0).
    """
    rows = []
    for s in TEST_SIGMAS:
        own = yasue_acceleration(s, 1.0, 1.0, 1.0)
        analytic = -0.25 / (s**3) - 1.0 * s
        rows.append(
            {
                "s": s,
                "own": own,
                "analytic": float(analytic),
                "abs": abs(own - float(analytic)),
                "rel": abs(own - float(analytic)) / max(abs(float(analytic)), 1e-300),
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
        "max_accel": max(r["own"] for r in rows),
    }


def yasue_scales() -> dict:
    """Collect the discriminator bundle (no verdict)."""
    from domains.fluid_universe.theory.variational_center import release_pair as gm_release_pair
    from domains.fluid_universe.theory.yasue_dynamics import quadrature_mild_crossing

    statics = static_residuals()
    attempts = [newton_attempt_yasue(mu0, s0) for mu0, s0 in STARTS]
    arc_profile = {
        "mu": attempts[0]["interior_mu"],
        "sg": attempts[0]["interior_sg"],
        "dt": attempts[0]["dt"],
        "n": GRID_N,
    }
    releases = [release_pair_yasue(mu0, s0) for mu0, s0 in RELEASES]
    twins = [
        dict(gm_release_pair(mu0, s0), mu0=mu0, s0_factor=s0)
        for mu0, s0 in RELEASES
    ]
    factors = [s0 for _, s0 in RELEASES]
    mild_quad = [quadrature_mild_crossing(f) for f in factors]
    probe_floor02 = release_pair_yasue(0.3, 1.2, floor=0.02)
    scaling = {
        "omega": SCALING_OMEGA,
        "yasue": release_pair_yasue(0.05, 1.01, omega=SCALING_OMEGA),
        "twin_mu": dict(
            gm_release_pair(0.05, 1.0, omega=SCALING_OMEGA),
            mu0=0.05,
            s0_factor=1.0,
        ),
        "twin_sg": dict(
            gm_release_pair(0.0, 1.01, omega=SCALING_OMEGA),
            mu0=0.0,
            s0_factor=1.01,
        ),
    }
    return {
        "grids": {"n": GRID_N, "horizon_fraction": HORIZON_FRACTION},
        "base": {"omega": 1.0, "hbar": 1.0, "mass": 1.0},
        "starts": [list(s) for s in STARTS],
        "releases_meta": [list(r) for r in RELEASES],
        "floors": list(YASUE_FLOORS),
        "dt": DT,
        "t_end": T_END,
        "statics": statics,
        "attempts": [
            {k: a[k] for k in a if k not in ("interior_mu", "interior_sg")}
            for a in attempts
        ],
        "arc_profile": arc_profile,
        "arc_min_sigma": min(a["min_sigma"] for a in attempts),
        "arc_max_sigma": max(a["max_sigma"] for a in attempts),
        "releases": releases,
        "twins": twins,
        "mild_quadrature": mild_quad,
        "floor_sensitivity": probe_floor02,
        "term_match": term_match(),
        "scaling": scaling,
    }
