import json, math, subprocess, sys
from pathlib import Path

binary = str(Path('target/x86_64-pc-windows-gnu/debug/research-engine.exe').resolve())
sys.path.insert(0, str(Path('..').resolve()))
import numpy as np
from domains.fluid_universe.theory.circulant import (
    circulant_matrix, dft_vectors, eigenvalues, extract_ac_delta, fit_masses,
    koide_tau_prediction, q_from_ac, q_masses, q_physical_from_roots, q_signed,
)


def run(*args):
    p = subprocess.run([binary, '--json', 'fluid-circulant', *map(str, args)],
                       capture_output=True, text=True, encoding='utf-8', timeout=180)
    if p.returncode != 0:
        raise RuntimeError(f'{args}: {p.stderr[:600]}')
    return json.loads(p.stdout)


def complex_json(matrix):
    return [[[float(np.real(v)), float(np.imag(v))] for v in row] for row in matrix]


def close(a, b):
    if isinstance(a, dict):
        return set(a) == set(b) and all(close(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(close(x, y) for x, y in zip(a, b))
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(float(a), float(b), rel_tol=1e-8, abs_tol=1e-8)
    return a == b


def check(label, rust, py):
    ok = close(rust, py)
    print(f'{label} equal:', ok)
    if not ok:
        print('  rust:', str(rust)[:500])
        print('  py:  ', str(py)[:500])


a, c, delta = 1.2, 0.35, 0.4
check('matrix', run('matrix', '--a', a, '--c', c, f'--delta={delta}'),
      complex_json(circulant_matrix(a, c, delta)))
check('eigenvalues', run('eigenvalues', '--a', a, '--c', c, f'--delta={delta}'),
      eigenvalues(a, c, delta).tolist())
check('dft', run('dft'), complex_json(dft_vectors()))

xs = [1.0, 2.0, 3.0]
check('q-signed', run('q-signed', '--xs', json.dumps(xs)), {'value': q_signed(xs)})
check('q-masses', run('q-masses', '--xs', json.dumps(xs)), {'value': q_masses(xs)})
check('q-physical', run('q-physical', '--xs', json.dumps([-1.0, 2.0, 3.0])),
      {'value': q_physical_from_roots([-1.0, 2.0, 3.0])})
check('q-from-ac', run('q-from-ac', '--a', a, '--c', c), {'value': q_from_ac(a, c)})

pa, pc, pdelta = extract_ac_delta(xs)
check('extract', run('extract', '--xs', json.dumps(xs)), {'a': pa, 'c': pc, 'delta': pdelta})

masses = [0.511, 105.7, 1776.9]
check('fit', run('fit', '--xs', json.dumps(masses)), fit_masses(masses))
check('koide', run('koide', '--me', 0.511, '--mmu', 105.7),
      {'value': koide_tau_prediction(0.511, 105.7)})
