import importlib, json, math, subprocess, sys
from dataclasses import asdict
from pathlib import Path

binary = str(Path('target/x86_64-pc-windows-gnu/debug/research-engine.exe').resolve())
sys.path.insert(0, str(Path('..').resolve()))
dyn = importlib.import_module('domains.pnn.dynamics')


def run(*args):
    p = subprocess.run([binary, '--json', 'pnn-dynamics', *map(str, args)],
                       capture_output=True, text=True, encoding='utf-8', timeout=180)
    if p.returncode != 0:
        raise RuntimeError(f'{args}: {p.stderr[:800]}')
    return json.loads(p.stdout)


def close(a, b):
    if isinstance(a, dict):
        return set(a) == set(b) and all(close(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(close(x, y) for x, y in zip(a, b))
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(float(a), float(b), rel_tol=1e-12, abs_tol=1e-12)
    return a == b


def check(label, rust, py):
    ok = close(rust, py)
    print(f'{label} equal:', ok)
    if not ok:
        print('  rust:', ascii(rust)[:1000])
        print('  py:  ', ascii(py)[:1000])


def point(t, lig, prot=None, contacts=None, dg=None, residues=None):
    return {'time_ns': t, 'ligand_rmsd': lig, 'protein_rmsd': prot,
            'contacts_count': contacts, 'mmgbsa_dg': dg,
            'residue_contacts': residues or {}}


for name, rows in [
    ('stable', [point(0.0, 1.1, 1.2, 4, -32.0, {'LYS201': True, 'ARG204': True}),
                point(1.0, 1.3, 1.3, 4, -33.0, {'LYS201': True, 'ARG204': True}),
                point(2.0, 1.2, 1.4, 5, -31.0, {'LYS201': True, 'ARG204': True}),
                point(3.0, 1.4, 1.3, 4, -34.0, {'LYS201': True, 'ARG204': True})]),
    ('partial', [point(0.0, 3.0, None, None, None),
                 point(1.0, 4.2, None, None, None),
                 point(2.0, 5.0, None, None, None)]),
]:
    py_points = [dyn.TrajectoryPoint(**row) for row in rows]
    py_analysis = dyn.analyze_trajectory(py_points)
    py_report = dyn.render_trajectory_report(py_analysis)
    result = run('analyze', '--points', json.dumps(rows))
    check(f'analysis {name}', json.loads(json.dumps(result.pop('analysis'))),
          json.loads(json.dumps(asdict(py_analysis))))
    check(f'report {name}', result.pop('report'), py_report)
    check(f'keys {name}', result, {})
