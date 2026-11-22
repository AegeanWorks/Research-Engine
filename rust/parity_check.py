import json, subprocess, sys
from pathlib import Path

db = sys.argv[1]
binary = str(Path('target/x86_64-pc-windows-gnu/debug/research-engine.exe').resolve())
root = Path('..').resolve()

def run(cmd, cwd):
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True,
                          check=True, timeout=120).stdout

rust = run([binary, '--db', db, '--json', 'search', 'quantum'], Path('.'))
py = run([sys.executable, '-m', 'engine', '--db', db, '--json', 'search', 'quantum'], root)
a, b = json.loads(rust), json.loads(py)
print('search equal:', a == b)
if a != b:
    for key in a:
        if a[key] != b.get(key):
            print(' differs:', key, repr(a[key])[:300], repr(b.get(key))[:300])

rust = run([binary, '--db', db, '--json', 'observation', 'list', 'c_000001'], Path('.'))
py = run([sys.executable, '-m', 'engine', '--db', db, '--json', 'observation', 'list', 'c_000001'], root)
a, b = json.loads(rust), json.loads(py)
for row in a + b:
    row.pop('at', None)
print('observation list equal (ignoring timestamps):', a == b)

rust = run([binary, '--db', db, '--json', 'check'], Path('.'))
py = run([sys.executable, '-m', 'engine', '--db', db, '--json', 'check'], root)
a, b = json.loads(rust), json.loads(py)
print('check findings equal:', a == b)
if a != b:
    ra = [(x['code'], x['subject']) for x in a]
    rb = [(x['code'], x['subject']) for x in b]
    print(' rust:', ra)
    print(' py:  ', rb)
