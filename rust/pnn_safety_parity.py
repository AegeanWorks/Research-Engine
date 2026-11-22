import json, subprocess, sys
from pathlib import Path

binary = str(Path('target/x86_64-pc-windows-gnu/debug/research-engine.exe').resolve())
root = Path('..').resolve()
helper = str(Path('pnn_safety_expected.py').resolve())

tox = [
    {'compound_id': 'PNN-101', 'species': 'rat', 'study_type': 'subchronic',
     'duration_days': 90, 'noael_mg_kg': 50.0, 'loael_mg_kg': 150.0,
     'target_organ': 'liver', 'findings': 'reversible enzyme elevation'},
    {'compound_id': 'PNN-101', 'species': 'dog', 'study_type': 'subchronic',
     'duration_days': 90, 'noael_mg_kg': 30.0, 'loael_mg_kg': 100.0,
     'target_organ': 'none', 'findings': 'none'},
    {'compound_id': 'PNN-202', 'species': 'mouse', 'study_type': 'acute',
     'duration_days': 28, 'noael_mg_kg': 10.0, 'loael_mg_kg': None,
     'target_organ': 'kidney', 'findings': 'necrosis'},
]
pharm = {
    'PNN-101': {'herg_ic50_um': 30.0, 'free_cmax_um': 0.5, 'cyp3a4_inhibition_pct': 20.0,
                'ames_positive': False, 'micronucleus_positive': False,
                'respiratory_noael_mg_kg': 100.0, 'cns_noael_mg_kg': 80.0},
    'PNN-202': {'herg_ic50_um': 5.0, 'free_cmax_um': 1.0, 'cyp3a4_inhibition_pct': 60.0,
                'ames_positive': True, 'micronucleus_positive': False,
                'respiratory_noael_mg_kg': None, 'cns_noael_mg_kg': None},
}

rust = json.loads(subprocess.run(
    [binary, '--json', 'pnn-safety', '--tox', json.dumps(tox), '--pharm', json.dumps(pharm)],
    capture_output=True, text=True, encoding='utf-8', check=True, timeout=180).stdout)
import tempfile
with tempfile.TemporaryDirectory() as tmp:
    tox_file = Path(tmp) / 'tox.json'
    pharm_file = Path(tmp) / 'pharm.json'
    tox_file.write_text(json.dumps(tox), encoding='utf-8')
    pharm_file.write_text(json.dumps(pharm), encoding='utf-8')
    py_proc = subprocess.run(
        [sys.executable, helper, str(tox_file), str(pharm_file)],
        cwd=str(root), capture_output=True, text=True, encoding='utf-8', timeout=180)
    if py_proc.returncode != 0:
        raise RuntimeError(py_proc.stderr[:1000])
    py = json.loads(py_proc.stdout)
print('assessments equal:', rust['assessments'] == py['assessments'])
print('report equal:', rust['report'] == py['report'])
if rust['assessments'] != py['assessments']:
    for a, b in zip(rust['assessments'], py['assessments']):
        if a != b:
            print(' rust:', json.dumps(a, sort_keys=True)[:500])
            print(' py:  ', json.dumps(b, sort_keys=True)[:500])
            break
if rust['report'] != py['report']:
    a, b = rust['report'], py['report']
    i = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))
    print(' report diff at', i, a[max(0, i-120):i+260], '|', b[max(0, i-120):i+260])
