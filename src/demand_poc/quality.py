"""Detect opportunity and role-estimate quality issues without discarding records."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

import pandas as pd

from .config import ForecastRules


ISSUE_COLUMNS = ["canonical_demand_id", "source_channel", "issue_code", "issue_description", "severity", "detected_at_utc"]


def collect_quality_issues(
    opportunities: pd.DataFrame,
    role_estimates: pd.DataFrame,
    initial_issues: list[dict[str, str]],
    rules: ForecastRules,
    snapshot_date: date,
    detected_at_utc: datetime,
) -> pd.DataFrame:
    """Combine source, role, completeness, and staleness findings into a stable dataset."""
    issues = list(initial_issues)
    estimates_by_opportunity = set(role_estimates.get("canonical_demand_id", pd.Series(dtype=str)).astype(str))
    role_start_by_opportunity: dict[str, bool] = {}
    for estimate in role_estimates.to_dict(orient="records"):
        canonical_id = str(estimate.get("canonical_demand_id", ""))
        parsed_start = pd.to_datetime(estimate.get("expected_start_date", ""), errors="coerce")
        role_start_by_opportunity[canonical_id] = role_start_by_opportunity.get(canonical_id, False) or not pd.isna(parsed_start)
    for opportunity in opportunities.to_dict(orient="records"):
        canonical_id = str(opportunity.get("canonical_demand_id", ""))
        channel = str(opportunity.get("source_channel", ""))
        plan = str(opportunity.get("source_forecast_window", "")).strip()
        status = str(opportunity.get("status_name", "")).casefold()
        if status and status not in rules.confidence_by_status:
            issues.append(_issue(canonical_id, channel, "UNRECOGNIZED_STATUS", f"Status '{opportunity.get('status_name')}' has no configured confidence.", "Warning"))
        if channel == "Indirect" and plan and plan.casefold() not in rules.close_plan_windows:
            issues.append(_issue(canonical_id, channel, "UNRECOGNIZED_CLOSE_PLAN", f"Close Plan '{plan}' has no configured forecast window.", "Warning"))
        if not plan and channel == "Indirect":
            issues.append(_issue(canonical_id, channel, "MISSING_CLOSE_PLAN", "Indirect opportunity has no Close Plan.", "Warning"))
        has_role_start = role_start_by_opportunity.get(canonical_id, False)
        has_direct_date = channel == "Direct" and bool(opportunity.get("estimated_close_at"))
        has_indirect_plan = channel == "Indirect" and plan.casefold() in rules.close_plan_windows
        if not has_role_start and not has_direct_date and not has_indirect_plan:
            issues.append(_issue(canonical_id, channel, "MISSING_FORECAST_INFORMATION", "No usable source forecast date or Close Plan is available.", "Warning"))
        if canonical_id not in estimates_by_opportunity:
            issues.append(_issue(canonical_id, channel, "MISSING_ROLE_ESTIMATE", "Opportunity has no linked role estimate.", "Warning"))
        activity = opportunity.get("modified_at") or opportunity.get("created_at")
        if activity:
            parsed = pd.to_datetime(activity, errors="coerce")
            if not pd.isna(parsed) and (snapshot_date - parsed.date()).days > rules.stale_opportunity_days:
                issues.append(_issue(canonical_id, channel, "STALE_OPPORTUNITY", f"No source activity in more than {rules.stale_opportunity_days} days.", "Warning"))

    detected = detected_at_utc.astimezone(timezone.utc).isoformat(timespec="seconds")
    channels = dict(zip(opportunities.canonical_demand_id, opportunities.source_channel))
    rows = [{
        "canonical_demand_id": issue.get("canonical_demand_id", ""),
        "source_channel": issue.get("source_channel") or channels.get(issue.get("canonical_demand_id", ""), "Unlinked"),
        "issue_code": issue.get("issue_code", ""),
        "issue_description": issue.get("issue_description", ""),
        "severity": issue.get("severity", "Warning"),
        "detected_at_utc": detected,
    } for issue in issues]
    return pd.DataFrame(rows, columns=ISSUE_COLUMNS)


def _issue(canonical_id: str, channel: str, code: str, description: str, severity: str) -> dict[str, str]:
    return {"canonical_demand_id": canonical_id, "source_channel": channel, "issue_code": code,
            "issue_description": description, "severity": severity}