"""Validate and normalize source opportunity rows into the canonical model."""

from __future__ import annotations

import re
import json
import unicodedata
from datetime import datetime, timezone
from typing import Any

import pandas as pd


INDIRECT_HEADERS = {
    "Status", "Owner", "Client Name", "Opportunity Description", "Close Plan",
    "Modified", "Opportunity Stage", "ACCN MMS ID",
}
DIRECT_HEADERS = {
    "Work Item Type", "ID", "Title", "Assigned To", "Solution Due Date",
    "Estimated Close Date", "Support Requested v2", "State", "Channel v2",
    "Created Date", "Industry Group", "Account", "Dominant Solution Area", "Requested By",
}

CANONICAL_COLUMNS = [
    "canonical_demand_id", "source_system", "source_channel", "source_record_id",
    "opportunity_reference", "record_type", "client_name", "client_name_key", "description",
    "owner_name", "owner_email", "status_code", "status_name", "opportunity_stage",
    "source_forecast_window", "solution_due_at", "estimated_close_at", "created_at", "modified_at",
    "industry_group", "solution_area", "support_requested", "requested_by_email", "ingested_at_utc",
    "source_payload",
]

DATE_FORMATS = ("%m/%d/%Y %H:%M", "%m/%d/%Y %H:%M:%S", "%m/%d/%Y")


def clean_text(value: Any) -> str:
    """Trim and collapse whitespace without modifying meaningful source casing."""
    if value is None or pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", str(value))).strip()


def normalized_key(value: str) -> str:
    """Create a comparison-only client key while preserving the source display value."""
    return re.sub(r"[^A-Z0-9]+", " ", clean_text(value).upper()).strip()


DIRECT_HEADER_ALIASES = {
    "estimate close date": "Estimated Close Date",
    "suppot request v2": "Support Requested v2",
    "dominant solution aea": "Dominant Solution Area",
}


def clean_headers(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalize export whitespace/BOMs and reject colliding column names."""
    frame = frame.copy()
    frame.columns = [clean_text(str(column).lstrip("\ufeff")) for column in frame.columns]
    if frame.columns.duplicated().any():
        raise ValueError("Source has duplicate headers after whitespace normalization")
    return frame


def validate_headers(frame: pd.DataFrame, required: set[str], source_name: str) -> None:
    """Fail early with a readable list of missing source columns."""
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"{source_name} is missing required headers: {missing}")


def parse_person(value: str) -> tuple[str, str]:
    """Split a source person value into display name and normalized email."""
    value = clean_text(value)
    match = re.fullmatch(r"(.+?)\s*<([^<>\s]+@[^<>\s]+)>", value)
    if match:
        return clean_text(match.group(1)), match.group(2).lower()
    if re.fullmatch(r"[^\s@]+@[^\s@]+", value):
        return "", value.lower()
    return value, ""


def parse_datetime(value: str) -> tuple[str, bool]:
    """Return ISO date text and a flag indicating non-empty invalid input."""
    value = clean_text(value)
    if not value:
        return "", False
    for date_format in DATE_FORMATS:
        try:
            return datetime.strptime(value, date_format).isoformat(timespec="seconds"), False
        except ValueError:
            continue
    parsed = pd.to_datetime(value, errors="coerce", utc=False)
    if not pd.isna(parsed):
        return parsed.to_pydatetime().isoformat(timespec="seconds"), False
    return "", True


def parse_indirect_status(value: str) -> tuple[str, str]:
    """Split the Indirect numeric status code from its label when present."""
    match = re.fullmatch(r"(\d+)\s*-\s*(.+)", clean_text(value))
    return (match.group(1), clean_text(match.group(2))) if match else ("", clean_text(value))


def extract_deal_reference(title: str) -> str:
    """Extract one A followed by nine digits from a Direct title, if present."""
    matches = re.findall(r"\bA\d{9}\b", clean_text(title), flags=re.IGNORECASE)
    return matches[0].upper() if len(matches) == 1 else ""


def _parsed_date(row: dict[str, str], field: str, issues: list[dict[str, str]], canonical_id: str, channel: str) -> str:
    parsed, invalid = parse_datetime(row.get(field, ""))
    if invalid:
        issues.append(_issue(canonical_id, channel, "INVALID_DATE", f"{field} contains an invalid date.", "Warning"))
    return parsed


def _issue(canonical_id: str, channel: str, code: str, description: str, severity: str) -> dict[str, str]:
    return {"canonical_demand_id": canonical_id, "source_channel": channel, "issue_code": code,
            "issue_description": description, "severity": severity}


def normalize_sources(
    direct_frame: pd.DataFrame,
    indirect_frame: pd.DataFrame,
    ingested_at_utc: datetime,
    close_plan_windows: dict[str, str],
) -> tuple[pd.DataFrame, list[dict[str, str]]]:
    """Normalize both validated source frames while retaining problematic records."""
    direct_frame = clean_headers(direct_frame)
    header_lookup = {header.casefold(): header for header in DIRECT_HEADERS}
    header_lookup.update(DIRECT_HEADER_ALIASES)
    direct_frame = direct_frame.rename(columns=lambda col: header_lookup.get(col.casefold(), col))
    if direct_frame.columns.duplicated().any():
        raise ValueError("Direct source has duplicate headers after alias mapping")
    indirect_frame = clean_headers(indirect_frame)
    validate_headers(direct_frame, DIRECT_HEADERS, "Direct source")
    validate_headers(indirect_frame, INDIRECT_HEADERS, "Indirect source")
    timestamp = ingested_at_utc.astimezone(timezone.utc).isoformat(timespec="seconds")
    normalized: list[dict[str, str]] = []
    issues: list[dict[str, str]] = []

    source_sets = (("Direct", direct_frame), ("Indirect", indirect_frame))
    duplicates = {
        channel: set(frame["ID" if channel == "Direct" else "ACCN MMS ID"].map(clean_text).loc[lambda ids: ids.ne("")].loc[lambda ids: ids.duplicated(keep=False)])
        for channel, frame in source_sets
    }

    for channel, frame in source_sets:
        for row_number, source in enumerate(frame.fillna("").to_dict(orient="records"), start=1):
            row = {str(key): clean_text(value) for key, value in source.items()}
            source_id = row["ID"] if channel == "Direct" else row["ACCN MMS ID"]
            # Invalid source keys remain loadable as distinct rows while the original key stays blank.
            canonical_id = f"{channel.upper()}:{source_id}" if source_id else f"{channel.upper()}:UNIDENTIFIED:{row_number}"
            id_field = "ID" if channel == "Direct" else "ACCN MMS ID"
            if not source_id:
                issues.append(_issue(canonical_id, channel, "MISSING_SOURCE_ID", f"{id_field} is empty.", "Error"))
            elif source_id in duplicates[channel]:
                issues.append(_issue(canonical_id, channel, "DUPLICATE_SOURCE_ID", f"{id_field} {source_id} is duplicated.", "Error"))
            status_code, status_name = ("", row["State"]) if channel == "Direct" else parse_indirect_status(row["Status"])
            client_name = row["Account"] if channel == "Direct" else row["Client Name"]
            owner_name, owner_email = parse_person(row["Assigned To"]) if channel == "Direct" else parse_person(row["Owner"])
            _, requested_by_email = parse_person(row["Requested By"]) if channel == "Direct" else ("", "")
            title = row.get("Title", "")
            reference = extract_deal_reference(title) if channel == "Direct" else source_id
            date_map = ({"solution_due_at": "Solution Due Date", "estimated_close_at": "Estimated Close Date", "created_at": "Created Date"}
                        if channel == "Direct" else {"modified_at": "Modified"})
            dates = {target: _parsed_date(row, source_field, issues, canonical_id, channel) for target, source_field in date_map.items()}
            normalized.append({
                "canonical_demand_id": canonical_id,
                "source_system": "Azure DevOps Boards" if channel == "Direct" else "SharePoint List",
                "source_channel": channel,
                "source_record_id": source_id,
                "opportunity_reference": reference,
                "record_type": row.get("Work Item Type", "Opportunity") if channel == "Direct" else "Opportunity",
                "client_name": client_name,
                "client_name_key": normalized_key(client_name),
                "description": title if channel == "Direct" else row["Opportunity Description"],
                "owner_name": owner_name,
                "owner_email": owner_email,
                "status_code": status_code,
                "status_name": status_name,
                "opportunity_stage": "" if channel == "Direct" else row["Opportunity Stage"],
                "source_forecast_window": "" if channel == "Direct" else row["Close Plan"],
                "solution_due_at": dates.get("solution_due_at", ""),
                "estimated_close_at": dates.get("estimated_close_at", ""),
                "created_at": dates.get("created_at", ""),
                "modified_at": dates.get("modified_at", ""),
                "industry_group": row.get("Industry Group", ""),
                "solution_area": row.get("Dominant Solution Area", ""),
                "support_requested": row.get("Support Requested v2", ""),
                "requested_by_email": requested_by_email,
                "ingested_at_utc": timestamp,
                "source_payload": json.dumps(row, ensure_ascii=True, sort_keys=True),
            })
            if not client_name:
                issues.append(_issue(canonical_id, channel, "MISSING_CLIENT", "Client name or Account is empty.", "Error"))
            if channel == "Direct" and title and normalized_key(title.split(" - ")[0]) != normalized_key(client_name):
                issues.append(_issue(canonical_id, channel, "TITLE_CLIENT_MISMATCH", "The client text at the start of Title differs from Account.", "Warning"))

    return pd.DataFrame(normalized, columns=CANONICAL_COLUMNS), issues