import json, subprocess, sys, tempfile
from pathlib import Path

binary = str(Path('target/x86_64-pc-windows-gnu/debug/research-engine.exe').resolve())
root = Path('..').resolve()
helper = str(Path('providers_expected.py').resolve())

def run(cmd, cwd):
    p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True,
                       encoding='utf-8', timeout=180)
    if p.returncode != 0:
        raise RuntimeError(f'{cmd}: {p.stderr[:700]}')
    return p.stdout

arxiv_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
 <entry><id>http://arxiv.org/abs/2401.01234v1</id><title>Sleep and Memory</title>
 <summary>Slow wave sleep supports memory.</summary><published>2024-01-02T00:00:00Z</published>
 <arxiv:doi>10.1/arxiv</arxiv:doi>
 <author><name>Ada Lovelace</name></author><author><name>Alan Turing</name></author></entry>
</feed>'''

crossref_json = json.dumps({'message': {'items': [
    {'title': ['Quantum Effects in Water'], 'author': [{'given': 'Ada', 'family': 'Lovelace'}],
     'issued': {'date-parts': [[2024, 3, 1]]}, 'container-title': ['Nature'],
     'abstract': '<p>Quantum effects observed.</p>', 'subject': ['physics'],
     'DOI': '10.1/crossref', 'URL': 'https://doi.org/10.1/crossref'},
]}})

openalex_json = json.dumps({'results': [
    {'title': 'Transformer Scaling Laws', 'doi': 'https://doi.org/10.1/openalex',
     'authorships': [{'author': {'display_name': 'Mei Lin'}}], 'publication_year': 2024,
     'primary_location': {'source': {'display_name': 'ICML'}},
     'abstract_inverted_index': {'Transformer': [0], 'scaling': [1], 'laws': [2]},
     'keywords': [{'display_name': 'transformer'}], 'id': 'https://openalex.org/W1'},
]})

europepmc_json = json.dumps({'resultList': {'result': [
    {'title': 'Sleep deprivation and memory', 'abstractText': '<p>No effect found.</p>',
     'id': '12345', 'keywordList': {'keyword': ['sleep', 'memory']},
     'authorString': 'Sato H, Nair P', 'pubYear': '2024', 'journalTitle': 'Sleep',
     'doi': '10.1/epmc'},
]}})

fixtures = {'arxiv': arxiv_xml, 'crossref': crossref_json,
            'openalex': openalex_json, 'europepmc': europepmc_json}

with tempfile.TemporaryDirectory() as tmp:
    for source, payload in fixtures.items():
        path = Path(tmp) / f'{source}.txt'
        path.write_text(payload, encoding='utf-8')
        url_file = Path(tmp) / f'{source}-url.json'
        py = json.loads(run([sys.executable, helper, source, 'sleep', '5', str(path), str(url_file)], root))
        rust = json.loads(run([binary, '--json', 'providers', 'parse', source,
                               '--payload-file', str(path), '--limit', '5'], Path('.')))
        py_url = json.loads(url_file.read_text(encoding='utf-8'))['url']
        rust_url = json.loads(run([binary, '--json', 'providers', 'url', source, 'sleep', '--limit', '5'], Path('.')))['url']
        print(f'{source} candidates equal:', rust == py)
        print(f'{source} url equal:', rust_url == py_url)
        if rust != py:
            print('  rust:', json.dumps(rust, sort_keys=True)[:500])
            print('  py:  ', json.dumps(py, sort_keys=True)[:500])
        if rust_url != py_url:
            print('  rust url:', rust_url)
            print('  py url:  ', py_url)
