# Presentation test, 14 October 2026

Direct input is an unchanged copy of the user-supplied `dummy_pursuit_requests.csv`. All 10 rows are classified as the Direct source, including three whose original Channel v2 is Partner and one with a blank channel. Source channel means source dataset here; the original channel is preserved in source_payload. The source contains two terminal-looking states, Completed and Cancelled. Their meaning is not assumed: both records stay in the opportunity count, and neither has a synthetic staffing estimate.

Indirect input contains 10 entirely synthetic opportunities named “Demo …”. The role-estimate file contains 16 entirely synthetic estimates across seven Direct and nine Indirect opportunities. Skills, levels, quantities and role-level start dates are test fixtures, not inferred business requirements. No existing role estimates from the original sample are carried over because their IDs do not match this dataset.

The synthetic inputs exercise all six forecast windows, unknown dates, unmapped plans, one stale record and incomplete estimate coverage. Quantities range from one to four roles per estimate. No staffing capacity, utilization, or actual-hours data is fabricated.

Two outputs are generated:

- `data/output/presentation-test/baseline/dashboard.html`: new opportunity inputs with no staffing estimates. All 20 records lack estimates, so zero displayed estimated demand means unknown staffing needs.
- `data/output/presentation-test/demo/dashboard.html`: the same opportunity inputs plus the synthetic role estimates. A visible demonstration notice is embedded in the dashboard.

Run from the project folder after dependency installation:

```sh
.venv/bin/python scripts/run_presentation_test.py
```

Both use snapshot date 2026-10-14, separate SQLite snapshots, and the existing configured confidence assumptions. The earlier sample output is preserved.

Header normalization now accepts case variations of Direct headers and three explicit aliases: Estimate Close Date → Estimated Close Date; Suppot Request V2 → Support Requested v2; Dominant Solution Aea → Dominant Solution Area. Conflicting alias/canonical columns fail rather than silently overwriting data.
