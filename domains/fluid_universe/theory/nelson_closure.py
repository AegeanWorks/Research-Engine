"""Osmotic-closure no-go at PDE level (claim 48, ADR-040).

Representation of the negative result, zero free parameters, no
dynamics asserted. For self-consistent osmotic drift b = D*grad(ln rho)
the stationary Fokker-Planck equation is identically satisfied:

    -div(rho * D*grad(ln rho)) + D*Laplacian(rho) = 0

for every smooth positive rho (rho*grad(ln rho) = grad(rho) exactly),
and the McKean moment flow preserves variance exactly
(d(sigma^2)/dt = 0). Selection of sigma^2 = hbar/(2*m*omega) = 0.5
therefore cannot live in osmotic-only data; in the Madelung reduction
it comes from the V(sigma) minimum (claim 22). The variational
(Yasui/Guerra-Morato) route stays an open candidate, never endorsed.

Numerics use the pinned conservative flux discretization with
np.gradient (2nd-order central interior, 1st-order at boundaries);
residuals are reported full-domain AND interior (|x| < L/2 - 1),
gated on interior. Key names avoid bare "fixed_point" (that is the
Ermakov term in-repo); this module speaks of stationary_map/sigma_map.
"""

from __future__ import annotations

import math

import numpy as np

from domains.fluid_universe.theory.nelson import osmotic_velocity

GRID_NS = (256, 512, 1024, 2048)
GRID_LENGTH = 20.0
DIFFUSION = 0.5
TRIAL_SIGMA_SQ = (0.125, 0.25, 0.5, 1.0, 2.0)


def trial_gaussian(x: np.ndarray, sigma_sq: float) -> np.ndarray:
    if sigma_sq <= 0.0:
        raise ValueError("sigma_sq must be positive")
    x = np.asarray(x, dtype=float)
    return np.exp(-x * x / (2.0 * sigma_sq)) / math.sqrt(
        2.0 * math.pi * sigma_sq
    )


def trial_bimodal(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    left = trial_gaussian(x + 2.0, 0.25)
    right = trial_gaussian(x - 2.0, 0.25)
    mix = 0.5 * (left + right)
    return mix / float(np.trapezoid(mix, x))


def fp_residual(
    rho: np.ndarray, dx: float, diffusion: float = DIFFUSION
) -> np.ndarray:
    """Stationary FP residual for self-consistent osmotic drift.

    R = -div(b*rho) + D*Laplacian(rho) with b = D*grad(ln rho),
    conservative flux form, np.gradient discretization.
    """
    rho = np.asarray(rho, dtype=float)
    if dx <= 0.0:
        raise ValueError("dx must be positive")
    drift = osmotic_velocity(rho, dx) * (diffusion / 0.5)
    flux = drift * np.maximum(rho, 1e-300)
    divergence = np.gradient(flux, dx)
    laplacian = np.gradient(np.gradient(np.maximum(rho, 1e-300), dx), dx)
    return -divergence + diffusion * laplacian


def interior_mask(x: np.ndarray, length: float = GRID_LENGTH) -> np.ndarray:
    return np.abs(np.asarray(x, dtype=float)) < length / 2.0 - 1.0


def residual_scaling() -> dict:
    """Max-abs residual vs dx for Gaussian probes and one bimodal probe."""
    probes = {
        f"gauss_{sq}": ("gaussian", sq) for sq in TRIAL_SIGMA_SQ
    }
    probes["bimodal"] = ("bimodal", None)
    rows = {}
    for name, (kind, sq) in probes.items():
        dx_values = []
        full_values = []
        interior_values = []
        for n in GRID_NS:
            dx = GRID_LENGTH / n
            x = (np.arange(n) - n // 2) * dx
            rho = (
                trial_gaussian(x, sq)
                if kind == "gaussian"
                else trial_bimodal(x)
            )
            residual = np.abs(fp_residual(rho, dx))
            dx_values.append(dx)
            full_values.append(float(np.max(residual)))
            interior_values.append(
                float(np.max(residual[interior_mask(x)]))
            )
        log_n = np.log(np.array([float(n) for n in GRID_NS]))
        slope_full = float(
            np.polyfit(log_n, np.log(np.array(full_values)), 1)[0]
        )
        slope_interior = float(
            np.polyfit(log_n, np.log(np.array(interior_values)), 1)[0]
        )
        rows[name] = {
            "dx": [float(v) for v in dx_values],
            "full": full_values,
            "interior": interior_values,
            "slope_full": slope_full,
            "slope_interior": slope_interior,
        }
    return {"grids": list(GRID_NS), "length": GRID_LENGTH, "rows": rows}


def frozen_drift_sigma_map() -> dict:
    """One frozen-drift reconstruction step per trial width.

    b is frozen from rho0; rho* is proportional to exp(int b/D);
    sigma* is refit by the second moment. Identity map predicts
    sigma* == sigma0 up to discretization.
    """
    entries = []
    for sq in TRIAL_SIGMA_SQ:
        sigma_values = []
        for n in GRID_NS:
            dx = GRID_LENGTH / n
            x = (np.arange(n) - n // 2) * dx
            rho0 = trial_gaussian(x, sq)
            drift = osmotic_velocity(rho0, dx)
            log_star = np.concatenate(
                [[0.0], np.cumsum(0.5 * (drift[1:] + drift[:-1]) * dx / DIFFUSION)]
            )
            log_star -= float(np.max(log_star))
            star = np.exp(np.clip(log_star, -700.0, 0.0))
            star /= float(np.trapezoid(star, x))
            sigma_star_sq = float(np.trapezoid(x * x * star, x))
            sigma_values.append(math.sqrt(max(sigma_star_sq, 0.0)))
        sigma0 = math.sqrt(sq)
        errors = [abs(v - sigma0) for v in sigma_values]
        if max(errors) <= 1e-13:
            slope = 0.0
            floor = True
        else:
            log_n = np.log(np.array([float(n) for n in GRID_NS]))
            slope = float(
                np.polyfit(
                    log_n,
                    np.log(np.maximum(np.array(errors), 1e-300)),
                    1,
                )[0]
            )
            floor = False
        entries.append(
            {
                "sigma0_sq": sq,
                "sigma_star": sigma_values,
                "abs_errors": errors,
                "error_slope": slope,
                "error_floor": floor,
            }
        )
    return {"entries": entries}


def ou_free_packet_instances() -> dict:
    """OU ground state and free packet satisfy the identity trivially."""
    from domains.fluid_universe.theory.nelson import free_packet_drift, ground_state_density

    x = np.linspace(-10.0, 10.0, 4097)
    dx = float(x[1] - x[0])
    rho_ou = ground_state_density(x, 1.0)
    residual_ou = fp_residual(rho_ou, dx)
    inner = interior_mask(x)
    return {
        "ou_residual_interior": float(np.max(np.abs(residual_ou[inner]))),
        "ou_residual_full": float(np.max(np.abs(residual_ou))),
        "free_drift_at_zero": [float(v) for v in free_packet_drift(
            np.array([0.0, 1.0, -1.0]), 0.0, 1.0
        )],
    }


def closure_scales() -> dict:
    """Collect the no-go correspondence bundle (no verdict)."""
    return {
        "grids": {"ns": list(GRID_NS), "length": GRID_LENGTH},
        "diffusion": DIFFUSION,
        "probes": {"gauss_sigma_sq": list(TRIAL_SIGMA_SQ), "bimodal": True},
        "units": {"hbar": 1.0, "mass": 1.0, "omega": 1.0},
        "stationary_map": residual_scaling(),
        "sigma_map": frozen_drift_sigma_map(),
        "instances": ou_free_packet_instances(),
    }
