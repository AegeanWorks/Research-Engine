import importlib, json, math, subprocess, sys
from pathlib import Path

binary = str(Path('target/x86_64-pc-windows-gnu/debug/research-engine.exe').resolve())
sys.path.insert(0, str(Path('..').resolve()))
ind = importlib.import_module('domains.pnn.ind')


def run(*args):
    p = subprocess.run([binary, '--json', 'pnn-ind', *map(str, args)],
                       capture_output=True, text=True, encoding='utf-8', timeout=180)
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


py_scale = ind.calculate_allometric_scaling(10.0, 11.7, 87.2, 80.0)
check('scale', run('scale', 10.0, 11.7, 87.2, 80.0),
      dict(zip(('hed_mg_kg', 'human_daily_mg', 'cl_human_l_h', 'vd_human_l',
                't12_human_h', 'noael_mg_kg', 'noael_hed', 'mrsd_mg'), py_scale)))

compounds = [
    {'compound_id': 'C1', 'name': 'Compound A'},
    {'compound_id': 'C2', 'name': 'Compound B'},
]
preclinical = {
    'C1': {'dose_mg_kg': 10.0, 'cl_l_h_kg': 11.7, 'vd_l_kg': 87.2,
           'noael_mg_kg': 80.0, 'brain_kp': 0.45, 'oral_f': 35.0},
    'C2': {'dose_mg_kg': 5.0, 'brain_kp': 0.12},
}
py_projections = ind.project_clinical_candidates(compounds, preclinical)
py_report = ind.render_ind_dossier(py_projections)
result = run('project', '--compounds', json.dumps(compounds),
             '--preclinical', json.dumps(preclinical))
check('projections', json.loads(json.dumps(result.pop('projections'))),
      json.loads(json.dumps([p.__dict__ for p in py_projections])))
check('report', result.pop('report'), py_report)
check('rows', result.pop('rows'), [p.as_row() for p in py_projections])
check('keys', result, {})
