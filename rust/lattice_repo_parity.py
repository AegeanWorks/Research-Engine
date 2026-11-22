import json, subprocess, sys, tempfile
from pathlib import Path

binary = str(Path('target/x86_64-pc-windows-gnu/debug/research-engine.exe').resolve())
root = Path('..').resolve()

def run(cmd, cwd):
    p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True,
                       encoding='utf-8', timeout=180)
    if p.returncode != 0:
        raise RuntimeError(f'{cmd}: {p.stderr[:600]}')
    return p.stdout

def strip_volatile(value):
    if isinstance(value, dict):
        return {k: strip_volatile(v) for k, v in value.items() if k not in ('created_at', 'screened_at')}
    if isinstance(value, list):
        return [strip_volatile(v) for v in value]
    return value

def compare(label, args, write=False):
    rust_db = str(Path(tmp) / 'rust.db')
    py_db = str(Path(tmp) / 'py.db')
    rust = strip_volatile(json.loads(run([binary, '--db', rust_db, '--json', 'lattice-repo'] + args, Path('.'))))
    py = strip_volatile(json.loads(run([sys.executable, str(Path('lattice_repo_expected.py').resolve()),
                                       '--db', py_db if write else rust_db] + args, root)))
    print(f'{label} equal:', rust == py)
    if rust != py:
        print('  rust:', json.dumps(rust, sort_keys=True)[:500])
        print('  py:  ', json.dumps(py, sort_keys=True)[:500])
    return rust

with tempfile.TemporaryDirectory() as tmp:
    paper_args = ['paper-add', '--title', 'Quantum Effects in Water', '--authors', 'Ada Lovelace',
                  '--year', '2024', '--venue', 'Nature', '--doi', 'https://doi.org/10.1/qw',
                  '--arxiv', 'arxiv:2401.01234', '--abstract-text',
                  'A computational simulation of fluid dynamics', '--tags', 'quantum, water']
    first = compare('paper-add', paper_args, write=True)
    paper_id = first['paper']['id']
    compare('paper-add-again', paper_args, write=True)

    claim_args = ['claim-add', paper_id, '--text', 'The simulation reproduces the effect',
                  '--quote', 'we observed the effect', '--locator', 'abstract:s1',
                  '--stance', 'supports', '--confidence', '0.8']
    compare('claim-add', claim_args, write=True)
    compare('question-add', ['question-add', 'Does the simulation reproduce the effect?'], write=True)
    compare('edge-add', ['edge-add', 'c_000001', 'q_000001', '--kind', 'supports'], write=True)
    compare('get', ['get', 'c_000001'])
    compare('search', ['search', 'quantum'])
    compare('stats', ['stats'])
