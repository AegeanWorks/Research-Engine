"""Python reference for the Rust `fluid-bridge` CLI commands."""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from domains.fluid_universe.theory.gaussian_bridge import (diffusivity, horizon,
                                                            pinney_coeffs, pinney_path)

parser = argparse.ArgumentParser()
sub = parser.add_subparsers(dest='command', required=True)
p = sub.add_parser('diffusivity')
p.add_argument('hbar', type=float)
p.add_argument('mass', type=float)
p = sub.add_parser('horizon')
p.add_argument('omega', type=float)
p = sub.add_parser('coeffs')
for name in ('s0', 'st', 'horizon_t', 'omega', 'hbar', 'mass'):
    p.add_argument(name, type=float)
p = sub.add_parser('path')
p.add_argument('--coeffs', required=True)
p.add_argument('--times', required=True)
p.add_argument('--omega', type=float, required=True)
args = parser.parse_args()

if args.command == 'diffusivity':
    out = {'value': diffusivity(args.hbar, args.mass)}
elif args.command == 'horizon':
    out = {'value': horizon(args.omega)}
elif args.command == 'coeffs':
    out = pinney_coeffs(args.s0, args.st, args.horizon_t, args.omega, args.hbar, args.mass)
else:
    coeffs = json.loads(args.coeffs)
    times = np.array(json.loads(args.times), dtype=float)
    out = [float(v) for v in pinney_path(coeffs, times, args.omega)]
print(json.dumps(out, indent=2, sort_keys=True))
