import json, subprocess, sys
from pathlib import Path

binary = str(Path('target/x86_64-pc-windows-gnu/debug/research-engine.exe').resolve())
root = Path('..').resolve()
helper = str(Path('fluid_bridge_expected.py').resolve())

def run(cmd, cwd):
    p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True,
                       encoding='utf-8', timeout=180)
    if p.returncode != 0:
        raise RuntimeError(f'{cmd}: {p.stderr[:700]}')
    return p.stdout

def close(a, b, tol=1e-12):
    if isinstance(a, float) and isinstance(b, float):
        return abs(a - b) <= tol
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(close(a[k], b[k], tol) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(close(x, y, tol) for x, y in zip(a, b))
    return a == b

def compare(label, args):
    rust = json.loads(run([binary, '--json', 'fluid-bridge'] + args, Path('.')))
    py = json.loads(run([sys.executable, helper] + args, root))
    print(f'{label} equal:', close(rust, py))
    if not close(rust, py):
        print('  rust:', json.dumps(rust, sort_keys=True)[:400])
        print('  py:  ', json.dumps(py, sort_keys=True)[:400])

compare('diffusivity', ['diffusivity', '1.0', '2.0'])
compare('horizon', ['horizon', '1.0'])
coeffs_args = ['coeffs', '1.2', '1.0', '0.7853981633974483', '1.0', '1.0', '1.0']
compare('coeffs', coeffs_args)
coeffs = json.loads(run([sys.executable, helper] + coeffs_args, root))
times = [0.0, 0.2, 0.4, 0.6, 0.7853981633974483]
compare('path', ['path', '--coeffs', json.dumps(coeffs[0]), '--times', json.dumps(times), '--omega', '1.0'])
