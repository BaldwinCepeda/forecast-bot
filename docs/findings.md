# Initial data-foundation findings

## What the samples support

The two sources can be normalized into a shared opportunity-level table. Both provide a source record key, client, description, owner, and some form of status or timing signal.

## Material limitations

1. These records represent opportunities or pursuit requests, not staffing roles.
2. Neither source provides role quantity, role title, primary skill, career level, or expected staffing start date.
3. Indirect records provide a planning window but no estimated close date.
4. Direct records provide estimated close dates but no opportunity stage or confidence value.
5. The meaning of `Next 60 Days` needs confirmation. The POC currently treats it literally as zero through 60 days, not as an exclusive 31–60-day bucket.
6. Client names require a governed alias table before cross-source matching. Automated spelling correction could merge unrelated clients.
7. The Direct title and Account disagree in two sample records. The pipeline flags these for review instead of selecting one value automatically.

## What can be demonstrated now

- Combined Direct and Indirect opportunity inventory
- Pipeline counts by source, status, stage, client, solution area, and planning window
- Due-date and estimated-close-date reporting for Direct records
- Data-quality exceptions requiring correction or enrichment

## Fields needed for staffing-demand forecasting

- Number of roles
- Role title
- Primary skill and optional secondary skills
- Career level
- Expected role start date
- Geography or staffing market
- Probability or an approved stage-to-confidence mapping
- Opportunity-to-role relationship
