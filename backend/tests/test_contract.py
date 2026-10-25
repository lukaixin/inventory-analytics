import json
from pathlib import Path
import pytest
from app.services import json_safe, template, validate_payload
from app.management import _aliases, _series_rows

ROOT=Path(__file__).resolve().parents[2]

def test_template_is_valid():
    assert validate_payload(template()) == []

def test_synthetic_fixture_accepts_unknown_money():
    payload=json.loads((ROOT / "data" / "synthetic-inventory.json").read_text(encoding="utf-8"))
    assert validate_payload(payload) == []

def test_orphan_snapshot_is_rejected():
    payload=template(); payload["records"][0]["snapshot_key"]="missing"
    assert any("不存在" in x for x in validate_payload(payload))

def test_duplicate_record_key_is_rejected():
    payload=template(); payload["records"].append(payload["records"][0].copy())
    assert any("record_key" in x for x in validate_payload(payload))

def test_legacy_decimal_float_is_serialized_as_decimal_string():
    value=json_safe({"amount":12.3,"row":4})
    assert value == {"amount":"12.3","row":4}

@pytest.mark.parametrize("mutate",[
    lambda p: p.update({"records":None}),
    lambda p: p.update({"snapshots":None}),
    lambda p: p.update({"records":[[]]}),
    lambda p: p.update({"snapshots":[{"key":[],"label":"x","exact_date":"2026-01-01","ordinal":1}]}),
    lambda p: p.update({"snapshots":[{"key":"x","label":"x","exact_date":"2026-01-01","ordinal":True}]}),
    lambda p: p.update({"unexpected":"value"}),
])
def test_malformed_shapes_are_rejected_without_raising(mutate):
    payload=template(); mutate(payload)
    assert validate_payload(payload)

def test_nullable_quantity_is_accepted():
    payload=template(); payload["records"][0]["quantity"]=None
    assert validate_payload(payload)==[]

def test_management_alias_resolution_uses_manifest_not_date_constant():
    payload=json.loads((ROOT / "data" / "management-demo.json").read_text(encoding="utf-8"))
    payload["snapshot_manifest"]["CURRENT"]="demo-2026-09-30"
    assert _aliases(payload)["CURRENT"]["exact_date"] == "2026-09-30"

def test_monthly_forecast_only_suppresses_its_own_quarter_summary():
    base={"metric_id":"m","scope_id":"GROUP","material_form":"ALL"}
    rows=_series_rows([], [], [base|{"period_key":"2026-Q3","period_type":"quarter"},base|{"period_key":"2026-Q4","period_type":"quarter"},base|{"period_key":"2026-10","period_type":"month","exact_date":"2026-10-31"}], "m", "GROUP", "ALL")
    assert {(x["observation_type"],x["period_key"]) for x in rows} == {("forecast","2026-Q3"),("forecast","2026-10")}
