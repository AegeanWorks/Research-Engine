"""Python reference for the Rust `web` CLI command."""
import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from adapters.lattice.database import open_database
from adapters.lattice.repository import Repository
from studio.web import dispatch_web_request

parser = argparse.ArgumentParser()
parser.add_argument('--db', required=True)
parser.add_argument('method')
parser.add_argument('path')
parser.add_argument('--body', default=None)
args = parser.parse_args()
repo = Repository(open_database(args.db))
response = dispatch_web_request(repo, args.method, args.path, args.body)
print(json.dumps(asdict(response), indent=2, sort_keys=True))
