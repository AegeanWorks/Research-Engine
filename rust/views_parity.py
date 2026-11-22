import json, subprocess, sys, tempfile
from pathlib import Path

db = sys.argv[1]
binary = str(Path('target/x86_64-pc-windows-gnu/debug/research-engine.exe').resolve())
root = Path('..').resolve()

def run(cmd, cwd):
    p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=180)
    if p.returncode != 0:
        raise RuntimeError(f'{cmd}: {p.stderr[:400]}')
    return p.stdout

def compare(label, args):
    rust = json.loads(run([binary, '--db', db, '--json'] + args, Path('.')))
    py = json.loads(run([sys.executable, '-m', 'engine', '--db', db, '--json'] + args, root))
    print(f'{label} equal:', rust == py)
    if rust != py:
        for key in sorted(set(rust) | set(py)):
            if rust.get(key) != py.get(key):
                print('  differs:', key, repr(rust.get(key))[:300], '|', repr(py.get(key))[:300])

compare('outline', ['outline', 'r_000001'])
compare('brief', ['brief', 'r_000001'])
compare('claim context', ['claim', 'context', 'c_000001'])

with tempfile.TemporaryDirectory() as tmp:
    rp = str(Path(tmp) / 'report.md')
    rust = json.loads(run([binary, '--db', db, '--json', 'report', 'r_000001', '--out', rp], Path('.')))
    py = json.loads(run([sys.executable, '-m', 'engine', '--db', db, '--json', 'report', 'r_000001', '--out', rp + '.py'], root))
    for key in ('content_sha256', 'graph_sha256', 'report_sha256'):
        print(f'{key} equal:', rust.get(key) == py.get(key), rust.get(key, '')[:12], py.get(key, '')[:12])
    check = json.loads(run([binary, '--db', db, '--json', 'report', 'r_000001', '--check', rp], Path('.')))
    pycheck = json.loads(run([sys.executable, '-m', 'engine', '--db', db, '--json', 'report', 'r_000001', '--check', rp], root))
    print('rust report --check clean:', check.get('clean'), 'drift:', check.get('drift'))
    print('python report --check clean:', pycheck.get('clean'), 'drift:', pycheck.get('drift'))

    export_path = str(Path(tmp) / 'graph.jsonl')
    rcounts = json.loads(run([binary, '--db', db, '--json', 'export', export_path], Path('.')))
    py_export = str(Path(tmp) / 'graph.py.jsonl')
    pcounts = json.loads(run([sys.executable, '-m', 'engine', '--db', db, '--json', 'export', py_export], root))
    print('export counts equal:', rcounts == pcounts)
    print('export bytes equal:', Path(export_path).read_bytes() == Path(py_export).read_bytes())
    rverify = json.loads(run([binary, '--db', db, '--json', 'export', export_path, '--check'], Path('.')))
    pyverify = json.loads(run([sys.executable, '-m', 'engine', '--db', db, '--json', 'export', export_path, '--check'], root))
    print('export verify equal:', rverify == pyverify)
