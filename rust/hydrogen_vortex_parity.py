import json, math, subprocess, sys
from pathlib import Path

binary = str(Path('target/x86_64-pc-windows-gnu/debug/research-engine.exe').resolve())
sys.path.insert(0, str(Path('..').resolve()))
import numpy as np
from domains.fluid_universe.theory import hydrogen_vortex as hv


def run(*args):
    p = subprocess.run([binary, '--json', 'hydrogen-vortex', *map(str, args)],
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
        return math.isclose(float(a), float(b), rel_tol=1e-12, abs_tol=1e-13)
    return a == b


def check(label, rust, py):
    ok = close(rust, py)
    print(f'{label} equal:', ok)
    if not ok:
        print('  rust:', str(rust)[:600])
        print('  py:  ', str(py)[:600])


xs = [0.0, 1.0, 2.0, 4.0, 8.0]
check('radial', run('radial', '--xs', json.dumps(xs)), hv.radial_2p(np.asarray(xs), 1.0).tolist())
check('probability', run('probability', '--xs', json.dumps(xs)),
      hv.radial_probability(np.asarray(xs), 1.0).tolist())
check('most probable', run('most-probable'), {'value': hv.most_probable_radius(1.0)})
check('azimuthal', run('azimuthal', 2.0, 1.5707963267948966, 1),
      {'value': hv.azimuthal_velocity(2.0, math.pi / 2.0, 1)})
check('circulation', run('circulation', 1), {'value': hv.circulation(1)})
check('loop', run('loop', 2.0, 1.5707963267948966, 1),
      {'value': hv.loop_circulation(2.0, math.pi / 2.0, 1)})
check('angular momentum', run('angular-momentum', 1), {'value': hv.angular_momentum(1)})
r = np.linspace(0.0, 80.0, 160001)
check('norm', run('norm'), {'value': float(np.trapezoid(hv.radial_probability(r, 1.0), r))})
