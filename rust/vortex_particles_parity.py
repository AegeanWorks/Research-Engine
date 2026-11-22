import json, math, subprocess, sys
from pathlib import Path

binary = str(Path('target/x86_64-pc-windows-gnu/debug/research-engine.exe').resolve())
sys.path.insert(0, str(Path('..').resolve()))
from domains.fluid_universe.theory.vortex_particles import (
    biot_savart_energy, koide_q, knot_length, mass_hypothesis, torus_knot,
)


def run(*args):
    p = subprocess.run([binary, '--json', 'vortex-particles', *map(str, args)],
                       capture_output=True, text=True, encoding='utf-8', timeout=300)
    if p.returncode != 0:
        raise RuntimeError(f'{args}: {p.stderr[:700]}')
    return json.loads(p.stdout)


def close(a, b):
    if isinstance(a, dict):
        return set(a) == set(b) and all(close(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(close(x, y) for x, y in zip(a, b))
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(float(a), float(b), rel_tol=1e-9, abs_tol=1e-11)
    return a == b


def check(label, rust, py):
    ok = close(rust, py)
    print(f'{label} equal:', ok)
    if not ok:
        print('  rust:', str(rust)[:900])
        print('  py:  ', str(py)[:900])


masses = [0.511, 105.7, 1776.9]
check('koide', run('koide', '--xs', json.dumps(masses)), {'value': koide_q(masses)})

for n, samples in [(3, 64), (5, 128)]:
    points, _ = torus_knot(n, samples=samples)
    check(f'length {n}', run('length', n, f'--samples={samples}'), {'value': knot_length(points)})
    check(f'energy {n}', run('energy', n, '--core', 0.1, f'--samples={samples}'),
          {'value': biot_savart_energy(points, 0.1)})

check('hypothesis', run('hypothesis', '--masses', json.dumps(masses), '--core', 0.1),
      mass_hypothesis(tuple(masses)))
