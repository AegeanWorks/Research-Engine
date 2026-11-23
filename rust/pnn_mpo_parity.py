import importlib, json, math, subprocess, sys
from dataclasses import asdict
from pathlib import Path

binary = str(Path('target/x86_64-pc-windows-gnu/debug/research-engine.exe').resolve())
sys.path.insert(0, str(Path('..').resolve()))
mpo = importlib.import_module('domains.pnn.mpo')


def run(*args):
    p = subprocess.run([binary, '--json', 'pnn-mpo', *map(str, args)],
                       capture_output=True, text=True, encoding='utf-8', timeout=180)
    if p.returncode != 0:
        raise RuntimeError(f'{args}: {p.stderr[:700]}')
    return json.loads(p.stdout)


def check(label, rust, py):
    print(f'{label} equal:', rust == py)
    if rust != py:
        print('  rust:', str(rust)[:800])
        print('  py:  ', str(py)[:800])


for val, low, high, inc in [(0.0, 0.0, 1.0, True), (0.5, 0.0, 1.0, True),
                            (0.5, 0.0, 1.0, False), (2.0, 1.0, 1.0, True)]:
    args = ['ramp', val, low, high]
    if not inc:
        args.append('--increasing=false')
    check(f'ramp {val} {low} {high} {inc}', run(*args),
          {'value': mpo._ramp_desirability(val, low, high, inc)})

for mw, logp, tpsa, hbd in [(345.5, 2.6, 58.0, 2), (480.0, 4.2, 95.0, 5)]:
    check(f'score {mw}', run('score', mw, logp, tpsa, hbd),
          {'value': mpo.calculate_cns_mpo(mw, logp, tpsa, hbd)})

profiles = [
    {'compound_id': 'C1', 'name': 'Compound A', 'mw': 345.5, 'logp': 2.6, 'tpsa': 58.0,
     'hbd': 2, 'pka': 8.2, 'ec50_nm': 42.0, 'brain_kp': 0.45, 'oral_f_pct': 24.0,
     'selectivity_index': 60.0},
    {'compound_id': 'C2', 'name': 'Compound B', 'mw': 480.0, 'logp': 4.2, 'tpsa': 95.0,
     'hbd': 5, 'pka': 9.4, 'ec50_nm': 400.0, 'brain_kp': 0.12, 'oral_f_pct': 8.0,
     'selectivity_index': 10.0},
]
py_profiles = [mpo.profile_candidate(**p) for p in profiles]
for profile in profiles:
    check(f'profile {profile["compound_id"]}',
          run('profile', '--compound', json.dumps(profile)), asdict(mpo.profile_candidate(**profile)))

result = run('report', '--profiles', json.dumps([asdict(p) for p in py_profiles]))
check('report', result.pop('markdown'), mpo.render_mpo_report(py_profiles))
check('report keys', result, {})
check('rows', run('rows', '--profiles', json.dumps([asdict(p) for p in py_profiles])),
      [p.as_row() for p in py_profiles])
