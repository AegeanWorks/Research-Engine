import json, subprocess, sys, tempfile
from pathlib import Path

binary = str(Path('target/x86_64-pc-windows-gnu/debug/research-engine.exe').resolve())
root = Path('..').resolve()

def run(cmd, cwd):
    p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True,
                       encoding='utf-8', timeout=180)
    if p.returncode != 0:
        raise RuntimeError(f'{cmd}: {p.stderr[:700]}')
    return p.stdout

with tempfile.TemporaryDirectory() as tmp:
    db = str(Path(tmp) / 'graph.db')
    helper = str(Path('lattice_repo_expected.py').resolve())
    paper = json.loads(run([sys.executable, helper, '--db', db, 'paper-add',
        '--title', 'Quantum Effects', '--year', '2024', '--doi', '10.1/q'], root))
    pid = paper['paper']['id']
    run([sys.executable, helper, '--db', db, 'claim-add', pid,
        '--text', 'Quantum simulation improves diffusion', '--quote', 'diffusion increased',
        '--locator', 'abstract:s1', '--stance', 'supports'], root)
    run([sys.executable, helper, '--db', db, 'claim-add', pid,
        '--text', 'Quantum simulation fails to improve diffusion', '--quote', 'diffusion unchanged',
        '--locator', 'abstract:s2', '--stance', 'contradicts'], root)
    run([sys.executable, helper, '--db', db, 'question-add', 'Does it improve?'], root)
    run([sys.executable, helper, '--db', db, 'question-add', 'Any open question?'], root)
    run([sys.executable, helper, '--db', db, 'edge-add', 'c_000001', 'q_000001', '--kind', 'supports'], root)
    run([sys.executable, helper, '--db', db, 'edge-add', 'c_000002', 'q_000001', '--kind', 'contradicts'], root)

    ref = str(Path('studio_api_expected.py').resolve())
    cases = [
        ('matrix', ['matrix']),
        ('matrix-filtered', ['matrix', '--questions', 'q_000001']),
        ('evidence', ['evidence', 'q_000001']),
    ]
    for label, args in cases:
        rust = json.loads(run([binary, '--db', db, '--json', 'studio'] + args, Path('.')))
        py = json.loads(run([sys.executable, ref, '--db', db] + args, root))
        print(f'{label} equal:', rust == py)
        if rust != py:
            a, b = json.dumps(rust, sort_keys=True), json.dumps(py, sort_keys=True)
            i = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))
            print('  diff at', i, a[max(0, i-120):i+280], '|', b[max(0, i-120):i+280])
