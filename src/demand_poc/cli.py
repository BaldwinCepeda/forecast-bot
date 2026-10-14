"""Command-line entry point for the local Demand Champion forecasting POC."""

from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

from .config import DEFAULT_RULES_PATH, database_url, load_rules
from .database import create_database, load_tables
from .forecast import build_forecast_summary, build_role_forecast, read_role_estimates, validate_roles
from .ingest import load_opportunities
from .quality import collect_quality_issues
from .dashboard import write_dashboard


def run_pipeline(
    direct_path: Path,
    indirect_path: Path,
    roles_path: Path,
    snapshot_date: date,
    output_dir: Path,
    rules_path: Path = DEFAULT_RULES_PATH,
    dataset_note: str = "",
) -> dict[str, int]:
    """Run ingestion, storage, forecasting, quality checks, and CSV exports."""
    rules = load_rules(rules_path)
    ingested_at = datetime.now(timezone.utc)
    opportunities, source_issues = load_opportunities(direct_path, indirect_path, ingested_at, rules.close_plan_windows)
    roles = read_role_estimates(str(roles_path))
    forecast, role_issues = build_role_forecast(opportunities, roles, rules, snapshot_date)
    valid_roles, _ = validate_roles(roles)
    all_issues = source_issues + role_issues
    quality = collect_quality_issues(opportunities, valid_roles, all_issues, rules, snapshot_date, ingested_at)

    output_dir.mkdir(parents=True, exist_ok=True)
    roles.to_csv(output_dir / "role_estimates_input.csv", index=False)
    opportunities.to_csv(output_dir / "opportunities.csv", index=False)
    forecast.to_csv(output_dir / "role_forecast.csv", index=False)
    build_forecast_summary(forecast).to_csv(output_dir / "forecast_summary.csv", index=False)
    quality.to_csv(output_dir / "data_quality_issues.csv", index=False)

    engine = create_database(database_url())
    load_tables(engine, opportunities, valid_roles, quality)
    engine.dispose()
    write_dashboard(output_dir, opportunities, forecast, quality, snapshot_date, rules, dataset_note)
    return {
        "opportunities": len(opportunities),
        "role_estimates": len(roles),
        "forecast_rows": len(forecast),
        "quality_issues": len(quality),
    }


def main() -> None:
    """Parse command-line arguments and print a concise run summary."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--direct", type=Path, required=True, help="Direct opportunity CSV")
    parser.add_argument("--indirect", type=Path, required=True, help="Indirect opportunity CSV")
    parser.add_argument("--roles", type=Path, required=True, help="Editable role-estimate CSV")
    parser.add_argument("--snapshot-date", type=date.fromisoformat, required=True, help="Forecast reference date (YYYY-MM-DD)")
    parser.add_argument("--output-dir", type=Path, required=True, help="Directory for Power BI CSV outputs")
    parser.add_argument("--rules", type=Path, default=DEFAULT_RULES_PATH, help="Forecast assumptions JSON")
    parser.add_argument("--dataset-note", default="", help="Visible dataset provenance or demonstration label")
    args = parser.parse_args()
    counts = run_pipeline(args.direct, args.indirect, args.roles, args.snapshot_date, args.output_dir, args.rules, args.dataset_note)
    print("Demand Champion POC run complete")
    for name, count in counts.items():
        print(f"{name.replace('_', ' ').title()}: {count}")


if __name__ == "__main__":
    main()