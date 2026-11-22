"""Python reference for the Rust `pnn-rules` CLI commands."""
import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from domains.pnn.compounds import Compound
from domains.pnn.rules import evaluate, weight

command = sys.argv[1]
if command == 'evaluate':
    compound = Compound(**json.loads(Path(sys.argv[2]).read_text(encoding='utf-8')))
    out = [asdict(row) for row in evaluate(compound)]
else:
    out = {'value': weight(sys.argv[2])}
print(json.dumps(out, indent=2, sort_keys=True))
