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

with tempfile.TemporaryDirectory() as tmp:
    db = str(Path(tmp) / 'graph.db')
    helper = str(Path('lattice_repo_expected.py').resolve())
    run([sys.executable, helper, '--db', db, 'paper-add', '--title', 'Quantum Effects',
         '--authors', 'Ada', '--year', '2024', '--venue', 'Nature', '--doi', '10.1/q'], root)
    run([sys.executable, helper, '--db', db, 'claim-add', 'p_ae72d0bb1cb1',
         '--text', 'The effect reproduced', '--quote', 'we observed it',
         '--locator', 'abstract:s1', '--stance', 'supports'], root)
    run([sys.executable, '-m', 'engine', '--db', db, 'db', 'integrity'], root) if False else None
    run([sys.executable, helper, '--db', db, 'question-add', 'Does it reproduce?'], root)
    run([sys.executable, helper, '--db', db, 'edge-add', 'c_000001', 'q_000001',
         '--kind', 'supports'], root)

    ref = str(Path('lattice_snapshots_expected.py').resolve())
    for command in ('records', 'bibtex', 'cytoscape', 'graphml'):
        rust = json.loads(run([binary, '--db', db, '--json', 'lattice-snap', command], Path('.')))
        py = json.loads(run([sys.executable, ref, '--db', db, command], root))
        print(f'{command} equal:', rust == py)
        if rust != py:
            a, b = json.dumps(rust, sort_keys=True), json.dumps(py, sort_keys=True)
            print('  rust:', a[:500])
            print('  py:  ', b[:500])

    out = str(Path(tmp) / 'snapshot.jsonl')
    result = json.loads(run([binary, '--db', db, '--json', 'lattice-snap', 'export', out], Path('.')))
    print('export counts:', result.get('papers'), result.get('claims'),
          result.get('questions'), result.get('edges'))
    print('export lines:', len(Path(out).read_text(encoding='utf-8').splitlines()))
