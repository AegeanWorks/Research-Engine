import json, subprocess, sys
from pathlib import Path

binary = str(Path('target/x86_64-pc-windows-gnu/debug/research-engine.exe').resolve())
root = Path('..').resolve()

def run(cmd, cwd):
    p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True,
                       encoding='utf-8', timeout=180)
    if p.returncode != 0:
        raise RuntimeError(f'{cmd}: {p.stderr[:600]}')
    return p.stdout

def compare(label, args, py_args=None):
    rust = json.loads(run([binary, '--json', 'lattice'] + args, Path('.')))
    py = json.loads(run([sys.executable, str(Path('lattice_expected.py').resolve())] + (py_args or args), root))
    print(f'{label} equal:', rust == py)
    if rust != py:
        print('  rust:', json.dumps(rust, sort_keys=True)[:400])
        print('  py:  ', json.dumps(py, sort_keys=True)[:400])

compare('normalize', ['normalize', 'Fluid   Universe—101!'])
compare('tags', ['tags', 'Physics; physics, AI ; ML'])
compare('derive-tags', ['derive-tags', 'Quantum Field Simulation',
                        '--abstract-text', 'A computational simulation of neural networks', '--limit', '5'],
        py_args=['derive-tags', 'Quantum Field Simulation', 'A computational simulation of neural networks', '5'])
compare('study-type', ['study-type', 'RCT'])
compare('infer-study', ['infer-study', 'A meta-analysis of deep learning',
                        '--abstract-text', 'We review computational transformer models'],
        py_args=['infer-study', 'A meta-analysis of deep learning', 'We review computational transformer models'])
compare('paper-id', ['paper-id', 'Fluid Universe', '--doi', '10.1/fluid'],
        py_args=['paper-id', 'Fluid Universe', '10.1/fluid', ''])
compare('paper-id-title', ['paper-id', 'Fluid Universe'])

bib = '''@article{key,
  title = {Quantum Effects in Water},
  author = {Ada Lovelace and Alan Turing},
  journal = {Nature},
  year = {2024},
  doi = {10.1/qw},
  keywords = {quantum, water},
  abstract = {A computational simulation of fluid dynamics}
}'''
compare('parse-bibtex', ['parse-bibtex', bib])

ris = '''TY  - JOUR
TI  - Quantum Effects in Water
AU  - Lovelace, Ada
AU  - Turing, Alan
JO  - Nature
PY  - 2024
DO  - 10.1/qw
KW  - quantum
ER  - '''
compare('parse-ris', ['parse-ris', ris])

csv = 'title,authors,year,doi,tags,study\nQuantum Effects,Ada,2024,10.1/qw,quantum,computational\n'
compare('parse-csv', ['parse-csv', csv])

csl = json.dumps([{
    'title': 'Quantum Effects in Water',
    'author': [{'family': 'Lovelace', 'given': 'Ada'}, {'literal': 'Alan Turing'}],
    'issued': {'date-parts': [[2024, 3, 1]]},
    'container-title': 'Nature',
    'DOI': '10.1/qw',
    'URL': 'https://arxiv.org/abs/2401.01234',
    'keyword': ['quantum', 'water'],
    'type': 'article-journal',
}])
compare('parse-csl', ['parse-csl', csl])
