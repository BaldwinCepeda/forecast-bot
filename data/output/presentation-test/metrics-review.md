# Dashboard test results

Snapshot: 14 October 2026. Direct data supplied by the user; Indirect opportunities and all role estimates are synthetic. These metrics demonstrate dashboard behavior, not actual staffing requirements.

| Measure | Direct | Indirect | Combined |
|---|---:|---:|---:|
| Opportunity records | 10 | 10 | 20 |
| Opportunities with estimates | 7 | 9 | 16 |
| Requested roles (synthetic) | 16 | 20 | 36 |
| Probability-weighted roles | 3.4 | 12.6 | 16.0 |
| Estimate coverage | 70% | 90% | 80% |
| Opportunities with quality findings | 7 | 3 | 10 |

Without synthetic role estimates, the baseline has 20 opportunity records, zero estimated roles, and 0% estimate coverage. Actual staffing demand is unknown.

## Timing

| Forecast window | Requested roles | Weighted roles |
|---|---:|---:|
| Past Due | 1 | 0.4 |
| 0–30 Days | 6 | 4.4 |
| 31–60 Days | 16 | 6.5 |
| 61–90 Days | 6 | 2.2 |
| 90+ Days | 4 | 1.7 |
| Unknown | 3 | 0.8 |
| Total | 36 | 16.0 |

The 31–60-day bucket contains the largest requested demand: 16 roles. The headline weighted total includes past-due and unknown-window demand; the dated future buckets total 14.8 weighted roles.

## Skills

| Skill | Requested roles | Weighted roles |
|---|---:|---:|
| Data & AI | 12 | 7.0 |
| Azure | 10 | 3.9 |
| Security | 7 | 2.4 |
| Workplace | 4 | 1.2 |
| Business Applications | 3 | 1.5 |

## Findings to discuss before presenting

- Eight requested roles across four Direct opportunities have unmapped statuses (Rework, New, On Hold), so they contribute zero weighted roles. Zero is a fallback, not a validated probability of no demand.
- Six Direct opportunities have unmapped statuses in total, including Completed and Cancelled, which have no synthetic role estimates. The meaning of these statuses and their inclusion in the denominator need business agreement.
- Four opportunities have no role estimates. Coverage is intentionally incomplete to test the warning.
- Three requested roles have unknown forecast windows. One synthetic role has a past-due start date.
- One synthetic Indirect record is stale; one has an unrecognized Close Plan; one lacks Close Plan. “Next 60 Days” retains the existing days-31–60 interpretation.
- The quality register has 23 findings affecting 10 opportunities. Role and opportunity checks can report the same issue category on the same opportunity; finding counts are not unique problem or opportunity counts.
- Staffing gaps, utilization and delivery efficiency remain unavailable because capacity, durations and actual hours are absent.

Validation: 17 pipeline tests pass. Counts and demand totals were reconciled independently against the fixtures. The original sample dashboard remains unchanged.
