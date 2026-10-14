# Source-to-canonical mapping

## Indirect source

| Source field | Canonical field | Rule |
|---|---|---|
| ACCN MMS ID | `source_record_id`, `opportunity_reference` | Preserve as text; used with the `INDIRECT:` prefix for the canonical ID |
| Status | `status_code`, `status_name` | Split the numeric prefix from the label |
| Owner | `owner_name` | Trim whitespace; do not change source casing |
| Client Name | `client_name`, `client_name_key` | Preserve display value; create an uppercase comparison key |
| Opportunity Description | `description` | Preserve text |
| Close Plan | `forecast_window_*` | Map known labels; keep missing or unknown values visible |
| Modified | `modified_at` | Parse as a timezone-naive ISO timestamp |
| Opportunity Stage | `opportunity_stage` | Preserve source stage |

## Direct source

| Source field | Canonical field | Rule |
|---|---|---|
| ID | `source_record_id` | Azure DevOps work-item key; used with the `DIRECT:` prefix for the canonical ID |
| Title | `description`, `opportunity_reference` | Preserve title and extract one `A#########` reference when present |
| Assigned To | `owner_name`, `owner_email` | Split `Name <email>` |
| Account | `client_name`, `client_name_key` | Preserve display value; create an uppercase comparison key |
| Work Item Type | `record_type` | Preserve source value |
| Solution Due Date | `solution_due_at` | Parse as a timezone-naive ISO timestamp |
| Estimated Close Date | `estimated_close_at` | Parse as a timezone-naive ISO timestamp |
| State | `status_name` | Preserve source state |
| Channel v2 | `source_channel` | Preserve source value, defaulting to Direct when blank |
| Created Date | `created_at` | Parse as a timezone-naive ISO timestamp |
| Industry Group | `industry_group` | Preserve source value |
| Dominant Solution Area | `solution_area` | Preserve source value |
| Support Requested v2 | `support_requested` | Preserve source value |
| Requested By | `requested_by_email` | Normalize email casing |

## Identifier policy

- `canonical_demand_id` identifies a record inside the POC and includes the channel prefix.
- `source_record_id` is the record key in the source system.
- `opportunity_reference` is a business/deal reference when available.
- Do not merge Direct and Indirect records solely because client names or descriptions look similar.
