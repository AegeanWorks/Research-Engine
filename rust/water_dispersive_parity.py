import json, math, subprocess, sys
from pathlib import Path

binary = str(Path('target/x86_64-pc-windows-gnu/debug/research-engine.exe').resolve())
sys.path.insert(0, str(Path('..').resolve()))
from domains.fluid_universe.theory import water_dispersive as wd


def run(*args):
    p = subprocess.run([binary, '--json', 'water-dispersive', *map(str, args)],
                       capture_output=True, text=True, encoding='utf-8', timeout=300)
    if p.returncode != 0:
        raise RuntimeError(f'{args}: {p.stderr[:700]}')
    return json.loads(p.stdout)


def close(a, b):
    if isinstance(a, dict):
        return set(a) == set(b) and all(close(a[k], b[k]) for k in a)
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(float(a), float(b), rel_tol=1e-10, abs_tol=1e-13)
    return a == b


def check(label, rust, py):
    ok = close(rust, py)
    print(f'{label} equal:', ok)
    if not ok:
        print('  rust:', str(rust)[:600])
        print('  py:  ', str(py)[:600])


for k in (0.0, 10.0, 500.0, 1e4):
    check(f'dispersion {k}', run('dispersion', k), {'value': wd.dispersion(k, 0.1)})
    check(f'group {k}', run('group', k), {'value': wd.group_velocity(k, 0.1)})

for omega in (2.0, 10.0, 50.0):
    check(f'wavenumber {omega}', run('wavenumber', omega), {'value': wd.horizon_wavenumber(omega, 0.1)})
    check(f'horizon {omega}', run('horizon', omega, '--flow-rate', 1e-3),
          wd.dispersive_horizon(omega, 1e-3, 0.1))

check('capillary', run('capillary'), {'value': wd.capillary_frequency(0.1)})
