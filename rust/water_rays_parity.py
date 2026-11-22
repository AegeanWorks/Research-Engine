import json, math, subprocess, sys
from pathlib import Path

binary = str(Path('target/x86_64-pc-windows-gnu/debug/research-engine.exe').resolve())
sys.path.insert(0, str(Path('..').resolve()))
from domains.fluid_universe.theory import water_rays as wr
from domains.fluid_universe.theory.water_analogue import horizon_radius, sound_speed


def run(*args):
    p = subprocess.run([binary, '--json', 'water-rays', *map(str, args)],
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
        return math.isclose(float(a), float(b), rel_tol=1e-12, abs_tol=1e-14)
    return a == b


def check(label, rust, py):
    ok = close(rust, py)
    print(f'{label} equal:', ok)
    if not ok:
        print('  rust:', str(rust)[:600])
        print('  py:  ', str(py)[:600])


flow = 1e-3
depth = 0.1
for r in (0.002, 0.005, 0.01):
    check(f'outgoing {r}', run('outgoing', r, '--flow-rate', flow),
          {'value': wr.outgoing_speed(r, flow, depth)})
    check(f'ingoing {r}', run('ingoing', r, '--flow-rate', flow),
          {'value': wr.ingoing_speed(r, flow, depth)})

check('peeling', run('peeling', '--flow-rate', flow), {'value': wr.peeling_rate(flow, depth)})
horizon = horizon_radius(flow, depth)
speed = sound_speed(depth)
check('analytic time', run('time', 0.01, 0.004, horizon, speed),
      {'value': wr.analytic_outgoing_time(0.01, 0.004, horizon, speed)})
check('integrate', run('integrate', 0.003, 0.004, '--flow-rate', flow, '--dt', 1e-5),
      wr.integrate_outgoing(0.003, 0.004, flow, depth, dt=1e-5))
