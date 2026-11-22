import json, math, subprocess, sys
from pathlib import Path

binary = str(Path('target/x86_64-pc-windows-gnu/debug/research-engine.exe').resolve())
sys.path.insert(0, str(Path('..').resolve()))
from domains.fluid_universe.theory import water_electron as we


def run(*args):
    p = subprocess.run([binary, '--json', 'water-electron', *map(str, args)],
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


for epsilon in (we.EPSILON_WATER, 4.0, 80.0):
    check(f'screened radius {epsilon}', run('screened-radius', f'--epsilon-r={epsilon}'),
          {'value': we.screened_bohr_radius(epsilon)})
    check(f'screened energy {epsilon}', run('screened-energy', f'--epsilon-r={epsilon}'),
          {'value': we.screened_energy_ev(epsilon)})

check('cavity radius', run('cavity-radius'), {'value': we.capillary_cavity_radius()})
check('cavity energy', run('cavity-energy'), {'value': we.capillary_cavity_energy_ev()})
for radius in (we.capillary_cavity_radius(), 2.5e-10):
    check(f'well gap {radius}', run('well-gap', radius), {'value': we.infinite_well_gap_ev(radius)})
for energy in (1.7, 0.5):
    check(f'radius for gap {energy}', run('radius-for-gap', energy), {'value': we.well_radius_for_gap(energy)})
check('scales', run('scales'), we.hydrated_scales())
