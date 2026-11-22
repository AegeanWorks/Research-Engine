"""Python reference for the Rust `mcp` CLI command."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from adapters.lattice.database import open_database
from adapters.lattice.repository import Repository
from studio.mcp import handle_message

parser = argparse.ArgumentParser()
parser.add_argument('--db', required=True)
parser.add_argument('message')
args = parser.parse_args()
repo = Repository(open_database(args.db))
result = handle_message(repo, json.loads(args.message))
print(json.dumps(result, indent=2, sort_keys=True))
