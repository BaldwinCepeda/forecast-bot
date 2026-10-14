"""Load forecasting assumptions and runtime configuration."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RULES_PATH = PROJECT_ROOT / "config" / "forecast_rules.json"


@dataclass(frozen=True)
class ForecastRules:
    """Business assumptions used to classify and weight demand."""

    default_mobilization_days: int
    stale_opportunity_days: int
    close_plan_windows: dict[str, str]
    confidence_by_status: dict[str, float]


def load_rules(path: Path = DEFAULT_RULES_PATH) -> ForecastRules:
    """Load and validate editable forecast assumptions from JSON."""
    raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    mobilization_days = int(raw["default_mobilization_days"])
    stale_days = int(raw["stale_opportunity_days"])
    confidence = {str(key): float(value) for key, value in raw["confidence_by_status"].items()}
    if mobilization_days < 0 or stale_days < 0:
        raise ValueError("Mobilization and stale-day settings must be non-negative")
    if any(not 0 <= value <= 1 for value in confidence.values()):
        raise ValueError("Confidence values must be between 0 and 1")
    return ForecastRules(
        default_mobilization_days=mobilization_days,
        stale_opportunity_days=stale_days,
        close_plan_windows={str(key).casefold(): str(value) for key, value in raw["close_plan_windows"].items()},
        confidence_by_status={key.casefold(): value for key, value in confidence.items()},
    )


def database_url() -> str:
    """Return database URL from the environment, defaulting to local SQLite."""
    configured = os.getenv("DEMAND_DATABASE_URL")
    if configured:
        return configured
    database_path = Path(os.getenv("DEMAND_DATABASE_PATH", str(PROJECT_ROOT / "data" / "demand_poc.sqlite")))
    database_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{database_path.as_posix()}"