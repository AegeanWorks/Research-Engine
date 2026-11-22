import json, subprocess, sys
from pathlib import Path

binary = str(Path('target/x86_64-pc-windows-gnu/debug/research-engine.exe').resolve())
sys.path.insert(0, str(Path('..').resolve()))
from domains.pnn.compounds import Compound
from domains.pnn.curation import Candidate, property_bin
from domains.pnn.screen import evaluate_compound
from domains.pnn.tables import SCREEN_FIELDS, CURATED_FIELDS, curated_row, screen_row


def run(*args):
    p = subprocess.run([binary, '--json', 'pnn-tables', *map(str, args)],
                       capture_output=True, text=True, encoding='utf-8', timeout=180)
    if p.returncode != 0:
        raise RuntimeError(f'{args}: {p.stderr[:600]}')
    return json.loads(p.stdout)


def check(label, rust, py):
    print(f'{label} equal:', rust == py)
    if rust != py:
        print('  rust:', str(rust)[:700])
        print('  py:  ', str(py)[:700])


def compound(cid, mw, logp, tpsa, hbd, hba, rot, **extra):
    data = {'compound_id': cid, 'mw': mw, 'logp': logp, 'tpsa': tpsa,
            'hbd': hbd, 'hba': hba, 'rotatable_bonds': rot}
    data.update(extra)
    return data


compounds_data = [
    compound('C1', 345.5, 2.6, 58.0, 2, 5, 4, name='Compound A', smiles='CCO',
             pka=8.2, charge='basic', logbb=-0.3, brain_plasma_ratio=0.45,
             oral_bioavailability=24.0, cyp3a4_inhibition=18.0,
             herg_liability=8.0, pnn_ec50_nm=42.0),
    compound('C2', 480.0, 4.2, 95.0, 5, 9, 9, pka=6.0, charge='acidic',
             herg_liability=40.0),
]

for width in (0.1, 0.25):
    for data in compounds_data:
        py_bins = list(property_bin(Compound(**data), width))
        rust_bins = run('bin', '--compound', json.dumps(data), f'--width={width}')
        check(f'bin {data["compound_id"]} w={width}', rust_bins, py_bins)

results_json = []
for data in compounds_data:
    result = evaluate_compound(Compound(**data))
    results_json.append({
        'compound': data, 'tier': result.tier, 'score': result.score,
        'failed_criteria': result.failed_criteria(),
        'unknown_criteria': result.unknown_criteria(),
    })

check('screen rows', run('screen', '--results', json.dumps(results_json)),
      [screen_row(evaluate_compound(Compound(**d))) for d in compounds_data])

candidates_json = []
for data in compounds_data:
    result = evaluate_compound(Compound(**data))
    candidates_json.append({
        'compound': data, 'source': 'synthetic-library',
        'result': {'tier': result.tier, 'score': result.score,
                   'failed_criteria': result.failed_criteria(),
                   'unknown_criteria': result.unknown_criteria()},
    })
py_curated = [curated_row(Candidate(Compound(**d), 'synthetic-library',
                                     evaluate_compound(Compound(**d))), 0.1)
              for d in compounds_data]
check('curated rows', run('curated', '--candidates', json.dumps(candidates_json)), py_curated)

check('fields', run('fields'), {'curated': list(CURATED_FIELDS), 'screen': list(SCREEN_FIELDS)})
