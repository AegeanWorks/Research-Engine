"""Python reference for the Rust `lattice-repo` CLI commands."""
import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from adapters.lattice.database import open_database
from adapters.lattice.repository import Repository

parser = argparse.ArgumentParser()
parser.add_argument('--db', required=True)
sub = parser.add_subparsers(dest='command', required=True)

p = sub.add_parser('paper-add')
p.add_argument('--title', required=True)
for name in ('authors', 'year', 'venue', 'doi', 'arxiv', 'url', 'abstract-text', 'tags', 'study-type'):
    p.add_argument('--' + name, default='')

p = sub.add_parser('claim-add')
p.add_argument('paper')
p.add_argument('--text', required=True)
p.add_argument('--quote', required=True)
p.add_argument('--locator', default='')
p.add_argument('--stance', default='mentions')
p.add_argument('--confidence', type=float, default=0.5)

p = sub.add_parser('question-add')
p.add_argument('text')

p = sub.add_parser('edge-add')
p.add_argument('src')
p.add_argument('dst')
p.add_argument('--kind', required=True)
p.add_argument('--note', default='')

p = sub.add_parser('get')
p.add_argument('reference')

p = sub.add_parser('search')
p.add_argument('query')
p.add_argument('--limit', type=int, default=20)

sub.add_parser('stats')

args = parser.parse_args()
repo = Repository(open_database(args.db))

if args.command == 'paper-add':
    metadata = {
        'kind': 'paper', 'title': args.title, 'authors': args.authors, 'year': args.year,
        'venue': args.venue, 'doi': args.doi, 'arxiv': args.arxiv, 'url': args.url,
        'abstract': args.abstract_text, 'tags': args.tags, 'study_type': args.study_type,
    }
    paper, created = repo.add_paper(metadata)
    out = {'paper': asdict(paper), 'created': created}
elif args.command == 'claim-add':
    out = asdict(repo.add_claim(args.paper, args.text, args.quote, args.locator,
                                args.stance, args.confidence))
elif args.command == 'question-add':
    out = asdict(repo.add_question(args.text))
elif args.command == 'edge-add':
    out = asdict(repo.add_edge(args.src, args.dst, args.kind, args.note))
elif args.command == 'get':
    out = repo.get(args.reference)
elif args.command == 'search':
    out = repo.search(args.query, args.limit)
else:
    out = repo.stats()

print(json.dumps(out, indent=2, sort_keys=True))
