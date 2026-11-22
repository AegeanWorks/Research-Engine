import json, math, subprocess, sys
from pathlib import Path

binary = str(Path('target/x86_64-pc-windows-gnu/debug/research-engine.exe').resolve())
sys.path.insert(0, str(Path('..').resolve()))
from domains.fluid_universe.theory import water_analogue as wa


def run(*args):
    p = subprocess.run([binary, '--json', 'water-analogue', *map(str, args)],
                       capture_output=True, text=True, encoding='utf-8', timeout=180)
    if p.returncode != 0:
        raise RuntimeError(f'{args}: {p.stderr[:600]}')
    return json.loads(p.stdout)


def close(a, b):
    if isinstance(a, dict):
        return set(a) == set(b) and all(close(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(close(x, y) for x, y in zip(a, b))
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(float(a), float(b), rel_tol=1e-13, abs_tol=1e-13)
    return a == b


def check(label, rust, py):
    ok = close(rust, py)
    print(f'{label} equal:', ok)
    if not ok:
        print('  rust:', str(rust)[:600])
        print('  py:  ', str(py)[:600])


check('speed', run('speed'), {'value': wa.sound_speed(0.1)})
check('flow', run('flow', 0.5, '--flow-rate', 1e-3), {'value': wa.flow_velocity(0.5, 1e-3, 0.1)})
check('radius', run('radius', '--flow-rate', 1e-3), {'value': wa.horizon_radius(1e-3, 0.1)})
check('gravity', run('gravity', '--flow-rate', 1e-3), {'value': wa.surface_gravity(1e-3, 0.1)})
kappa = wa.surface_gravity(1e-3, 0.1)
check('temperature', run('temperature', kappa), {'value': wa.hawking_temperature(kappa)})
check('metric', run('metric', 0.5, '--flow-rate', 1e-3), wa.acoustic_metric(0.5, 1e-3, 0.1))
check('lab', run('lab'), wa.lab_scales())
check('capillary', run('capillary'), {'value': wa.capillary_length()})
radius = wa.horizon_radius(1e-3, 0.1)
length = wa.capillary_length()
check('ratio', run('ratio', radius, length), {'value': wa.capillary_ratio(radius, length)})
check('min-flow', run('min-flow'), {'value': wa.long_wavelength_min_flow(0.1)})
check('validity', run('validity'), wa.validity())
