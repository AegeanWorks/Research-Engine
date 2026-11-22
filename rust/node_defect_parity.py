import json, math, subprocess, sys
from pathlib import Path

binary = str(Path('target/x86_64-pc-windows-gnu/debug/research-engine.exe').resolve())
sys.path.insert(0, str(Path('..').resolve()))
import numpy as np
from domains.fluid_universe.theory import node_defect as nd


def run(*args):
    p = subprocess.run([binary, '--json', 'node-defect', *map(str, args)],
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
        return math.isclose(float(a), float(b), rel_tol=1e-10, abs_tol=1e-12)
    return a == b


def check(label, rust, py):
    ok = close(rust, py)
    print(f'{label} equal:', ok)
    if not ok:
        print('  rust:', str(rust)[:700])
        print('  py:  ', str(py)[:700])


xs = [-2.0, -1.0, 0.0, 1.0, 2.0]
py_split = nd.branch_split(np.asarray(xs), 1.0)
check('split', run('split', '--xs', json.dumps(xs)),
      {
          'sign': py_split['sign'].tolist(),
          'magnitude': py_split['magnitude'].tolist(),
          'identity_residual': py_split['identity_residual'],
          'node_density': py_split['node_density'],
          'phase_slip': py_split['phase_slip'],
      })
check('pressure', run('pressure', '--xs', json.dumps(xs)),
      nd.branch_regular_pressure_match(np.asarray(xs), 1.0))
check('scaling', run('scaling'), nd.node_scaling())
check('vortex', run('vortex'), nd.vortex_gate())
check('scales', run('scales'), nd.representation_scales())
