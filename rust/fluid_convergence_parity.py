import json, math, subprocess, sys
from pathlib import Path

binary = str(Path('target/x86_64-pc-windows-gnu/debug/research-engine.exe').resolve())
sys.path.insert(0, str(Path('..').resolve()))
from domains.fluid_universe.sims.convergence import (
    compare_scans, compare_temporal, summarize_trend,
)


def run(*args):
    p = subprocess.run([binary, '--json', 'fluid-convergence', *map(str, args)],
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
    if a is None or b is None:
        return a is b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(float(a), float(b), rel_tol=1e-12, abs_tol=1e-12)
    return a == b


def check(label, rust, py):
    ok = close(rust, py)
    print(f'{label} equal:', ok)
    if not ok:
        print('  rust:', str(rust)[:600])
        print('  py:  ', str(py)[:600])


def payload(n, steps, dt, h, h_up, z3, force, bond, status):
    return {
        'n': n, 'length': 20.0, 'mu': 0.5, 'steps': steps, 'dt': dt,
        'final': {'H': h, 'H_upsampled': h_up, 'Z3': z3,
                  'force_rms': force, 'max_bond': bond},
        'verdict': {'claim_15_status': status},
    }


low = payload(64, 1000, 0.01, 0.92, 0.99, 0.48, 0.02, 0.31, 'UNVERIFIED')
high = payload(128, 1000, 0.01, 0.97, 1.002, 0.505, 0.015, 0.29, 'UNVERIFIED')
check('scan', run('scan', '--low', json.dumps(low), '--high', json.dumps(high)),
      compare_scans(low, high))

coarse = payload(64, 1000, 0.02, 0.90, 0.98, 0.47, 0.03, 0.35, 'UNVERIFIED')
fine = payload(64, 2000, 0.01, 0.96, 1.001, 0.502, 0.02, 0.30, 'UNVERIFIED')
check('temporal', run('temporal', '--coarse', json.dumps(coarse), '--fine', json.dumps(fine)),
      compare_temporal(coarse, fine))

rows = [
    {'steps': 100, 't': 1.0, 'Z3': 0.10, 'force_rms': 0.09, 'claim_15_status': 'UNVERIFIED'},
    {'steps': 200, 't': 2.0, 'Z3': 0.22, 'force_rms': 0.07, 'claim_15_status': 'UNVERIFIED'},
    {'steps': 400, 't': 4.0, 'Z3': 0.46, 'force_rms': 0.03, 'claim_15_status': 'SUPPORTED'},
]
check('trend', run('trend', '--rows', json.dumps(rows)), summarize_trend(rows))
check('trend custom', run('trend', '--rows', json.dumps(rows), '--z3-target', 0.6, '--force-tol', 0.02),
      summarize_trend(rows, z3_target=0.6, force_tol=0.02))
