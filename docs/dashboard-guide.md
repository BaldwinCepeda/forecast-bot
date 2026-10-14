# Staffing dashboard

Open `data/output/dashboard.html` in a browser. It is a self-contained snapshot with no external scripts or network dependencies. Rerun the pipeline after changing the source CSVs or forecast assumptions. Filter by source, normalized client key, status, or search; filters apply to all three views and exports. Unlinked quality issues appear in the unfiltered register.

## What the measures mean

- Opportunity records: input rows across Direct and Indirect. Duplicate IDs are retained and flagged. This is not a deduplicated count of business deals.
- Estimated roles: sum of positive, finite quantities on validated estimates with a unique source opportunity link. This is not FTE; duration and allocation are absent.
- Weighted demand: estimated quantity multiplied by the role override or configured status probability. These probabilities are assumptions, not a calibrated prediction.
- Estimate coverage: percentage of selected opportunity records with at least one usable linked estimate. Unknown demand is never assumed to be zero.
- Planning readiness: estimate coverage, missing information, stale source records, and the opportunity worklist. These are workflow indicators, not utilization or productivity.

The included sample has 11 opportunity records, one valid role estimate requesting two roles, and 1.0 weighted role under the 50% In Progress assumption. Coverage is 1/11 (9.09%). Samples are illustrative; they do not establish actual staffing needs.

## Normalization and safeguards

CSV readers preserve source IDs as text, including leading zeros. Headers tolerate surrounding whitespace and BOMs; duplicate normalized headers fail clearly. Text uses Unicode NFKC and collapsed whitespace. Client keys normalize punctuation and case for grouping only. Person fields split names and emails. Original source fields remain in the source payload (with normalized whitespace); the original input CSVs are preserved.

Direct and Indirect rows remain source-prefixed. Client names alone are not a reliable cross-source deal identifier; no fuzzy merging is performed. Confirm a shared business opportunity identifier or provide an explicit mapping before deduplicating across systems.

Duplicate or missing role IDs, nonpositive/nonfinite quantities, and invalid confidence overrides are excluded from forecasts and the typed role table. All role inputs remain in `role_estimates_input.csv`; the quality register records errors. All copies of duplicate role IDs are excluded to avoid selecting an arbitrary version. Estimates with ambiguous source IDs are excluded from forecasts; valid but unmatched role inputs remain in the role table for remediation.

Forecast windows refer to the supplied snapshot date. Direct fallback uses close date plus mobilization days; Indirect fallback uses the source Close Plan bucket. “Next 60 Days” currently means days 31–60 and requires confirmation. A source bucket cannot be aged forward reliably without source history, so refresh Indirect data when advancing the snapshot date.

## Additional data for efficiency

Provide the two full source exports with headers and identifiers intact. Useful next inputs:

- Role estimates: opportunity identifier, skill, level, requested quantity, geography, expected start, duration/end date, and allocation percentage or required hours.
- Capacity: staff identifier, skill, level, geography, available hours by week, contracted hours, leave, and existing assignments.
- Actual work: staff identifier, week, project/opportunity identifier, productive/billable hours, and total available hours.
- Pipeline history: opportunity identifier, stage/status, entered timestamp, exited timestamp, and outcome.
- Mapping decisions: client aliases, shared opportunity IDs, stage/confidence definitions, time zone, and whether Closed/Lost opportunities should be excluded.

With these fields, staffing gaps can compare required and available hours at the same time/skill/geography grain; utilization can use productive hours divided by available hours; stage duration can use actual transitions. None of these is inferred from opportunity counts.
