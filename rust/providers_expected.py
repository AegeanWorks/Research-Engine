"""Python reference for the Rust `providers` CLI commands."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from adapters.lattice.discovery import (ArxivProvider, CrossrefProvider, EuropePmcProvider,
                                        OpenAlexProvider)

source, query, limit, payload_file, url_out = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4], sys.argv[5]
payload = Path(payload_file).read_text(encoding='utf-8')
captured = {}

def fetcher(url, timeout):
    captured['url'] = url
    return payload

providers = {
    'arxiv': ArxivProvider, 'crossref': CrossrefProvider,
    'openalex': OpenAlexProvider, 'europepmc': EuropePmcProvider,
}
candidates = providers[source](fetcher=fetcher).search(query, limit)
Path(url_out).write_text(json.dumps({'url': captured['url']}), encoding='utf-8')
print(json.dumps([c.to_dict() for c in candidates], indent=2, sort_keys=True))
