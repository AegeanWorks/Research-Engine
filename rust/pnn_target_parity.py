import importlib, json, subprocess, sys
from dataclasses import asdict
from pathlib import Path

binary = str(Path('target/x86_64-pc-windows-gnu/debug/research-engine.exe').resolve())
sys.path.insert(0, str(Path('..').resolve()))
target = importlib.import_module('domains.pnn.target')


def run(*args):
    p = subprocess.run([binary, '--json', 'pnn-target', *map(str, args)],
                       capture_output=True, text=True, encoding='utf-8', timeout=180)
    if p.returncode != 0:
        raise RuntimeError(f'{args}: {p.stderr[:700]}')
    return json.loads(p.stdout)


def check(label, rust, py):
    print(f'{label} equal:', rust == py)
    if rust != py:
        print('  rust:', str(rust)[:800])
        print('  py:  ', str(py)[:800])


py_profiles = json.loads(json.dumps([asdict(p) for p in target.list_targets()]))
check('list', run('list'), py_profiles)
for target_id in ('PTPsigma', 'LAR', 'NgR1', 'ADAMTS4'):
    rust = run('show', target_id)
    profile = target.get_target(target_id)
    # Rust exposes tuples as JSON arrays; Python dataclass uses tuples.
    check(f'show {target_id}', rust,
          json.loads(json.dumps(asdict(profile))))

for target_id in ('PTPsigma', 'MMP9'):
    profile = target.get_target(target_id)
    py_config = target.generate_vina_config(profile)
    result = run('config', target_id)
    check(f'config {target_id}', result.pop('config'), py_config)
    check(f'config keys {target_id}', result, {})
