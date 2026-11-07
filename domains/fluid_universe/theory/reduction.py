"""Dimensional reduction and the effective moment of inertia (claim 6b).

For a scalar wall profile phi(x) that connects two adjacent vacua, the energy
per unit length is the 1D tension T = (8/3) sqrt(mu).  For a configuration
phi(x,y) that also depends on y,

    E_2D = int dy [ int dx (1/2 (d_x phi)^2 + V(phi)) + 1/2 (d_y phi)^2 ]
         >= T L_y,

with equality iff d_y phi = 0.  This is a trivial lower bound, not an exact
dimensional reduction: any y-dependence adds positive gradient energy.

The effective moment of inertia in 2D is

    I_eff = int d^2r rho(r) r^2 = 2 pi int rho(r) r^3 dr.

For a power tail rho ~ r^-alpha, the integrand scales as r^(3-alpha): I_eff is
finite only for alpha > 4, logarithmically divergent for alpha = 4, and
power-divergent for alpha < 4.  A 1/r^4 tail therefore gives the log divergence
noted in the brief; a 1/r^2 tail diverges quadratically.
"""

from __future__ import annotations

import math

from scipy.integrate import quad


def wall_tension(mu: float) -> float:
    if mu < 0.0:
        raise ValueError("mu must be non-negative")
    return (8.0 / 3.0) * math.sqrt(mu)


def wall_lower_bound_2d(mu: float, length_y: float) -> float:
    if length_y < 0.0:
        raise ValueError("length must be non-negative")
    return wall_tension(mu) * length_y


def moment_power(alpha: float) -> float:
    """Power of r in the 2D moment integrand for rho ~ r^-alpha."""
    return 3.0 - alpha


def moment_finite(alpha: float) -> bool:
    return alpha > 4.0


def moment_log_divergent(alpha: float) -> bool:
    return alpha == 4.0


def moment_numeric(alpha: float, r_min: float = 1.0, r_max: float = 1.0e4) -> float:
    """2*pi int rho r^3 dr for rho = r^-alpha on [r_min, r_max]."""
    if r_min <= 0.0 or r_max <= r_min:
        raise ValueError("need 0 < r_min < r_max")
    if alpha == 4.0:
        return 2.0 * math.pi * math.log(r_max / r_min)
    exponent = 4.0 - alpha
    return 2.0 * math.pi * (r_max**exponent - r_min**exponent) / exponent


def moment_profile(profile, r_max: float, points: int = 200) -> float:
    """Numerical 2*pi int_0^rmax profile(r) r^3 dr; profile must be regular at 0."""
    if r_max <= 0.0:
        raise ValueError("r_max must be positive")
    value, _error = quad(lambda r: profile(r) * r**3, 0.0, r_max, limit=points)
    return 2.0 * math.pi * value


def verdict(stated_alpha: float = 4.0) -> dict:
    return {
        "6b_i_trivial_lower_bound": True,
        "6b_ii_exact_dimensional_reduction": False,
        "6b_iii_moment_finite_for_stated_profile": moment_finite(stated_alpha),
        "stated_tail_alpha": stated_alpha,
        "stated_tail_status": (
            "log-divergent" if moment_log_divergent(stated_alpha) else
            "finite" if moment_finite(stated_alpha) else "power-divergent"
        ),
        "note": (
            "E_2D >= T L_y is a trivial positive-gradient bound, not an exact reduction. "
            "The stated 1/r^4 profile makes I_eff logarithmically divergent; a finite "
            "I_eff requires a tail steeper than r^-4."
        ),
    }


def render_markdown(payload: dict) -> str:
    v = payload["verdict"]
    lines = [
        "# Dimensional reduction and moment of inertia (claim 6b)",
        "",
        f"1D wall tension at mu=1: T = {payload['wall_tension']:.12f}.",
        f"Lower-bound example: T * L_y (L_y=2) = {payload['lower_bound_example']:.12f}.",
        "",
        "| tail rho ~ r^-alpha | I_eff status |",
        "|---:|---|",
        "| 2 | power-divergent (integrand ~ r^1) |",
        "| 4 | log-divergent (integrand ~ r^-1) |",
        "| 5 | finite (integrand ~ r^-2) |",
        "",
        "I_eff = 2*pi int rho(r) r^3 dr; a tail steeper than r^-4 is required for convergence.",
        "",
        f"**Verdict:** trivial lower bound: **{v['6b_i_trivial_lower_bound']}**; "
        f"exact dimensional reduction: **{v['6b_ii_exact_dimensional_reduction']}**; "
        f"finite I_eff for the stated profile: **{v['6b_iii_moment_finite_for_stated_profile']}** "
        f"({v['stated_tail_status']}).",
        "",
        v["note"],
        "",
        f"- Config SHA-256: `{payload['meta']['config_sha256']}`",
        f"- Git: `{payload['meta']['git']['commit']}` (dirty={payload['meta']['git']['dirty']})",
        "",
    ]
    return "\n".join(lines)
