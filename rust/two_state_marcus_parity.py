import json, math, subprocess, sys
from pathlib import Path

binary = str(Path('target/x86_64-pc-windows-gnu/debug/research-engine.exe').resolve())
sys.path.insert(0, str(Path('..').resolve()))
from domains.fluid_universe.theory import two_state_marcus as ts
from domains.fluid_universe.theory.water_marcus import marcus_width_ev, KB_EV
from domains.fluid_universe.theory.water_lineshape import LAMBDA_EV, SHAPE_RATIO_TOL


def run(*args):
    p = subprocess.run([binary, '--json', 'two-state-marcus', *map(str, args)],
                       capture_output=True, text=True, encoding='utf-8', timeout=180)
    if p.returncode != 0:
        raise RuntimeError(f'{args}: {p.stderr[:600]}')
    return json.loads(p.stdout)


def close(a, b):
    if isinstance(a, dict):
        return set(a) == set(b) and all(close(a[k], b[k]) for k in a)
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(float(a), float(b), rel_tol=1e-13, abs_tol=1e-15)
    return a == b


def check(label, rust, py):
    ok = close(rust, py)
    print(f'{label} equal:', ok)
    if not ok:
        print('  rust:', str(rust)[:600])
        print('  py:  ', str(py)[:600])


for lambda_ev, temp in [(LAMBDA_EV, 300.0), (2.0, 298.0), (1.0, 200.0)]:
    check(f'width {lambda_ev} {temp}',
          run('width', f'--lambda-ev={lambda_ev}', f'--temperature-k={temp}'),
          {'value': marcus_width_ev(lambda_ev, temp)})

for temp in (300.0, 250.0):
    check(f'shared {temp}', run('shared', f'--temperature-k={temp}'),
          ts.shared_lambda_widths(temp))
    check(f'scales {temp}', run('scales', f'--temperature-k={temp}'),
          ts.two_state_scales(temp))

check('ratio', run('ratio'), ts.component_ratio())
check('thresholds', run('thresholds'), ts.kill_thresholds())
