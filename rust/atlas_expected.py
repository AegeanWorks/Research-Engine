"""Python reference for the Rust `atlas` CLI commands."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from domains.atlas.schema import coerce_muse_payload, merge_analyses, muse_json_schema

parser = argparse.ArgumentParser()
sub = parser.add_subparsers(dest='command', required=True)

p = sub.add_parser('coerce')
p.add_argument('--payload', required=True)
p.add_argument('--document-ref', default='')
p.add_argument('--source-page', type=int, default=0)
p.add_argument('--figure-id', default='')

p = sub.add_parser('merge')
p.add_argument('--analyses', required=True)

sub.add_parser('schema')

args = parser.parse_args()
if args.command == 'coerce':
    out = coerce_muse_payload(json.loads(args.payload), args.document_ref,
                              args.source_page, args.figure_id).to_dict()
elif args.command == 'merge':
    from domains.atlas.schema import VisualAnalysis
    parsed = [VisualAnalysis.from_dict(value) for value in json.loads(args.analyses)]
    out = merge_analyses(parsed).to_dict()
else:
    out = muse_json_schema()
print(json.dumps(out, indent=2, sort_keys=True))
