import json, subprocess, sys
from dataclasses import asdict
from pathlib import Path

binary = str(Path('target/x86_64-pc-windows-gnu/debug/research-engine.exe').resolve())
sys.path.insert(0, str(Path('..').resolve()))
from domains.pnn.docking import parse_docking_scores
from domains.pnn.rank import build_shortlist


def run(*args):
    p = subprocess.run([binary, '--json', 'pnn-rank', *map(str, args)],
                       capture_output=True, text=True, encoding='utf-8', timeout=180)
    if p.returncode != 0:
        raise RuntimeError(f'{args}: {p.stderr[:700]}')
    return json.loads(p.stdout)


def check(label, rust, py):
    print(f'{label} equal:', rust == py)
    if rust != py:
        print('  rust:', str(rust)[:900])
        print('  py:  ', str(py)[:900])


rows = [
    {'Compound ID': 'C1', 'Target': 'TP53', 'Vina': '-9.2', 'Glide': '-6.1',
     'mmGBSA': '-45.3', 'RMSD': '1.2', 'HBonds': '3', 'key interactions': 'H-bonds with SER'},
    {'id': 'C1', 'receptor': 'MDM2', 'vinaaffinity': '-8.0', 'glidescore': '-5.0',
     'dG': '-40.0', 'rmsdligand': '2.0', 'hbondcount': '2'},
    {'compound': 'C2', 'targetname': 'TP53', 'affinity': '-7.5', 'mmgbsadg': '-35.0'},
    {'compound_id': 'C3', 'target': 'EGFR', 'vina': '-6.0', 'rmsd': '4.5'},
]
scores = parse_docking_scores(rows, 'input')
screen = {
    'C1': {'name': 'Compound A', 'smiles': 'CCO', 'tier': 'A', 'score': '0.9'},
    'C2': {'name': 'Compound B', 'smiles': 'CCN', 'tier': 'B', 'score': '0.6'},
    'C3': {'name': 'Compound C', 'smiles': 'CCC', 'tier': 'C', 'score': '0.2'},
}

for tier in ('A', 'B'):
    py_rows, py_summary = build_shortlist(scores, screen, min_tier=tier)
    py = {'rows': [asdict(r) for r in py_rows], 'summary': py_summary}
    args = ['build', '--rows', json.dumps(rows), '--screen', json.dumps(screen), '--min-tier', tier]
    check(f'shortlist tier {tier}', run(*args), py)

py_rows, py_summary = build_shortlist(scores, None, min_tier='B', max_rmsd=2.0, min_vina=-8.5)
check('shortlist no screen + filters',
      run('build', '--rows', json.dumps(rows), '--max-rmsd=2.0', '--min-vina=-8.5'),
      {'rows': [asdict(r) for r in py_rows], 'summary': py_summary})
