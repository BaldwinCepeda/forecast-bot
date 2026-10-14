"""Portable SQLAlchemy persistence for opportunities, roles, and quality issues."""

from __future__ import annotations

from sqlalchemy import DateTime, Float, Integer, MetaData, String, Table, Column, create_engine
from sqlalchemy.engine import Engine


metadata = MetaData()

demand_opportunity = Table(
    "demand_opportunity", metadata,
    Column("opportunity_row_id", Integer, primary_key=True, autoincrement=True),
    Column("canonical_demand_id", String(100), nullable=False, index=True),
    Column("source_system", String(100), nullable=False), Column("source_channel", String(100), nullable=False),
    Column("source_record_id", String(100), nullable=False), Column("opportunity_reference", String(100)),
    Column("record_type", String(100)), Column("client_name", String(300)), Column("client_name_key", String(300)),
    Column("description", String), Column("owner_name", String(300)), Column("owner_email", String(320)),
    Column("status_code", String(30)), Column("status_name", String(200)), Column("opportunity_stage", String(100)),
    Column("source_forecast_window", String(100)), Column("solution_due_at", DateTime),
    Column("estimated_close_at", DateTime), Column("created_at", DateTime), Column("modified_at", DateTime),
    Column("industry_group", String(100)), Column("solution_area", String(300)),
    Column("support_requested", String(300)), Column("requested_by_email", String(320)),
    Column("ingested_at_utc", DateTime, nullable=False), Column("source_payload", String),
)

role_estimate = Table(
    "role_estimate", metadata,
    Column("role_estimate_id", String(100), primary_key=True),
    Column("canonical_demand_id", String(100), nullable=False, index=True),
    Column("role_title", String(300)), Column("primary_skill", String(200)), Column("career_level", String(100)),
    Column("quantity", Float), Column("expected_start_date", String(30)), Column("confidence_override", Float),
    Column("geography", String(200)), Column("notes", String), Column("created_at", String(40)), Column("updated_at", String(40)),
)

data_quality_issue = Table(
    "data_quality_issue", metadata,
    Column("issue_id", Integer, primary_key=True, autoincrement=True),
    Column("canonical_demand_id", String(100)), Column("source_channel", String(100)),
    Column("issue_code", String(100), nullable=False), Column("issue_description", String, nullable=False),
    Column("severity", String(30), nullable=False), Column("detected_at_utc", String(40), nullable=False),
)


def create_database(database_url: str) -> Engine:
    """Create the configured database engine and initialize local POC tables."""
    engine = create_engine(database_url, future=True)
    metadata.create_all(engine)
    return engine


def load_tables(engine: Engine, opportunities, roles, issues) -> None:
    """Replace the current POC snapshot in one transaction for repeatable runs."""
    with engine.begin() as connection:
        connection.execute(data_quality_issue.delete())
        connection.execute(role_estimate.delete())
        connection.execute(demand_opportunity.delete())
        if not opportunities.empty:
            connection.execute(demand_opportunity.insert(), _database_records(opportunities.to_dict(orient="records"), demand_opportunity))
        if not roles.empty:
            connection.execute(role_estimate.insert(), _database_records(roles.to_dict(orient="records"), role_estimate))
        if not issues.empty:
            connection.execute(data_quality_issue.insert(), issues.to_dict(orient="records"))


def _database_records(records: list[dict], table: Table) -> list[dict]:
    """Convert pandas missing values and ISO date strings to SQL-compatible values."""
    converted = []
    date_columns = {column.name for column in table.columns if isinstance(column.type, DateTime)}
    numeric_columns = {"quantity", "confidence_override"}
    for record in records:
        output = {}
        for key, value in record.items():
            if key not in table.c:
                continue
            if value is None or (isinstance(value, float) and value != value):
                output[key] = None
            elif key in date_columns and not value:
                output[key] = None
            elif key in date_columns:
                from datetime import datetime
                output[key] = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            elif key in numeric_columns and value == "":
                output[key] = None
            elif key in numeric_columns:
                try:
                    output[key] = float(value)
                except (TypeError, ValueError):
                    output[key] = None
            elif hasattr(value, "item"):
                output[key] = value.item()
            else:
                output[key] = value
        converted.append(output)
    return converted