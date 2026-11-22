"""Python reference for the Rust `lattice` pure-function CLI."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from adapters.lattice.models import (normalize_text, normalize_tags, derive_tags,
                                     normalize_study_type, infer_study_type, paper_id)
from adapters.lattice.ingest import parse_bibtex, parse_ris, parse_csv, parse_csl_json

command, *args = sys.argv[1:]
if command == 'normalize':
    out = {'value': normalize_text(args[0])}
elif command == 'tags':
    out = {'value': normalize_tags(args[0])}
elif command == 'derive-tags':
    out = {'value': derive_tags(args[0], args[1] if len(args) > 1 else '',
                                int(args[2]) if len(args) > 2 else 6)}
elif command == 'study-type':
    out = {'value': normalize_study_type(args[0])}
elif command == 'infer-study':
    out = {'value': infer_study_type(args[0], args[1] if len(args) > 1 else '')}
elif command == 'paper-id':
    out = {'value': paper_id(args[0], args[1] if len(args) > 1 else '',
                             args[2] if len(args) > 2 else '')}
elif command == 'parse-bibtex':
    out = parse_bibtex(args[0])
elif command == 'parse-ris':
    out = parse_ris(args[0])
elif command == 'parse-csv':
    out = parse_csv(args[0])
elif command == 'parse-csl':
    out = parse_csl_json(args[0])
else:
    raise SystemExit(f'unknown command {command}')
print(json.dumps(out, indent=2, sort_keys=True))
