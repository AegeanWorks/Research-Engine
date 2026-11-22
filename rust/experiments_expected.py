"""Python reference implementation of the Rust `experiment` CLI commands."""
import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.database import connect
from experiments import (add_intervention, add_metric, add_metric_definition, add_event,
                         list_interventions, list_metric_definitions, list_metrics, list_events,
                         analyze_baseline_vs_intervention, correlation_matrix,
                         analyze_multiple_metrics)

db, command, *args = sys.argv[1:]
conn = connect(db)
opt = lambda value: value if value else None

if command == 'intervention-add':
    research, name, start, projected, end, dosage, notes = args
    out = add_intervention(conn, research, name, start, opt(projected), opt(end), dosage, notes)
elif command == 'metricdef-add':
    research, name, description, unit = args
    out = add_metric_definition(conn, research, name, description, unit)
elif command == 'metric-add':
    research, metric, day, value, intervention, note = args
    out = add_metric(conn, research, metric, day, float(value), opt(intervention), note)
elif command == 'event-add':
    research, name, timestamp, severity, notes, intervention = args
    out = add_event(conn, research, name, timestamp, int(severity) if severity else None,
                    notes, opt(intervention))
elif command == 'list':
    research, kind = args
    fn = {'intervention': list_interventions, 'metricdef': list_metric_definitions,
          'event': list_events, 'metric': list_metrics}[kind]
    out = fn(conn, research)
elif command == 'analyze':
    research, metric, start, baseline_days, intervention_days = args
    out = analyze_baseline_vs_intervention(conn, research, metric, start,
                                           int(baseline_days), int(intervention_days))
elif command == 'correlation':
    research, metrics = args
    out = correlation_matrix(conn, research, [m for m in metrics.split(',') if m] or None)
elif command == 'multi':
    research, metrics, start, baseline_days, intervention_days = args
    out = analyze_multiple_metrics(conn, research, [m for m in metrics.split(',') if m],
                                   start, int(baseline_days), int(intervention_days))
else:
    raise SystemExit(f'unknown command {command}')

payload = [asdict(row) for row in out] if isinstance(out, list) else out
if hasattr(out, '__dataclass_fields__'):
    payload = asdict(out)
print(json.dumps(payload, indent=2, sort_keys=True))
