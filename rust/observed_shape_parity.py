import json, subprocess, sys
from pathlib import Path

binary = str(Path('target/x86_64-pc-windows-gnu/debug/research-engine.exe').resolve())
sys.path.insert(0, str(Path('..').resolve()))
from domains.fluid_universe.theory import water_observed_shape as wos


def run(*args):
    p = subprocess.run([binary, '--json', 'observed-shape', *map(str, args)],
                       capture_output=True, text=True, encoding='utf-8', timeout=180)
    if p.returncode != 0:
        raise RuntimeError(f'{args}: {p.stderr[:600]}')
    return json.loads(p.stdout)


def check(label, rust, py):
    print(f'{label} equal:', rust == py)
    if rust != py:
        print('  rust:', str(rust)[:700])
        print('  py:  ', str(py)[:700])


for span in (45.0, 90.0):
    check(f'width {span}', run('width', f'--span-k={span}'), wos.observed_width_change_ev(span))
check('evidence', run('evidence'), wos.shape_evidence())
check('scales', run('scales'), wos.observed_scales())
for temp in (299.15, 210.0, 298.0):
    check(f'side widths {temp}', run('side-widths', f'--temperature-k={temp}'),
          wos.jou_freeman_side_widths(temp))
