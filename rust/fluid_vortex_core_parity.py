import json, math, subprocess, sys
from pathlib import Path

binary = str(Path('target/x86_64-pc-windows-gnu/debug/research-engine.exe').resolve())
sys.path.insert(0, str(Path('..').resolve()))
import numpy as np
from domains.fluid_universe.theory.vortex_core import (
    core_density, core_norm, core_phase, core_q_zero, core_radius,
    core_velocity, fd_q_zero, ho_sigma,
)


def run(*args):
    p = subprocess.run([binary, '--json', 'fluid-vortex-core', *map(str, args)],
                       capture_output=True, text=True, encoding='utf-8', timeout=180)
    if p.returncode != 0:
        raise RuntimeError(f'{args}: {p.stderr[:600]}')
    return json.loads(p.stdout)


def close(a, b):
    if isinstance(a, dict):
        return set(a) == set(b) and all(close(a[k], b[k]) for k in a)
    if isinstance(a, (list, tuple, np.ndarray)):
        aa, bb = list(a), list(b)
        return len(aa) == len(bb) and all(close(x, y) for x, y in zip(aa, bb))
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(float(a), float(b), rel_tol=1e-10, abs_tol=1e-12)
    return a == b


def check(label, rust, py):
    ok = close(rust, py)
    print(f'{label} equal:', ok)
    if not ok:
        print('  rust:', str(rust)[:400])
        print('  py:  ', str(py)[:400])


check('radius', run('radius'), {'value': core_radius()})
for omega, hbar, mass in [(1.0, 1.0, 1.0), (2.0, 0.5, 3.0)]:
    check('sigma', run('sigma', '--omega', omega, '--hbar', hbar, '--mass', mass),
          {'value': ho_sigma(omega, hbar, mass)})

for eps, sigma in [(0.1, 1.0), (0.0, 2.0)]:
    check('norm', run('norm', eps, sigma), {'value': core_norm(eps, sigma)})

xs = [-3.0, -2.0, -1.0, 0.0, 1.0, 2.0, 3.0]
xs_json = json.dumps(xs)
for eps, sigma in [(0.1, 1.0), (0.4, 2.0)]:
    check('density', run('density', eps, sigma, '--xs', xs_json),
          core_density(np.asarray(xs), eps, sigma).tolist())
    check('phase', run('phase', eps, '--xs', xs_json),
          core_phase(np.asarray(xs), eps).tolist())
    check('velocity', run('velocity', eps, '--hbar', 1.0, '--mass', 1.0, '--xs', xs_json),
          core_velocity(np.asarray(xs), eps, 1.0, 1.0).tolist())

for eps, sigma in [(0.1, 1.0), (0.25, 2.0)]:
    check('q-zero', run('q-zero', eps, '--sigma', sigma),
          {'value': core_q_zero(eps, sigma, 1.0, 1.0)})

for eps, n in [(0.1, 64), (0.1, 256), (0.25, 128)]:
    check(f'fd-q n={n}', run('fd-q', eps, n), {'value': fd_q_zero(eps, n)})
