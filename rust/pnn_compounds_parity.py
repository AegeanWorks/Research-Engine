import json, subprocess, sys
from pathlib import Path

binary = str(Path('target/x86_64-pc-windows-gnu/debug/research-engine.exe').resolve())
sys.path.insert(0, str(Path('..').resolve()))
from dataclasses import asdict
from domains.pnn.compounds import normalize_field, parse_compounds


def run(*args):
    p = subprocess.run([binary, '--json', 'pnn-compounds', *map(str, args)],
                       capture_output=True, text=True, encoding='utf-8', timeout=180)
    if p.returncode != 0:
        raise RuntimeError(f'{args}: {p.stderr[:600]}')
    return json.loads(p.stdout)


def check(label, rust, py):
    print(f'{label} equal:', rust == py)
    if rust != py:
        print('  rust:', str(rust)[:600])
        print('  py:  ', str(py)[:600])


for name in ('ID', 'MolWeight', 'CLogP', 'TPSA (A2)', 'HBD count', 'Compound Name',
             'Canonical SMILES', 'Ionization', 'unknown-column'):
    check(f'field {name}', run('field', name), {'field': normalize_field(name) or ''})

rows = [
    {'ID': 'C1', 'Molecular Weight': '345.5', 'clogp': '2.6', 'Polar Area': '58',
     'Donors': '2', 'Acceptors': '5', 'Rotors': '4', 'Compound Name': 'Compound A',
     'Canonical SMILES': 'CCO', 'Ion Class': 'weakly basic', 'logBB': '-0.3',
     'Oral F': '24%', 'hERG': '8', 'EC50nM': '42'},
    {'compound': 'C2', 'mw': '400', 'logp': '3.0', 'tpsa': '70', 'hbd': '3',
     'hba': '7', 'rotatable_bonds': '7', 'pKa': '4.5', 'charge': 'acid'},
]
# The oral-F fixture uses a percentage suffix only to exercise string coercion;
# replace it with a plain number so both parsers see the same value.
rows[0]['Oral F'] = '24'
json_rows = json.dumps(rows)

py = [asdict(c) for c in parse_compounds(rows, 'input')]
rust = run('parse', '--rows', json_rows)
check('parse', rust, py)

dupes = [rows[0], dict(rows[0])]
try:
    parse_compounds(dupes, 'input')
    py_result = 'accepted'
except Exception:
    py_result = 'rejected'
proc = subprocess.run([binary, '--json', 'pnn-compounds', 'parse', '--rows', json.dumps(dupes)],
                      capture_output=True, text=True, timeout=180)
rust_result = 'rejected' if proc.returncode != 0 else 'accepted'
check('duplicate', rust_result, py_result)
