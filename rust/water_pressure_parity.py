import json, math, subprocess, sys
from pathlib import Path

binary = str(Path('target/x86_64-pc-windows-gnu/debug/research-engine.exe').resolve())
sys.path.insert(0, str(Path('..').resolve()))
from domains.fluid_universe.theory import water_pressure as wp
from domains.fluid_universe.theory.water_electron import capillary_cavity_radius
from domains.fluid_universe.theory.water_well import born_depth_ev


def run(*args):
    p = subprocess.run([binary, '--json', 'water-pressure', *map(str, args)],
                       capture_output=True, text=True, encoding='utf-8', timeout=300)
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
        # Golden-section vs scipy bounded search: scipy's xatol=1e-14 m is
        # coarse next to a ~4e-10 m radius, so derived small eigenvalues can
        # differ by ~1e-4 relative while both find the same energy minimum.
        return math.isclose(float(a), float(b), rel_tol=1e-3, abs_tol=1e-12)
    return a == b


def check(label, rust, py):
    ok = close(rust, py)
    print(f'{label} equal:', ok)
    if not ok:
        print('  rust:', str(rust)[:800])
        print('  py:  ', str(py)[:800])


radius = capillary_cavity_radius()
born = born_depth_ev(radius)
check('surface', run('surface', radius), {'value': wp.surface_energy_ev(radius)})
check('total bound', run('total', radius, born), {'value': wp.total_energy_ev(radius, born)})
check('total unbound', run('total', 1e-10, 0.5), {'value': wp.total_energy_ev(1e-10, 0.5)})
for depth in (born, 4.0, 5.5):
    check(f'equilibrium {depth}', run('equilibrium', depth), wp.equilibrium_radius(depth))
check('vde matched', run('vde-matched', '--binding-ev', 3.27), wp.vde_matched_depth(3.27))
check('scales', run('scales'), wp.pressure_scales())
