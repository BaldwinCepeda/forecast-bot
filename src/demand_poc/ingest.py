"""Read source CSV files and invoke canonical normalization."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from .normalize import normalize_sources


def load_opportunities(direct_path: Path, indirect_path: Path, ingested_at_utc: datetime, close_plan_windows: dict[str, str]):
    """Load both source CSVs as text and normalize them without dropping rows."""
    direct = pd.read_csv(direct_path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    indirect = pd.read_csv(indirect_path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    return normalize_sources(direct, indirect, ingested_at_utc, close_plan_windows)