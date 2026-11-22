import json, subprocess, sys, tempfile
from pathlib import Path

binary = str(Path('target/x86_64-pc-windows-gnu/debug/research-engine.exe').resolve())
sys.path.insert(0, str(Path('..').resolve()))
from domains.pnn.reports import write_csv, write_json, write_text


def check(label, rust, py):
    ok = rust == py
    print(f'{label} equal:', ok)
    if not ok:
        print('  rust:', repr(rust)[:500])
        print('  py:  ', repr(py)[:500])


with tempfile.TemporaryDirectory() as tmp:
    base = Path(tmp)
    fields = ['compound_id', 'name', 'note', 'score', 'flag', 'empty']

    rows = [
        {'compound_id': 'C1', 'name': 'Plain', 'note': 'has, comma', 'score': 0.985, 'flag': True, 'empty': None},
        {'compound_id': 'C2', 'name': 'A "quoted" name', 'note': 'line1\nline2', 'score': 1.0, 'flag': False, 'empty': ''},
    ]
    py_csv = base / 'py.csv'
    write_csv(py_csv, fields, rows)
    rust_csv = base / 'rust.csv'
    subprocess.run([binary, '--json', 'pnn-reports', 'csv', '--path', str(rust_csv),
                    '--fieldnames', json.dumps(fields), '--rows', json.dumps(rows)],
                   capture_output=True, text=True, timeout=180, check=True)
    check('csv', rust_csv.read_bytes(), py_csv.read_bytes())

    report = {'z': 1.25, 'a': {'nested': [1, 2, 3]}, 'count': 7, 'ok': True, 'none': None}
    py_json = base / 'py.json'
    write_json(py_json, report)
    rust_json = base / 'rust.json'
    subprocess.run([binary, '--json', 'pnn-reports', 'json', '--path', str(rust_json),
                    '--report', json.dumps(report)],
                   capture_output=True, text=True, timeout=180, check=True)
    check('json', rust_json.read_bytes(), py_json.read_bytes())

    text = 'line one\nline two\n'
    py_text = base / 'py.txt'
    write_text(py_text, text)
    rust_text = base / 'rust.txt'
    subprocess.run([binary, '--json', 'pnn-reports', 'text', '--path', str(rust_text),
                    '--text', text], capture_output=True, text=True, timeout=180, check=True)
    check('text', rust_text.read_bytes(), py_text.read_bytes())

    nested = base / 'deep' / 'report.csv'
    write_csv(nested, fields, rows)
    check('nested directories', nested.is_file(), True)
