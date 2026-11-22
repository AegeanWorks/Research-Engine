import json, subprocess, sys
from pathlib import Path

binary = str(Path('target/x86_64-pc-windows-gnu/debug/research-engine.exe').resolve())
root = Path('..').resolve()
helper = str(Path('atlas_expected.py').resolve())

def run(cmd, cwd):
    p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True,
                       encoding='utf-8', timeout=180)
    if p.returncode != 0:
        raise RuntimeError(f'{cmd}: {p.stderr[:700]}')
    return p.stdout

def compare(label, args):
    rust = json.loads(run([binary, '--json', 'atlas'] + args, Path('.')))
    py = json.loads(run([sys.executable, helper] + args, root))
    print(f'{label} equal:', rust == py)
    if rust != py:
        a, b = json.dumps(rust, sort_keys=True), json.dumps(py, sort_keys=True)
        i = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))
        print('  diff at', i, a[max(0, i-120):i+280], '|', b[max(0, i-120):i+280])

payload = {
    'entities': [
        {'id': 'e1', 'name': 'Hippocampus', 'category': 'anatomical-structure',
         'box': [100, 200, 400, 500], 'confidence': 0.9, 'description': 'Memory structure'},
        {'id': 'e2', 'name': 'Memory', 'category': 'function', 'confidence': 0.8},
    ],
    'relationships': [
        {'source_id': 'e1', 'target_id': 'e2', 'rel_type': 'participates-in', 'confidence': 0.7},
    ],
}
compare('coerce', ['coerce', '--payload', json.dumps(payload), '--document-ref', 'doc-1',
                   '--source-page', '3', '--figure-id', 'fig-1'])
compare('schema', ['schema'])

a1 = {'entities': [
        {'id': 'e1', 'name': 'Hippocampus', 'category': 'anatomical-structure',
         'bbox': {'x_min': 0.1, 'y_min': 0.2, 'x_max': 0.4, 'y_max': 0.5},
         'description': 'Memory structure', 'confidence': 0.9},
        {'id': 'e2', 'name': 'Memory', 'category': 'function', 'confidence': 0.8},
      ],
      'relationships': [{'source_id': 'e1', 'target_id': 'e2',
                         'rel_type': 'participates-in', 'confidence': 0.7}],
      'document_ref': 'doc-1'}
a2 = {'entities': [
        {'id': 'e1', 'name': 'hippocampus ', 'category': 'anatomical-structure',
         'description': 'A longer description of the hippocampus structure',
         'source_evidence': 'p. 12', 'confidence': 0.95},
        {'id': 'e3', 'name': 'Cortex', 'category': 'anatomical-structure', 'confidence': 0.6},
      ],
      'relationships': [{'source_id': 'e1', 'target_id': 'e3',
                         'rel_type': 'projects-to', 'confidence': 0.5}],
      'document_ref': 'doc-1'}
compare('merge', ['merge', '--analyses', json.dumps([a1, a2])])
