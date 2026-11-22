"""Python reference for the Rust `studio` CLI commands."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from adapters.lattice.database import open_database
from adapters.lattice.repository import Repository
from studio.api import get_evidence_matrix

parser = argparse.ArgumentParser()
parser.add_argument('--db', required=True)
sub = parser.add_subparsers(dest='command', required=True)

p = sub.add_parser('matrix')
p.add_argument('--questions', default='')

p = sub.add_parser('evidence')
p.add_argument('reference')

args = parser.parse_args()
repo = Repository(open_database(args.db))
if args.command == 'matrix':
    values = [q.strip() for q in args.questions.split(',') if q.strip()] or None
    out = get_evidence_matrix(repo, values)
else:
    out = repo.evidence(args.reference)
print(json.dumps(out, indent=2, sort_keys=True))
