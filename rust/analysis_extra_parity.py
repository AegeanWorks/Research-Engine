import json, subprocess, sys
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
        if isinstance(rust, list) and isinstance(py, list):
            print('  counts:', len(rust), len(py))
            for a, b in zip(rust, py):
                if a != b:
                    print('  first diff:', json.dumps(a, sort_keys=True)[:250], '|', json.dumps(b, sort_keys=True)[:250])
                    break
        elif isinstance(rust, dict):
            for key in sorted(set(rust) | set(py)):
                if rust.get(key) != py.get(key):
                    print('  differs:', key, repr(rust.get(key))[:250], '|', repr(py.get(key))[:250])

compare('calibration', ['analysis', 'calibration', 'r_000001'])
compare('contradictions', ['analysis', 'contradictions', 'r_000001'])
compare('unlinked', ['analysis', 'contradictions', 'r_000001', '--unlinked'])
compare('matrix', ['analysis', 'matrix', 'r_000001'])
compare('keystone', ['analysis', 'keystone', 'r_000001'])
compare('expose', ['analysis', 'expose', 'c_000001'])
compare('correlation', ['analysis', 'correlation', 'c_000001'])
