#!/usr/bin/env python3
"""Normalize Direct and Indirect demand samples into one canonical dataset."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


INDIRECT_HEADERS = {
    "Status",
    "Owner",
    "Client Name",
    "Opportunity Description",
    "Close Plan",
    "Modified",
    "Opportunity Stage",
    "ACCN MMS ID",
}

DIRECT_HEADERS = {
    "Work Item Type",
    "ID",
    "Title",
    "Assigned To",
    "Solution Due Date",
    "Estimated Close Date",
    "Support Requested v2",
    "State",
    "Channel v2",
    "Created Date",
    "Industry Group",
    "Account",
    "Dominant Solution Area",
    "Requested By",
}

CANONICAL_COLUMNS = [
    "canonical_demand_id",
    "source_system",
    "source_channel",
    "source_record_id",
    "opportunity_reference",
    "record_type",
    "client_name",
    "client_name_key",
    "description",
    "owner_name",
    "owner_email",
    "status_code",
    "status_name",
    "opportunity_stage",
    "forecast_window_code",
    "forecast_window_lower_days",
    "forecast_window_upper_days",
    "solution_due_at",
    "estimated_close_at",
    "created_at",
    "modified_at",
    "industry_group",
    "solution_area",
    "support_requested",
    "requested_by_email",
    "data_quality_flags",
]

DATETIME_FORMATS = (
    "%m/%d/%Y %H:%M",
    "%m/%d/%Y %H:%M:%S",
    "%m/%d/%Y",
)


def clean_text(value: object) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def normalized_key(value: str) -> str:
    value = clean_text(value).upper()
    return re.sub(r"[^A-Z0-9]+", " ", value).strip()


def read_csv(path: Path, required_headers: set[str]) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        actual = {clean_text(header) for header in (reader.fieldnames or [])}
        missing = sorted(required_headers - actual)
        if missing:
            raise ValueError(f"{path.name} is missing required headers: {missing}")
        return [{clean_text(k): clean_text(v) for k, v in row.items()} for row in reader]


def parse_datetime(value: str, field: str, issues: list[str]) -> str:
    value = clean_text(value)
    if not value:
        return ""
    for fmt in DATETIME_FORMATS:
        try:
            return datetime.strptime(value, fmt).isoformat(timespec="minutes")
        except ValueError:
            pass
    issues.append(f"invalid_{field}")
    return ""


def parse_person(value: str) -> tuple[str, str]:
    value = clean_text(value)
    match = re.fullmatch(r"(.+?)\s*<([^<>\s]+@[^<>\s]+)>", value)
    if match:
        return clean_text(match.group(1)), match.group(2).lower()
    if re.fullmatch(r"[^\s@]+@[^\s@]+", value):
        return "", value.lower()
    return value, ""


def parse_indirect_status(value: str, issues: list[str]) -> tuple[str, str]:
    match = re.fullmatch(r"(\d+)\s*-\s*(.+)", clean_text(value))
    if not match:
        issues.append("invalid_status_format")
        return "", clean_text(value)
    return match.group(1), clean_text(match.group(2))


def parse_close_plan(value: str, issues: list[str]) -> tuple[str, str, str]:
    normalized = clean_text(value).casefold()
    mapping = {
        "next 30 days": ("NEXT_30_DAYS", "0", "30"),
        "next 60 days": ("NEXT_60_DAYS", "0", "60"),
        "90+ days": ("DAYS_90_PLUS", "90", ""),
    }
    if not normalized:
        issues.append("missing_close_plan")
        return "UNSPECIFIED", "", ""
    if normalized not in mapping:
        issues.append("unknown_close_plan")
        return "UNMAPPED", "", ""
    return mapping[normalized]


def extract_deal_reference(title: str, issues: list[str]) -> str:
    matches = re.findall(r"\bA\d{9}\b", title, flags=re.IGNORECASE)
    if len(matches) == 1:
        return matches[0].upper()
    issues.append("missing_or_ambiguous_deal_reference")
    return ""


def title_client_prefix(title: str) -> str:
    return re.split(r"\s+-\s+A\d{9}\b", title, maxsplit=1, flags=re.IGNORECASE)[0]


def duplicate_keys(rows: Iterable[dict[str, str]], field: str) -> set[str]:
    counts = Counter(clean_text(row.get(field, "")) for row in rows)    
    return {key for key, count in counts.items() if key and count > 1}


def normalize_indirect(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    duplicates = duplicate_keys(rows, "ACCN MMS ID")
    result: list[dict[str, str]] = []
    for row in rows:
        issues: list[str] = []
        source_id = row["ACCN MMS ID"]
        if not source_id:
            issues.append("missing_source_record_id")
        elif source_id in duplicates:
            issues.append("duplicate_source_record_id")
        elif not source_id.isdigit():
            issues.append("non_numeric_source_record_id")

        status_code, status_name = parse_indirect_status(row["Status"], issues)
        window_code, lower_days, upper_days = parse_close_plan(row["Close Plan"], issues)
        client_name = row["Client Name"]

        result.append(
            {
                "canonical_demand_id": f"INDIRECT:{source_id}" if source_id else "",
                "source_system": "SharePoint List",
                "source_channel": "Indirect",
                "source_record_id": source_id,
                "opportunity_reference": source_id,
                "record_type": "Opportunity",
                "client_name": client_name,
                "client_name_key": normalized_key(client_name),
                "description": row["Opportunity Description"],
                "owner_name": row["Owner"],
                "owner_email": "",
                "status_code": status_code,
                "status_name": status_name,
                "opportunity_stage": row["Opportunity Stage"],
                "forecast_window_code": window_code,
                "forecast_window_lower_days": lower_days,
                "forecast_window_upper_days": upper_days,
                "solution_due_at": "",
                "estimated_close_at": "",
                "created_at": "",
                "modified_at": parse_datetime(row["Modified"], "modified_at", issues),
                "industry_group": "",
                "solution_area": "",
                "support_requested": "",
                "requested_by_email": "",
                "data_quality_flags": ";".join(sorted(set(issues))),
            }
        )
    return result


def normalize_direct(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    duplicates = duplicate_keys(rows, "ID")
    result: list[dict[str, str]] = []
    for row in rows:
        issues: list[str] = []
        source_id = row["ID"]
        if not source_id:
            issues.append("missing_source_record_id")
        elif source_id in duplicates:
            issues.append("duplicate_source_record_id")

        owner_name, owner_email = parse_person(row["Assigned To"])
        title = row["Title"]
        client_name = row["Account"]
        title_client = title_client_prefix(title)
        if normalized_key(title_client) != normalized_key(client_name):
            issues.append("client_title_mismatch_review")

        requested_name, requested_email = parse_person(row["Requested By"])
        if requested_name and not requested_email:
            issues.append("requested_by_email_unparsed")

        result.append(
            {
                "canonical_demand_id": f"DIRECT:{source_id}" if source_id else "",
                "source_system": "Azure DevOps Boards",
                "source_channel": row["Channel v2"] or "Direct",
                "source_record_id": source_id,
                "opportunity_reference": extract_deal_reference(title, issues),
                "record_type": row["Work Item Type"],
                "client_name": client_name,
                "client_name_key": normalized_key(client_name),
                "description": title,
                "owner_name": owner_name,
                "owner_email": owner_email,
                "status_code": "",
                "status_name": row["State"],
                "opportunity_stage": "",
                "forecast_window_code": "",
                "forecast_window_lower_days": "",
                "forecast_window_upper_days": "",
                "solution_due_at": parse_datetime(row["Solution Due Date"], "solution_due_at", issues),
                "estimated_close_at": parse_datetime(row["Estimated Close Date"], "estimated_close_at", issues),
                "created_at": parse_datetime(row["Created Date"], "created_at", issues),
                "modified_at": "",
                "industry_group": row["Industry Group"],
                "solution_area": row["Dominant Solution Area"],
                "support_requested": row["Support Requested v2"],
                "requested_by_email": requested_email,
                "data_quality_flags": ";".join(sorted(set(issues))),
            }
        )
    return result


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CANONICAL_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def build_profile(rows: list[dict[str, str]]) -> dict[str, object]:
    issue_counts: Counter[str] = Counter()
    for row in rows:
        issue_counts.update(flag for flag in row["data_quality_flags"].split(";") if flag)

    nonempty_dates = [
        row[field]
        for row in rows
        for field in ("created_at", "modified_at")
        if row[field]
    ]
    canonical_ids = [row["canonical_demand_id"] for row in rows if row["canonical_demand_id"]]

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "record_count": len(rows),
        "source_counts": dict(sorted(Counter(row["source_channel"] for row in rows).items())),
        "unique_canonical_id_count": len(set(canonical_ids)),
        "duplicate_canonical_id_count": len(canonical_ids) - len(set(canonical_ids)),
        "records_with_quality_flags": sum(bool(row["data_quality_flags"]) for row in rows),
        "quality_issue_counts": dict(sorted(issue_counts.items())),
        "missing_value_counts": {
            column: sum(not row[column] for row in rows)
            for column in CANONICAL_COLUMNS
            if column != "data_quality_flags"
        },
        "status_distribution": dict(sorted(Counter(row["status_name"] or "UNSPECIFIED" for row in rows).items())),
        "forecast_window_distribution": dict(
            sorted(Counter(row["forecast_window_code"] or "NOT_PROVIDED" for row in rows).items())
        ),
        "opportunity_stage_distribution": dict(
            sorted(Counter(row["opportunity_stage"] or "NOT_PROVIDED" for row in rows).items())
        ),
        "activity_date_min": min(nonempty_dates) if nonempty_dates else None,
        "activity_date_max": max(nonempty_dates) if nonempty_dates else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--indirect", type=Path, required=True)
    parser.add_argument("--direct", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    indirect_rows = read_csv(args.indirect, INDIRECT_HEADERS)
    direct_rows = read_csv(args.direct, DIRECT_HEADERS)
    canonical_rows = normalize_indirect(indirect_rows) + normalize_direct(direct_rows)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.output_dir / "canonical_demand.csv", canonical_rows)
    profile = build_profile(canonical_rows)
    (args.output_dir / "data_quality_profile.json").write_text(
        json.dumps(profile, indent=2), encoding="utf-8"
    )

    print(json.dumps(profile, indent=2))


if __name__ == "__main__":
    main()
