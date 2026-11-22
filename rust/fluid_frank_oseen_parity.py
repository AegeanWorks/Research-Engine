import math, subprocess, sys
from pathlib import Path

binary = str(Path('target/x86_64-pc-windows-gnu/debug/research-engine.exe').resolve())
sys.path.insert(0, str(Path('..').resolve()))
from domains.fluid_universe.theory.frank_oseen import (
    anisotropy, dispersion, elastic_matrix, equal_constant_dispersion, modes,
)


def run(*args):
    p = subprocess.run([binary, '--json', 'fluid-frank-oseen', *map(str, args)],
                       capture_output=True, text=True, encoding='utf-8', timeout=180)
    if p.returncode != 0:
        raise RuntimeError(f'{args}: {p.stderr[:600]}')
    import json
    return json.loads(p.stdout)


def close(a, b):
    if isinstance(a, dict):
        return set(a) == set(b) and all(close(a[k], b[k]) for k in a)
    if isinstance(a, (list, tuple)):
        return len(a) == len(b) and all(close(x, y) for x, y in zip(a, b))
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-12)
    return a == b


def check(label, rust, py):
    ok = close(rust, py)
    print(f'{label} equal:', ok)
    if not ok:
        print('  rust:', str(rust)[:400])
        print('  py:  ', str(py)[:400])


cases = [
    (1.0, 2.0, 3.0, 1.2, 0.8, 1.5, 1.3),
    (0.3, 0.7, 2.1, 0.9, 0.9, 0.9, 2.0),
    (1.0, 1.0, 0.0, 2.0, 0.5, 1.0, 1.0),
]
for kx, ky, kz, k1, k2, k3, rho in cases:
    py_m = elastic_matrix(kx, ky, kz, k1, k2, k3).tolist()
    check('matrix', run('matrix', kx, ky, kz, k1, k2, k3), py_m)
    py_d = [float(x) for x in dispersion(kx, ky, kz, k1, k2, k3, rho)]
    check('dispersion', run('dispersion', kx, ky, kz, k1, k2, k3, '--rho', rho), py_d)

for k, K, rho in [(3.0, 2.0, 1.0), (2.5, 0.4, 2.0), (0.0, 1.0, 1.0)]:
    check('equal', run('equal', k, K, '--rho', rho),
          {'value': equal_constant_dispersion(k, K, rho)})

for direction, k1, k2, k3 in [((1, 2, 2), 1.2, 0.8, 1.5), ((0, 0, 1), 1.0, 1.0, 1.0)]:
    py_a = anisotropy(direction, k1, k2, k3)
    check('anisotropy', run('anisotropy', *direction, k1, k2, k3), py_a)

check('modes', run('modes'), modes())
