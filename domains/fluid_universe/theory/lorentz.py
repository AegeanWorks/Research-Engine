"""Linearised director dispersion and the emergent-metric question (claims 11-12).

For a background n0 = z, the two transverse director modes have a 2x2 elastic
matrix M(k).  Their speeds are direction-dependent unless K1=K2=K3.  We define
the residual anisotropy

    xi = (c_max^2 - c_min^2) / mean(c^2)

over directions and polarisations.

There is no emergent metric in this model: the background selects a preferred
frame, and for unequal K the two modes have different speeds.  A Lorentz-
invariant IR point would require an additional RG calculation that does not
exist here.

The director modes are neutral.  Photon birefringence, GRB dispersion, CMB
isotropy, and clock/cavity limits therefore do not directly constrain them.
We record those limits and mark them "not applicable" unless a coupling to
photons is added.  A conditional statement is included: if a model identified
the director modes with photons with O(1) coupling, the equal-K case would pass
all bounds exactly, while an O(1) anisotropy would be excluded by many orders
of magnitude.
"""

from __future__ import annotations

import math

import numpy as np


def elastic_matrix(k: np.ndarray, k1: float, k2: float, k3: float) -> np.ndarray:
    kx, ky, kz = (float(x) for x in k)
    return np.array(
        [
            [k1 * kx * kx + k2 * ky * ky + k3 * kz * kz, (k1 - k2) * kx * ky],
            [(k1 - k2) * kx * ky, k1 * ky * ky + k2 * kx * kx + k3 * kz * kz],
        ]
    )


def speeds(
    direction: tuple[float, float, float],
    k1: float,
    k2: float,
    k3: float,
    rho: float = 1.0,
) -> np.ndarray:
    if rho <= 0.0:
        raise ValueError("rho must be positive")
    vector = np.asarray(direction, dtype=float)
    norm = float(np.linalg.norm(vector))
    if norm == 0.0:
        raise ValueError("direction must be nonzero")
    unit = vector / norm
    values = np.linalg.eigvalsh(elastic_matrix(unit, k1, k2, k3))
    if np.any(values < 0.0):
        raise ValueError("elastic matrix is not positive semidefinite")
    return np.sqrt(values / rho)


def residual_anisotropy(
    k1: float,
    k2: float,
    k3: float,
    rho: float = 1.0,
    n_samples: int = 4000,
    seed: int = 20261025,
) -> dict:
    """Sample directions on the sphere and return the max fractional speed split."""
    if k1 == k2 == k3:
        if k1 <= 0.0 or rho <= 0.0:
            raise ValueError("K and rho must be positive")
        c2 = k1 / rho
        return {
            "xi": 0.0,
            "c2_min": float(c2),
            "c2_max": float(c2),
            "c2_mean": float(c2),
            "n_samples": n_samples,
            "seed": seed,
        }
    rng = np.random.default_rng(seed)
    vectors = rng.normal(size=(n_samples, 3))
    vectors /= np.linalg.norm(vectors, axis=1)[:, None]
    all_speeds = []
    for vector in vectors:
        all_speeds.extend(speeds(tuple(vector), k1, k2, k3, rho))
    all_speeds = np.asarray(all_speeds)
    c2 = all_speeds * all_speeds
    mean = float(np.mean(c2))
    if mean <= 0.0:
        raise ValueError("mean speed squared must be positive")
    xi = float((np.max(c2) - np.min(c2)) / mean)
    return {
        "xi": xi,
        "c2_min": float(np.min(c2)),
        "c2_max": float(np.max(c2)),
        "c2_mean": mean,
        "n_samples": n_samples,
        "seed": seed,
    }


def axis_speeds(k1: float, k2: float, k3: float, rho: float = 1.0) -> dict:
    return {
        "along_x": [float(x) for x in speeds((1, 0, 0), k1, k2, k3, rho)],
        "along_y": [float(x) for x in speeds((0, 1, 0), k1, k2, k3, rho)],
        "along_z": [float(x) for x in speeds((0, 0, 1), k1, k2, k3, rho)],
    }


BOUNDS = [
    {
        "name": "vacuum birefringence (spectropolarimetry)",
        "quantity": "dimensionless LV coefficient",
        "limit_order": -34,
        "limit": 1e-34,
        "applies_to_director_modes": False,
        "why": "The bound is on photon-polarisation coefficients; director modes are neutral.",
    },
    {
        "name": "GRB dispersion (Fermi-LAT, linear, 10 GeV)",
        "quantity": "Delta c / c",
        "limit_order": -18,
        "limit": 1e-18,
        "applies_to_director_modes": False,
        "why": "The bound is on photon time-of-flight; no photon coupling in the model.",
    },
    {
        "name": "CMB isotropy",
        "quantity": "Delta T / T",
        "limit_order": -5,
        "limit": 1e-5,
        "applies_to_director_modes": False,
        "why": "Indirect, and requires the director modes to source the CMB; not modelled.",
    },
    {
        "name": "clock/cavity comparison",
        "quantity": "Delta c / c",
        "limit_order": -17,
        "limit": 1e-17,
        "applies_to_director_modes": False,
        "why": "Bounds photon/cavity propagation; no coupling to the director sector.",
    },
]


def verdict(k1: float, k2: float, k3: float) -> dict:
    equal = k1 == k2 == k3
    aniso = residual_anisotropy(k1, k2, k3)
    return {
        "equal_K": equal,
        "xi": aniso["xi"],
        "11a_emergent_metric_at_tree_level": False,
        "11b_one_loop_RG_to_Lorentz_invariant_IR": "UNVERIFIED",
        "12_lv_bounds_directly_applicable": False,
        "12_equal_K_is_isotropic": bool(equal),
        "12_conditional_xi_above_grb_bound": bool(aniso["xi"] > 1e-18),
        "note": (
            "The linearised model has a preferred frame and no metric. The two "
            "transverse modes have equal speed only for K1=K2=K3. The director "
            "modes are neutral, so photon-birefringence and GRB bounds do not "
            "directly apply. If a coupling to photons were added, equal K would "
            "pass all bounds exactly, while an O(1) anisotropy would be excluded "
            "by the GRB/clock/birefringence limits."
        ),
    }


def conditional_bound(k1: float, k2: float, k3: float) -> dict:
    aniso = residual_anisotropy(k1, k2, k3)
    xi = aniso["xi"]
    rows = []
    for bound in BOUNDS:
        if bound["quantity"] == "Delta c / c":
            rows.append(
                {
                    "name": bound["name"],
                    "limit": bound["limit"],
                    "xi": xi,
                    "passes_if_photon": bool(xi <= bound["limit"]),
                }
            )
    return {"xi": xi, "checks": rows}
