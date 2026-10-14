"""Calculate role-level staffing forecasts from opportunities and estimates."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

import pandas as pd
import math

from .normalize import clean_headers, clean_text

from .config import ForecastRules


ROLE_COLUMNS = [
    "role_estimate_id", "canonical_demand_id", "role_title", "primary_skill", "career_level",
    "quantity", "expected_start_date", "confidence_override", "geography", "notes", "created_at", "updated_at",
]
FORECAST_COLUMNS = [
    "role_estimate_id", "canonical_demand_id", "source_channel", "source_system", "source_record_id",
    "client_name", "role_title", "primary_skill", "career_level", "quantity", "expected_start_date",
    "projected_staffing_start_date", "forecast_window", "forecast_basis", "forecast_confidence",
    "raw_role_demand", "weighted_role_demand", "snapshot_date", "geography", "notes",
]


def read_role_estimates(path: str) -> pd.DataFrame:
    """Read role estimates from an editable CSV while preserving invalid rows for reporting."""
    frame = clean_headers(pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig"))
    missing = sorted(set(ROLE_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(f"Role estimates are missing required headers: {missing}")
    return frame[ROLE_COLUMNS].apply(lambda col: col.map(clean_text))


def validate_roles(role_estimates: pd.DataFrame) -> tuple[pd.DataFrame, list[dict[str, str]]]:
    """Exclude ambiguous/invalid estimates from metrics; keep raw inputs separately."""
    frame = role_estimates.copy().fillna("")
    for col in frame.columns:
        frame[col] = frame[col].map(clean_text)
    if "role_estimate_id" not in frame:
        frame["role_estimate_id"] = ""
    duplicates = set(frame.loc[frame.role_estimate_id.duplicated(False), "role_estimate_id"])
    accepted, issues = [], []
    for row in frame.to_dict("records"):
        cid = row.get("canonical_demand_id", "")
        rid = row.get("role_estimate_id", "")
        errors = []
        if not rid:
            errors.append(("MISSING_ROLE_ESTIMATE_ID", "Role estimate ID is empty."))
        elif rid in duplicates:
            errors.append(("DUPLICATE_ROLE_ESTIMATE_ID", f"Role estimate ID {rid} is ambiguous; all copies excluded."))
        try:
            qty = float(row.get("quantity", ""))
        except (ValueError, TypeError):
            qty = float("nan")
        if not math.isfinite(qty) or qty <= 0:
            errors.append(("INVALID_ROLE_QUANTITY", f"Role estimate {rid} needs a finite, positive quantity."))
        override = row.get("confidence_override", "")
        if override:
            try:
                valid = math.isfinite(float(override)) and 0 <= float(override) <= 1
            except (ValueError, TypeError):
                valid = False
            if not valid:
                errors.append(("INVALID_CONFIDENCE_OVERRIDE", f"Role estimate {rid} confidence must be between 0 and 1."))
        issues.extend(_issue(cid, code, message, "Error") for code, message in errors)
        if not errors:
            accepted.append(row)
    return pd.DataFrame(accepted, columns=frame.columns), issues


def _as_date(value: Any) -> date | None:
    """Parse a date-like value, returning None when absent or invalid."""
    if value is None or not str(value).strip():
        return None
    parsed = pd.to_datetime(value, errors="coerce")
    return None if pd.isna(parsed) else parsed.date()


def classify_window(start_date: date | None, snapshot_date: date) -> str:
    """Assign an inclusive forecast window relative to the supplied snapshot date."""
    if start_date is None:
        return "Unknown"
    days_out = (start_date - snapshot_date).days
    if days_out < 0:
        return "Past Due"
    if days_out <= 30:
        return "0-30 Days"
    if days_out <= 60:
        return "31-60 Days"
    if days_out <= 90:
        return "61-90 Days"
    return "90+ Days"


def _confidence(override: Any, status: str, rules: ForecastRules) -> float:
    """Prefer an explicit per-role probability, then a configured status assumption."""
    if str(override or "").strip():
        try:
            value = float(override)
        except (TypeError, ValueError):
            return 0.0
        return value if 0 <= value <= 1 else 0.0
    return rules.confidence_by_status.get(clean_text(status).casefold(), 0.0)


def build_role_forecast(
    opportunities: pd.DataFrame,
    role_estimates: pd.DataFrame,
    rules: ForecastRules,
    snapshot_date: date,
) -> tuple[pd.DataFrame, list[dict[str, str]]]:
    """Join role estimates to opportunities, calculate forecast fields, and report issues."""
    role_estimates, issues = validate_roles(role_estimates)
    forecast_rows: list[dict[str, Any]] = []
    ambiguous_ids = set(opportunities.loc[opportunities.canonical_demand_id.duplicated(False), "canonical_demand_id"])
    opportunity_map = {str(row.canonical_demand_id): row for row in opportunities.itertuples(index=False)
                       if row.canonical_demand_id not in ambiguous_ids and row.source_record_id}
    seen_estimate_ids: set[str] = set()

    for estimate in role_estimates.to_dict(orient="records"):
        estimate_id = str(estimate.get("role_estimate_id", "")).strip()
        canonical_id = str(estimate.get("canonical_demand_id", "")).strip()
        if not estimate_id:
            issues.append(_issue(canonical_id, "MISSING_ROLE_ESTIMATE_ID", "Role estimate ID is empty.", "Error"))
            estimate_id = f"MISSING:{len(seen_estimate_ids) + 1}"
        if estimate_id in seen_estimate_ids:
            issues.append(_issue(canonical_id, "DUPLICATE_ROLE_ESTIMATE_ID", f"Role estimate ID {estimate_id} is duplicated.", "Error"))
        seen_estimate_ids.add(estimate_id)
        if canonical_id in ambiguous_ids:
            issues.append(_issue(canonical_id, "AMBIGUOUS_OPPORTUNITY", f"Role estimate {estimate_id} links to duplicate source rows; excluded.", "Error"))
            continue
        opportunity = opportunity_map.get(canonical_id)
        if opportunity is None:
            issues.append(_issue(canonical_id, "MISSING_OPPORTUNITY", f"Role estimate {estimate_id} references no canonical opportunity.", "Error"))
            continue

        raw_quantity = str(estimate.get("quantity", "")).strip()
        try:
            quantity = float(raw_quantity)
        except (TypeError, ValueError):
            quantity = 0.0
        if quantity <= 0:
            issues.append(_issue(canonical_id, "INVALID_ROLE_QUANTITY", f"Role estimate {estimate_id} has a missing, invalid, or zero quantity.", "Error"))

        explicit_start = _as_date(estimate.get("expected_start_date"))
        projected_start = explicit_start
        basis = "role_estimate.expected_start_date" if explicit_start else ""
        raw_start = str(estimate.get("expected_start_date", "")).strip()
        if raw_start and explicit_start is None:
            issues.append(_issue(canonical_id, "INVALID_DATE", f"Role estimate {estimate_id} has an invalid expected_start_date.", "Warning"))
        if projected_start is None and opportunity.source_channel == "Direct":
            close_date = _as_date(opportunity.estimated_close_at)
            if close_date:
                projected_start = close_date + timedelta(days=rules.default_mobilization_days)
                basis = "estimated_close_at_plus_mobilization"
        if projected_start is not None:
            window = classify_window(projected_start, snapshot_date)
        elif opportunity.source_channel == "Indirect":
            source_plan = str(opportunity.source_forecast_window or "").casefold()
            window = rules.close_plan_windows.get(source_plan, "Unknown")
            basis = "indirect_close_plan" if window != "Unknown" else ""
        else:
            window = "Unknown"

        status_key = clean_text(opportunity.status_name).casefold()
        confidence = _confidence(estimate.get("confidence_override"), opportunity.status_name, rules)
        if status_key not in rules.confidence_by_status and not str(estimate.get("confidence_override", "")).strip():
            issues.append(_issue(canonical_id, "UNRECOGNIZED_STATUS", f"Status '{opportunity.status_name}' has no configured confidence.", "Warning"))
        if window == "Unknown":
            issues.append(_issue(canonical_id, "MISSING_FORECAST_INFORMATION", "No role start date, Direct close date, or recognized Indirect Close Plan is available.", "Warning"))
        forecast_rows.append({
            "role_estimate_id": estimate_id,
            "canonical_demand_id": canonical_id,
            "source_channel": opportunity.source_channel,
            "source_system": opportunity.source_system,
            "source_record_id": opportunity.source_record_id,
            "client_name": opportunity.client_name,
            "role_title": estimate.get("role_title", ""),
            "primary_skill": estimate.get("primary_skill", ""),
            "career_level": estimate.get("career_level", ""),
            "quantity": quantity,
            "expected_start_date": estimate.get("expected_start_date", ""),
            "projected_staffing_start_date": projected_start.isoformat() if projected_start else "",
            "forecast_window": window,
            "forecast_basis": basis,
            "forecast_confidence": confidence,
            "raw_role_demand": quantity,
            "weighted_role_demand": quantity * confidence,
            "snapshot_date": snapshot_date.isoformat(),
            "geography": estimate.get("geography", ""),
            "notes": estimate.get("notes", ""),
        })

    return pd.DataFrame(forecast_rows, columns=FORECAST_COLUMNS), issues


def build_forecast_summary(forecast: pd.DataFrame) -> pd.DataFrame:
    """Aggregate role demand and unique opportunity counts for Power BI."""
    columns = ["source_channel", "forecast_window", "primary_skill", "career_level", "opportunity_count", "raw_role_demand", "weighted_role_demand"]
    if forecast.empty:
        return pd.DataFrame(columns=columns)
    summary = forecast.groupby(["source_channel", "forecast_window", "primary_skill", "career_level"], dropna=False).agg(
        opportunity_count=("canonical_demand_id", "nunique"),
        raw_role_demand=("raw_role_demand", "sum"),
        weighted_role_demand=("weighted_role_demand", "sum"),
    ).reset_index()
    return summary[columns]


def _issue(canonical_id: str, code: str, description: str, severity: str) -> dict[str, str]:
    return {"canonical_demand_id": canonical_id, "issue_code": code, "issue_description": description, "severity": severity}