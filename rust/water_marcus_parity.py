import json, math, subprocess, sys
from pathlib import Path

binary = str(Path('target/x86_64-pc-windows-gnu/debug/research-engine.exe').resolve())
sys.path.insert(0, str(Path('..').resolve()))
from domains.fluid_universe.theory import water_marcus as wm


def run(*args):
    p = subprocess.run([binary, '--json', 'water-marcus', *map(str, args)],
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


for lam, temp in [(1.6171325440878093, 300.0), (2.0, 298.0)]:
    check(f'width {lam} {temp}', run('width', f'--lambda-ev={lam}', f'--temperature-k={temp}'),
          {'value': wm.marcus_width_ev(lam, temp)})
for energy, center, fwhm in [(1.7, 1.7, 0.68), (2.0, 1.7, 0.68)]:
    check(f'line {energy}', run('line', energy, center, fwhm),
          {'value': wm.gaussian_line_shape(energy, center, fwhm)})
check('scales', run('scales'), wm.marcus_scales())
