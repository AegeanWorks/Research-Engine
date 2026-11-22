import json, math, subprocess, sys
from pathlib import Path

binary = str(Path('target/x86_64-pc-windows-gnu/debug/research-engine.exe').resolve())
sys.path.insert(0, str(Path('..').resolve()))
from dataclasses import asdict
from domains.pnn.compounds import Compound
from domains.pnn.screen import evaluate_compound, screen_compounds, summarize


def run(*args):
    p = subprocess.run([binary, '--json', 'pnn-screen', *map(str, args)],
                       capture_output=True, text=True, encoding='utf-8', timeout=180)
    if p.returncode != 0:
        raise RuntimeError(f'{args}: {p.stderr[:600]}')
    return json.loads(p.stdout)


def close(a, b):
    if isinstance(a, dict):
        return set(a) == set(b) and all(close(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(close(x, y) for x, y in zip(a, b))
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-12)
    return a == b


def check(label, rust, py):
    ok = close(rust, py)
    print(f'{label} equal:', ok)
    if not ok:
        print('  rust:', str(rust)[:700])
        print('  py:  ', str(py)[:700])


def compound(cid, mw, logp, tpsa, hbd, hba, rot, **extra):
    data = {'compound_id': cid, 'mw': mw, 'logp': logp, 'tpsa': tpsa,
            'hbd': hbd, 'hba': hba, 'rotatable_bonds': rot}
    data.update(extra)
    return data


compounds = [
    compound('C1', 345.5, 2.6, 58.0, 2, 5, 4, pka=8.2, charge='basic', logbb=-0.3,
             brain_plasma_ratio=0.45, oral_bioavailability=24.0,
             cyp3a4_inhibition=18.0, herg_liability=8.0, pnn_ec50_nm=42.0),
    compound('C2', 480.0, 4.2, 95.0, 5, 9, 9, pka=6.0, charge='acidic', logbb=-1.5,
             brain_plasma_ratio=0.05, oral_bioavailability=5.0,
             cyp3a4_inhibition=75.0, herg_liability=40.0, pnn_ec50_nm=1500.0),
    compound('C3', 300.0, 2.0, 60.0, 2, 5, 3),
    compound('C4', 410.0, 3.1, 68.0, 3, 6, 5, charge='neutral', logbb=-0.7,
             brain_plasma_ratio=0.2, oral_bioavailability=18.0),
]
json_compounds = json.dumps(compounds)

single = run('evaluate', '--compound', json.dumps(compounds[0]))
single.pop('failed_criteria', None)
single.pop('unknown_criteria', None)
check('evaluate', single, asdict(evaluate_compound(Compound(**compounds[0]))))

rank = run('rank', '--compounds', json_compounds)
for row in rank:
    row.pop('failed_criteria', None)
    row.pop('unknown_criteria', None)
py_rank = [asdict(r) for r in screen_compounds([Compound(**c) for c in compounds])]
check('rank', rank, py_rank)
check('summary', run('summary', '--compounds', json_compounds),
      summarize(screen_compounds([Compound(**c) for c in compounds])))
