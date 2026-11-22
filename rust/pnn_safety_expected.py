"""Python reference for the Rust `pnn-safety` CLI command."""
import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from domains.pnn.safety import SafetyPharm, ToxStudy, assess_safety, render_safety_report

tox_path, pharm_path = sys.argv[1:3]
studies = [ToxStudy(**row) for row in json.loads(Path(tox_path).read_text(encoding='utf-8'))]
pharm = {key: SafetyPharm(compound_id=key, **value) for key, value in
         json.loads(Path(pharm_path).read_text(encoding='utf-8')).items()}
assessments = assess_safety(studies, pharm)
print(json.dumps({
    'assessments': [asdict(a) for a in assessments],
    'report': render_safety_report(assessments, {}),
}, indent=2, sort_keys=True))
