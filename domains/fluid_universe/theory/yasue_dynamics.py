"""Yasui dynamical discriminator: collapse vs G-M oscillation (claim 52, ADR-044).

Zero free parameters, no full-field claims. Spelling note: the
literature name is Yasue (K. Yasue 1981); spans 49-51 wrote "Yasui"
for the same referent. New code uses Yasue; old modules are untouched.

For the time-dependent Gaussian trial the Yasui action gives

    sddot = -(nu^2/s^3) - omega^2*s < 0 for all s > 0,

so a release from rest can never turn around: monotone collapse to
any recording floor, with floor-hit before pi/(2*omega) by the
harmonic comparison (L2). The identical Verlet machinery run on the
G-M acceleration from the same releases oscillates with period pi
(span-51 construction). Shared integrator + opposite outcomes = the
controlled experiment: the SIGN of the osmotic term is the discriminator.

The comparison uses the mild threshold sigma = 0.5 (both methods
accurate there): quadrature of the energy integral vs Verlet first
passage. Floor-hit times are recorded (floors 0.05 and 0.02), never
gated on absolute value - only bounded above (collapse must happen).
"""

from __future__ import annotations

import math

BASE = {"omega": 1.0, "hbar": 1.0, "mass": 1.0}
RELEASE_FACTORS = (1.01, 0.99, 1.5)
FLOORS = (0.05, 0.02)
DT = 0.001
T_END = 2.0 * math.pi
MILD_SIGMA = 0.5


def yasue_acceleration(s: float, omega: float, hbar: float, mass: float) -> float:
    from domains.fluid_universe.theory.variational_dynamics import diffusivity

    if s <= 0.0 or omega <= 0.0:
        raise ValueError("s and omega must be positive")
    nu = diffusivity(hbar, mass)
    return -nu * nu / (s * s * s) - omega * omega * s


def yasue_release(
    factor: float,
    omega: float = 1.0,
    hbar: float = 1.0,
    mass: float = 1.0,
    floor: float = 0.05,
    dt: float = DT,
    t_end: float = T_END,
) -> dict:
    """Velocity-Verlet release from rest; stops at the floor."""
    from domains.fluid_universe.theory.gaussian_fluid import quantum_width

    width = quantum_width(omega, hbar, mass)
    s = width * factor
    v = 0.0
    t = 0.0
    previous = s - width
    upward = 0
    crossings = []
    mild_time = 0.0 if s <= MILD_SIGMA else None
    monotone_diffs = []
    prev_s = s
    hit_time = None
    while t < t_end and s > floor:
        acc = yasue_acceleration(s, omega, hbar, mass)
        v += 0.5 * dt * acc
        s_new = s + dt * v
        acc_new = yasue_acceleration(s_new, omega, hbar, mass) if s_new > 0.0 else acc
        v += 0.5 * dt * acc_new
        t += dt
        monotone_diffs.append(s_new - s)
        if mild_time is None and s > MILD_SIGMA >= s_new:
            frac = (s - MILD_SIGMA) / (s - s_new) if s != s_new else 0.0
            mild_time = t - dt + frac * dt
        current = s_new - width * factor
        if previous < 0.0 <= current and t > dt:
            upward += 1
            crossings.append(t)
        previous = current
        s = s_new
        if s <= floor:
            hit_time = t
            break
    return {
        "factor": factor,
        "monotone": bool(all(d < 0.0 for d in monotone_diffs)),
        "floor_hit_time": hit_time,
        "upward_crossings": upward,
        "crossing_times": crossings,
        "mild_crossing_time": mild_time,
        "min_sigma": float(s),
    }


def quadrature_mild_crossing(
    factor: float, omega: float = 1.0, hbar: float = 1.0, mass: float = 1.0
) -> float:
    """Energy-integral time from release to sigma = 0.5.

    Substitutes u = sqrt(s0 - s) to remove the turning-point
    1/sqrt singularity; the transformed integrand is smooth, so the
    plain trapezoid rule is spectrally accurate here.
    """
    from domains.fluid_universe.theory.gaussian_fluid import quantum_width
    from domains.fluid_universe.theory.variational_dynamics import diffusivity

    width = quantum_width(omega, hbar, mass)
    s0 = width * factor
    nu = diffusivity(hbar, mass)
    if s0 <= MILD_SIGMA:
        return 0.0
    energy = (
        -mass * nu * nu / (2.0 * s0 * s0)
        + 0.5 * mass * omega * omega * s0 * s0
    )

    def speed_squared(s: float) -> float:
        potential = (
            -mass * nu * nu / (2.0 * s * s)
            + 0.5 * mass * omega * omega * s * s
        )
        return max(energy - potential, 0.0) * 2.0 / mass

    umax = math.sqrt(s0 - MILD_SIGMA)
    n = 20001
    total = 0.0
    prev_u = 0.0
    # Limit of 2u/v(s0-u^2) as u -> 0: with V_Y' > 0, v ~= u*sqrt(2 V_Y'/m),
    # so the integrand tends to sqrt(2 m / V_Y'(s0)). Yasui sign (+ +).
    slope_y = mass * nu * nu / (s0 * s0 * s0) + mass * omega * omega * s0
    prev_f = math.sqrt(2.0 * mass / slope_y)
    for i in range(1, n):
        u = umax * i / (n - 1)
        s = s0 - u * u
        v2 = speed_squared(s)
        cur = 2.0 * u / math.sqrt(v2) if v2 > 0.0 else 0.0
        total += 0.5 * (prev_f + cur) * (u - prev_u)
        prev_u, prev_f = u, cur
    return total


def yasue_scales() -> dict:
    """Collect the discriminator correspondence bundle (no verdict)."""
    from domains.fluid_universe.theory.variational_dynamics import release_period as gm_release

    releases = [yasue_release(f) for f in RELEASE_FACTORS]
    twins = [dict(gm_release(f), factor=f) for f in RELEASE_FACTORS]
    mild_quad = [quadrature_mild_crossing(f) for f in RELEASE_FACTORS]
    floor02 = [yasue_release(f, floor=0.02) for f in RELEASE_FACTORS]
    omega2 = 2.0
    scaling_release = yasue_release(1.01, omega=omega2)
    scaling_twin = dict(gm_release(1.01, omega=omega2), factor=1.01)
    scaling_quad = quadrature_mild_crossing(1.01, omega=omega2)
    return {
        "base": dict(BASE),
        "factors": list(RELEASE_FACTORS),
        "floors": list(FLOORS),
        "dt": DT,
        "t_end": T_END,
        "releases": releases,
        "twins": twins,
        "mild_quadrature": mild_quad,
        "floor_sensitivity": floor02,
        "scaling": {
            "omega": omega2,
            "release": scaling_release,
            "twin": scaling_twin,
            "mild_quadrature": scaling_quad,
        },
    }
