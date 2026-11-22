import json, subprocess, sys
from pathlib import Path

binary = str(Path('target/x86_64-pc-windows-gnu/debug/research-engine.exe').resolve())

def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', timeout=180)
    if p.returncode != 0:
        raise RuntimeError(f'{cmd}: {p.stderr[:600]}')
    return p.stdout

def compare(label, args):
    rust = json.loads(run([binary, '--json', 'meta'] + args))
    py = json.loads(run([sys.executable, 'meta_expected.py'] + args))
    print(f'{label} equal:', rust == py)
    if rust != py:
        print('  rust:', json.dumps(rust, sort_keys=True)[:600])
        print('  py:  ', json.dumps(py, sort_keys=True)[:600])

compare('study-ci', ['study-ci', 's1', 'Study One', '0.5', '0.1', '0.9'])
compare('study-groups', ['study-groups', 's2', 'Study Two', '30', '10.0', '2.0', '28', '8.5', '2.1'])

studies = json.dumps([
    {'id': 's1', 'label': 'Study One', 'effect_size': 0.5, 'ci_lower': 0.1, 'ci_upper': 0.9},
    {'id': 's2', 'label': 'Study Two', 'effect_size': 0.8, 'ci_lower': 0.3, 'ci_upper': 1.3},
    {'id': 's3', 'label': 'Study Three', 'effect_size': 0.2, 'ci_lower': -0.2, 'ci_upper': 0.6},
])
compare('analyze-random', ['analyze', '--studies', studies, '--model', 'random'])
compare('analyze-fixed', ['analyze', '--studies', studies, '--model', 'fixed'])
compare('forest', ['forest', '--studies', studies, '--model', 'random', '--width', '40'])
