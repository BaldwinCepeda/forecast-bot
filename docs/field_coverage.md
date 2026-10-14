# Canonical field coverage

| Business field | Indirect | Direct | Interpretation |
|---|---|---|---|
| Source record ID | Yes | Yes | Reliable source-level key in both samples |
| Opportunity reference | ACCN MMS ID | Extracted `A#########` | Confirm whether the two reference types share a business meaning |
| Client | Yes | Yes | Requires an alias table before cross-source matching |
| Description | Yes | Yes | Opportunity description versus Azure DevOps title |
| Owner name | Yes | Yes | Direct also provides an email address |
| Status | Yes | Yes | Different status systems; do not compare without a mapping table |
| Opportunity stage | Yes | No | Available only for Indirect records |
| Planning window | Mostly | No | One Indirect record is missing a Close Plan |
| Estimated close date | No | Yes | Available only for Direct records |
| Solution due date | No | Yes | Available only for Direct records |
| Created date | No | Yes | Available only for Direct records |
| Modified date | Yes | No | Available only for Indirect records in the sample |
| Solution area | No | Yes | Available only for Direct records |
| Role quantity | No | No | Required before opportunity demand can become role demand |
| Role title | No | No | Required for staffing forecasts |
| Primary skill | No | No | Do not infer automatically from free text for the initial POC |
| Career level | No | No | Required for supply matching |
| Expected staffing start date | No | No | Required for 30/60/90 role forecasts |
