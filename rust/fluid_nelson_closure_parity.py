import json, math, subprocess, sys
from pathlib import Path

binary = str(Path('target/x86_64-pc-windows-gnu/debug/research-engine.exe').resolve())
sys.path.insert(0, str(Path('..').resolve()))
import numpy as np
from domains.fluid_universe.theory import nelson_closure as nc


def run(*args):
    p = subprocess.run([binary, '--json', 'fluid-nelson-closure', *map(str, args)],
                       capture_output=True, text=True, encoding='utf-8', timeout=300)
    if p.returncode != 0:
        raise RuntimeError(f'{args}: {p.stderr[:600]}')
    return json.loads(p.stdout)


def close(a, b, key=None):
    if isinstance(a, dict):
        return set(a) == set(b) and all(close(a[k], b[k], k) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(close(x, y, key) for x, y in zip(a, b))
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        # error_slope is a log-log fit over ~1e-16 error floors: ULP-level
        # differences in the floor are amplified, so it is compared more loosely.
        rel = 1e-3 if key == "error_slope" else 1e-8
        return math.isclose(float(a), float(b), rel_tol=rel, abs_tol=1e-11)
    return a == b


def check(label, rust, py):
    ok = close(rust, py)
    print(f'{label} equal:', ok)
    if not ok:
        print('  rust:', str(rust)[:600])
        print('  py:  ', str(py)[:600])


x = np.asarray([-2.0, -1.0, 0.0, 1.0, 2.0])
rho = nc.trial_gaussian(x, 0.5)
check('osmotic', run('osmotic', '--xs', json.dumps(rho.tolist()), '--dx', 1.0),
      nc.osmotic_velocity(rho, 1.0).tolist())
check('fp-residual', run('fp-residual', '--xs', json.dumps(rho.tolist()), '--dx', 1.0),
      nc.fp_residual(rho, 1.0).tolist())

check('residual-scaling', run('residual-scaling'), nc.residual_scaling())
check('sigma-map', run('sigma-map'), nc.frozen_drift_sigma_map())
check('instances', run('instances'), nc.ou_free_packet_instances())
check('scales', run('scales'), nc.closure_scales())
