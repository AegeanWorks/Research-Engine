import json, math, subprocess, sys
from pathlib import Path

binary = str(Path('target/x86_64-pc-windows-gnu/debug/research-engine.exe').resolve())
sys.path.insert(0, str(Path('..').resolve()))
from domains.fluid_universe.theory import water_vde as wv


def run(*args):
    p = subprocess.run([binary, '--json', 'water-vde', *map(str, args)],
                       capture_output=True, text=True, encoding='utf-8', timeout=300)
    if p.returncode != 0:
        raise RuntimeError(f'{args}: {p.stderr[:700]}')
    return json.loads(p.stdout)


def close(a, b):
    if isinstance(a, dict):
        return set(a) == set(b) and all(close(a[k], b[k]) for k in a)
    if a is None or b is None:
        return a is b
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(float(a), float(b), rel_tol=1e-10, abs_tol=1e-13)
    return a == b


def check(label, rust, py):
    ok = close(rust, py)
    print(f'{label} equal:', ok)
    if not ok:
        print('  rust:', str(rust)[:700])
        print('  py:  ', str(py)[:700])


for radius in (3.2e-10, 3.732e-10, 4.0e-10):
    check(f'depth {radius}', run('depth', radius, 3.27),
          {'value': wv.depth_for_binding(radius, 3.27)})

for binding, gap in [(3.27, 1.7), (3.17, 1.7), (3.37, 1.7)]:
    check(f'cavity {binding}', run('cavity', f'--binding-ev={binding}', f'--gap-ev={gap}'),
          wv.cavity_for_observables(binding, gap))

check('scales', run('scales'), wv.vde_scales())
