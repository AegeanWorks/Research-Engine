import json, math, subprocess, sys
from pathlib import Path

binary = str(Path('target/x86_64-pc-windows-gnu/debug/research-engine.exe').resolve())
sys.path.insert(0, str(Path('..').resolve()))
from domains.fluid_universe.theory import water_reorganization as wr
from domains.fluid_universe.theory.water_electron import capillary_cavity_radius


def run(*args):
    p = subprocess.run([binary, '--json', 'water-reorganization', *map(str, args)],
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
        return math.isclose(float(a), float(b), rel_tol=1e-3, abs_tol=1e-12)
    return a == b


def check(label, rust, py):
    ok = close(rust, py)
    print(f'{label} equal:', ok)
    if not ok:
        print('  rust:', str(rust)[:800])
        print('  py:  ', str(py)[:800])


for s, opt in [(78.4, 1.78), (80.0, 2.0)]:
    check(f'contrast {s} {opt}', run('contrast', f'--epsilon-s={s}', f'--epsilon-opt={opt}'),
          {'value': wr._dielectric_contrast(s, opt)})

radius = capillary_cavity_radius()
for r in (radius, 3.2e-10):
    check(f'energy {r}', run('energy', r), {'value': wr.reorganization_energy_ev(r)})
for gap in (1.57, 1.0):
    check(f'radius {gap}', run('radius', gap), {'value': wr.radius_for_difference(gap)})
check('scales', run('scales'), wr.reorganization_scales())
