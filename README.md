# Demand Champion Forecasting POC

This local proof of concept combines Direct Azure DevOps and Indirect SharePoint opportunity data, links manual role estimates, calculates weighted demand, and exports analysis-ready CSVs for Power BI. It includes a repeatable data pipeline and a portable interactive staffing dashboard.

An **opportunity** is a source pursuit or request. A **role estimate** is one staffing requirement linked to an opportunity. One opportunity can have multiple role estimates, each with its own skill, level, quantity, and expected start date.

## Open the dashboard

Open `data/output/dashboard.html` in your browser for the included sample snapshot. The staffing, planning-readiness, and data-quality views share source/client/status/search filters and export the selected records to CSV. No server or internet connection is needed to view it.

See [Dashboard guide](docs/dashboard-guide.md) for metric definitions, normalization rules, and the next data needed for utilization and capacity gaps.

For macOS/Linux, install Python 3.12+ and run:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m demand_poc.cli --direct data/input/direct_sample.csv --indirect data/input/indirect_sample.csv --roles data/reference/role_estimates.csv --snapshot-date 2026-09-25 --output-dir data/output
```

On macOS, `./run_dashboard.command` refreshes and opens the sample dashboard after installation. Pass a date such as `./run_dashboard.command 2026-10-14` to change the snapshot. Refresh the source extracts too: Indirect Close Plan buckets reflect the source snapshot, not exact dates.

## Pipeline

The command validates source headers, preserves each source row, normalizes common opportunity fields, joins role estimates, calculates forecast windows and weighted demand, stores a replaceable snapshot in SQLite, records quality issues, and exports four CSV files. Problematic rows are reported rather than silently removed.

Canonical IDs use source prefixes such as `DIRECT:1111` and `INDIRECT:0012552111`. Azure DevOps `ID` remains the Direct source record ID; an `A#########` value extracted from Title is stored separately as the opportunity reference. ACCN MMS IDs are read as text so leading zeros are retained. A normalized client key is provided for matching, while source values are retained in `source_payload`.

## Install

Use Python 3.12, then from the repository root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

Copy `.env.example` to `.env` and set `DEMAND_DATABASE_URL` only when overriding the SQLite default. No passwords or tokens belong in source files. Environment variables are read directly by the CLI; load `.env` in your shell or development environment if you use one.

## Run

```powershell
python -m demand_poc.cli `
  --direct data/input/direct_sample.csv `
  --indirect data/input/indirect_sample.csv `
  --roles data/reference/role_estimates.csv `
  --snapshot-date 2026-09-25 `
  --output-dir data/output
```

Install the package in editable mode first so the `src` package is importable. You can also run `demand-poc` after installation. Use `--rules path/to/forecast_rules.json` to select another rule file.

The sample role CSV is editable. Add one row per staffing role and set `canonical_demand_id` to an existing opportunity. `confidence_override` is a decimal from `0` to `1`; blank uses the configured status mapping. Expected start dates use a format pandas can parse, preferably `YYYY-MM-DD`.

## Forecast assumptions

Business rules live in `config/forecast_rules.json`. Role start date takes precedence; absent that, Direct uses estimated close date plus 14 mobilization days; Indirect uses its configured Close Plan bucket. Otherwise the window is `Unknown`. Date-based windows are evaluated relative to the supplied snapshot date. Yesterday or earlier is `Past Due`; 0–30, 31–60, 61–90, and 91+ days map to the four future buckets.

Confidence assumptions are initial POC values requiring business validation: Needs More Information 20%, Technical Solutioning 40%, In Progress 50%, Proposal / SOW Negotiation 70%, and Approved or Confirmed 90%. Unknown statuses receive zero confidence and a quality issue until mapped or overridden.

Close Plan mappings initially use Next 30 Days → 0–30 Days, Next 60 Days → 31–60 Days, and 90+ Days → 90+ Days. **The business meaning of “Next 60 Days” still requires confirmation.** Close Plan provides a bucket, not an exact date, so the projected staffing start date remains blank when an Indirect estimate relies on Close Plan alone.

## Outputs

- `dashboard.html`: offline interactive dashboard generated with each successful run.
- `role_estimates_input.csv`: every input role row retained for audit, including rejected estimates.
- `opportunities.csv`: one normalized row per input opportunity, plus original source values in `source_payload`.
- `role_forecast.csv`: one row per valid opportunity-linked role estimate, including forecast basis, confidence, raw demand, and weighted demand.
- `forecast_summary.csv`: source, forecast window, skill, and level aggregates; opportunity count is distinct within each group.
- `data_quality_issues.csv`: detected issue code, description, severity, source channel, opportunity key, and UTC detection time.
- `data/demand_poc.sqlite`: local snapshot tables `demand_opportunity`, `role_estimate`, and `data_quality_issue`.

Run tests with `python -m pytest`. The older standalone `src/ingest_demand.py` remains available for the original canonical CSV and JSON profile workflow; the package CLI is the full forecasting pipeline.

## Known limitations and next steps

The samples do not provide actual staffing roles, so role estimates are manual. Client aliases are not governed, status vocabularies differ by source, and confidence assumptions need business approval. The pipeline does not call source APIs or infer skills from free text. Invalid quantities, duplicate role IDs, invalid confidence, and ambiguous source links are reported and excluded from forecast totals; role rows without a matching opportunity are retained in SQLite and the issue dataset but cannot appear in the joined forecast output.

The input readers can later be replaced or supplemented by Microsoft Graph and Azure DevOps REST API clients. SQLAlchemy keeps the persistence boundary portable; configure an Azure SQL SQLAlchemy driver and URL to move beyond SQLite. Power BI can consume the exported CSVs now and later connect to Azure SQL or a managed dataflow.

## Presentation test dataset

The supplied October Direct export and synthetic Indirect/role fixtures are in `data/scenarios/presentation-test`. Run `python scripts/run_presentation_test.py` using the installed environment to regenerate baseline and demo dashboards. Open `data/output/presentation-test/demo/dashboard.html` for the labeled demonstration, or `baseline/dashboard.html` for a run without staffing estimates. Read `data/output/presentation-test/metrics-review.md` for reconciled totals and caveats. These runs preserve the original sample output.
