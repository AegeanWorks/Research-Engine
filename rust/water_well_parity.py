import json, math, subprocess, sys
from pathlib import Path

binary = str(Path('target/x86_64-pc-windows-gnu/debug/research-engine.exe').resolve())
sys.path.insert(0, str(Path('..').resolve()))
from domains.fluid_universe.theory import water_well as ww
from domains.fluid_universe.theory.water_electron import capillary_cavity_radius


def run(*args):
    p = subprocess.run([binary, '--json', 'water-well', *map(str, args)],
                       capture_output=True, text=True, encoding='utf-8', timeout=180)
    if p.returncode != 0:
        raise RuntimeError(f'{args}: {p.stderr[:700]}')
    return json.loads(p.stdout)


def close(a, b):
    if isinstance(a, dict):
        return set(a) == set(b) and all(close(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(close(x, y) for x, y in zip(a, b))
    if a is None or b is None:
        return a is b
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


radius = capillary_cavity_radius()
for r in (radius, 3.2e-10, 4.703128884e-10):
    check(f'born {r}', run('born', r), {'value': ww.born_depth_ev(r)})
    check(f'threshold {r}', run('threshold', r), {'value': ww.threshold_depth_ev(r)})
    check(f'infinite {r}', run('infinite', r), {'value': ww.infinite_well_transition_ev(r)})

for r, depth in [(radius, ww.born_depth_ev(radius)), (radius, 10.0), (3.2e-10, 4.0)]:
    check(f'roots {r} {depth}', run('roots', r, depth), ww.well_roots(r, depth))

for r in (radius, 3.2e-10):
    check(f'required {r}', run('required', r),
          {'value': ww.required_depth_ev(r, 1.7)})

check('minimum', run('minimum'), ww.minimum_required_depth(1.7))
check('scales', run('scales'), ww.well_scales())
