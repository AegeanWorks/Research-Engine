"""Real Z3 rotor potential scan (claim 19, ADR-010).

Hamiltonian on the phase circle:

    H = (L - A)^2/(2I) + mu (1 - cos 3 phi) + nu (1 - cos 6 phi).

A real potential preserves the antiunitary symmetry that makes the k=1 and k=2
sectors degenerate at A=0.  A fractional flux A splits them, but the three
lowest sector energies may still be too compressed to reach Koide Q=2/3.  This
module scans the (nu, A) family and reports the maximum Q, with a Fourier
truncation check at the best point.
"""

from __future__ import annotations

import numpy as np

from domains.fluid_universe.theory.vortex_particles import koide_q

KOIDE_TARGET = 2.0 / 3.0
KOIDE_TOLERANCE = 0.01


def sector_matrix(
    mu: float,
    nu: float,
    flux: float,
    sector: int,
    n_cutoff: int = 120,
    inertia: float = 1.0,
) -> np.ndarray:
    if sector not in (0, 1, 2):
        raise ValueError("sector must be 0, 1 or 2")
    if mu < 0.0 or nu < 0.0:
        raise ValueError("mu and nu must be non-negative")
    if inertia <= 0.0:
        raise ValueError("inertia must be positive")
    if n_cutoff < 8:
        raise ValueError("n_cutoff too small")
    n = np.arange(-n_cutoff, n_cutoff + 1)
    keep = n[np.mod(n, 3) == sector % 3]
    matrix = np.diag((keep.astype(float) - flux) ** 2 / (2.0 * inertia))
    index = {int(value): i for i, value in enumerate(keep)}
    for i, value in enumerate(keep):
        matrix[i, i] += mu + nu
        for shift in (+3, -3):
            j = index.get(int(value + shift))
            if j is not None:
                matrix[i, j] += -0.5 * mu
        for shift in (+6, -6):
            j = index.get(int(value + shift))
            if j is not None:
                matrix[i, j] += -0.5 * nu
    return matrix


def sector_energies(
    mu: float,
    nu: float,
    flux: float,
    n_cutoff: int = 120,
    inertia: float = 1.0,
) -> np.ndarray:
    values = [
        np.linalg.eigvalsh(sector_matrix(mu, nu, flux, sector, n_cutoff, inertia))[0]
        for sector in (0, 1, 2)
    ]
    return np.asarray(values, dtype=float)


def scan(
    mu: float = 1.0,
    nus: tuple[float, ...] = (0.0, 1.0, 3.0, 10.0),
    fluxes: np.ndarray | tuple[float, ...] = tuple(np.linspace(0.0, 1.0, 11)),
    n_cutoff: int = 120,
) -> dict:
    rows = []
    for nu in nus:
        for flux in fluxes:
            energies = sector_energies(mu, nu, float(flux), n_cutoff)
            rows.append(
                {
                    "mu": mu,
                    "nu": nu,
                    "flux": float(flux),
                    "energies": [float(value) for value in energies],
                    "koide_q": koide_q(energies),
                    "e1_minus_e2": float(energies[1] - energies[2]),
                }
            )
    best = max(rows, key=lambda row: row["koide_q"])
    zero_flux = [row for row in rows if row["flux"] == 0.0]
    degenerate = all(abs(row["e1_minus_e2"]) < 1e-10 for row in zero_flux)
    best_high = sector_energies(mu, best["nu"], best["flux"], n_cutoff * 2)
    best_high_q = koide_q(best_high)
    convergence = abs(best_high_q - best["koide_q"])
    max_q_by_nu = {
        str(nu): max(row["koide_q"] for row in rows if row["nu"] == nu)
        for nu in nus
    }
    falsified = bool(best["koide_q"] < KOIDE_TARGET - KOIDE_TOLERANCE)
    return {
        "rows": rows,
        "best": best,
        "best_n_cutoff_q": best_high_q,
        "best_convergence_delta": convergence,
        "zero_flux_degenerate": bool(degenerate),
        "max_q_by_nu": max_q_by_nu,
        "koide_target": KOIDE_TARGET,
        "koide_tolerance": KOIDE_TOLERANCE,
        "falsified": falsified,
        "status": (
            "FALSIFIED (real Z3 rotor never reaches Q=2/3 in the scan)"
            if falsified
            else "UNVERIFIED (a scan point reaches Q=2/3; not a derivation)"
        ),
        "note": (
            "A real potential cannot split the k=1,2 sectors at zero flux; a "
            "fractional flux splits them but the lowest levels remain close. "
            "Reaching Q=2/3 needs a complex phase or a different mass mapping."
        ),
    }
