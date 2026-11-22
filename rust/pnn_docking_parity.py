import json, subprocess, sys, tempfile
from pathlib import Path

binary = str(Path('target/x86_64-pc-windows-gnu/debug/research-engine.exe').resolve())
root = Path('..').resolve()
helper = str(Path('pnn_docking_expected.py').resolve())


def run(cmd, cwd):
    p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True,
                       encoding='utf-8', timeout=180)
    if p.returncode != 0:
        raise RuntimeError(f'{cmd}: {p.stderr[:700]}')
    return p.stdout


rows = [
    {'Compound ID': 'C1', 'Target': 'TP53', 'Vina (kcal/mol)': '-9.2', 'Glide': '-6.1',
     'mmGBSA': '-45.3', 'RMSD': '1.2', 'HBonds': '3', 'key interactions': 'H-bonds with SER'},
    {'id': 'C1', 'receptor': 'MDM2', 'vinaaffinity': '-8.0', 'glidescore': '-5.0',
     'dG': '-40.0', 'rmsdligand': '2.0', 'hbondcount': '2'},
    {'compound': 'C2', 'targetname': 'TP53', 'affinity': '-7.5', 'mmgbsadg': '-35.0'},
    {'compound_id': 'C3', 'target': 'EGFR', 'vina': '-6.0', 'rmsd': '4.5'},
]

with tempfile.TemporaryDirectory() as tmp:
    path = Path(tmp) / 'rows.json'
    path.write_text(json.dumps(rows), encoding='utf-8')

    py_parse = json.loads(run([sys.executable, helper, 'parse', str(path), 'input'], root))
    rust_parse = json.loads(run([binary, '--json', 'pnn-docking', 'parse', '--rows', str(path)], Path('.')))
    print('parse equal:', rust_parse == py_parse)
    if rust_parse != py_parse:
        print('  rust:', json.dumps(rust_parse, sort_keys=True)[:600])
        print('  py:  ', json.dumps(py_parse, sort_keys=True)[:600])

    for label, py_extra, rust_extra in [
        ('rank-default', [], []),
        ('rank-filtered', ['2.0', '-8.5'], ['--max-rmsd=2.0', '--min-vina=-8.5']),
    ]:
        py = json.loads(run([sys.executable, helper, 'rank', str(path)] + py_extra, root))
        rust = json.loads(run([binary, '--json', 'pnn-docking', 'rank', '--rows', str(path)] + rust_extra, Path('.')))
        print(f'{label} equal:', rust == py)
        if rust != py:
            for key in py:
                if rust.get(key) != py[key]:
                    print(f'  {key} rust:', json.dumps(rust.get(key), sort_keys=True)[:600])
                    print(f'  {key} py:  ', json.dumps(py[key], sort_keys=True)[:600])
