"""Derrick scaling for the exact Frank-Oseen + Skyrme + Z3 energy.

In d spatial dimensions, under x -> lambda x,
    E2 = (K/2) int |grad n|^2      -> lambda^(d-2) E2,
    E4 = (kappa/2) int F_ij^2      -> lambda^(d-4) E4,
    V  = mu int (1 - cos 3 phi)    -> lambda^d V.
For d=3: E(lambda) = lambda E2 + lambda^-1 E4 + lambda^3 V, and a stationary
soliton satisfies the virial relation E2 - E4 + 3V = 0.  The second derivative
is 2(E4 + 3V) > 0, so a stationary point is a scaling minimum whenever
E4 + 3V > 0.

This is a necessary condition, not an existence proof.  In particular:
  * kappa = 0 gives dE/dlambda = E2 + 3 lambda^2 V > 0: no stationary point;
  * kappa < 0 makes E4 negative and the energy unbounded as lambda -> 0.
So a stable scaling soliton in d=3 requires kappa > 0 (with K > 0, mu >= 0).
Whether a Hopfion with H >= 1 actually exists still requires a numerical
solution; no such solution is claimed here.
"""

from __future__ import annotations

import math


def exponents(d: int = 3) -> dict[str, int]:
    if d < 1:
        raise ValueError("d must be positive")
    return {"gradient": d - 2, "skyrme": d - 4, "potential": d}


def scaling_energy(lambda_: float, e2: float, e4: float, potential: float, d: int = 3) -> float:
    if lambda_ <= 0.0:
        raise ValueError("lambda must be positive")
    power = exponents(d)
    return (
        lambda_ ** power["gradient"] * e2
        + lambda_ ** power["skyrme"] * e4
        + lambda_ ** power["potential"] * potential
    )


def virial(e2: float, e4: float, potential: float, d: int = 3) -> float:
    power = exponents(d)
    return (
        power["gradient"] * e2
        + power["skyrme"] * e4
        + power["potential"] * potential
    )


def second_derivative(e2: float, e4: float, potential: float, d: int = 3) -> float:
    power = exponents(d)
    return (
        power["gradient"] * (power["gradient"] - 1) * e2
        + power["skyrme"] * (power["skyrme"] - 1) * e4
        + power["potential"] * (power["potential"] - 1) * potential
    )


def stationary_scale_squared(e2: float, e4: float, potential: float, d: int = 3) -> float | None:
    """Return lambda^2 at the stationary point for d=3, or None if none exists."""
    if d != 3:
        raise ValueError("closed form implemented for d=3 only")
    if e2 <= 0.0:
        raise ValueError("gradient energy must be positive")
    if potential == 0.0:
        if e4 <= 0.0:
            return None
        return e4 / e2
    if potential < 0.0:
        raise ValueError("potential energy must be non-negative")
    # dE/dlambda = 0  =>  3 V y^2 + E2 y - E4 = 0, y = lambda^2.
    discriminant = e2 * e2 + 12.0 * potential * e4
    if discriminant < 0.0:
        return None
    y = (-e2 + math.sqrt(discriminant)) / (6.0 * potential)
    return y if y > 0.0 else None


def scaling_minimum(e2: float, e4: float, potential: float) -> dict | None:
    y = stationary_scale_squared(e2, e4, potential, d=3)
    if y is None:
        return None
    lam = math.sqrt(y)
    energy = scaling_energy(lam, e2, e4, potential, d=3)
    curvature = second_derivative(e2, e4, potential, d=3)
    return {
        "lambda": lam,
        "lambda_squared": y,
        "energy": energy,
        "curvature": curvature,
        "is_minimum": curvature > 0.0,
        "virial_at_lambda_one": virial(e2, e4, potential, d=3),
    }


def stable_region(k: float, kappa: float, mu: float) -> dict:
    """Necessary conditions for a stable scaling soliton in d=3."""
    if k <= 0.0:
        raise ValueError("K must be positive")
    if mu < 0.0:
        raise ValueError("mu must be non-negative")
    has_skyrme = kappa > 0.0
    bounded_below = kappa >= 0.0
    return {
        "K_positive": True,
        "mu_non_negative": True,
        "kappa_positive": has_skyrme,
        "energy_bounded_below": bounded_below,
        "scaling_minimum_exists": has_skyrme and bounded_below,
        "hopfion_existence_proved": False,
        "note": (
            "k=0 or kappa<=0: no stable scaling soliton in d=3. "
            "kappa>0: a scaling minimum exists for any E2>0, E4>0, V>=0, "
            "but existence of a Hopfion solution is not proved by Derrick scaling."
        ),
    }


def symbolic_virial() -> bool:
    """Verify d/dlambda E(lambda) at lambda=1 equals the virial expression."""
    import sympy as sp

    lam, d, e2, e4, potential = sp.symbols("lambda d E2 E4 V", positive=True)
    energy = lam ** (d - 2) * e2 + lam ** (d - 4) * e4 + lam**d * potential
    derivative = sp.simplify(sp.diff(energy, lam).subs(lam, 1))
    expected = (d - 2) * e2 + (d - 4) * e4 + d * potential
    return sp.simplify(derivative - expected) == 0
