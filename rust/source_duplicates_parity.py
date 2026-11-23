import json, subprocess, sys, tempfile
from pathlib import Path

binary = str(Path('target/x86_64-pc-windows-gnu/debug/research-engine.exe').resolve())
sys.path.insert(0, str(Path('..').resolve()))
from engine.database import connect, initialize
from engine.duplicates import duplicate_sources, normalize_doi, normalize_title
from engine.researches import create_research
from engine.sources import add_source


def run(*args):
    p = subprocess.run([binary, '--json', *args], capture_output=True, text=True,
                       encoding='utf-8', timeout=180)
    if p.returncode != 0:
        raise RuntimeError(f'{args}: {p.stderr[:700]}')
    return json.loads(p.stdout)


def check(label, rust, py):
    print(f'{label} equal:', rust == py)
    if rust != py:
        print('  rust:', json.dumps(rust, sort_keys=True)[:800])
        print('  py:  ', json.dumps(py, sort_keys=True)[:800])


conn = connect(':memory:')
initialize(conn)
rid = create_research(conn, 'Duplicate study').id
add_source(conn, rid, 'Sleep and Memory', year=2020, doi='https://doi.org/10.1/abc')
add_source(conn, rid, 'Sleep and Memory', year=2020, doi='10.1/abc')
add_source(conn, rid, 'Café Effects', year=2019, doi='10.2/one')
add_source(conn, rid, 'Cafe Effects', year=2019, doi='10.2/two')
add_source(conn, rid, 'Unique Paper', year=2021, doi='10.3/unique')

py_result = duplicate_sources(conn, None, 20)
rows = conn.execute('SELECT id, research_id, title, year, doi, url, status FROM source').fetchall()
sources = [{'id': r['id'], 'research_id': r['research_id'], 'title': r['title'],
            'year': r['year'], 'doi': r['doi'], 'url': r['url'], 'status': r['status']}
           for r in rows]
rust_result = run('run', 'execute', 'corpus.duplicates', '--input',
                  json.dumps({'sources': sources, 'limit': 20}))
check('duplicates', rust_result, py_result)
