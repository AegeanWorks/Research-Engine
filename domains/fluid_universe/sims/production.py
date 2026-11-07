"""Production scan for claim 15: E2 + Skyrme E4 + Z3 potential.

The scan starts from the analytic H=1 map, relaxes with fixed vacuum faces, and
records the Hopf charge, the Z3 order parameter, the residual force, the energy
drift and the field smoothness.  The Hopf estimator is checked against a
spectrally upsampled field; the native N=64 diagnostic becomes unreliable once
the field develops features at the grid scale.

Acceptance criteria are fixed here, before the production run:

* ``H`` within ``H_TOL`` of 1 and the native and upsampled estimates agree
  within ``H_TOL``;
* ``Z3 >= Z3_MIN``;
* ``force_rms <= FORCE_TOL`` and the relative energy drift over the last chunk
  is at most ``DRIFT_TOL``;
* the maximum bond difference is at most ``BOND_TOL`` (at least two grid
  points per feature).

A failed scan cannot falsify the existence of some other 3D simulation with
coexistence; the claim stays UNVERIFIED unless every criterion holds.  The
scan is deterministic for a fixed seed, so two separate processes can be
compared directly.
"""

from __future__ import annotations

import math
import time

import jax
import jax.numpy as jnp
import numpy as np

jax.config.update("jax_enable_x64", True)

from domains.fluid_universe.sims.core3d import energy, energy_terms, normalize, z3_order
from domains.fluid_universe.theory.hopf import chern_simons_charge, compactified_field

H_TOL = 5.0e-3
Z3_MIN = 0.5
FORCE_TOL = 1.0e-2
DRIFT_TOL = 1.0e-2
BOND_TOL = 0.5
PRE_NORM_TOL = 0.1
MAX_WALL_SECONDS = 900.0


def spectral_upsample(field: np.ndarray, factor: int) -> np.ndarray:
    """Band-limited upsampling of a periodic real field by an integer factor.

    The compactified field is smooth and vacuum at the faces, so the periodic
    spectral interpolation is accurate away from the grid scale.  The result is
    renormalized; this is a diagnostic of the estimator, not a new simulation.
    """
    if factor < 1:
        raise ValueError("factor must be at least 1")
    field = np.asarray(field, dtype=float)
    if factor == 1:
        return field
    n = field.shape[0]
    m = n * factor
    spectrum = np.fft.fftshift(
        np.fft.fftn(field, axes=(0, 1, 2)), axes=(0, 1, 2)
    )
    pad = (m - n) // 2
    padded = np.zeros((m, m, m, field.shape[-1]), dtype=complex)
    padded[pad : pad + n, pad : pad + n, pad : pad + n] = spectrum
    out = np.fft.ifftn(
        np.fft.ifftshift(padded, axes=(0, 1, 2)), axes=(0, 1, 2)
    ).real * factor**3
    return out / np.linalg.norm(out, axis=-1, keepdims=True)


def field_metrics(
    field: np.ndarray,
    dx: float,
    mu: float,
    upsample_factor: int = 2,
) -> dict:
    """Energy, topology and smoothness of one field."""
    field = np.asarray(field, dtype=float)
    terms = energy_terms(jnp.asarray(field), dx, mu)
    metrics = {key: float(value) for key, value in terms.items()}
    metrics["H"] = float(chern_simons_charge(field, dx))
    metrics["Z3"] = float(z3_order(field))
    if upsample_factor > 1:
        upsampled = spectral_upsample(field, upsample_factor)
        metrics["H_upsampled"] = float(
            chern_simons_charge(upsampled, dx / upsample_factor)
        )
    else:
        metrics["H_upsampled"] = metrics["H"]
    gradient = jax.grad(energy, argnums=0)(
        jnp.asarray(field), dx, 1.0, 1.0, mu
    )
    metrics["force_rms"] = float(jnp.sqrt(jnp.mean(gradient * gradient)))
    differences = [
        np.abs(field - np.roll(field, -1, axis=axis)) for axis in range(3)
    ]
    flat = np.concatenate([value.reshape(-1) for value in differences])
    metrics["max_bond"] = float(np.max(flat))
    metrics["mean_bond"] = float(np.mean(flat))
    metrics["fraction_bond_gt_tol"] = float(np.mean(flat > BOND_TOL))
    return metrics


def run_stage(
    field: np.ndarray,
    dx: float,
    mu: float,
    steps: int,
    dt: float,
    deadline: float | None = None,
) -> tuple[np.ndarray, dict]:
    """Relax for ``steps`` steps and record the smallest pre-normalization norm."""
    current = normalize(jnp.asarray(field))
    n = current.shape[0]
    mask = np.zeros((n, n, n), dtype=bool)
    mask[0, :, :] = mask[-1, :, :] = True
    mask[:, 0, :] = mask[:, -1, :] = True
    mask[:, :, 0] = mask[:, :, -1] = True
    boundary = jnp.asarray(mask)[..., None]
    value_and_grad = jax.jit(jax.value_and_grad(energy, argnums=0))
    history = np.empty(steps + 1)
    energy_now, update = value_and_grad(current, dx, 1.0, 1.0, mu)
    history[0] = float(energy_now)
    min_pre_norm = math.inf
    for step in range(steps):
        if deadline is not None and time.perf_counter() > deadline:
            raise TimeoutError(
                "What: production stage exceeded the wall-clock limit.\n"
                "Why: project guideline G-003 caps every simulation run at 900 s (15 min).\n"
                "Fix: reduce N or steps, or increase max_wall_seconds only for offline runs."
            )
        update = jnp.where(boundary, 0.0, update)
        pre = current - dt * update
        norm = jnp.linalg.norm(pre, axis=-1, keepdims=True)
        min_pre_norm = min(min_pre_norm, float(jnp.min(norm)))
        current = pre / norm
        energy_now, update = value_and_grad(current, dx, 1.0, 1.0, mu)
        history[step + 1] = float(energy_now)
    terms = energy_terms(current, dx, mu)
    payload = {key: float(value) for key, value in terms.items()}
    payload["force_rms"] = float(jnp.sqrt(jnp.mean(update * update)))
    payload["min_pre_norm"] = float(min_pre_norm)
    payload["monotone"] = bool(np.all(np.diff(history) <= 1e-8))
    payload["energy_drift"] = float(history[-1] - history[0])
    payload["history"] = history
    return np.asarray(current, dtype=float), payload


def run_production(
    n: int = 64,
    length: float = 10.0,
    mu: float = 20.0,
    steps: int = 3600,
    dt: float = 5.0e-4,
    seed: int = 20261026,
    perturbation: float = 0.0,
    upsample_factor: int = 2,
    chunk: int = 600,
    max_wall_seconds: float = MAX_WALL_SECONDS,
    initial_field: np.ndarray | None = None,
    return_field: bool = False,
) -> dict:
    """Run one deterministic production scan and apply the acceptance criteria.

    ``initial_field`` resumes from a saved field (used by the checkpointed
    N=96 extension); it cannot be combined with a perturbation.  ``return_field``
    adds the final field to the payload for the caller to save; it is omitted by
    default so the payload stays JSON-serializable.
    """
    if steps < 1 or chunk < 1:
        raise ValueError("steps and chunk must be positive")
    if max_wall_seconds <= 0.0:
        raise ValueError("max_wall_seconds must be positive")
    t0 = time.perf_counter()
    deadline = t0 + max_wall_seconds
    if initial_field is not None:
        if perturbation > 0.0:
            raise ValueError("initial_field cannot be combined with perturbation")
        field = np.asarray(initial_field, dtype=float)
        expected = (n, n, n, 3)
        if field.shape != expected:
            raise ValueError(
                f"initial_field shape must be {expected}, got {field.shape}"
            )
        field = field / np.linalg.norm(field, axis=-1, keepdims=True)
        _, dx = compactified_field(n, length)
    else:
        field, dx = compactified_field(n, length)
        if perturbation > 0.0:
            rng = np.random.default_rng(seed)
            field = field + perturbation * rng.normal(size=field.shape)
            field = field / np.linalg.norm(field, axis=-1, keepdims=True)
    rows = []
    min_pre_norm = math.inf
    history_parts = [
        np.array([float(energy_terms(jnp.asarray(field), dx, mu)["E"])])
    ]
    for start in range(0, steps, chunk):
        count = min(chunk, steps - start)
        field, stage = run_stage(field, dx, mu, count, dt, deadline=deadline)
        metrics = field_metrics(field, dx, mu, upsample_factor=1)
        metrics.update(
            {
                "step": start + count,
                "chunk_steps": count,
                "min_pre_norm": stage["min_pre_norm"],
                "monotone": stage["monotone"],
                "chunk_energy_drift": stage["energy_drift"],
            }
        )
        rows.append(metrics)
        min_pre_norm = min(min_pre_norm, stage["min_pre_norm"])
        history_parts.append(stage["history"][1:])
    history = np.concatenate(history_parts)
    final = field_metrics(field, dx, mu, upsample_factor=upsample_factor)
    elapsed_seconds = float(time.perf_counter() - t0)
    if elapsed_seconds > max_wall_seconds:
        raise TimeoutError(
            "What: production scan exceeded the wall-clock limit.\n"
            "Why: project guideline G-003 caps every simulation run at 900 s (15 min).\n"
            "Fix: reduce N or steps, or increase max_wall_seconds only for offline runs."
        )
    final["step"] = rows[-1]["step"]
    final["min_pre_norm"] = min_pre_norm
    last_drift = abs(rows[-1]["chunk_energy_drift"]) / max(
        1.0, abs(rows[-1]["E"])
    )
    topology_preserved = min_pre_norm > PRE_NORM_TOL
    h_ok = (
        abs(final["H"] - 1.0) <= H_TOL
        and abs(final["H"] - final["H_upsampled"]) <= H_TOL
    )
    z3_ok = final["Z3"] >= Z3_MIN
    converged = final["force_rms"] <= FORCE_TOL and last_drift <= DRIFT_TOL
    resolved = final["max_bond"] <= BOND_TOL
    coexistence = bool(h_ok and z3_ok)
    verified = bool(coexistence and converged and resolved and topology_preserved)
    if verified:
        status = "VERIFIED (numeric)"
    else:
        reasons = []
        if not h_ok:
            reasons.append("H estimator not converged")
        if not z3_ok:
            reasons.append("Z3 below threshold")
        if not converged:
            reasons.append("not converged")
        if not resolved:
            reasons.append("field under-resolved")
        if not topology_preserved:
            reasons.append("pre-normalization norm too small")
        status = "UNVERIFIED (" + "; ".join(reasons) + ")"
    payload = {
        "n": n,
        "length": length,
        "mu": mu,
        "steps": steps,
        "dt": dt,
        "seed": seed,
        "perturbation": perturbation,
        "dx": dx,
        "max_wall_seconds": max_wall_seconds,
        "rows": rows,
        "final": final,
        "history": history.tolist(),
        "min_pre_norm": min_pre_norm,
        "criteria": {
            "H_TOL": H_TOL,
            "Z3_MIN": Z3_MIN,
            "FORCE_TOL": FORCE_TOL,
            "DRIFT_TOL": DRIFT_TOL,
            "BOND_TOL": BOND_TOL,
            "PRE_NORM_TOL": PRE_NORM_TOL,
            "MAX_WALL_SECONDS": MAX_WALL_SECONDS,
        },
        "verdict": {
            "coexistence_H_and_Z3": coexistence,
            "H_ok": bool(h_ok),
            "Z3_ok": bool(z3_ok),
            "converged": bool(converged),
            "resolved": bool(resolved),
            "topology_preserved": bool(topology_preserved),
            "production_ready": verified,
            "claim_15_status": status,
            "note": (
                "A failed scan cannot prove that no 3D simulation can achieve "
                "coexistence. The Hopf charge is conserved by the normalized "
                "flow when the pre-normalization norm stays positive and the "
                "boundary is fixed; a native estimator below 1 at grid scale is "
                "an estimator-resolution issue, not a topological transition."
            ),
        },
    }
    if return_field:
        payload["field"] = np.asarray(field, dtype=float)
    return payload
