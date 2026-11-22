import json, math, subprocess, sys
from pathlib import Path

binary = str(Path('target/x86_64-pc-windows-gnu/debug/research-engine.exe').resolve())
sys.path.insert(0, str(Path('..').resolve()))
import numpy as np
from domains.fluid_universe.theory.vortex_cascade import (
    geometric_spectrum, power_law_spectrum, run_hypotheses, solve_power_for_koide,
)
from domains.fluid_universe.theory.vortex_particles import koide_q


def run(*args):
    p = subprocess.run([binary, '--json', 'vortex-cascade', *map(str, args)],
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
        return math.isclose(float(a), float(b), rel_tol=1e-11, abs_tol=1e-13)
    return a == b


def check(label, rust, py):
    ok = close(rust, py)
    print(f'{label} equal:', ok)
    if not ok:
        print('  rust:', str(rust)[:700])
        print('  py:  ', str(py)[:700])


masses = [0.511, 105.7, 1776.9]
check('koide', run('koide', '--xs', json.dumps(masses)), {'value': koide_q(np.asarray(masses))})
for ratio in (2.0, 10.0, 206.0):
    check(f'geometric {ratio}', run('geometric', ratio), geometric_spectrum(ratio).tolist())
for exponent in (0.5, 2.0, 4.5):
    check(f'power {exponent}', run('power', exponent), power_law_spectrum(exponent).tolist())
check('solve', run('solve'), {'value': solve_power_for_koide()})
check('hypotheses', run('hypotheses', '--masses', json.dumps(masses)), run_hypotheses(tuple(masses)))
