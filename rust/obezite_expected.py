"""Python reference for the Rust `obezite` CLI commands."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from domains.obezite.atif import atiflar
from domains.obezite.dedup import deduplicate

parser = argparse.ArgumentParser()
sub = parser.add_subparsers(dest='command', required=True)
p = sub.add_parser('atiflar')
p.add_argument('text')
p = sub.add_parser('dedupe')
p.add_argument('--chunks', required=True)
p.add_argument('--retracted', required=True)
p.add_argument('--archive', required=True)
p.add_argument('--updated', required=True)
p.add_argument('--stamp', default='')
args = parser.parse_args()

if args.command == 'atiflar':
    out = atiflar(args.text)
else:
    out = deduplicate([Path(p.strip()) for p in args.chunks.split(',') if p.strip()],
                      Path(args.retracted), Path(args.archive), Path(args.updated),
                      stamp=args.stamp or None)
print(json.dumps(out, indent=2, sort_keys=True))
