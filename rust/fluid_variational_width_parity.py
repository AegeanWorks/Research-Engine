import json, math, subprocess, sys
from pathlib import Path

binary = str(Path('target/x86_64-pc-windows-gnu/debug/research-engine.exe').resolve())
sys.path.insert(0, str(Path('..').resolve()))
import numpy as np
from domains.fluid_universe.theory import variational_width as vw


def run(*args):
    p = subprocess.run([binary, '--json', 'fluid-variational-width', *map(str, args)],
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
        return math.isclose(float(a), float(b), rel_tol=1e-11, abs_tol=1e-11)
    return a == b


def check(label, rust, py):
    ok = close(rust, py)
    print(f'{label} equal:', ok)
    if not ok:
        print('  rust:', str(rust)[:600])
        print('  py:  ', str(py)[:600])


check('diffusivity', run('diffusivity'), {'value': vw.diffusivity(1.0, 1.0)})
check('action-gm', run('action-gm', 0.5), {'value': vw.action_gm(0.5, 1.0, 1.0, 1.0)})
check('action-yasui', run('action-yasui', 0.5), {'value': vw.action_yasui(0.5, 1.0, 1.0, 1.0)})
check('d-gm', run('d-gm', 0.5), {'value': vw.d_action_gm(0.5, 1.0, 1.0, 1.0)})
check('d-yasui', run('d-yasui', 0.5), {'value': vw.d_action_yasui(0.5, 1.0, 1.0, 1.0)})
check('d2s2', run('d2s2', 0.5), {'value': vw.d2_action_gm_s2(0.5, 1.0, 1.0, 1.0)})
check('d2-sigma', run('d2-sigma', 0.7071067811865476),
      {'value': vw.d2_action_gm_sigma(0.7071067811865476, 1.0, 1.0, 1.0)})
check('extremum', run('extremum'), {'value': vw.extremum_s2(1.0, 1.0, 1.0)})
check('newton', run('newton', 0.6), {'value': vw.newton_refine(0.6, 1.0, 1.0, 1.0)})

grid = np.asarray(vw.GRID_S2)
check('grid-max', run('grid-max'), vw.grid_maximum(grid, 1.0, 1.0, 1.0))
check('yasui-monotone', run('yasui-monotone'), vw.yasui_monotone(grid, 1.0, 1.0, 1.0))
check('ermakov', run('ermakov'), vw.ermakov_cross_check())
check('scales', run('scales'), vw.selection_scales())
