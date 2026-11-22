import json, shutil, subprocess, sys, tempfile
from pathlib import Path

binary = str(Path('target/x86_64-pc-windows-gnu/debug/research-engine.exe').resolve())
root = Path('..').resolve()

def run(cmd, cwd):
    p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True,
                       encoding='utf-8', timeout=180)
    if p.returncode != 0:
        raise RuntimeError(f'{cmd}: {p.stderr[:600]}')
    return p.stdout

def close(a, b, tol=1e-12):
    if isinstance(a, float) and isinstance(b, float):
        return abs(a - b) <= tol
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(close(a[k], b[k], tol) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(close(x, y, tol) for x, y in zip(a, b))
    return a == b

def compare(label, args, rust_args=None, ignore=()):
    results = []
    for name, cmd, cwd in [
        ('rust', [binary, '--db', dbs['rust'], '--json'] + (rust_args or args), Path('.')),
        ('py', [sys.executable, str(Path('experiments_expected.py').resolve()), dbs['py']] + args, root),
    ]:
        results.append(json.loads(run(cmd, cwd)))
    a, b = results
    for key in ignore:
        if isinstance(a, dict): a.pop(key, None)
        if isinstance(b, dict): b.pop(key, None)
    if isinstance(a, list):
        for row in a + b:
            for key in ignore: row.pop(key, None)
    print(f'{label} equal (float tol 1e-12):', close(a, b))
    if not close(a, b):
        if isinstance(a, dict):
            for key in sorted(set(a) | set(b)):
                if a.get(key) != b.get(key):
                    print('  differs:', key, repr(a.get(key))[:300], '|', repr(b.get(key))[:300])
        else:
            for x, y in zip(a, b):
                if x != y:
                    print('  first diff:', json.dumps(x, sort_keys=True)[:300], '|', json.dumps(y, sort_keys=True)[:300])
                    break

with tempfile.TemporaryDirectory() as tmp:
    base = str(Path(tmp) / 'base.db')
    run([sys.executable, '-m', 'engine', '--db', base, 'init'], root)
    run([sys.executable, '-m', 'engine', '--db', base, 'research', 'add', 'N1 Program'], root)
    dbs = {'rust': str(Path(tmp) / 'rust.db'), 'py': str(Path(tmp) / 'py.db')}
    for db in dbs.values(): shutil.copyfile(base, db)

    compare('intervention-add', ['intervention-add', 'r_000001', 'dose A', '2026-01-01',
                                 '', '2026-02-14', '10mg', 'notes'],
            rust_args=['experiment', 'intervention-add', 'r_000001', 'dose A', '2026-01-01',
                       '--end', '2026-02-14', '--dosage', '10mg', '--notes', 'notes'],
            ignore=('created_at',))
    for metric in ['m1', 'm2']:
        compare(f'metricdef-{metric}', ['metricdef-add', 'r_000001', metric, 'desc', 'mg'],
                rust_args=['experiment', 'metric-def-add', 'r_000001', metric,
                           '--description', 'desc', '--unit', 'mg'], ignore=('created_at',))
    for day in range(18, 32):
        d = f'2026-01-{day:02d}'
        compare(f'metric-{d}', ['metric-add', 'r_000001', 'm1', d, str(day / 10), '', ''],
                rust_args=['experiment', 'metric-add', 'r_000001', 'm1', d, str(day / 10)],
                ignore=('created_at',))
    for day in range(1, 15):
        d = f'2026-02-{day:02d}'
        compare(f'metric-{d}', ['metric-add', 'r_000001', 'm1', d, str(2 + day / 10), '', ''],
                rust_args=['experiment', 'metric-add', 'r_000001', 'm1', d, str(2 + day / 10)],
                ignore=('created_at',))
    compare('event-add', ['event-add', 'r_000001', 'adverse', '2026-02-05T09:00:00+00:00',
                          '2', '', 'iv_000001'],
            rust_args=['experiment', 'event-add', 'r_000001', 'adverse',
                       '2026-02-05T09:00:00+00:00', '--severity', '2', '--intervention', 'iv_000001'],
            ignore=('created_at',))
    for kind in ['intervention', 'metricdef', 'metric', 'event']:
        compare(f'list-{kind}', ['list', 'r_000001', kind],
                rust_args=['experiment', 'list', 'r_000001', '--kind', kind], ignore=('created_at',))
    compare('analyze', ['analyze', 'r_000001', 'm1', '2026-02-01', '14', '14'],
            rust_args=['experiment', 'analyze', 'r_000001', 'm1', '2026-02-01',
                       '--baseline-days', '14', '--intervention-days', '14'])
    compare('correlation', ['correlation', 'r_000001', 'm1'],
            rust_args=['experiment', 'correlation', 'r_000001', '--metrics', 'm1'])
    compare('multi', ['multi', 'r_000001', 'm1', '2026-02-01', '14', '14'],
            rust_args=['experiment', 'multi', 'r_000001', '--metrics', 'm1', '2026-02-01',
                       '--baseline-days', '14', '--intervention-days', '14'])
