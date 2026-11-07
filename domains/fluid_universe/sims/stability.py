"""Tangent-space Hessian of the 3D Faddeev-Niemi + Z3 energy.

The field is a product of unit spheres, one per interior site, so the physical
tangent space has two directions per site.  The radial direction is a pure
gauge mode: the energy normalizes the field internally.  A matrix-free
operator that keeps the ambient three components therefore carries a
two-thirds-dimensional null space, and ARPACK on it can return spurious
values.  This module removes the radial modes explicitly with a per-site
orthonormal tangent basis before building the operator.

The dense check at N<=8 compares the matrix-free operator with
`jax.hessian(energy)` restricted to the same tangent basis.  That is the
validation the earlier ambient operator failed.

A negative eigenvalue falsifies this candidate as a local minimum.  A
positive spectrum is evidence at one grid and one candidate, never a proof of
stability.
"""

from __future__ import annotations

import math

import jax
import jax.numpy as jnp
import numpy as np
from scipy.sparse.linalg import LinearOperator, eigsh

from domains.fluid_universe.sims.core3d import energy, relax, z3_order
from domains.fluid_universe.sims.scale_iteration import rescale_field
from domains.fluid_universe.theory.hopf import chern_simons_charge, compactified_field

jax.config.update("jax_enable_x64", True)

NEGATIVE_TOLERANCE = 1e-6
VALIDATION_TOLERANCE = 1e-8


def tangent_basis(field: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return two orthonormal tangent vectors at every interior site."""
    interior = field[1:-1, 1:-1, 1:-1]
    norm = np.linalg.norm(interior, axis=-1, keepdims=True)
    if np.any(norm <= 0.0):
        raise ValueError("field has a zero-length site")
    normal = interior / norm

    reference = np.empty_like(normal)
    near_pole = np.abs(normal[..., 2]) < 0.9
    reference[near_pole] = np.array([0.0, 0.0, 1.0])
    reference[~near_pole] = np.array([1.0, 0.0, 0.0])

    e1 = np.cross(reference, normal)
    e1 /= np.linalg.norm(e1, axis=-1, keepdims=True)
    e2 = np.cross(normal, e1)
    return e1, e2


def build_candidate(
    n: int = 64,
    length: float = 10.0,
    iterations: int = 5,
    steps: int = 600,
    dt: float = 5e-4,
) -> tuple[np.ndarray, dict]:
    """Damped scale iteration, returning the snapshot with the smallest |virial|."""
    initial, dx = compactified_field(n, length)
    field = initial
    best: np.ndarray | None = None
    best_virial = float("inf")
    best_terms: dict | None = None
    for _ in range(iterations):
        relaxed, _history, terms = relax(
            jnp.asarray(field), dx, 0.0, steps, dt, fix_boundary=True
        )
        snapshot = np.asarray(relaxed)
        virial = terms["E2"] - terms["E4"]
        if abs(virial) < best_virial:
            best_virial = abs(virial)
            best = snapshot
            best_terms = terms
        lam = math.sqrt(terms["E4"] / terms["E2"])
        field = rescale_field(snapshot, dx, length, math.sqrt(lam))
    if best is None or best_terms is None:
        raise RuntimeError("no candidate recorded")
    return best, {
        "n": n,
        "length": length,
        "dx": float(dx),
        "E2": float(best_terms["E2"]),
        "E4": float(best_terms["E4"]),
        "virial": float(best_terms["E2"] - best_terms["E4"]),
        "H": float(chern_simons_charge(best, dx)),
        "Z3": float(z3_order(best)),
        "force_rms": float(best_terms["force_rms"]),
    }


def _dense_tangent_hessian(
    field: np.ndarray, dx: float, e1: np.ndarray, e2: np.ndarray
) -> np.ndarray:
    """Dense Hessian of the energy restricted to the tangent basis (N<=8 only)."""
    n = field.shape[0]
    if n > 8:
        raise ValueError("dense tangent Hessian is limited to N<=8")
    v = jnp.asarray(field)
    hessian = np.asarray(jax.hessian(lambda x: energy(x, dx, 1.0, 1.0, 0.0))(v))
    hessian = hessian.reshape(3 * n**3, 3 * n**3)

    interior_mask = np.zeros((n, n, n), dtype=bool)
    interior_mask[1:-1, 1:-1, 1:-1] = True
    keep = np.repeat(interior_mask.reshape(-1), 3)
    hessian = hessian[np.ix_(keep, keep)]

    n_interior = (n - 2) ** 3
    q = np.zeros((3 * n_interior, 2 * n_interior))
    e1_flat = e1.reshape(-1, 3)
    e2_flat = e2.reshape(-1, 3)
    for site in range(n_interior):
        q[3 * site : 3 * site + 3, 2 * site] = e1_flat[site]
        q[3 * site : 3 * site + 3, 2 * site + 1] = e2_flat[site]
    return q.T @ hessian @ q


def tangent_operator(
    field: np.ndarray,
    dx: float,
    e1: np.ndarray | None = None,
    e2: np.ndarray | None = None,
) -> tuple[LinearOperator, int]:
    """Matrix-free Hessian on the two-dimensional tangent space of each site."""
    n = field.shape[0]
    if e1 is None or e2 is None:
        e1, e2 = tangent_basis(field)
    v = jnp.asarray(field)
    e1_j = jnp.asarray(e1)
    e2_j = jnp.asarray(e2)
    n_interior = (n - 2) ** 3
    dimension = 2 * n_interior
    grad_fn = jax.jit(lambda x: jax.grad(energy, argnums=0)(x, dx, 1.0, 1.0, 0.0))

    def matvec(coefficients: np.ndarray) -> np.ndarray:
        c = jnp.asarray(coefficients).reshape(n - 2, n - 2, n - 2, 2)
        tangent = c[..., 0:1] * e1_j + c[..., 1:2] * e2_j
        full = jnp.zeros_like(v).at[1:-1, 1:-1, 1:-1].set(tangent)
        _, product = jax.jvp(grad_fn, (v,), (full,))
        out = product[1:-1, 1:-1, 1:-1]
        first = jnp.sum(out * e1_j, axis=-1)
        second = jnp.sum(out * e2_j, axis=-1)
        return np.asarray(jnp.stack([first, second], axis=-1), dtype=np.float64).reshape(-1)

    operator = LinearOperator(
        (dimension, dimension), matvec=matvec, dtype=np.float64
    )
    return operator, dimension


def validate_operator(
    n: int = 8,
    length: float = 4.0,
    steps: int = 20,
    dt: float = 5e-4,
    k: int = 4,
) -> dict:
    """Compare the matrix-free operator with the dense tangent Hessian."""
    candidate, info = build_candidate(
        n=n, length=length, iterations=1, steps=steps, dt=dt
    )
    e1, e2 = tangent_basis(candidate)
    dense = _dense_tangent_hessian(candidate, info["dx"], e1, e2)
    operator, dimension = tangent_operator(candidate, info["dx"], e1, e2)
    basis = np.eye(dimension)
    matrix_free = np.column_stack(
        [operator.matvec(basis[:, column]) for column in range(dimension)]
    )
    error = float(np.max(np.abs(dense - matrix_free)))
    symmetry = float(np.max(np.abs(matrix_free - matrix_free.T)))
    dense_values = np.sort(np.linalg.eigvalsh(dense))[: min(k, dimension)]
    operator_values = np.sort(
        eigsh(operator, k=min(k, dimension - 1), which="SA", return_eigenvectors=False)
    )
    return {
        "n": n,
        "dimension": dimension,
        "max_abs_error": error,
        "symmetry_error": symmetry,
        "dense_smallest": [float(value) for value in dense_values],
        "operator_smallest": [float(value) for value in operator_values],
        "passed": bool(
            error < VALIDATION_TOLERANCE and symmetry < VALIDATION_TOLERANCE
        ),
    }


def hessian_spectrum(
    field: np.ndarray,
    dx: float,
    k: int = 8,
    e1: np.ndarray | None = None,
    e2: np.ndarray | None = None,
) -> dict:
    """Low-lying eigenvalues of the tangent-space Hessian."""
    operator, dimension = tangent_operator(field, dx, e1, e2)
    if dimension < 2:
        raise ValueError("tangent space is too small for a spectrum")
    requested = min(k, dimension - 1)
    values = np.sort(
        eigsh(
            operator,
            k=requested,
            which="SA",
            return_eigenvectors=False,
            tol=1e-8,
            maxiter=50_000,
        )
    )
    return {
        "n": field.shape[0],
        "dimension": dimension,
        "requested_k": requested,
        "smallest_eigenvalues": [float(value) for value in values],
        "min_eigenvalue": float(values[0]),
        "negative_count": int(np.sum(values < -NEGATIVE_TOLERANCE)),
        "near_zero_count": int(np.sum(np.abs(values) < 1e-4)),
    }


def classify_escape(attempts: list[dict], note: str | None = None) -> dict:
    """Summarise a saddle-escape search without promoting beyond one grid."""
    found = any(attempt.get("local_minimum") is True for attempt in attempts)
    if found:
        status = "NUMERIC (local minimum at N=64; not a proof)"
    else:
        status = "UNVERIFIED"
    return {
        "attempts": len(attempts),
        "local_minimum_found": bool(found),
        "claim_14b_status": status,
        "note": note
        or (
            "A positive spectrum at one grid and one perturbed candidate is "
            "numerical evidence, not a stability proof; a negative search does "
            "not rule out a different ansatz."
        ),
    }


def hessian_modes(
    field: np.ndarray,
    dx: float,
    k: int = 1,
    e1: np.ndarray | None = None,
    e2: np.ndarray | None = None,
) -> dict:
    """Lowest tangent eigenpairs, with each eigenvector mapped back to a field."""
    n = field.shape[0]
    if e1 is None or e2 is None:
        e1, e2 = tangent_basis(field)
    operator, dimension = tangent_operator(field, dx, e1, e2)
    requested = min(k, dimension - 1)
    values, vectors = eigsh(
        operator,
        k=requested,
        which="SA",
        return_eigenvectors=True,
        tol=1e-8,
        maxiter=50_000,
    )
    order = np.argsort(values)
    values = values[order]
    vectors = vectors[:, order]
    modes = []
    for column in range(values.size):
        coefficients = vectors[:, column].reshape(n - 2, n - 2, n - 2, 2)
        mode = np.zeros_like(field)
        mode[1:-1, 1:-1, 1:-1] = (
            coefficients[..., 0:1] * e1 + coefficients[..., 1:2] * e2
        )
        modes.append(mode)
    return {
        "n": n,
        "dimension": dimension,
        "requested_k": requested,
        "eigenvalues": [float(value) for value in values],
        "modes": modes,
    }


def normalize_mode(mode: np.ndarray) -> np.ndarray:
    """Scale a tangent mode to unit RMS over the interior."""
    interior = np.asarray(mode)[1:-1, 1:-1, 1:-1]
    rms = float(np.sqrt(np.mean(interior * interior)))
    if rms <= 0.0:
        raise ValueError("mode has zero interior norm")
    return np.asarray(mode, dtype=float) / rms


def perturb_along_mode(field: np.ndarray, mode: np.ndarray, amplitude: float) -> np.ndarray:
    """Add a normalized tangent mode and renormalize every site."""
    if amplitude == 0.0:
        raise ValueError("amplitude must be nonzero")
    perturbed = np.asarray(field, dtype=float) + amplitude * normalize_mode(mode)
    return perturbed / np.linalg.norm(perturbed, axis=-1, keepdims=True)


def classify_candidate(validation: dict, spectrum: dict) -> dict:
    """Classify one candidate's Hessian without overstating the result."""
    n = spectrum["n"]
    if not validation["passed"]:
        status = "UNVERIFIED (operator validation failed)"
        claim_14b = "UNVERIFIED"
    elif spectrum["min_eigenvalue"] < -NEGATIVE_TOLERANCE:
        status = f"FALSIFIED (negative Hessian modes at N={n})"
        claim_14b = "UNVERIFIED"
    else:
        status = f"NUMERIC (local minimum at N={n}; evidence, not proof)"
        claim_14b = f"NUMERIC (local minimum at N={n}; not a proof)"
    local_minimum = bool(
        validation["passed"]
        and spectrum["min_eigenvalue"] >= -NEGATIVE_TOLERANCE
    )
    return {
        "operator_validated": validation["passed"],
        "local_minimum_at_N64": local_minimum,
        "stable_at_N64_proved": False,
        "claim_14b_status": claim_14b,
        "candidate_status": status,
        "note": (
            "The Hessian acts on the two-dimensional tangent space at every "
            "site, so the radial normalization modes are removed. A negative "
            "eigenvalue falsifies this candidate as a local minimum; a "
            "positive spectrum is evidence at one grid, not a stability proof. "
            "Fixed vacuum boundaries lift exact translation zero modes."
        ),
    }


def run_stability_check(
    n: int = 64,
    length: float = 10.0,
    iterations: int = 5,
    steps: int = 600,
    dt: float = 5e-4,
    k: int = 8,
    validate_n: int = 8,
) -> dict:
    """Build the scale-stationary candidate and compute its tangent Hessian."""
    candidate, info = build_candidate(
        n=n, length=length, iterations=iterations, steps=steps, dt=dt
    )
    validation = validate_operator(n=validate_n)
    spectrum = hessian_spectrum(candidate, info["dx"], k=k)

    if not validation["passed"]:
        status = "UNVERIFIED (operator validation failed)"
    elif spectrum["min_eigenvalue"] < -NEGATIVE_TOLERANCE:
        status = "FALSIFIED (negative Hessian modes at N=64)"
    else:
        status = "NUMERIC (local minimum at N=64; evidence, not proof)"

    local_minimum = bool(
        validation["passed"] and spectrum["min_eigenvalue"] >= -NEGATIVE_TOLERANCE
    )
    return {
        "candidate": info,
        "dense_validation": validation,
        "spectrum": spectrum,
        "verdict": {
            "operator_validated": validation["passed"],
            "local_minimum_at_N64": local_minimum,
            "stable_at_N64_proved": False,
            "claim_14b_status": "UNVERIFIED",
            "claim_14d_status": status,
            "note": (
                "The Hessian acts on the two-dimensional tangent space at every "
                "site, so the radial normalization modes are removed. A negative "
                "eigenvalue falsifies this candidate as a local minimum; a "
                "positive spectrum is evidence at one grid, not a stability proof. "
                "Fixed vacuum boundaries lift exact translation zero modes."
            ),
        },
    }
