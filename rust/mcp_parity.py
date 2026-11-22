import json, re, subprocess, sys, tempfile
from pathlib import Path

TS = re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00')

def normalize(value):
    return TS.sub('<TS>', json.dumps(value, sort_keys=True))

binary = str(Path('target/x86_64-pc-windows-gnu/debug/research-engine.exe').resolve())
root = Path('..').resolve()
helper = str(Path('mcp_expected.py').resolve())

def run(cmd, cwd):
    p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True,
                       encoding='utf-8', timeout=180)
    if p.returncode != 0:
        raise RuntimeError(f'{cmd}: {p.stderr[:700]}')
    return p.stdout

def compare(label, message, db_rust, db_py):
    rust = json.loads(run([binary, '--db', db_rust, '--json', 'mcp', json.dumps(message)], Path('.')))
    py = json.loads(run([sys.executable, helper, '--db', db_py, json.dumps(message)], root))
    print(f'{label} equal:', normalize(rust) == normalize(py))
    if normalize(rust) != normalize(py):
        a, b = normalize(rust), normalize(py)
        i = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))
        print('  diff at', i, a[max(0, i-120):i+280], '|', b[max(0, i-120):i+280])

with tempfile.TemporaryDirectory() as tmp:
    rdb, pdb = str(Path(tmp) / 'rust.db'), str(Path(tmp) / 'py.db')
    msgs = [
        ('initialize', {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize'}),
        ('ping', {'jsonrpc': '2.0', 'id': 2, 'method': 'ping'}),
        ('tools-list', {'jsonrpc': '2.0', 'id': 3, 'method': 'tools/list'}),
        ('resources-list', {'jsonrpc': '2.0', 'id': 4, 'method': 'resources/list'}),
        ('prompts-list', {'jsonrpc': '2.0', 'id': 5, 'method': 'prompts/list'}),
        ('resources-read', {'jsonrpc': '2.0', 'id': 6, 'method': 'resources/read',
                            'params': {'uri': 'lattice://stats'}}),
        ('tool-stats', {'jsonrpc': '2.0', 'id': 7, 'method': 'tools/call',
                        'params': {'name': 'stats', 'arguments': {}}}),
        ('tool-outline', {'jsonrpc': '2.0', 'id': 8, 'method': 'tools/call',
                          'params': {'name': 'outline', 'arguments': {'tokens': 400}}}),
        ('notification', {'jsonrpc': '2.0', 'method': 'notifications/initialized'}),
        ('unknown-method', {'jsonrpc': '2.0', 'id': 9, 'method': 'does/not/exist'}),
        ('tool-add-question', {'jsonrpc': '2.0', 'id': 10, 'method': 'tools/call',
                               'params': {'name': 'add_question', 'arguments': {'text': 'Does it work?'}}}),
    ]
    for label, message in msgs:
        compare(label, message, rdb, pdb)
