import importlib, json, math, subprocess, sys
from dataclasses import asdict
from pathlib import Path

binary = str(Path('target/x86_64-pc-windows-gnu/debug/research-engine.exe').resolve())
sys.path.insert(0, str(Path('..').resolve()))
pathway = importlib.import_module('domains.pnn.pathway')


def run(*args):
    p = subprocess.run([binary, '--json', 'pnn-pathway', *map(str, args)],
                       capture_output=True, text=True, encoding='utf-8', timeout=300)
    if p.returncode != 0:
        raise RuntimeError(f'{args}: {p.stderr[:800]}')
    return json.loads(p.stdout)


def close(a, b):
    if isinstance(a, dict):
        return set(a) == set(b) and all(close(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(close(x, y) for x, y in zip(a, b))
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(float(a), float(b), rel_tol=1e-10, abs_tol=1e-10)
    return a == b


def check(label, rust, py):
    ok = close(rust, py)
    print(f'{label} equal:', ok)
    if not ok:
        print('  rust:', str(rust)[:900])
        print('  py:  ', str(py)[:900])


for regimen in ('INTERMITTENT_PULSATILE', 'CONTINUOUS_DAILY', 'SINGLE_DOSE'):
    points, summary = pathway.simulate_circuit_dynamics(regimen=regimen, duration_days=7)
    py_report = pathway.render_pathway_report(summary, points)
    result = run('simulate', '--regimen', regimen, '--days', 7)
    check(f'report {regimen}', result.pop('report'), py_report)
    sim = result.pop('simulation')
    check(f'summary {regimen}', sim['summary'], asdict(summary))
    check(f'points {regimen}', sim['points'], [asdict(p) for p in points])
    check(f'keys {regimen}', result, {})
