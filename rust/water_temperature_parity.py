import json, math, subprocess, sys
from pathlib import Path

binary = str(Path('target/x86_64-pc-windows-gnu/debug/research-engine.exe').resolve())
sys.path.insert(0, str(Path('..').resolve()))
from domains.fluid_universe.theory import water_temperature as wt


def run(*args):
    p = subprocess.run([binary, '--json', 'water-temperature', *map(str, args)],
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
        return math.isclose(float(a), float(b), rel_tol=1e-3, abs_tol=1e-12)
    return a == b


def check(label, rust, py):
    ok = close(rust, py)
    print(f'{label} equal:', ok)
    if not ok:
        print('  rust:', str(rust)[:800])
        print('  py:  ', str(py)[:800])


for temp in (0.0, 25.0, 45.0, 100.0):
    check(f'dielectric {temp}', run('dielectric', temp), {'value': wt.water_dielectric_constant(temp)})
    check(f'tension {temp}', run('tension', temp), {'value': wt.water_surface_tension(temp)})
for temp in (0.0, 25.0, 45.0):
    check(f'cavity {temp}', run('cavity', temp), wt.born_cavity_at_temperature(temp))
check('scales', run('scales'), wt.temperature_scales())
