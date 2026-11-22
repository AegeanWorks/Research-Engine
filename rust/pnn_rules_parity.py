import json, subprocess, sys, tempfile
from pathlib import Path

binary = str(Path('target/x86_64-pc-windows-gnu/debug/research-engine.exe').resolve())
root = Path('..').resolve()
helper = str(Path('pnn_rules_expected.py').resolve())

def run(cmd, cwd):
    p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True,
                       encoding='utf-8', timeout=180)
    if p.returncode != 0:
        raise RuntimeError(f'{cmd}: {p.stderr[:700]}')
    return p.stdout

compound = {
    'compound_id': 'PNN-101', 'name': 'Compound A', 'smiles': 'CCO',
    'mw': 345.5, 'logp': 2.6, 'tpsa': 58.0, 'hbd': 2, 'hba': 5,
    'rotatable_bonds': 4, 'pka': 8.2, 'charge': 'basic', 'logbb': -0.3,
    'brain_plasma_ratio': 0.45, 'oral_bioavailability': 24.0,
    'cyp3a4_inhibition': 18.0, 'herg_liability': 8.0, 'pnn_ec50_nm': 42.0,
}
with tempfile.TemporaryDirectory() as tmp:
    path = Path(tmp) / 'compound.json'
    path.write_text(json.dumps(compound), encoding='utf-8')
    rust = json.loads(run([binary, '--json', 'pnn-rules', 'evaluate', '--compound',
                           json.dumps(compound)], Path('.')))
    py = json.loads(run([sys.executable, helper, 'evaluate', str(path)], root))
    print('evaluate equal:', rust == py)
    if rust != py:
        for a, b in zip(rust, py):
            if a != b:
                print(' rust:', json.dumps(a, sort_keys=True)[:400])
                print(' py:  ', json.dumps(b, sort_keys=True)[:400])
                break
    for criterion in ('mw', 'logbb', 'herg_liability'):
        r = json.loads(run([binary, '--json', 'pnn-rules', 'weight', criterion], Path('.')))
        p = json.loads(run([sys.executable, helper, 'weight', criterion], root))
        print(f'weight-{criterion} equal:', r == p)
