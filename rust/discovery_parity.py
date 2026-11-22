import json, subprocess, sys, tempfile
from pathlib import Path

binary = str(Path('target/x86_64-pc-windows-gnu/debug/research-engine.exe').resolve())
root = Path('..').resolve()
helper = str(Path('discovery_expected.py').resolve())

def run(cmd, cwd):
    p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True,
                       encoding='utf-8', timeout=180)
    if p.returncode != 0:
        raise RuntimeError(f'{cmd}: {p.stderr[:700]}')
    return p.stdout

def compare(label, args, db_rust=None, db_py=None):
    rust_cmd = [binary, '--json', 'discovery'] + args
    if db_rust:
        rust_cmd = [binary, '--db', db_rust, '--json', 'discovery'] + args
    py_cmd = [sys.executable, helper, '--db', db_py or ':memory:'] + args
    rust = json.loads(run(rust_cmd, Path('.')))
    py = json.loads(run(py_cmd, root))
    print(f'{label} equal:', rust == py)
    if rust != py:
        a, b = json.dumps(rust, sort_keys=True), json.dumps(py, sort_keys=True)
        i = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))
        print('  diff at', i, a[max(0, i-100):i+220], '|', b[max(0, i-100):i+220])

compare('providers', ['providers'])
compare('offline', ['offline', 'sleep', '--limit', '5'])
compare('crossref-authors', ['crossref-authors',
    '[{"family":"Lovelace","given":"Ada"},{"literal":"Grace Hopper"}]'])
compare('crossref-year', ['crossref-year', '{"issued":{"date-parts":[[2024,3,1]]}}'])
compare('inverted-abstract', ['inverted-abstract',
    '{"quantum":[0,3],"effects":[1],"water":[4],"observed":[2]}'])

with tempfile.TemporaryDirectory() as tmp:
    rdb, pdb = str(Path(tmp) / 'rust.db'), str(Path(tmp) / 'py.db')
    compare('discover', ['discover', 'sleep', '--source', 'offline', '--limit', '5'], rdb, pdb)
