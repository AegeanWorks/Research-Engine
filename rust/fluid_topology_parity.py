import json, subprocess, sys
from pathlib import Path

binary = str(Path('target/x86_64-pc-windows-gnu/debug/research-engine.exe').resolve())
sys.path.insert(0, str(Path('..').resolve()))
from domains.fluid_universe.theory.topology import (
    direct_result, extensions, has_z3_factor, render_markdown, verdict,
)


def run(*args):
    p = subprocess.run([binary, '--json', 'fluid-topology', *args],
                       capture_output=True, text=True, encoding='utf-8', timeout=180)
    if p.returncode != 0:
        raise RuntimeError(f'{args}: {p.stderr[:600]}')
    return json.loads(p.stdout)


def check(label, rust, py):
    ok = rust == py
    print(f'{label} equal:', ok)
    if not ok:
        print('  rust:', str(rust)[:500])
        print('  py:  ', str(py)[:500])


if has_z3_factor():
    raise RuntimeError('unexpected Z3 factor in the Python reference')
check('direct', run('direct'), direct_result())
check('extensions', run('extensions'), extensions())
py_verdict = verdict()
check('verdict', run('verdict'), py_verdict)

payload = {'verdict': py_verdict, 'meta': {
    'config_sha256': 'abc123', 'git': {'commit': 'deadbeef', 'dirty': False},
}}
result = run('render', '--payload', json.dumps(payload))
check('render', result.pop('markdown'), render_markdown(payload))
check('render keys', result, {})
