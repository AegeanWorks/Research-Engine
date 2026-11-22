import json, re, shutil, subprocess, sys, tempfile
from pathlib import Path

binary = str(Path('target/x86_64-pc-windows-gnu/debug/research-engine.exe').resolve())
root = Path('..').resolve()
helper = str(Path('lattice_repo_expected.py').resolve())
ref = str(Path('web_expected.py').resolve())
TS = re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00')

def run(cmd, cwd):
    p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True,
                       encoding='utf-8', timeout=180)
    if p.returncode != 0:
        raise RuntimeError(f'{cmd}: {p.stderr[:700]}')
    return p.stdout

def compare(label, method, path, body=None):
    rust_cmd = [binary, '--db', db, '--json', 'web', method, path]
    py_cmd = [sys.executable, ref, '--db', db, method, path]
    if body is not None:
        rust_cmd += ['--body', body]
        py_cmd += ['--body', body]
    rust = json.loads(run(rust_cmd, Path('.')))
    py = json.loads(run(py_cmd, root))
    a, b = TS.sub('<TS>', json.dumps(rust, sort_keys=True)), TS.sub('<TS>', json.dumps(py, sort_keys=True))
    print(f'{label} equal:', a == b)
    if a != b:
        i = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))
        print('  diff at', i, a[max(0, i-120):i+280], '|', b[max(0, i-120):i+280])

with tempfile.TemporaryDirectory() as tmp:
    db = str(Path(tmp) / 'graph.db')
    paper = json.loads(run([sys.executable, helper, '--db', db, 'paper-add',
        '--title', 'Quantum Effects in Water', '--year', '2024', '--venue', 'Nature',
        '--doi', '10.1/q', '--abstract-text', 'Quantum effects in water were observed.'], root))
    pid = paper['paper']['id']
    run([sys.executable, helper, '--db', db, 'claim-add', pid,
        '--text', 'Quantum effect observed', '--quote', 'Quantum effects in water were observed',
        '--locator', 'abstract', '--stance', 'supports'], root)
    run([sys.executable, helper, '--db', db, 'question-add', 'Does it work?'], root)
    run([sys.executable, helper, '--db', db, 'edge-add', 'c_000001', 'q_000001', '--kind', 'supports'], root)

    for label, path in [
        ('index', '/'), ('overview', '/api/overview'), ('matrix', '/api/matrix'),
        ('export', '/api/export'), ('search', '/api/search?q=quantum'),
        ('literature', '/api/literature?q=quantum'), ('outline', '/api/outline?tokens=400'),
        ('bibtex', '/api/export-bibtex'), ('graphml', '/api/export-graphml'),
        ('cytoscape', '/api/export-cytoscape'), ('unknown', '/api/nope'),
    ]:
        compare(label, 'GET', path)

    rdb, pdb = str(Path(tmp) / 'post-rust.db'), str(Path(tmp) / 'post-py.db')
    shutil.copyfile(db, rdb)
    shutil.copyfile(db, pdb)
    for label, path, payload in [
        ('post-questions', '/api/questions', {'text': 'Is it reproducible?'}),
        ('post-question-status', '/api/question-status', {'question': 'q_000002', 'status': 'answered'}),
        ('post-edges', '/api/edges', {'src': 'claim:c_000001', 'dst': 'question:q_000001', 'kind': 'answers'}),
        ('post-papers', '/api/papers', {'title': 'New Paper', 'doi': '10.1/new', 'year': '2025'}),
        ('post-detect', '/api/detect-contradictions', {'auto_link': False}),
    ]:
        body = json.dumps(payload)
        rust = json.loads(run([binary, '--db', rdb, '--json', 'web', 'POST', path, '--body', body], Path('.')))
        py = json.loads(run([sys.executable, ref, '--db', pdb, 'POST', path, '--body', body], root))
        a, b = TS.sub('<TS>', json.dumps(rust, sort_keys=True)), TS.sub('<TS>', json.dumps(py, sort_keys=True))
        print(f'{label} equal:', a == b)
        if a != b:
            i = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))
            print('  diff at', i, a[max(0, i-120):i+260], '|', b[max(0, i-120):i+260])
