import json, math, subprocess, sys
from pathlib import Path

binary = str(Path('target/x86_64-pc-windows-gnu/debug/research-engine.exe').resolve())
sys.path.insert(0, str(Path('..').resolve()))
import numpy as np
from domains.fluid_universe.theory.excited_fluid import (
    excited_density, excited_quantum_pressure_regular, excited_wavefunction,
    phase_gradient_max, phase_slip, scaling_slope,
)


def run(*args):
    p = subprocess.run([binary, '--json', 'excited-fluid', *map(str, args)],
                       capture_output=True, text=True, encoding='utf-8', timeout=180)
    if p.returncode != 0:
        raise RuntimeError(f'{args}: {p.stderr[:600]}')
    return json.loads(p.stdout)


def close(a, b):
    if isinstance(a, dict):
        return set(a) == set(b) and all(close(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(close(x, y) for x, y in zip(a, b))
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(float(a), float(b), rel_tol=1e-11, abs_tol=1e-13)
    return a == b


def check(label, rust, py):
    ok = close(rust, py)
    print(f'{label} equal:', ok)
    if not ok:
        print('  rust:', str(rust)[:600])
        print('  py:  ', str(py)[:600])


xs = [-2.0, -1.0, -0.25, 0.0, 0.25, 1.0, 2.0]
xs_json = json.dumps(xs)
arr = np.asarray(xs)

check('density', run('density', '--xs', xs_json), excited_density(arr, 1.0).tolist())
check('wavefunction', run('wavefunction', '--xs', xs_json), excited_wavefunction(arr, 1.0).tolist())
check('pressure', run('pressure', '--xs', xs_json),
      excited_quantum_pressure_regular(arr, 1.0).tolist())

psi = excited_wavefunction(arr, 1.0)
check('phase slip', run('phase-slip', '--xs', json.dumps(psi.tolist())), {'value': phase_slip(psi)})
check('phase gradient', run('phase-gradient', '--xs', json.dumps(psi.tolist()), '--dx', 0.25),
      {'value': phase_gradient_max(psi, 0.25)})
check('phase gradient positive', run('phase-gradient', '--xs', json.dumps(np.abs(psi).tolist()), '--dx', 0.25),
      {'value': phase_gradient_max(np.abs(psi), 0.25)})

dxs = [0.1, 0.05, 0.025, 0.0125]
maxima = [8.0, 16.1, 32.2, 64.5]
check('scaling slope', run('scaling-slope', '--dxs', json.dumps(dxs), '--maxima', json.dumps(maxima)),
      {'value': scaling_slope(np.asarray(dxs), np.asarray(maxima))})
