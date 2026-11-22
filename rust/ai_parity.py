import json, shutil, subprocess, sys, tempfile
from pathlib import Path

binary = str(Path('target/x86_64-pc-windows-gnu/debug/research-engine.exe').resolve())
root = Path('..').resolve()

def run(cmd, cwd):
    p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True,
                       encoding='utf-8', timeout=180)
    if p.returncode != 0:
        raise RuntimeError(f'{cmd}: {p.stderr[:500]}')
    return p.stdout

def compare(label, args, ignore=()):
    results = []
    for name, exe, cwd in [('rust', [binary], Path('.')),
                           ('py', [sys.executable, '-m', 'engine'], root)]:
        db = str(Path(tmp) / f'{label}-{name}.db')
        shutil.copyfile(base, db)
        results.append(json.loads(run(exe + ['--db', db, '--json'] + args, cwd)))
    a, b = results
    for key in ignore:
        if isinstance(a, dict): a.pop(key, None)
        if isinstance(b, dict): b.pop(key, None)
    print(f'{label} equal:', a == b)
    if a != b:
        if isinstance(a, dict):
            for key in sorted(set(a) | set(b)):
                if a.get(key) != b.get(key):
                    print('  differs:', key, repr(a.get(key))[:250], '|', repr(b.get(key))[:250])
        else:
            print('  rust:', json.dumps(a, sort_keys=True)[:300])
            print('  py:  ', json.dumps(b, sort_keys=True)[:300])

with tempfile.TemporaryDirectory() as tmp:
    base = str(Path(tmp) / 'base.db')
    run([sys.executable, '-m', 'engine', '--db', base, 'init'], root)
    run([sys.executable, '-m', 'engine', '--db', base, 'research', 'add', 'AI Program'], root)
    run([sys.executable, '-m', 'engine', '--db', base, 'source', 'add', 'r_000001', '--title', 'Paper', '--year', '2024'], root)
    run([sys.executable, '-m', 'engine', '--db', base, 'question', 'add', 'r_000001', 'Does it work?'], root)

    prompt = Path(tmp) / 'prompt.txt'
    output = Path(tmp) / 'output.txt'
    prompt.write_text('Extract the claim')
    output.write_text('The effect is real')

    cited = '[{"source_id": "s_000001", "locator": "p. 3"}]'
    run([sys.executable, '-m', 'engine', '--db', base, 'ai', 'sweep', 'r_000001', '--kind', 'extraction',
         '--model', 'local:test', '--prompt-file', str(prompt), '--output-file', str(output),
         '--cited', cited], root)
    run([sys.executable, '-m', 'engine', '--db', base, 'ai', 'sweep', 'r_000001', '--kind', 'idea',
         '--model', 'local:test', '--prompt-file', str(prompt), '--output-file', str(output)], root)
    run([sys.executable, '-m', 'engine', '--db', base, 'claim', 'add', 'r_000001', '--kind', 'empirical',
         '--source', 's_000001', '--text', 'The effect is real', '--quote', 'effect is real',
         '--locator', 'p. 3'], root)
    compare('sweep', ['ai', 'sweep', 'r_000001', '--kind', 'extraction', '--model', 'local:test',
                      '--prompt-file', str(prompt), '--output-file', str(output), '--cited', cited],
            ignore=('created_at',))
    compare('artifacts', ['ai', 'artifacts', '--research', 'r_000001'], ignore=('created_at',))
    compare('extract', ['ai', 'extract', '--artifact', 'a_000001', '--text', 'The effect is real',
                        '--kind', 'empirical', '--source', 's_000001', '--quote', 'effect is real',
                        '--locator', 'p. 3', '--question', 'q_000001'], ignore=('created_at', 'updated_at'))
    compare('idea', ['ai', 'idea', '--artifact', 'a_000002', '--statement', 'It replicates',
                     '--criterion', 'no effect'], ignore=('created_at',))
    compare('propose', ['ai', 'propose-test', '--artifact', 'a_000001', '--template', 'constant-probe',
                        '--name', 'probe', '--claim', 'c_000001'], ignore=('created_at',))
    compare('draft', ['ai', 'draft', 'r_000001'])

    # diff: identical exports, then a changed graph
    old = Path(tmp) / 'old.jsonl'
    new = Path(tmp) / 'new.jsonl'
    run([binary, '--db', base, 'export', str(old)], Path('.'))
    run([binary, '--db', base, 'export', str(new)], Path('.'))
    run([sys.executable, '-m', 'engine', '--db', base, 'claim', 'add', 'r_000001', '--kind', 'derived',
         '--text', 'New evidence', '--basis', 'b'], root)
    run([binary, '--db', base, 'export', str(new)], Path('.'))
    r = json.loads(run([binary, '--db', base, '--json', 'diff', str(old), str(new)], Path('.')))
    diff_proc = subprocess.run([sys.executable, '-m', 'engine', '--db', base, '--json', 'diff', str(old), str(new)],
                               cwd=str(root), capture_output=True, text=True, encoding='utf-8', timeout=180)
    p = json.loads(diff_proc.stdout)
    print('diff equal:', r == p)
