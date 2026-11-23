import importlib, json, math, subprocess, sys
from dataclasses import asdict
from pathlib import Path

binary = str(Path('target/x86_64-pc-windows-gnu/debug/research-engine.exe').resolve())
sys.path.insert(0, str(Path('..').resolve()))
pre = importlib.import_module('domains.pnn.preclinical')


def run(*args):
    p = subprocess.run([binary, '--json', 'pnn-preclinical', *map(str, args)],
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
        return math.isclose(float(a), float(b), rel_tol=1e-12, abs_tol=1e-12)
    return a == b


def check(label, rust, py):
    ok = close(rust, py)
    print(f'{label} equal:', ok)
    if not ok:
        print('  rust:', str(rust)[:900])
        print('  py:  ', str(py)[:900])


points = [
    {'time_h': 0.0, 'concentration': 0.0},
    {'time_h': 1.0, 'concentration': 120.0},
    {'time_h': 3.0, 'concentration': 80.0},
    {'time_h': 8.0, 'concentration': 30.0},
    {'time_h': 24.0, 'concentration': 5.0},
]
py_nca = pre.calculate_nca([pre.ConcentrationPoint(**p) for p in points], 10.0, 'C1', 'PO', 'plasma')
check('nca', run('nca', '--points', json.dumps(points), '--dose', 10.0), asdict(py_nca))

po_plasma = asdict(pre.calculate_nca([pre.ConcentrationPoint(**p) for p in points], 10.0, 'C1', 'PO', 'plasma'))
iv_plasma = asdict(pre.calculate_nca([pre.ConcentrationPoint(**p) for p in points], 5.0, 'C1', 'IV', 'plasma'))
po_brain = asdict(pre.calculate_nca([pre.ConcentrationPoint(**p) for p in points], 10.0, 'C1', 'PO', 'brain'))
pk = {'C1': {'PO_plasma': po_plasma, 'IV_plasma': iv_plasma, 'PO_brain': po_brain}}
pd = {'C1': asdict(pre.PdOutcome('C1', 10.0, 28.0, 35.0))}
criteria = {'min_kp_brain': 0.30, 'min_oral_f_pct': 20.0,
            'min_wfa_reduction_pct': 15.0, 'min_itt_improvement_pct': 20.0}
py_candidates = pre.evaluate_candidates(
    {'C1': {k: pre.PkProfile(**v) for k, v in pk['C1'].items()}},
    {'C1': pre.PdOutcome(**pd['C1'])}, **criteria)
py_report = pre.render_preclinical_report(py_candidates, criteria)

result = run('run', '--pk', json.dumps(pk), '--pd', json.dumps(pd))
check('candidates', json.loads(json.dumps(result.pop('candidates'))),
      json.loads(json.dumps([asdict(c) for c in py_candidates])))
check('report', result.pop('report'), py_report)
check('rows', result.pop('rows'), [c.as_row() for c in py_candidates])
check('keys', result, {})
