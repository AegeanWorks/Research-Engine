"""Python reference for the Rust `pnn-docking` CLI commands."""
import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from domains.pnn.docking import (
    aggregate_best, filter_scores, normalize_scores, parse_docking_scores,
)

command = sys.argv[1]
rows = json.loads(Path(sys.argv[2]).read_text(encoding='utf-8'))
source = sys.argv[3] if command == 'parse' else 'input'

scores = parse_docking_scores(rows, source=source)
if command == 'parse':
    out = [asdict(s) for s in scores]
else:
    max_rmsd = float(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3] else None
    min_vina = float(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[4] else None
    kept, dropped = filter_scores(scores, max_rmsd=max_rmsd, min_vina=min_vina)
    ranks = normalize_scores(kept)
    aggregated = aggregate_best(ranks)
    out = {
        'scores': [asdict(s) for s in scores],
        'kept': len(kept),
        'dropped': dropped,
        'ranks': [asdict(r) for r in ranks],
        'aggregated': {k: asdict(v) for k, v in aggregated.items()},
    }
print(json.dumps(out, indent=2, sort_keys=True))
