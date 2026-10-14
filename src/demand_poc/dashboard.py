"""Generate a portable, offline dashboard from the same validated CSV snapshot."""
from dataclasses import asdict
from datetime import date
import json
from pathlib import Path

import pandas as pd


def write_dashboard(output_dir, opportunities, forecast, issues, snapshot_date: date, rules, dataset_note=""):
    # Deliberately omit source payloads and contact email addresses from the browser artifact.
    columns = ["canonical_demand_id", "source_channel", "source_record_id", "client_name", "client_name_key",
               "description", "owner_name", "status_name", "solution_area", "created_at", "modified_at"]
    def records(frame):
        return json.loads(frame.to_json(orient="records", date_format="iso"))
    payload = {"snapshot": snapshot_date.isoformat(), "dataset_note": dataset_note, "opportunities": records(opportunities[columns]),
               "forecast": records(forecast), "issues": records(issues), "rules": asdict(rules)}
    # Escape HTML-sensitive characters to prevent source text closing the JSON script element.
    serialized = json.dumps(payload, ensure_ascii=True, allow_nan=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    template = Path(__file__).with_name("dashboard.html").read_text(encoding="utf-8")
    Path(output_dir, "dashboard.html").write_text(template.replace("__DASHBOARD_DATA__", serialized), encoding="utf-8")
