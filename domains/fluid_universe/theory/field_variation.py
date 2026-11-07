"""Unstructured 1D fixed-endpoint-density G-M field variation (claim 58, ADR-050).

Zero free parameters, no full-field (>1D) claims. The discrete G-M
field action on rho with exact 1D flux elimination (zero left flux,
slice-normalized mass, exp-parameterized positivity) is minimized
over unstructured interior densities with L-BFGS-B. Endpoint densities
are pinned Gaussians (1.2*sigma_q -> sigma_q, T = pi/4, m = w = 1).
The Gaussian bridge is the predicted global minimizer (continuous
(\\rho,m) convexity); multi-start convergence is the empirical check.
The nu = 0 (dust) problem must reproduce the classical
Gaussian-transport value -0.23852813742385703.

Trial-BVP field consistency only. A converged below-Gaussian action
that persists at the fine tier FALSIFIES the trial-class program's
optimality premise; coarse-only deviations mandate refinement
(UNVERIFIED), never a verdict.
"""

from __future__ import annotations

import math

import numpy as np

BASE = {"omega": 1.0, "hbar": 1.0, "mass": 1.0}
NU_QUANTUM = 0.5
NU_CLASSICAL = 0.0
X_LIM = 6.0
GRID_COARSE = (101, 101)
GRID_FINE = (201, 201)
HORIZON_FRACTION = 0.25
S0_FACTOR = 1.2
STARTS = ("gauss_linear", "bump", "bimodal", "wide")
GRAD_TOL = 1e-6
ACTION_TOL = 1e-4
ATTRIB_TOL = 1e-4
J_QUANTUM_BANK = -0.3906340559
J_CLASSICAL_BANK = -0.23852813742385703


def diffusivity(hbar: float, mass: float) -> float:
    if hbar <= 0.0 or mass <= 0.0:
        raise ValueError("hbar and mass must be positive")
    return hbar / (2.0 * mass)


def horizon(omega: float) -> float:
    if omega <= 0.0:
        raise ValueError("omega must be positive")
    return math.pi / (4.0 * omega)


def endpoint_densities(s0: float, sT: float, xc: np.ndarray) -> tuple:
    def gauss(s: float) -> np.ndarray:
        return np.exp(-xc**2 / (2.0 * s * s)) / math.sqrt(2.0 * math.pi * s * s)

    return gauss(s0), gauss(sT)


def bridge_widths(t: np.ndarray, s0: float, omega: float = 1.0) -> np.ndarray:
    """Analytic G-M primary-branch widths for the (s0 -> sigma_q) ends."""
    from domains.fluid_universe.theory.gaussian_bridge import pinney_coeffs, pinney_path
    from domains.fluid_universe.theory.gaussian_fluid import quantum_width

    sq = float(quantum_width(omega, 1.0, 1.0))
    horizon_T = horizon(omega)
    coeffs = pinney_coeffs(s0, sq, horizon_T, omega, 1.0, 1.0)
    return np.asarray(pinney_path(coeffs[0], np.asarray(t, dtype=float), omega))


def start_fields(
    kind: str,
    nt_interior: int,
    xc: np.ndarray,
    dx: float,
    rho0: np.ndarray,
    rhoT: np.ndarray,
    sq: float,
) -> np.ndarray:
    """Initial interior densities (mass-1 normalized slices)."""
    grids = np.linspace(0.0, 1.0, nt_interior + 2)[1:-1]
    out = np.empty((nt_interior, len(xc)))
    lam = (np.linspace(0.0, 1.0, nt_interior + 2)[1:-1])[:, None]
    if kind == "gauss_linear":
        s2 = (1.2 * sq) ** 2 + (sq**2 - (1.2 * sq) ** 2) * grids
        for k in range(nt_interior):
            s = math.sqrt(s2[k])
            out[k] = np.exp(-xc**2 / (2.0 * s * s)) / math.sqrt(2.0 * math.pi * s * s)
    elif kind == "bump":
        out[:] = 0.0
        base = start_fields("gauss_linear", nt_interior, xc, dx, rho0, rhoT, sq)
        bump = 0.1 * np.sin(math.pi * xc / X_LIM)[None, :] * np.sin(math.pi * lam)
        out = np.maximum(base + bump, 1e-12)
    elif kind == "bimodal":
        g = 0.5 * np.exp(-((xc + 0.5) ** 2) / (2.0 * 0.09)) + 0.5 * np.exp(
            -((xc - 0.5) ** 2) / (2.0 * 0.09)
        )
        g = g / math.sqrt(2.0 * math.pi * 0.09)
        out[:] = g[None, :]
    elif kind == "wide":
        s = 1.0
        g = np.exp(-xc**2 / (2.0 * s * s)) / math.sqrt(2.0 * math.pi * s * s)
        out[:] = g[None, :]
    else:
        raise ValueError(f"unknown start: {kind}")
    out = out / (out.sum(axis=1, keepdims=True) * dx)
    return out


class FieldProblem:
    """Discrete G-M field action with exact flux elimination."""

    def __init__(
        self,
        nx: int,
        nt: int,
        nu: float,
        omega: float = 1.0,
        mass: float = 1.0,
        x_lim: float = X_LIM,
        s0_factor: float = S0_FACTOR,
    ) -> None:
        from domains.fluid_universe.theory.gaussian_fluid import quantum_width

        self.nx = nx
        self.nt = nt
        self.nu = nu
        self.omega = omega
        self.mass = mass
        self.sq = float(quantum_width(omega, 1.0, 1.0))
        self.T = horizon(omega)
        self.dt = self.T / (nt - 1)
        self.dx = 2.0 * x_lim / nx
        self.xc = -x_lim + self.dx / 2.0 + np.arange(nx) * self.dx
        self.s0 = s0_factor * self.sq
        self.sT = self.sq
        rho0, rhoT = endpoint_densities(self.s0, self.sT, self.xc)
        self.rho0 = rho0 / (rho0.sum() * self.dx)
        self.rhoT = rhoT / (rhoT.sum() * self.dx)
        self.n_interior = nt - 2

    def unpack(self, phi: np.ndarray) -> np.ndarray:
        phi = np.asarray(phi, dtype=float).reshape(self.n_interior, self.nx - 1)
        rho = np.empty((self.nt, self.nx))
        rho[0] = self.rho0
        rho[-1] = self.rhoT
        for k in range(self.n_interior):
            full = np.concatenate([phi[k], [0.0]])
            e = np.exp(full - np.max(full))
            rho[k + 1] = e / (e.sum() * self.dx)
        return rho

    def action_and_gradient(
        self, phi: np.ndarray
    ) -> tuple[float, np.ndarray]:
        phi = np.asarray(phi, dtype=float).reshape(self.n_interior, self.nx - 1)
        rho = self.unpack(phi)
        dt, dx = self.dt, self.dx
        nu, omega, mass, xc = self.nu, self.omega, self.mass, self.xc
        J = 0.0
        grad_rho = np.zeros_like(rho)
        for k in range(self.nt - 1):
            a, b = rho[k], rho[k + 1]
            rm = 0.5 * (a + b)
            d = (b - a) / dt
            f = np.zeros(self.nx + 1)
            for i in range(self.nx):
                f[i + 1] = f[i] - dx * d[i]
            fv = 0.5 * (f[:-1] + f[1:])
            dr = np.empty(self.nx)
            dr[1:-1] = (rm[2:] - rm[:-2]) / (2.0 * dx)
            dr[0] = (rm[1] - rm[0]) / dx
            dr[-1] = (rm[-1] - rm[-2]) / dx
            # Floor well above the safe**2 underflow edge (1e-300**2 -> 0).
            # Vacuum mask: cells below 1e-12 carry only floating-point
            # noise (flux plateau residue ~1e-14 over true-vacuum
            # densities ~1e-31); their true action contribution is ~1e-12
            # and excluding them changes J far below any gate.
            safe = np.maximum(rm, 1e-150)
            live = (rm > 1e-12).astype(float)
            dens = (
                0.5 * mass * fv * fv / safe
                - mass * nu * nu / 2.0 * dr * dr / safe
                - 0.5 * mass * omega * omega * xc * xc * safe
            ) * live
            J += float(np.sum(dens) * dx * dt)
            g_fv = dx * dt * mass * fv / safe * live
            g_dr = -dx * dt * mass * nu * nu * dr / safe * live
            g_rm = (
                dx
                * dt
                * (
                    -0.5 * mass * fv * fv / safe**2
                    + mass * nu * nu / 2.0 * dr * dr / safe**2
                    - 0.5 * mass * omega * omega * xc * xc
                )
                * live
            )
            g_f = np.zeros(self.nx + 1)
            g_f[0] += 0.5 * g_fv[0]
            for i in range(1, self.nx):
                g_f[i] += 0.5 * (g_fv[i - 1] + g_fv[i])
            g_f[self.nx] += 0.5 * g_fv[self.nx - 1]
            suffix = np.cumsum(g_f[:0:-1])[::-1]
            g_d = np.empty(self.nx)
            g_d[0] = -dx * np.sum(g_f[1:])
            g_d[1:] = -dx * suffix[1:]
            g_rm = g_rm + self._dT(g_dr, dx)
            g_a = 0.5 * g_rm - g_d / dt
            g_b = 0.5 * g_rm + g_d / dt
            grad_rho[k] += g_a
            grad_rho[k + 1] += g_b
        grad_phi = np.empty((self.n_interior, self.nx - 1))
        for k in range(self.n_interior):
            g = grad_rho[k + 1]
            r = rho[k + 1]
            full = r * (g - dx * float(np.sum(g * r)))
            grad_phi[k] = full[:-1]
        return J, grad_phi.ravel()

    @staticmethod
    def _dT(g_dr: np.ndarray, dx: float) -> np.ndarray:
        """Exact transpose of the central/one-sided difference operator."""
        g = np.asarray(g_dr, dtype=float)
        n = g.shape[0]
        out = np.empty_like(g)
        out[0] = -g[0] / dx - g[1] / (2.0 * dx)
        out[n - 1] = g[n - 2] / (2.0 * dx) + g[n - 1] / dx
        if n > 3:
            out[1] = g[0] / dx - g[2] / (2.0 * dx)
            out[n - 2] = g[n - 3] / (2.0 * dx) - g[n - 1] / dx
            out[2 : n - 2] = (g[1 : n - 3] - g[3 : n - 1]) / (2.0 * dx)
        elif n == 3:
            out[1] = g[0] / dx - g[2] / dx
        return out

    def optimize(
        self, start: str, maxiter: int = 2000
    ) -> dict:
        from scipy.optimize import minimize

        init = start_fields(
            start, self.n_interior, self.xc, self.dx, self.rho0, self.rhoT, self.sq
        )
        phi0 = np.log(np.maximum(init * self.dx, 1e-300))
        phi0 = (phi0 - phi0[:, -1:])[:, :-1].ravel()

        def fun(p: np.ndarray) -> tuple[float, np.ndarray]:
            return self.action_and_gradient(p)

        res = minimize(
            fun,
            phi0,
            jac=True,
            method="L-BFGS-B",
            options={"maxiter": maxiter, "ftol": 1e-14, "gtol": 1e-9, "maxcor": 20},
        )
        J, grad = self.action_and_gradient(res.x)
        grad_inf = float(np.max(np.abs(grad)))
        rho = self.unpack(res.x)
        return {
            "start": start,
            "J_init": float(fun(phi0)[0]),
            "J_final": J,
            "grad_inf": grad_inf,
            "converged": bool(grad_inf <= 1e-6),
            "nit": int(res.nit),
            "nfev": int(res.nfev),
            "message": str(res.message),
            "interior": rho[1:-1].tolist(),
            "mass_err": float(np.max(np.abs(rho.sum(axis=1) * self.dx - 1.0))),
            "min_rho": float(np.min(rho)),
        }
