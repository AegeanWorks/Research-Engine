import json, math, subprocess, sys
from pathlib import Path

binary = str(Path('target/x86_64-pc-windows-gnu/debug/research-engine.exe').resolve())
sys.path.insert(0, str(Path('..').resolve()))
import numpy as np
from domains.fluid_universe.theory.hydrogen_radial_nodes import (
    branch_split_20, node_position, norm_20, overlap_10_20, peak_radii_20,
    phase_slip_20, radial_10, radial_20, radial_probability_20,
    representation_scales,
)


def run(*args):
    p = subprocess.run([binary, '--json', 'hydrogen-radial', *map(str, args)],
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
        return math.isclose(float(a), float(b), rel_tol=1e-8, abs_tol=1e-9)
    return a == b


def check(label, rust, py):
    ok = close(rust, py)
    print(f'{label} equal:', ok)
    if not ok:
        print('  rust:', str(rust)[:500])
        print('  py:  ', str(py)[:500])


xs = [0.0, 0.5, 1.0, 2.0, 3.0, 5.0]
xs_json = json.dumps(xs)
r = np.asarray(xs)

check('radial10', run('radial10', '--xs', xs_json), radial_10(r).tolist())
check('radial20', run('radial20', '--xs', xs_json), radial_20(r).tolist())
check('probability', run('probability', '--xs', xs_json), radial_probability_20(r).tolist())
py_branch = branch_split_20(r)
check('branch', run('branch', '--xs', xs_json),
      {'sign': py_branch['sign'].tolist(), 'magnitude': py_branch['magnitude'].tolist(),
       'identity_residual': py_branch['identity_residual']})
check('phase', run('phase', '--xs', xs_json), {'value': phase_slip_20(r)})
check('node', run('node'), {'value': node_position()})
check('overlap', run('overlap'), {'value': overlap_10_20()})
check('norm', run('norm'), {'value': norm_20()})
inner, outer = peak_radii_20()
check('peaks', run('peaks'), {'inner': inner, 'outer': outer})
check('balance', run('balance'), representation_scales()['preserved']['balance_residuals'])
check('circulation', run('circulation', 2.0, math.pi / 2.0, 1),
      {'value': representation_scales()['preserved']['loop_circulation']})
check('scales', run('scales'), representation_scales())
