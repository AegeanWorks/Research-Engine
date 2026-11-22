import json, subprocess, sys
from pathlib import Path

db = sys.argv[1]
binary = str(Path('target/x86_64-pc-windows-gnu/debug/research-engine.exe').resolve())
root = Path('..').resolve()

def run(cmd, cwd):
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True,
                          check=True, timeout=180).stdout

for args in (['analysis', 'stats', 'c_000001', '--baseline', 'baseline', '--treatment', 'treatment'],
             ['analysis', 'trend', 'c_000001', '--group', 'baseline']):
    rust = json.loads(run([binary, '--db', db, '--json'] + args, Path('.')))
    # Python CLI emits the result dataclass as JSON directly.
    py = json.loads(run([sys.executable, '-m', 'engine', '--db', db, '--json'] + args, root))
    label = args[1]
    print(f'{label} equal:', rust == py)
    if rust != py:
        for key in sorted(set(rust) | set(py)):
            if rust.get(key) != py.get(key):
                print('  differs:', key, repr(rust.get(key))[:220], '|', repr(py.get(key))[:220])
