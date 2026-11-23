import importlib, json, subprocess, sys
from dataclasses import asdict
from pathlib import Path

binary = str(Path('target/x86_64-pc-windows-gnu/debug/research-engine.exe').resolve())
sys.path.insert(0, str(Path('..').resolve()))
assay = importlib.import_module('domains.pnn.assay')


def run(*args):
    p = subprocess.run([binary, '--json', 'pnn-assay', *map(str, args)],
                       capture_output=True, text=True, encoding='utf-8', timeout=180)
    if p.returncode != 0:
        raise RuntimeError(f'{args}: {p.stderr[:800]}')
    return json.loads(p.stdout)


def check(label, rust, py):
    print(f'{label} equal:', rust == py)
    if rust != py:
        print('  rust:', str(rust)[:900])
        print('  py:  ', str(py)[:900])


degradation = {
    'C1': assay.DegradationResult('C1', 42.0, 78.0, 1.1),
    'C2': assay.DegradationResult('C2', 500.0, 45.0, 0.9),
    'C3': assay.DegradationResult('C3', 9000.0, 12.0),
    'C4': assay.DegradationResult('C4', 60.0, 70.0, 1.0),
}
permeability = {
    'C1': assay.PermeabilityResult('C1', 'PAMPA', pe_1e6_cm_s=5.2),
    'C2': assay.PermeabilityResult('C2', 'MDCK', efflux_ratio=1.8),
    'C4': assay.PermeabilityResult('C4', 'MDCK', efflux_ratio=6.0),
}
cytotoxicity = {
    'C1': assay.CytotoxicityResult('C1', 80.0),
    'C2': assay.CytotoxicityResult('C2', 12.0),
    'C4': assay.CytotoxicityResult('C4', 60.0),
}
criteria = {'ec50_ceiling_nm': 10000.0, 'max_deg_floor_pct': 20.0,
            'pampa_pe_floor': 3.0, 'mdck_efflux_ceiling': 3.0,
            'min_selectivity_index': 50.0}


def as_json_map(items):
    return json.loads(json.dumps({key: asdict(value) for key, value in items.items()}))


py_hits = assay.qualify_leads(degradation, permeability, cytotoxicity)
py_report = assay.render_assay_report(py_hits, criteria)
args = ['qualify', '--degradation', json.dumps({k: asdict(v) for k, v in degradation.items()}),
        '--permeability', json.dumps({k: asdict(v) for k, v in permeability.items()}),
        '--cytotoxicity', json.dumps({k: asdict(v) for k, v in cytotoxicity.items()})]
result = run(*args)
check('hits', result.pop('hits'), [asdict(h) for h in py_hits])
check('report', result.pop('report'), py_report)
check('rows', result.pop('rows'), [h.as_row() for h in py_hits])
check('keys', result, {})

result2 = run('qualify', '--degradation', json.dumps({k: asdict(v) for k, v in degradation.items()}))
check('no aux data', [h['status'] for h in result2['hits']],
      [h.status for h in assay.qualify_leads(degradation)])
