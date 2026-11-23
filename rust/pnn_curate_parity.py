import csv, json, subprocess, sys, tempfile
from pathlib import Path

binary = str(Path('target/x86_64-pc-windows-gnu/debug/research-engine.exe').resolve())
sys.path.insert(0, str(Path('..').resolve()))
import importlib
curate_cli = importlib.import_module('domains.pnn.curate')


def run(*args):
    p = subprocess.run([binary, '--json', 'pnn-curate', *map(str, args)],
                       capture_output=True, text=True, encoding='utf-8', timeout=180)
    if p.returncode != 0:
        raise RuntimeError(f'{args}: {p.stderr[:700]}')
    return json.loads(p.stdout)


def make_csv(path, rows):
    fields = ['compound_id', 'name', 'smiles', 'mw', 'logp', 'tpsa', 'hbd', 'hba',
              'rotatable_bonds', 'pka', 'charge']
    with open(path, 'w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


rows_a = [
    {'compound_id': 'C1', 'name': 'Compound A', 'smiles': 'CCO', 'mw': '345.5',
     'logp': '2.6', 'tpsa': '58', 'hbd': '2', 'hba': '5', 'rotatable_bonds': '4',
     'pka': '8.2', 'charge': 'basic'},
    {'compound_id': 'C2', 'name': 'Compound B', 'smiles': 'CCN', 'mw': '300.0',
     'logp': '2.0', 'tpsa': '60', 'hbd': '2', 'hba': '5', 'rotatable_bonds': '3',
     'pka': '', 'charge': ''},
]
rows_b = [
    {'compound_id': 'C1', 'name': '', 'smiles': 'CCO', 'mw': '350.0', 'logp': '2.7',
     'tpsa': '59', 'hbd': '2', 'hba': '5', 'rotatable_bonds': '4', 'pka': '', 'charge': ''},
    {'compound_id': 'C3', 'name': 'Compound C', 'smiles': 'CCC', 'mw': '410.0',
     'logp': '3.1', 'tpsa': '68', 'hbd': '3', 'hba': '6', 'rotatable_bonds': '5',
     'pka': '', 'charge': 'neutral'},
]

with tempfile.TemporaryDirectory() as tmp:
    base = Path(tmp)
    csv_a = base / 'a.csv'
    csv_b = base / 'b.csv'
    make_csv(csv_a, rows_a)
    make_csv(csv_b, rows_b)

    py_out = base / 'py.csv'
    py_json = base / 'py.json'
    rc = curate_cli.main([str(csv_a), str(csv_b), '--out', str(py_out),
                          '--json', str(py_json), '--min-tier', 'B'])
    assert rc == 0, rc

    rust_out = base / 'rust.csv'
    rust_json = base / 'rust.json'
    inputs = [{'source': str(csv_a), 'rows': rows_a}, {'source': str(csv_b), 'rows': rows_b}]
    result = run('run', '--inputs', json.dumps(inputs), '--out', str(rust_out),
                 '--json-path', str(rust_json), '--min-tier', 'B')

    print('csv equal:', rust_out.read_bytes() == py_out.read_bytes())
    py_report = json.loads(py_json.read_text(encoding='utf-8'))
    rust_report = json.loads(rust_json.read_text(encoding='utf-8'))
    py_report.pop('output', None)
    rust_report.pop('output', None)
    print('json equal:', rust_report == py_report)
    print('input rows equal:', result['input_rows'] == 4)
