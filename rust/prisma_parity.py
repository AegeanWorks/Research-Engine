import json, subprocess, sys, tempfile
from pathlib import Path

binary = str(Path('target/x86_64-pc-windows-gnu/debug/research-engine.exe').resolve())
sys.path.insert(0, str(Path('..').resolve()))
from engine.database import connect, initialize
from engine.researches import create_research
from engine.sources import add_source
from engine.screening import prisma_flow, set_screening


def run(*args):
    p = subprocess.run([binary, '--json', *map(str, args)], capture_output=True, text=True,
                       encoding='utf-8', timeout=180)
    if p.returncode != 0:
        raise RuntimeError(f'{args}: {p.stderr[:700]}')
    return json.loads(p.stdout)


with tempfile.TemporaryDirectory() as tmp:
    db = Path(tmp) / 'prisma.db'
    conn = connect(str(db))
    initialize(conn)
    rid = create_research(conn, 'Review').id
    ids = [add_source(conn, rid, f'Paper {i}', year=2020, doi=f'10.1/{i}') .id for i in range(6)]
    for source_id, status, reason in [
        (ids[0], 'screened_in', ''), (ids[1], 'screened_out', 'not_relevant'),
        (ids[2], 'included', ''), (ids[3], 'excluded', 'duplicate'),
        (ids[4], 'excluded', 'duplicate'),
    ]:
        set_screening(conn, source_id, status, reason)
    conn.commit()

    py = prisma_flow(conn, rid)
    rust = run('--db', str(db), 'source', 'prisma', '--research', rid)
    print('prisma scoped equal:', rust == py)
    if rust != py:
        print('  rust:', json.dumps(rust, sort_keys=True)[:600])
        print('  py:  ', json.dumps(py, sort_keys=True)[:600])

    py_all = prisma_flow(conn)
    rust_all = run('--db', str(db), 'source', 'prisma')
    print('prisma all equal:', rust_all == py_all)
    conn.close()
