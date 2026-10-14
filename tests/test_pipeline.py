"""Synthetic tests for the Demand Champion POC transformation rules."""

from datetime import date, datetime, timezone

import pandas as pd

from demand_poc.config import ForecastRules, load_rules
from demand_poc.forecast import build_forecast_summary, build_role_forecast, classify_window
from demand_poc.normalize import DIRECT_HEADERS, INDIRECT_HEADERS, normalize_sources, parse_datetime, parse_person
from demand_poc.quality import collect_quality_issues


def _direct_row(**overrides):
    row = {header: "" for header in DIRECT_HEADERS}
    row.update({"Work Item Type": "Pursuit Request", "ID": "1111", "Title": "Example Client - A000474407 - Discovery",
                "Assigned To": "Taylor Example <Taylor@example.com>", "Estimated Close Date": "9/29/2026 17:00",
                "State": "In Progress", "Channel v2": "Direct", "Created Date": "9/1/2026", "Account": "Example Client"})
    row.update(overrides)
    return row


def _indirect_row(**overrides):
    row = {header: "" for header in INDIRECT_HEADERS}
    row.update({"Status": "2 - Technical Solutioning", "Owner": "Taylor Example", "Client Name": "Sample Co",
                "Opportunity Description": "Discovery", "Close Plan": "Next 60 Days", "Modified": "9/8/2026 9:11",
                "Opportunity Stage": "Stage 1", "ACCN MMS ID": "0012552111"})
    row.update(overrides)
    return row


def _rules():
    return ForecastRules(
        default_mobilization_days=14,
        stale_opportunity_days=90,
        close_plan_windows={"next 30 days": "0-30 Days", "next 60 days": "31-60 Days", "90+ days": "90+ Days"},
        confidence_by_status={"in progress": 0.5, "technical solutioning": 0.4},
    )


def _normalize(direct_rows=None, indirect_rows=None):
    direct = pd.DataFrame(direct_rows or [_direct_row()])
    indirect = pd.DataFrame(indirect_rows or [_indirect_row()])
    return normalize_sources(direct, indirect, datetime(2026, 9, 25, tzinfo=timezone.utc), _rules().close_plan_windows)


def test_source_ids_and_direct_deal_reference_are_separate():
    opportunities, _ = _normalize()
    direct = opportunities.loc[opportunities["source_channel"] == "Direct"].iloc[0]
    indirect = opportunities.loc[opportunities["source_channel"] == "Indirect"].iloc[0]
    assert direct["canonical_demand_id"] == "DIRECT:1111"
    assert direct["source_record_id"] == "1111"
    assert direct["source_channel"] == "Direct"
    assert direct["opportunity_reference"] == "A000474407"
    assert indirect["canonical_demand_id"] == "INDIRECT:0012552111"
    assert indirect["source_record_id"] == "0012552111"
    assert '"ACCN MMS ID": "0012552111"' in indirect["source_payload"]


def test_person_and_date_parsing():
    assert parse_person("Taylor Example <Taylor@Example.com>") == ("Taylor Example", "taylor@example.com")
    assert parse_person("taylor@example.com") == ("", "taylor@example.com")
    assert parse_datetime("9/13/2026 17:00") == ("2026-09-13T17:00:00", False)
    assert parse_datetime("not-a-date") == ("", True)


def test_forecast_window_boundaries():
    snapshot = date(2026, 9, 25)
    assert classify_window(date(2026, 9, 24), snapshot) == "Past Due"
    assert classify_window(snapshot, snapshot) == "0-30 Days"
    assert classify_window(date(2026, 10, 25), snapshot) == "0-30 Days"
    assert classify_window(date(2026, 10, 26), snapshot) == "31-60 Days"
    assert classify_window(date(2026, 11, 24), snapshot) == "31-60 Days"
    assert classify_window(date(2026, 11, 25), snapshot) == "61-90 Days"
    assert classify_window(date(2026, 12, 24), snapshot) == "61-90 Days"
    assert classify_window(date(2026, 12, 25), snapshot) == "90+ Days"
    assert classify_window(None, snapshot) == "Unknown"


def test_mobilization_and_confidence_override():
    opportunities, _ = _normalize()
    roles = pd.DataFrame([{"role_estimate_id": "R1", "canonical_demand_id": "DIRECT:1111", "role_title": "Architect",
                           "primary_skill": "Cloud", "career_level": "Senior", "quantity": "2",
                           "expected_start_date": "", "confidence_override": "0.8", "geography": "", "notes": ""}])
    forecast, issues = build_role_forecast(opportunities, roles, _rules(), date(2026, 9, 25))
    row = forecast.iloc[0]
    assert row["projected_staffing_start_date"] == "2026-10-13"
    assert row["forecast_basis"] == "estimated_close_at_plus_mobilization"
    assert row["forecast_confidence"] == 0.8
    assert row["weighted_role_demand"] == 1.6
    assert not issues


def test_duplicate_source_ids_are_reported():
    duplicates = [_direct_row(), _direct_row(Title="Example Client - A000474408 - Review")]
    _, issues = _normalize(direct_rows=duplicates)
    assert sum(issue["issue_code"] == "DUPLICATE_SOURCE_ID" for issue in issues) == 2


def test_missing_close_plan_and_unknown_mapping_are_reported():
    opportunities, source_issues = _normalize(indirect_rows=[_indirect_row(**{"Close Plan": ""})])
    quality = collect_quality_issues(opportunities, pd.DataFrame(columns=["canonical_demand_id"]), source_issues,
                                     _rules(), date(2026, 9, 25), datetime(2026, 9, 25, tzinfo=timezone.utc))
    assert "MISSING_CLOSE_PLAN" in set(quality["issue_code"])
    assert "MISSING_ROLE_ESTIMATE" in set(quality["issue_code"])


def test_invalid_quantity_and_missing_opportunity_relationship_are_reported():
    opportunities, _ = _normalize()
    roles = pd.DataFrame([
        {"role_estimate_id": "R1", "canonical_demand_id": "DIRECT:1111", "quantity": "0"},
        {"role_estimate_id": "R2", "canonical_demand_id": "DIRECT:missing", "quantity": "1"},
    ])
    _, issues = build_role_forecast(opportunities, roles, _rules(), date(2026, 9, 25))
    assert {issue["issue_code"] for issue in issues} >= {"INVALID_ROLE_QUANTITY", "MISSING_OPPORTUNITY"}


def test_indirect_close_plan_maps_next_sixty_to_31_60_and_summary_counts_unique_opportunities():
    opportunities, _ = _normalize()
    roles = pd.DataFrame([
        {"role_estimate_id": "R1", "canonical_demand_id": "INDIRECT:0012552111", "quantity": "1", "role_title": "Architect", "primary_skill": "Cloud", "career_level": "Senior"},
        {"role_estimate_id": "R2", "canonical_demand_id": "INDIRECT:0012552111", "quantity": "2", "role_title": "Engineer", "primary_skill": "Cloud", "career_level": "Senior"},
    ])
    forecast, _ = build_role_forecast(opportunities, roles, _rules(), date(2026, 9, 25))
    summary = build_forecast_summary(forecast)
    assert set(forecast["forecast_window"]) == {"31-60 Days"}
    assert summary["opportunity_count"].sum() == 1
    assert summary["raw_role_demand"].sum() == 3


def test_configured_assumptions_are_loadable():
    rules = load_rules()
    assert rules.default_mobilization_days == 14
    assert rules.close_plan_windows["next 60 days"] == "31-60 Days"

def test_invalid_numeric_values_do_not_contribute_to_demand():
    opportunities, _ = _normalize()
    for quantity in ['-2', 'nan', 'inf', 'abc', '0']:
        forecast, issues = build_role_forecast(opportunities, pd.DataFrame([
            {'role_estimate_id': 'R1', 'canonical_demand_id': 'DIRECT:1111', 'quantity': quantity}
        ]), _rules(), date(2026, 9, 25))
        assert forecast.empty
        assert 'INVALID_ROLE_QUANTITY' in {i['issue_code'] for i in issues}


def test_duplicate_roles_and_ambiguous_links_are_excluded():
    opportunities, _ = _normalize(direct_rows=[_direct_row(), _direct_row()])
    role = {'role_estimate_id': 'R1', 'canonical_demand_id': 'DIRECT:1111', 'quantity': '2'}
    forecast, issues = build_role_forecast(opportunities, pd.DataFrame([role]), _rules(), date(2026, 9, 25))
    assert forecast.empty
    assert 'AMBIGUOUS_OPPORTUNITY' in {i['issue_code'] for i in issues}
    opportunities, _ = _normalize()
    forecast, issues = build_role_forecast(opportunities, pd.DataFrame([role, role]), _rules(), date(2026, 9, 25))
    assert forecast.empty
    assert len(issues) == 2


def test_confidence_override_must_be_finite_probability():
    opportunities, _ = _normalize()
    for value in ['nan', 'inf', '-0.1', '1.1', 'unknown']:
        forecast, issues = build_role_forecast(opportunities, pd.DataFrame([
            {'role_estimate_id': 'R1', 'canonical_demand_id': 'DIRECT:1111', 'quantity': '2', 'confidence_override': value}
        ]), _rules(), date(2026, 9, 25))
        assert forecast.empty
        assert 'INVALID_CONFIDENCE_OVERRIDE' in {i['issue_code'] for i in issues}


def test_header_whitespace_and_owner_email_normalization():
    direct = pd.DataFrame([_direct_row()]).rename(columns=lambda col: ' '+col+'  ')
    indirect = pd.DataFrame([_indirect_row(Owner='Taylor Example <Taylor@Example.com>')])
    opportunities, _ = normalize_sources(direct, indirect, datetime.now(timezone.utc), _rules().close_plan_windows)
    assert opportunities.iloc[1].owner_email == 'taylor@example.com'
    assert opportunities.iloc[1].source_record_id == '0012552111'


def test_pipeline_writes_dashboard_and_handles_duplicate_roles(tmp_path, monkeypatch):
    from demand_poc.cli import run_pipeline
    from demand_poc.config import PROJECT_ROOT
    import json
    import re
    import sqlite3
    monkeypatch.setenv('DEMAND_DATABASE_PATH', str(tmp_path/'test.sqlite'))
    roles = pd.read_csv(PROJECT_ROOT/'data/reference/role_estimates.csv', dtype=str, keep_default_na=False)
    roles = pd.concat([roles, roles], ignore_index=True)
    role_path = tmp_path/'roles.csv'
    roles.to_csv(role_path, index=False)
    counts = run_pipeline(PROJECT_ROOT/'data/input/direct_sample.csv', PROJECT_ROOT/'data/input/indirect_sample.csv', role_path, date(2026, 9, 25), tmp_path)
    assert counts['forecast_rows'] == 0
    assert len(pd.read_csv(tmp_path/'role_estimates_input.csv')) == 2
    html = (tmp_path/'dashboard.html').read_text()
    data = json.loads(re.search(r'<script id="dataset" type="application/json">(.*?)</script>', html, re.S).group(1))
    assert len(data['opportunities']) == 11
    assert data['forecast'] == []
    with sqlite3.connect(tmp_path/'test.sqlite') as db:
        assert db.execute('select count(*) from role_estimate').fetchone()[0] == 0
    # A second run replaces the snapshot rather than accumulating rows.
    run_pipeline(PROJECT_ROOT/'data/input/direct_sample.csv', PROJECT_ROOT/'data/input/indirect_sample.csv', PROJECT_ROOT/'data/reference/role_estimates.csv', date(2026, 9, 25), tmp_path)
    with sqlite3.connect(tmp_path/'test.sqlite') as db:
        assert db.execute('select count(*) from demand_opportunity').fetchone()[0] == 11
        assert db.execute('select count(*) from role_estimate').fetchone()[0] == 1


def test_dashboard_escapes_source_markup_and_supports_empty_data(tmp_path):
    from demand_poc.dashboard import write_dashboard
    from demand_poc.forecast import FORECAST_COLUMNS
    from demand_poc.quality import ISSUE_COLUMNS
    opportunities, _ = _normalize()
    opportunities.loc[0, 'client_name'] = '</script><script>alert(1)</script>'
    write_dashboard(tmp_path, opportunities, pd.DataFrame(columns=FORECAST_COLUMNS), pd.DataFrame(columns=ISSUE_COLUMNS), date(2026, 9, 25), _rules())
    html = (tmp_path/'dashboard.html').read_text()
    assert '</script><script>alert(1)</script>' not in html
    assert '\\u003c/script\\u003e' in html
    write_dashboard(tmp_path, opportunities.iloc[:0], pd.DataFrame(columns=FORECAST_COLUMNS), pd.DataFrame(columns=ISSUE_COLUMNS), date(2026, 9, 25), _rules())


def test_direct_export_aliases_and_collision_detection():
    import pytest
    aliases = {'Work Item Type': 'Work Item type', 'Created Date': 'Created date',
               'Estimated Close Date': 'Estimate Close Date', 'Support Requested v2': 'Suppot Request V2',
               'Dominant Solution Area': 'Dominant Solution Aea'}
    direct = pd.DataFrame([_direct_row()]).rename(columns=aliases)
    indirect = pd.DataFrame([_indirect_row()])
    opportunities, _ = normalize_sources(direct, indirect, datetime.now(timezone.utc), _rules().close_plan_windows)
    assert opportunities.iloc[0].estimated_close_at == '2026-09-29T17:00:00'
    direct['Estimated Close Date'] = '2026-10-01'
    with pytest.raises(ValueError, match='duplicate headers after alias mapping'):
        normalize_sources(direct, indirect, datetime.now(timezone.utc), _rules().close_plan_windows)


def test_dashboard_dataset_note_is_escaped(tmp_path):
    from demand_poc.dashboard import write_dashboard
    from demand_poc.forecast import FORECAST_COLUMNS
    from demand_poc.quality import ISSUE_COLUMNS
    opportunities, _ = _normalize()
    write_dashboard(tmp_path, opportunities, pd.DataFrame(columns=FORECAST_COLUMNS), pd.DataFrame(columns=ISSUE_COLUMNS), date(2026,9,25), _rules(), 'Synthetic <test> dataset')
    assert 'Synthetic \\u003ctest\\u003e dataset' in (tmp_path/'dashboard.html').read_text()
