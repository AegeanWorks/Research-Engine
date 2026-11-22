"""Python reference for the Rust `discovery` CLI commands."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from adapters.lattice.database import open_database
from adapters.lattice.discovery import (DiscoveryService, OfflineCorpusProvider, default_registry,
                                        _dedupe_candidates, _reconstruct_inverted_abstract,
                                        _format_crossref_authors, _extract_crossref_year)
from adapters.lattice.repository import Repository

parser = argparse.ArgumentParser()
parser.add_argument('--db', default=':memory:')
sub = parser.add_subparsers(dest='command', required=True)

sub.add_parser('providers')
p = sub.add_parser('offline')
p.add_argument('query')
p.add_argument('--limit', type=int, default=10)
p = sub.add_parser('discover')
p.add_argument('query')
p.add_argument('--source', default='offline')
p.add_argument('--limit', type=int, default=10)
p.add_argument('--no-ingest', action='store_true')
p = sub.add_parser('crossref-authors')
p.add_argument('authors')
p = sub.add_parser('crossref-year')
p.add_argument('item')
p = sub.add_parser('inverted-abstract')
p.add_argument('inverted')

args = parser.parse_args()
if args.command == 'providers':
    out = default_registry().names()
elif args.command == 'offline':
    out = [c.to_dict() for c in OfflineCorpusProvider().search(args.query, args.limit)]
elif args.command == 'discover':
    out = DiscoveryService(Repository(open_database(args.db))).discover(
        args.query, source=args.source, limit=args.limit, ingest=not args.no_ingest)
elif args.command == 'crossref-authors':
    out = {'value': _format_crossref_authors(json.loads(args.authors))}
elif args.command == 'crossref-year':
    out = {'value': _extract_crossref_year(json.loads(args.item))}
else:
    out = {'value': _reconstruct_inverted_abstract(json.loads(args.inverted))}
print(json.dumps(out, indent=2, sort_keys=True))
