import json, subprocess, sys
from pathlib import Path

binary = str(Path('target/x86_64-pc-windows-gnu/debug/research-engine.exe').resolve())
sys.path.insert(0, str(Path('..').resolve()))
from domains.fluid_universe.phenomenology import predictions as pred


def run(*args):
    p = subprocess.run([binary, '--json', 'predictions', *map(str, args)],
                       capture_output=True, text=True, encoding='utf-8', timeout=180)
    if p.returncode != 0:
        raise RuntimeError(f'{args}: {p.stderr[:600]}')
    return json.loads(p.stdout)


def check(label, rust, py):
    print(f'{label} equal:', rust == py)
    if rust != py:
        print('  rust:', str(rust)[:700])
        print('  py:  ', str(py)[:700])


check('candidates', run('candidates'), pred.CANDIDATES)

py_payload = pred.run_prediction_audit(write=False)
check('verdict', run('verdict'), py_payload['verdict'])

result = run('render', '--payload', json.dumps(py_payload))
check('render', result.pop('markdown'), pred.render_markdown(py_payload))
check('render keys', result, {})
