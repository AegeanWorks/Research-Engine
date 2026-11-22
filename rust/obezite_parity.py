import json, subprocess, sys, tempfile
from pathlib import Path

binary = str(Path('target/x86_64-pc-windows-gnu/debug/research-engine.exe').resolve())
root = Path('..').resolve()
ref = str(Path('obezite_expected.py').resolve())

def run(cmd, cwd):
    p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True,
                       encoding='utf-8', timeout=180)
    if p.returncode != 0:
        raise RuntimeError(f'{cmd}: {p.stderr[:700]}')
    return p.stdout

def check(label, rust, py):
    print(f'{label} equal:', rust == py)
    if rust != py:
        print('  rust:', json.dumps(rust, sort_keys=True)[:500])
        print('  py:  ', json.dumps(py, sort_keys=True)[:500])

text = ('Bulgur 74, Nature. 2020;578(7795):444-448, PMID: 12345, doi:10.1038/s41586-020-1, '
        ' Metabolism 1999;48(4):472-476, 120 ve 90, 42')
check('atiflar', json.loads(run([binary, '--json', 'obezite', 'atiflar', text], Path('.'))),
      json.loads(run([sys.executable, ref, 'atiflar', text], root)))

with tempfile.TemporaryDirectory() as tmp:
    base = Path(tmp)
    chunks = [base / 'chunk1.md', base / 'chunk2.md']
    chunks[0].write_text('# defter\n| **1** | birinci | x |\n| **2** | ikinci | y |\n', encoding='utf-8')
    chunks[1].write_text('# defter\n| **3** | üçüncü | z |\n', encoding='utf-8')
    retracted = base / 'CURUTULMUS.md'
    retracted.write_text('| **1** | eski birinci | a |\n| **2** | eski ikinci | b |\n| **4** | korunur | c |\n',
                         encoding='utf-8')
    outputs = {}
    for name, runner in [('rust', binary), ('py', sys.executable)]:
        out = base / name
        out.mkdir()
        if name == 'rust':
            command = [runner, '--json', 'obezite', 'dedupe', '--chunks', ','.join(str(c) for c in chunks),
                       '--retracted', str(retracted), '--archive', str(out / 'archive.md'),
                       '--updated', str(out / 'updated.md'), '--stamp', '2026-01-01']
            result = json.loads(run(command, Path('.')))
        else:
            command = [runner, ref, 'dedupe', '--chunks', ','.join(str(c) for c in chunks),
                       '--retracted', str(retracted), '--archive', str(out / 'archive.md'),
                       '--updated', str(out / 'updated.md'), '--stamp', '2026-01-01']
            result = json.loads(run(command, root))
        result.pop('archive', None)
        result.pop('updated', None)
        outputs[name] = (result, (out / 'archive.md').read_text(encoding='utf-8'),
                         (out / 'updated.md').read_text(encoding='utf-8'))
    check('dedupe counts', outputs['rust'][0], outputs['py'][0])
    check('dedupe archive', outputs['rust'][1], outputs['py'][1])
    check('dedupe updated', outputs['rust'][2], outputs['py'][2])
