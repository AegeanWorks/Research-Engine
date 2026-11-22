"""Python reference for the Rust `lattice-snap` CLI commands."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from adapters.lattice.database import open_database
from adapters.lattice.repository import Repository
from adapters.lattice.snapshots import (collect_repository_records, export_graphml_string,
                                        export_cytoscape_data)
from adapters.lattice.synthesis import format_bibtex

parser = argparse.ArgumentParser()
parser.add_argument('--db', required=True)
parser.add_argument('command', choices=('records', 'bibtex', 'cytoscape', 'graphml'))
args = parser.parse_args()
repo = Repository(open_database(args.db))

if args.command == 'records':
    out = collect_repository_records(repo)
elif args.command == 'bibtex':
    out = {'text': format_bibtex(repo.search_literature(limit=100000)['papers'])}
elif args.command == 'cytoscape':
    out = export_cytoscape_data(repo)
else:
    out = {'text': export_graphml_string(repo)}

print(json.dumps(out, indent=2, sort_keys=True))
