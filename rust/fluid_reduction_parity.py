import json, math, subprocess, sys
from pathlib import Path

binary = str(Path('target/x86_64-pc-windows-gnu/debug/research-engine.exe').resolve())
sys.path.insert(0, str(Path('..').resolve()))
from domains.fluid_universe.theory.reduction import (
    moment_finite, moment_log_divergent, moment_numeric, moment_power,
    render_markdown, verdict, wall_lower_bound_2d, wall_tension,
)


def run(*args):
    p = subprocess.run([binary, '--json', 'fluid-reduction', *map(str, args)],
                       capture_output=True, text=True, encoding='utf-8', timeout=180)
    if p.returncode != 0:
        raise RuntimeError(f'{args}: {p.stderr[:600]}')
    return json.loads(p.stdout)


def close(a, b):
    if isinstance(a, dict):
        return set(a) == set(b) and all(close(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(close(x, y) for x, y in zip(a, b))
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(float(a), float(b), rel_tol=1e-12, abs_tol=1e-12)
    return a == b


def check(label, rust, py):
    ok = close(rust, py)
    print(f'{label} equal:', ok)
    if not ok:
        print('  rust:', str(rust)[:500])
        print('  py:  ', str(py)[:500])


for mu in (0.0, 1.0, 2.25):
    check(f'tension mu={mu}', run('tension', mu), {'value': wall_tension(mu)})
    check(f'lower mu={mu}', run('lower', mu, 2.0), {'value': wall_lower_bound_2d(mu, 2.0)})

for alpha in (2.0, 4.0, 5.0):
    check(f'power {alpha}', run('power', alpha), {'value': moment_power(alpha)})
    check(f'finite {alpha}', run('finite', alpha), {'value': moment_finite(alpha)})
    check(f'log-divergent {alpha}', run('log-divergent', alpha), {'value': moment_log_divergent(alpha)})
    check(f'numeric {alpha}', run('numeric', alpha), {'value': moment_numeric(alpha)})
    check(f'verdict {alpha}', run('verdict', '--alpha', alpha), verdict(alpha))

payload = {
    'wall_tension': wall_tension(1.0),
    'lower_bound_example': wall_lower_bound_2d(1.0, 2.0),
    'verdict': verdict(4.0),
    'meta': {'config_sha256': 'abc123', 'git': {'commit': 'deadbeef', 'dirty': True}},
}
result = run('render', '--payload', json.dumps(payload))
check('render', result.pop('markdown'), render_markdown(payload))
check('render keys', result, {})
