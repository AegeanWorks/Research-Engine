"""Fixed-endpoint Gaussian transport bridge (claim 54, ADR-046).

Zero free parameters, no full-field claims. Extremize the discrete
G-M action over paths with PINNED endpoint densities
rho(0) = N(0, s0^2), rho(T) = N(0, sigma_q^2), T = pi/(4*omega),
with the midpoint Lagrangian. The analytic stationary paths are the
Pinney two-branch family sigma^2 = A*u^2 + 2*B*u*v + C*v^2
(u = cos(omega*t), v = sin(omega*t)/omega, Wronskian 1) with the
quadratic constraint A*C - B^2 = nu^2 (= hbar^2/(4*m^2)) imposed by
the ODE itself, NOT fitted: imposing the two endpoint widths selects
at most two branches (algebraic consequence of the quadratic
constraint — present-work inference, NOT a cited Pinney theorem).

Base case (omega = 1): s0 = 1.2*sigma_q, A = s0^2 = 0.72 exactly,
B^2 + 1.44*B + 0.0484 = 0, i.e. B_1 = -0.0344345399 (primary) and
B_2 = -1.4055654601 (bounce), with C_1 = 0.3488690799 and
C_2 = 3.0911309201.

This is NOT the entropic-interpolation K^eps_t / Bunne Sigma_t bridge:
different functional (G-M fixed-density action vs KL-to-Wiener), so
no K^eps_t comparison is attempted (shape-only remarks would be
decorative). The Morato-Ugolini framework explicitly excludes
two-point pinning; the present boundary class is Eulerian fixed
density, a different setup.
"""

from __future__ import annotations

import math

import numpy as np

GRID_N = 401
RESID_TOL = 1e-9
BASE = {"omega": 1.0, "hbar": 1.0, "mass": 1.0}
START_S0_FACTOR = 1.2
STARTS = ("const_s0", "const_sq", "linear", "bump", "vdip", "hbump")
BUMP_AMP = 0.3


def diffusivity(hbar: float, mass: float) -> float:
    if hbar <= 0.0 or mass <= 0.0:
        raise ValueError("hbar and mass must be positive")
    return hbar / (2.0 * mass)


def horizon(omega: float) -> float:
    if omega <= 0.0:
        raise ValueError("omega must be positive")
    return math.pi / (4.0 * omega)


def pinney_coeffs(
    s0: float, sT: float, horizon_T: float, omega: float, hbar: float, mass: float
) -> list:
    """Solve A (pinned start), then the quadratic for B, then C."""
    nu = diffusivity(hbar, mass)
    u0, v0 = 1.0, 0.0
    uT, vT = math.cos(omega * horizon_T), math.sin(omega * horizon_T) / omega
    A = s0 * s0
    # A*uT^2 + 2*B*uT*vT + C*vT^2 = sT^2 ; A*C - B^2 = nu^2.
    a2 = uT * uT
    b2 = 2.0 * uT * vT
    c2 = vT * vT
    if abs(c2) < 1e-15:
        raise ValueError("degenerate endpoint basis (vT == 0)")
    # C = (sT^2 - A*a2 - B*b2)/c2 ; A*C - B^2 = nu^2 -> quadratic in B.
    # -(b2/c2)*B^2 ... expand: A*(sT^2-A*a2-B*b2)/c2 - B^2 = nu^2
    # => B^2*(1 + A*b2/(c2*? ...)). Do it carefully:
    # A*sT^2/c2 - A*A*a2/c2 - A*b2*B/c2 - B^2 - nu^2 = 0
    # => B^2 + (A*b2/c2)*B + (nu^2 - A*sT^2/c2 + A*A*a2/c2) = 0
    qa = 1.0
    qb = A * b2 / c2
    qc = nu * nu - A * sT * sT / c2 + A * A * a2 / c2
    disc = qb * qb - 4.0 * qa * qc
    if disc < 0.0:
        return []
    out = []
    for sgn in (1.0, -1.0):
        bval = (-qb + sgn * math.sqrt(disc)) / (2.0 * qa)
        cval = (sT * sT - A * a2 - bval * b2) / c2
        out.append({"A": A, "B": bval, "C": cval})
    # Primary = small-|B| branch (near-constant, connected to span-51).
    out.sort(key=lambda d: abs(d["B"]))
    return out


def pinney_path(
    coeffs: dict, t_values: np.ndarray, omega: float
) -> np.ndarray:
    t_values = np.asarray(t_values, dtype=float)
    u = np.cos(omega * t_values)
    v = np.sin(omega * t_values) / omega
    return np.sqrt(
        np.maximum(
            coeffs["A"] * u * u
            + 2.0 * coeffs["B"] * u * v
            + coeffs["C"] * v * v,
            0.0,
        )
    )


def jacobi_first_zero(
    sigma_of_t,
    omega: float,
    hbar: float,
    mass: float,
    t_end: float,
    n: int = 20001,
) -> float | None:
    """First conjugate zero of u'' + Q(t) u = 0 along a bridge path.

    Q(t) = V''(sigma(t))/m with V the Gaussian width potential.
    Returns the first zero crossing time, or None if none found.
    """
    from domains.fluid_universe.theory.variational_dynamics import diffusivity as _nu

    nu = _nu(hbar, mass)
    t = np.linspace(0.0, t_end, n)
    dt = t[1] - t[0]
    u_prev, v_prev = 0.0, 1.0
    for i in range(1, n):
        s = float(sigma_of_t(t[i - 1]))
        q = 3.0 * nu * nu / max(s, 1e-12) ** 4 + omega * omega
        v_new = v_prev + dt * (-q * u_prev)
        u_new = u_prev + dt * v_new
        if u_new == 0.0 or (u_prev < 0.0) != (u_new < 0.0):
            return float(t[i])
        u_prev, v_prev = u_new, v_new
    return None


def newton_bridge(
    start_kind: str,
    omega: float = 1.0,
    hbar: float = 1.0,
    mass: float = 1.0,
    n: int = GRID_N,
    steps: int = 12,
) -> dict:
    """Discrete-EL Newton solve with pinned endpoint densities."""
    from domains.fluid_universe.theory.gaussian_fluid import quantum_width

    sq = float(quantum_width(omega, hbar, mass))
    s0 = START_S0_FACTOR * sq
    T = horizon(omega)
    dt = T / (n - 1)
    grid = np.linspace(0.0, T, n)
    if start_kind == "const_s0":
        interior = np.full(n - 2, s0)
    elif start_kind == "const_sq":
        interior = np.full(n - 2, sq)
    elif start_kind == "linear":
        interior = s0 + (sq - s0) * np.linspace(dt / T, 1.0 - dt / T, n - 2)
    elif start_kind == "bump":
        base = s0 + (sq - s0) * np.linspace(dt / T, 1.0 - dt / T, n - 2)
        interior = base + BUMP_AMP * np.sin(math.pi * np.linspace(dt / T, 1.0 - dt / T, n - 2))
    elif start_kind == "vdip":
        base = s0 + (sq - s0) * np.linspace(dt / T, 1.0 - dt / T, n - 2)
        dip = np.minimum(0.0, -0.5 * np.sin(math.pi * np.linspace(dt / T, 1.0 - dt / T, n - 2)))
        interior = np.maximum(base + dip, 0.3 * sq)
    elif start_kind == "hbump":
        base = s0 + (sq - s0) * np.linspace(dt / T, 1.0 - dt / T, n - 2)
        interior = base + 0.5 * np.sin(math.pi * np.linspace(dt / T, 1.0 - dt / T, n - 2))
    else:
        raise ValueError(f"unknown start kind: {start_kind}")
    # Achievable floor is fp roundoff ~eps*s/dt^2 (~4e-11 here);
    # 1e-9 separates it from any genuine non-stationary residual.
    converged = True
    try:
        for _ in range(steps):
            residual = _discrete_residual(interior, omega, hbar, mass, dt, s0, sq)
            if float(np.max(np.abs(residual))) < RESID_TOL:
                break
            h = 1e-7
            cols = []
            for j in range(len(interior)):
                pert = np.zeros_like(interior)
                pert[j] = h
                cols.append(
                    (
                        _discrete_residual(
                            interior + pert, omega, hbar, mass, dt, s0, sq
                        )
                        - residual
                    )
                    / h
                )
            jacobian = np.column_stack(cols)
            interior = interior - np.linalg.solve(jacobian, residual)
    except np.linalg.LinAlgError:
        converged = False
    final = _discrete_residual(interior, omega, hbar, mass, dt, s0, sq)
    if float(np.max(np.abs(final))) > RESID_TOL:
        converged = False
    return {
        "start": start_kind,
        "interior": [float(v) for v in interior],
        "max_residual": float(np.max(np.abs(final))),
        "converged": bool(converged),
        "dt": dt,
        "T": T,
    }


def _discrete_residual(
    interior: np.ndarray,
    omega: float,
    hbar: float,
    mass: float,
    dt: float,
    s0: float,
    sT: float,
) -> np.ndarray:
    from domains.fluid_universe.theory.variational_dynamics import diffusivity as _nu

    interior = np.asarray(interior, dtype=float)
    nu = _nu(hbar, mass)
    full = np.concatenate([[s0], interior, [sT]])
    left, mid, right = full[:-2], full[1:-1], full[2:]
    acc = (
        mass * (mid - left) / dt**2
        - mass * (right - mid) / dt**2
        - 0.5 * (-mass * nu * nu / (0.5 * (left + mid)) ** 3 + mass * omega * omega * 0.5 * (left + mid))
        - 0.5 * (-mass * nu * nu / (0.5 * (mid + right)) ** 3 + mass * omega * omega * 0.5 * (mid + right))
    )
    return acc


def analytic_action(
    coeffs: dict, omega: float, hbar: float, mass: float, n: int = 200001
) -> float:
    """High-accuracy quadrature of the continuous action on a Pinney path."""
    from domains.fluid_universe.theory.gaussian_fluid import quantum_width

    sq = float(quantum_width(omega, hbar, mass))
    T = horizon(omega)
    t = np.linspace(0.0, T, n)
    dt = t[1] - t[0]
    u = np.cos(omega * t)
    v = np.sin(omega * t) / omega
    s2 = coeffs["A"] * u * u + 2.0 * coeffs["B"] * u * v + coeffs["C"] * v * v
    s = np.sqrt(np.maximum(s2, 1e-300))
    nu = diffusivity(hbar, mass)
    vel = np.gradient(s, dt)
    dens = (
        0.5 * mass * vel * vel
        - mass * nu * nu / (2.0 * s * s)
        - 0.5 * mass * omega * omega * s * s
    )
    return float(np.trapezoid(dens, t))


def discrete_action(
    full_path: np.ndarray, omega: float, hbar: float, mass: float, dt: float
) -> float:
    """Same midpoint discrete action the Newton solver extremizes."""
    from domains.fluid_universe.theory.gaussian_fluid import quantum_width

    nu = diffusivity(hbar, mass)
    s = np.asarray(full_path, dtype=float)
    mid = 0.5 * (s[:-1] + s[1:])
    vel = (s[1:] - s[:-1]) / dt
    dens = (
        0.5 * mass * vel * vel
        - mass * nu * nu / (2.0 * mid * mid)
        - 0.5 * mass * omega * omega * mid * mid
    )
    return float(np.sum(dens) * dt)


def match_to_branches(
    newton_interior: list, grid: np.ndarray, branches: list, omega: float
) -> list:
    """Max-abs deviation of a Newton result from each analytic branch."""
    interior = np.asarray(newton_interior, dtype=float)
    out = []
    for coeffs in branches:
        analytic = pinney_path(coeffs, grid[1:-1], omega)
        out.append(float(np.max(np.abs(interior - analytic))))
    return out


def bridge_scales() -> dict:
    """Collect the fixed-endpoint bridge bundle (no verdict)."""
    from domains.fluid_universe.theory.gaussian_fluid import quantum_width

    omega, hbar, mass = 1.0, 1.0, 1.0
    sq = float(quantum_width(omega, hbar, mass))
    T = horizon(omega)
    grid = np.linspace(0.0, T, GRID_N)
    dt = T / (GRID_N - 1)
    starts = list(STARTS)
    s0 = START_S0_FACTOR * sq
    extrema = []
    for kind in starts:
        out = newton_bridge(kind, omega, hbar, mass)
        full = np.concatenate([[s0], np.array(out["interior"]), [sq]])
        out["discrete_action"] = discrete_action(full, omega, hbar, mass, dt)
        extrema.append(dict(kind=kind, **out))
    coeffs = pinney_coeffs(s0, sq, T, omega, hbar, mass)
    pinney_vals = [float(v) for v in pinney_path(coeffs[0], grid, omega)]
    jac_primary = jacobi_first_zero(
        lambda t: float(np.interp(t, grid, pinney_vals)), omega, hbar, mass, T
    )
    analytic_primary = analytic_action(coeffs[0], omega, hbar, mass)
    matches = [
        match_to_branches(e["interior"], grid, coeffs, omega) for e in extrema
    ]
    scaling = scaling_bundle()
    return {
        "grids": {"n": GRID_N, "T": T},
        "base": {"omega": omega, "hbar": hbar, "mass": mass},
        "s0": s0,
        "sq": sq,
        "starts": starts,
        "extrema": extrema,
        "pinney": {"coeffs": coeffs, "values": pinney_vals},
        "analytic_action": analytic_primary,
        "matches": matches,
        "jacobi_primary_first_zero": jac_primary,
        "scaling": scaling,
    }


def scaling_bundle() -> dict:
    """omega = 2 mirror of the base bundle (same gates, rescaled horizon)."""
    from domains.fluid_universe.theory.gaussian_fluid import quantum_width

    omega, hbar, mass = 2.0, 1.0, 1.0
    sq = float(quantum_width(omega, hbar, mass))
    s0 = START_S0_FACTOR * sq
    T = horizon(omega)
    grid = np.linspace(0.0, T, GRID_N)
    dt = T / (GRID_N - 1)
    coeffs = pinney_coeffs(s0, sq, T, omega, hbar, mass)
    extrema = []
    for kind in ("linear", "const_s0"):
        out = newton_bridge(kind, omega, hbar, mass)
        full = np.concatenate([[s0], np.array(out["interior"]), [sq]])
        out["discrete_action"] = discrete_action(full, omega, hbar, mass, dt)
        extrema.append(dict(kind=kind, **out))
    pinney_vals = [float(v) for v in pinney_path(coeffs[0], grid, omega)]
    matches = [
        match_to_branches(e["interior"], grid, coeffs, omega) for e in extrema
    ]
    jac = jacobi_first_zero(
        lambda t: float(np.interp(t, grid, pinney_vals)), omega, hbar, mass, T
    )
    analytic = analytic_action(coeffs[0], omega, hbar, mass)
    return {
        "omega": omega,
        "s0": s0,
        "sq": sq,
        "T": T,
        "coeffs": coeffs,
        "extrema": extrema,
        "matches": matches,
        "jacobi_first_zero": jac,
        "analytic_action": analytic,
    }



