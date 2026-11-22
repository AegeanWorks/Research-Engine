"""Python reference for the Rust `meta` CLI commands."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from adapters.lattice.meta import (compute_meta_analysis, render_forest_ascii,
                                   study_from_confidence_interval, study_from_two_groups)

parser = argparse.ArgumentParser()
sub = parser.add_subparsers(dest='command', required=True)

p = sub.add_parser('study-ci')
for name in ('id', 'label'):
    p.add_argument(name)
for name in ('effect', 'lower', 'upper'):
    p.add_argument(name, type=float)
p.add_argument('--study-type', default='General Study')

p = sub.add_parser('study-groups')
for name in ('id', 'label'):
    p.add_argument(name)
p.add_argument('n1', type=int)
for name in ('m1', 'sd1'):
    p.add_argument(name, type=float)
p.add_argument('n2', type=int)
for name in ('m2', 'sd2'):
    p.add_argument(name, type=float)
p.add_argument('--study-type', default='Randomized Controlled Trial')

p = sub.add_parser('analyze')
p.add_argument('--studies', required=True)
p.add_argument('--model', default='random')

p = sub.add_parser('forest')
p.add_argument('--studies', required=True)
p.add_argument('--model', default='random')
p.add_argument('--width', type=int, default=40)

args = parser.parse_args()
if args.command == 'study-ci':
    out = study_from_confidence_interval(args.id, args.label, args.effect,
                                         args.lower, args.upper, args.study_type).to_dict()
elif args.command == 'study-groups':
    out = study_from_two_groups(args.id, args.label, args.n1, args.m1, args.sd1,
                                args.n2, args.m2, args.sd2, args.study_type).to_dict()
else:
    studies = json.loads(args.studies)
    result = compute_meta_analysis(studies, model=args.model)
    out = {'text': render_forest_ascii(result, args.width)} if args.command == 'forest' else result.to_dict()
print(json.dumps(out, indent=2, sort_keys=True))
