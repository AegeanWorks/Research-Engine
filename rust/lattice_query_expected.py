"""Python reference for the Rust `lattice-query` CLI commands."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from adapters.lattice.database import open_database
from adapters.lattice.repository import Repository
from adapters.lattice.analysis import detect_contradictions
from adapters.lattice.context import (build_context_pack, compact_search, outline)

parser = argparse.ArgumentParser()
parser.add_argument('--db', required=True)
sub = parser.add_subparsers(dest='command', required=True)

p = sub.add_parser('outline')
p.add_argument('--tokens', type=int, default=400)

sub.add_parser('contradictions')

p = sub.add_parser('compact-search')
p.add_argument('query')
p.add_argument('--limit', type=int, default=20)
p.add_argument('--tokens', type=int, default=800)

p = sub.add_parser('context-pack')
p.add_argument('--targets', default='')
p.add_argument('--max-tokens', type=int, default=2000)
p.add_argument('--format', default='markdown')

args = parser.parse_args()
repo = Repository(open_database(args.db))

if args.command == 'outline':
    out = outline(repo, args.tokens)
elif args.command == 'contradictions':
    out = [pair.to_dict() for pair in detect_contradictions(repo, auto_link=False)]
elif args.command == 'compact-search':
    out = compact_search(repo.search(args.query, args.limit), args.tokens)
else:
    targets = [t for t in args.targets.split(',') if t] or None
    out = build_context_pack(repo, targets=targets, max_tokens=args.max_tokens,
                             format=args.format).to_dict()

print(json.dumps(out, indent=2, sort_keys=True))
