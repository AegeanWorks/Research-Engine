"""Python reference for the Rust `client` CLI commands."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from studio.client import LatticeClient

parser = argparse.ArgumentParser()
parser.add_argument('--db', required=True)
parser.add_argument('--read-only', action='store_true')
sub = parser.add_subparsers(dest='command', required=True)

sub.add_parser('tool-schemas')
sub.add_parser('resource-schemas')
sub.add_parser('prompt-schemas')
p = sub.add_parser('call')
p.add_argument('name')
p.add_argument('--arguments', default='{}')
p.add_argument('--kwargs', default='{}')
p = sub.add_parser('read-resource')
p.add_argument('uri')

args = parser.parse_args()
with LatticeClient(args.db, read_only=args.read_only) as client:
    if args.command == 'tool-schemas':
        out = client.tool_schemas()
    elif args.command == 'resource-schemas':
        out = client.resource_schemas()
    elif args.command == 'prompt-schemas':
        out = client.prompt_schemas()
    elif args.command == 'call':
        out = client.call_tool(args.name, json.loads(args.arguments), **json.loads(args.kwargs))
    else:
        out = client.read_resource(args.uri)
print(json.dumps(out, indent=2, sort_keys=True))
