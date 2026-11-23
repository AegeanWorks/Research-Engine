import csv, importlib, json, subprocess, sys, tempfile
from pathlib import Path

binary = str(Path('target/x86_64-pc-windows-gnu/debug/research-engine.exe').resolve())
sys.path.insert(0, str(Path('..').resolve()))
selection = importlib.import_module('domains.pnn.selection')


def run(*args):
    p = subprocess.run([binary, '--json', 'lead-selection', *map(str, args)],
                       capture_output=True, text=True, encoding='utf-8', timeout=300)
    if p.returncode != 0:
        raise RuntimeError(f'{args}: {p.stderr[:800]}')
    return json.loads(p.stdout)


def make_csv(path, fields, rows):
    with open(path, 'w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


compound_fields = ['compound_id', 'name', 'smiles', 'mw', 'logp', 'tpsa', 'hbd', 'hba',
                   'rotatable_bonds', 'pka', 'charge']
compounds_a = [
    {'compound_id': 'C1', 'name': 'Compound A', 'smiles': 'CCO', 'mw': '345.5', 'logp': '2.6',
     'tpsa': '58', 'hbd': '2', 'hba': '5', 'rotatable_bonds': '4', 'pka': '8.2', 'charge': 'basic'},
    {'compound_id': 'C2', 'name': 'Compound B', 'smiles': 'CCN', 'mw': '300.0', 'logp': '2.0',
     'tpsa': '60', 'hbd': '2', 'hba': '5', 'rotatable_bonds': '3', 'pka': '', 'charge': ''},
]
compounds_b = [
    {'compound_id': 'C3', 'name': 'Compound C', 'smiles': 'CCC', 'mw': '410.0', 'logp': '3.1',
     'tpsa': '68', 'hbd': '3', 'hba': '6', 'rotatable_bonds': '5', 'pka': '', 'charge': 'neutral'},
]
dock_fields = ['Compound ID', 'Target', 'Vina', 'Glide', 'mmGBSA', 'RMSD', 'HBonds']
docking = [
    {'Compound ID': 'C1', 'Target': 'TP53', 'Vina': '-9.2', 'Glide': '-6.1', 'mmGBSA': '-45.3',
     'RMSD': '1.2', 'HBonds': '3'},
    {'Compound ID': 'C2', 'Target': 'MDM2', 'Vina': '-8.0', 'Glide': '-5.0', 'mmGBSA': '-40.0',
     'RMSD': '2.0', 'HBonds': '2'},
]

with tempfile.TemporaryDirectory() as tmp:
    base = Path(tmp)
    a = base / 'a.csv'
    b = base / 'b.csv'
    d = base / 'docking.csv'
    make_csv(a, compound_fields, compounds_a)
    make_csv(b, compound_fields, compounds_b)
    make_csv(d, dock_fields, docking)

    py_sel = selection.select_leads([str(a), str(b)], str(d))
    opts = selection._options('B', 25, 0.1, None, None, None)
    py_report = selection.render_lead_report(py_sel, opts, top_n=25)

    result = run('report', '--inputs', f'{a},{b}', '--docking', str(d))
    rust_report = result.pop('report')
    sel = result.pop('selection')

    print('report equal:', rust_report == py_report)
    if rust_report != py_report:
        import difflib
        print('\n'.join(list(difflib.unified_diff(py_report.splitlines(), rust_report.splitlines()))[:30]))
    print('input rows equal:', sel['curation']['input_rows'] == len(compounds_a) + len(compounds_b))
    print('emitted equal:', sel['curation']['selected'] == 3)
    print('shortlist equal:', sel['ranking']['summary']['emitted'] == py_sel.ranking['emitted'])
