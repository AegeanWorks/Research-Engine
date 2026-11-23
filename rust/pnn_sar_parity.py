import importlib, json, subprocess, sys
from pathlib import Path

binary = str(Path('target/x86_64-pc-windows-gnu/debug/research-engine.exe').resolve())
sys.path.insert(0, str(Path('..').resolve()))
sar = importlib.import_module('domains.pnn.sar')


def run(*args):
    p = subprocess.run([binary, '--json', 'pnn-sar', *map(str, args)],
                       capture_output=True, text=True, encoding='utf-8', timeout=180)
    if p.returncode != 0:
        raise RuntimeError(f'{args}: {p.stderr[:800]}')
    return json.loads(p.stdout)


def check(label, rust, py):
    print(f'{label} equal:', rust == py)
    if rust != py:
        print('  rust:', str(rust)[:900])
        print('  py:  ', str(py)[:900])


smiles_cases = [
    'CCO',
    'c1ccccc1',
    'CC(=O)Nc1ccc(O)cc1',
    'CN1C=NC2=C1C(=O)N(C(=O)N2C)C',
    'CC(C)CC1=CC=C(C=C1)C(C)C(=O)O',
]
for smiles in smiles_cases:
    atoms, adj = sar.parse_smiles_graph(smiles)
    py_graph = {'atoms': atoms, 'edges': sorted([min(u, v), max(u, v)] for u, vs in adj.items() for v in vs)}
    rust_graph = run('graph', smiles)
    rust_graph['edges'] = sorted([min(e), max(e)] for e in rust_graph['edges'])
    check(f'graph {smiles[:14]}', rust_graph, py_graph)

    py_blocks = sorted([sorted(b) for b in sar.find_biconnected_blocks(len(atoms), adj)])
    rust_blocks = sorted([sorted(b) for b in run('blocks', smiles)])
    check(f'blocks {smiles[:14]}', rust_blocks, py_blocks)

    rust_scaffold = run('scaffold', smiles)
    py_core, py_name, py_rgroups = sar.extract_scaffold(smiles)
    check(f'scaffold name {smiles[:14]}', rust_scaffold['scaffold_name'], py_name)
    check(f'r_groups {smiles[:14]}', rust_scaffold['r_groups'], py_rgroups)
    if rust_scaffold['core_smiles'] == py_core:
        check(f'core string {smiles[:14]}', True, True)
    else:
        # Serialization order depends on set iteration order; verify graph isomorphism.
        def canonical(core):
            graph = run('graph', core)
            atoms = graph['atoms']
            edges = set()
            for u, v in graph['edges']:
                edges.add((min(u, v), max(u, v)))
            neighbours = {i: [] for i in range(len(atoms))}
            for u, v in edges:
                neighbours[u].append(atoms[v])
                neighbours[v].append(atoms[u])
            return sorted((atoms[i], tuple(sorted(neighbours[i]))) for i in range(len(atoms)))
        check(f'core graph {smiles[:14]}', canonical(rust_scaffold['core_smiles']), canonical(py_core))
