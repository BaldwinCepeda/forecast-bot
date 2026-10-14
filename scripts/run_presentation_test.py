"""Reproduce both test snapshots from the supplied Direct CSV and synthetic fixtures."""
import os
import sys
from pathlib import Path
from datetime import date
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root/'src'))
from demand_poc.cli import run_pipeline

inputs = root/'data/scenarios/presentation-test'
for name, roles, note in [
    ('baseline', 'roles_empty.csv', 'TEST BASELINE: 10 user-supplied Direct records + 10 synthetic Indirect records. No staffing estimates supplied. Zero estimated roles means demand is unknown.'),
    ('demo', 'roles_synthetic.csv', 'DEMONSTRATION DATA: 10 user-supplied Direct records + 10 synthetic Indirect records. ALL staffing quantities, skills, levels and role start dates are synthetic test assumptions, not business forecasts. Unmapped statuses receive zero confidence and are flagged.'),
]:
    output = root/'data/output/presentation-test'/name
    output.mkdir(parents=True, exist_ok=True)
    os.environ['DEMAND_DATABASE_PATH'] = str(output/'snapshot.sqlite')
    counts = run_pipeline(inputs/'direct.csv', inputs/'indirect_synthetic.csv', inputs/roles, date(2026,10,14), output, dataset_note=note)
    print(name, counts)
