import json, re, subprocess, sys, tempfile
from pathlib import Path

binary = str(Path('target/x86_64-pc-windows-gnu/debug/research-engine.exe').resolve())
root = Path('..').resolve()
helper = str(Path('lattice_repo_expected.py').resolve())
ref = str(Path('client_expected.py').resolve())
TS = re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00')

def run(cmd, cwd):
    p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True,
                       encoding='utf-8', timeout=180)
    if p.returncode != 0:
        raise RuntimeError(f'{cmd}: {p.stderr[:700]}')
    return p.stdout

def compare(label, args, db_rust, db_py, py_args=None):
    rust = json.loads(run([binary, '--db', db_rust, '--json', 'client'] + args, Path('.')))
    py_proc = subprocess.run([sys.executable, ref, '--db', db_py] + (py_args or args), cwd=str(root),
                             capture_output=True, text=True, encoding='utf-8', timeout=180)
    if py_proc.returncode != 0:
        raise RuntimeError(f'py: {py_proc.stderr[:700]}')
    py = json.loads(py_proc.stdout)
    a, b = TS.sub('<TS>', json.dumps(rust, sort_keys=True)), TS.sub('<TS>', json.dumps(py, sort_keys=True))
    print(f'{label} equal:', a == b)
    if a != b:
        i = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))
        print('  diff at', i, a[max(0, i-120):i+260], '|', b[max(0, i-120):i+260])

with tempfile.TemporaryDirectory() as tmp:
    rdb, pdb = str(Path(tmp) / 'rust.db'), str(Path(tmp) / 'py.db')
    paper = json.loads(run([sys.executable, helper, '--db', rdb, 'paper-add',
        '--title', 'Quantum Effects', '--doi', '10.1/q'], root))
    run([sys.executable, helper, '--db', pdb, 'paper-add',
        '--title', 'Quantum Effects', '--doi', '10.1/q'], root)
    compare('tool-schemas', ['tool-schemas'], rdb, pdb)
    compare('tool-schemas-ro', ['tool-schemas', '--read-only'], rdb, pdb,
            py_args=['--read-only', 'tool-schemas'])
    compare('resource-schemas', ['resource-schemas'], rdb, pdb)
    compare('prompt-schemas', ['prompt-schemas'], rdb, pdb)
    compare('call-stats', ['call', 'stats'], rdb, pdb)
    compare('call-entity', ['call', 'get_entity', '--arguments', json.dumps({'ref': 'p_ae72d0bb1cb1'})], rdb, pdb)
    compare('read-resource', ['read-resource', 'lattice://stats'], rdb, pdb)
    compare('call-question', ['call', 'add_question', '--arguments', json.dumps({'text': 'Does it work?'})], rdb, pdb)
