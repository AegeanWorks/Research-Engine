import json, subprocess, sys
from pathlib import Path

binary = str(Path('target/x86_64-pc-windows-gnu/debug/research-engine.exe').resolve())
sys.path.insert(0, str(Path('..').resolve()))
from dataclasses import asdict
from domains.pnn.compounds import Compound
from domains.pnn.curation import curate, deduplicate, prepare_candidates


def run(*args):
    p = subprocess.run([binary, '--json', 'pnn-curation', *map(str, args)],
                       capture_output=True, text=True, encoding='utf-8', timeout=180)
    if p.returncode != 0:
        raise RuntimeError(f'{args}: {p.stderr[:700]}')
    return json.loads(p.stdout)


def strip(result):
    result = dict(result)
    result.pop('failed_criteria', None)
    result.pop('unknown_criteria', None)
    return result


def normalize_candidate(candidate):
    candidate = dict(candidate)
    if 'result' in candidate:
        candidate['result'] = strip(candidate['result'])
    return candidate


def normalize(payload):
    if isinstance(payload, dict):
        out = {k: normalize(v) for k, v in payload.items()}
        if 'candidates' in out:
            out['candidates'] = [normalize_candidate(c) for c in out['candidates']]
        return out
    if isinstance(payload, list):
        return [normalize_candidate(c) if isinstance(c, dict) and 'compound' in c else normalize(c)
                for c in payload]
    return payload


def eq(a, b):
    if isinstance(a, dict) and isinstance(b, dict):
        return set(a) == set(b) and all(eq(a[k], b[k]) for k in a)
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(eq(x, y) for x, y in zip(a, b))
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return float(a) == float(b)
    return a == b


def check(label, rust, py):
    rust = normalize(rust)
    ok = eq(rust, py)
    print(f'{label} equal:', ok)
    if not ok:
        print('  rust:', str(rust)[:900])
        print('  py:  ', str(py)[:900])


def compound(cid, mw, logp, tpsa, hbd, hba, rot, smiles='', name='', **extra):
    data = {'compound_id': cid, 'mw': mw, 'logp': logp, 'tpsa': tpsa,
            'hbd': hbd, 'hba': hba, 'rotatable_bonds': rot,
            'name': name, 'smiles': smiles, 'pka': None, 'charge': '',
            'logbb': None, 'brain_plasma_ratio': None, 'oral_bioavailability': None,
            'cyp3a4_inhibition': None, 'herg_liability': None, 'pnn_ec50_nm': None}
    data.update(extra)
    return data


lib_a = [
    compound('C1', 345.5, 2.6, 58.0, 2, 5, 4, 'CCO', 'Compound A', pka=8.2, charge='basic'),
    compound('C2', 300.0, 2.0, 60.0, 2, 5, 3, 'CCN', 'Compound B'),
    compound('C3', 410.0, 3.1, 68.0, 3, 6, 5, '', 'no smiles', charge='neutral'),
]
lib_b = [
    compound('C1', 350.0, 2.7, 59.0, 2, 5, 4, 'CCO', ''),
    compound('C4', 480.0, 4.2, 95.0, 5, 9, 9, 'CCCC', 'Compound D', herg_liability=40.0),
]

inputs = [{'source': 'libA', 'compounds': lib_a}, {'source': 'libB', 'compounds': lib_b}]
py_prepared = prepare_candidates([(source, [Compound(**d) for d in compounds])
                                  for source, compounds in [('libA', lib_a), ('libB', lib_b)]])
check('prepare', run('prepare', '--inputs', json.dumps(inputs)), [asdict(c) for c in py_prepared])

prepared_json = run('prepare', '--inputs', json.dumps(inputs))
py_dupes, py_stats = deduplicate(py_prepared)
check('dedupe', run('dedupe', '--candidates', json.dumps(prepared_json)),
      {'candidates': [asdict(c) for c in py_dupes], 'stats': py_stats})

for kwargs in [{}, {'min_tier': 'A', 'per_bin': 1, 'bin_width': 0.25, 'max_compounds': 2}]:
    args = ['curate', '--candidates', json.dumps(prepared_json),
            '--min-tier', kwargs.get('min_tier', 'B'),
            '--per-bin', kwargs.get('per_bin', 25),
            f'--bin-width={kwargs.get("bin_width", 0.1)}']
    if 'max_compounds' in kwargs:
        args.append('--max-compounds')
        args.append(str(kwargs['max_compounds']))
    py_kept, py_summary = curate(py_prepared, **kwargs)
    check(f'curate {kwargs}', run(*args),
          {'candidates': [asdict(c) for c in py_kept], 'summary': py_summary})
