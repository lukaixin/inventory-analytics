"""Real isolated DuckDB integration test; no development database is touched."""
import json
import os
import uuid
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pytest
from sqlalchemy import text
ROOT=Path(__file__).resolve().parents[2]
if os.getenv("RUN_DUCKDB_INTEGRATION") != "1":
    pytest.skip("set RUN_DUCKDB_INTEGRATION=1 with a dedicated test DuckDB URL", allow_module_level=True)
TEST_URL=os.getenv("DATABASE_URL", "")
if not TEST_URL.startswith("duckdb:") or "inventory-test" not in TEST_URL:
    pytest.skip("DATABASE_URL must name the dedicated inventory-test DuckDB file", allow_module_level=True)

from fastapi.testclient import TestClient
from app.db import SessionLocal
from app.main import app
import app.main as main_module
import app.management_overview as overview_module
from app.policy import AccessPolicy, ActorContext

@pytest.fixture(scope="module")
def client():
    db=SessionLocal()
    try:
        db.execute(text("select version_num from alembic_version"))
    except Exception:
        from alembic import command
        from alembic.config import Config
        cfg=Config(str(ROOT / "backend" / "alembic.ini"))
        command.upgrade(cfg,"head")
    finally: db.close()
    db=SessionLocal()
    try:
        from app.seed import seed_legacy, seed_management
        seed_legacy(db)
        seed_management(db)
    finally: db.close()
    return TestClient(app)

def unique_payload():
    payload=json.loads((ROOT / "data" / "import-example.json").read_text(encoding="utf-8"))
    suffix=uuid.uuid4().hex[:10]
    payload["series"]["code"] += "-"+suffix
    payload["series"]["title"] += suffix
    payload["version_label"] += "-"+suffix
    return payload

def test_preview_does_not_create_dataset_and_commit_is_idempotent(client):
    payload=unique_payload(); before=client.get("/api/v1/datasets").json()["data"]
    response=client.post("/api/v1/imports/preview",files={"file":("import.json",json.dumps(payload).encode(),"application/json")})
    assert response.status_code==200
    batch=response.json()["data"]
    assert batch["status"]=="preview" and not batch["errors"]
    assert client.get("/api/v1/datasets").json()["data"] == before
    first=client.post(f"/api/v1/imports/{batch['id']}/commit",json={"set_current":False})
    assert first.status_code==200 and first.json()["data"]["already_committed"] is False
    second=client.post(f"/api/v1/imports/{batch['id']}/commit",json={"set_current":False})
    assert second.json()["data"]["already_committed"] is True
    version_id=first.json()["data"]["version_id"]
    snapshots=client.get("/api/v1/inventory/snapshots",params={"version_id":version_id})
    assert snapshots.status_code==200 and len(snapshots.json()["data"])==1
    snap_id=snapshots.json()["data"][0]["id"]
    explored=client.get("/api/v1/inventory/explore",params={"version_id":version_id,"snapshot_id":snap_id})
    assert explored.status_code==200 and explored.json()["data"]["current_total"] is not None

def test_invalid_preview_never_creates_committable_version(client):
    payload=unique_payload(); payload["records"][0]["snapshot_key"]="orphan"
    response=client.post("/api/v1/imports/preview",files={"file":("bad.json",json.dumps(payload).encode(),"application/json")})
    assert response.status_code==200
    batch=response.json()["data"]
    assert batch["status"]=="rejected" and batch["errors"]
    assert client.post(f"/api/v1/imports/{batch['id']}/commit").status_code==409

def test_all_unknown_amount_stays_null_not_zero(client):
    payload=unique_payload()
    for record in payload["records"]:
        record["unit_cost"]=None
        record["total_cost_amount"]=None
    previewed=client.post("/api/v1/imports/preview",files={"file":("unknown.json",json.dumps(payload).encode(),"application/json")}).json()["data"]
    committed=client.post(f"/api/v1/imports/{previewed['id']}/commit",json={}).json()["data"]
    snap=client.get("/api/v1/inventory/snapshots",params={"version_id":committed["version_id"]}).json()["data"][0]
    result=client.get("/api/v1/inventory/explore",params={"version_id":committed["version_id"],"snapshot_id":snap["id"],"group_by":"material_category"}).json()["data"]
    assert result["current_total"] is None
    assert result["unknown_count"] == 3
    assert all(group["current"] is None for group in result["groups"])

def test_known_zero_plus_unknown_is_known_zero(client):
    payload=unique_payload()
    payload["records"][0]["quantity"]="0"
    payload["records"][0]["unit_cost"]="0"
    payload["records"][0]["total_cost_amount"]="0"
    for record in payload["records"][1:]:
        record["unit_cost"]=None; record["total_cost_amount"]=None
    known_category=payload["records"][0]["material_category"]
    previewed=client.post("/api/v1/imports/preview",files={"file":("zero-plus-unknown.json",json.dumps(payload).encode(),"application/json")}).json()["data"]
    committed=client.post(f"/api/v1/imports/{previewed['id']}/commit",json={}).json()["data"]
    snap=client.get("/api/v1/inventory/snapshots",params={"version_id":committed["version_id"]}).json()["data"][0]
    result=client.get("/api/v1/inventory/explore",params={"version_id":committed["version_id"],"snapshot_id":snap["id"],"group_by":"material_category"}).json()["data"]
    assert Decimal(result["current_total"]) == Decimal("0")
    assert result["unknown_count"] == 2
    assert Decimal(next(group for group in result["groups"] if group["key"]==known_category)["current"]) == Decimal("0")

def test_seeded_aging_exposes_reconciliation_gaps(client):
    datasets=client.get("/api/v1/datasets").json()["data"]
    legacy=next((x for x in datasets if x["kind"]=="legacy"), None)
    if legacy is None:
        pytest.skip("optional private historical transcription is not included in the repository")
    version=client.get(f"/api/v1/datasets/{legacy['id']}/versions").json()["data"][0]["id"]
    records=client.get("/api/v1/legacy/aging",params={"version_id":version}).json()["data"]["records"]
    assert any(record["reconciliation_gap"] == "0.0001" for record in records)

@pytest.mark.parametrize("payload", [[], {"records": None, "snapshots": None}])
def test_malformed_preview_returns_rejected_not_500(client, payload):
    response=client.post("/api/v1/imports/preview",files={"file":("bad.json",json.dumps(payload).encode(),"application/json")})
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "rejected"

def test_same_sha_concurrent_commits_converge_to_one_version(client):
    payload=unique_payload(); encoded=json.dumps(payload).encode()
    first=client.post("/api/v1/imports/preview",files={"file":("parallel.json",encoded,"application/json")}).json()["data"]
    second=client.post("/api/v1/imports/preview",files={"file":("parallel.json",encoded,"application/json")}).json()["data"]
    def commit(batch_id):
        with TestClient(app) as threaded:
            return threaded.post(f"/api/v1/imports/{batch_id}/commit",json={}).json()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(commit,[first["id"],second["id"]]))
    assert all("data" in item for item in results)
    assert {item["data"]["version_id"] for item in results}.__len__()==1

def management_version(client):
    datasets=client.get("/api/v1/datasets").json()["data"]
    series=next(x for x in datasets if x["kind"]=="management_demo")
    return client.get(f"/api/v1/datasets/{series['id']}/versions").json()["data"][0]["id"]

def test_management_alias_catalog_and_exact_target_match(client):
    version_id=management_version(client)
    catalog=client.get("/api/v1/management/catalog",params={"version_id":version_id})
    assert catalog.status_code==200
    aliases={x["alias"]:x["snapshot_key"] for x in catalog.json()["data"]["snapshot_aliases"]}
    assert aliases["CURRENT"] == "demo-2026-10-22"
    overview=client.get("/api/v1/management/overview",params={"version_id":version_id,"analysis_period":"2026-10-22","baseline_period":"2025-12-31"})
    assert overview.status_code==200
    cards=overview.json()["data"]["cards"]
    assert all(card["target"]["match_status"] in {"matched","missing"} for card in cards)
    assert all(card["relative_delta"] is None or card["baseline"] not in {None,"0"} for card in cards)
    shipment=next(card for card in cards if card["metric_id"]=="shipment_cost")
    assert {point["observation_type"] for point in shipment["series"]} == {"actual","target","forecast"}
    assert all(point["observation_type"] is not None for point in shipment["series"])
    assert [point["order"] for point in shipment["series"]] == sorted(point["order"] for point in shipment["series"])
    assert not any(point["observation_type"]=="forecast" and point["period_type"]=="quarter" for point in shipment["series"])

def test_management_tree_parent_totals_and_quantity_semantics(client):
    version_id=management_version(client)
    root=client.get("/api/v1/management/inventory-table",params={"version_id":version_id,"snapshot_alias":"CURRENT","size":100}).json()["data"]
    assert root["rows"] and root["totals"]["inventory_amount"] is not None
    assert sum(Decimal(x["inventory_amount"]) for x in root["rows"] if x["inventory_amount"] is not None) == Decimal(root["totals"]["inventory_amount"])
    child=client.get("/api/v1/management/inventory-table",params={"version_id":version_id,"snapshot_alias":"CURRENT","parent_key":root["rows"][0]["row_key"],"size":100}).json()["data"]
    assert child["rows"]
    assert root["rows"][0]["quantity_status"] in {"complete","partial","mixed_unit","non_additive","unavailable"}
    assert set(root["totals"]["aging_quantities"]) == {"D0_7","D8_14","D15_30","D31_60","D61_90","D91_180","D181_PLUS","UNKNOWN"}

def test_management_analysis_export_and_invalid_inputs(client):
    version_id=management_version(client)
    analysis=client.get("/api/v1/management/analysis",params={"version_id":version_id,"current_alias":"CURRENT","baseline_alias":"YEAR_START"})
    assert analysis.status_code==200
    summary=analysis.json()["data"]["summary"]
    assert summary["over_180_amount"] != summary["policy_risk_amount"]
    assert summary["unit"] == "演示万元"
    exported=client.get("/api/v1/management/export",params={"version_id":version_id,"snapshot_alias":"CURRENT"})
    assert exported.status_code==200 and exported.content.startswith("\ufeff".encode("utf-8"))
    filtered_export=client.get("/api/v1/management/export",params={"version_id":version_id,"snapshot_alias":"CURRENT","business_line_id":"DEMO-BL-NETWORK","material_form":"finished","risk_view":"policy_hit","search":"DEMO"})
    assert "业务线筛选,DEMO-BL-NETWORK" in filtered_export.text and "物料形态筛选,finished" in filtered_export.text and "风险范围,policy_hit" in filtered_export.text
    scoped_analysis=client.get("/api/v1/management/analysis",params={"version_id":version_id,"current_alias":"CURRENT","baseline_alias":"YEAR_START","business_line_id":"DEMO-BL-NETWORK","material_form":"finished"})
    assert scoped_analysis.status_code==200
    assert all(row["business_line_id"]=="DEMO-BL-NETWORK" for row in scoped_analysis.json()["data"]["turnover_facts"])
    invalid=client.get("/api/v1/management/inventory-table",params={"version_id":version_id,"snapshot_alias":"NOT_AN_ALIAS"})
    assert invalid.status_code==422

def test_management_restricted_scope_cannot_export_or_request_group(client, monkeypatch):
    version_id=management_version(client)
    policy=AccessPolicy(ActorContext(management_business_lines=frozenset({"DEMO-BL-NETWORK"})))
    monkeypatch.setattr(main_module, "POLICY", policy)
    group=client.get("/api/v1/management/overview",params={"version_id":version_id})
    assert group.status_code==403
    exported=client.get("/api/v1/management/export",params={"version_id":version_id,"snapshot_alias":"CURRENT","business_line_id":"DEMO-BL-ICE"})
    assert exported.status_code==403
    allowed=client.get("/api/v1/management/inventory-table",params={"version_id":version_id,"snapshot_alias":"CURRENT","business_line_id":"DEMO-BL-NETWORK"})
    assert allowed.status_code==200


def test_management_overview_structure_is_server_authoritative_and_reconciled(client):
    version_id=management_version(client)
    base=client.get("/api/v1/management/overview",params={"version_id":version_id,"analysis_period":"2026-10-22","baseline_period":"2025-12-31"})
    assert base.status_code==200
    data=base.json()["data"]
    assert data["structure"]["metric_id"]=="turnover_days"
    assert all(row["share"] is None and row["share_status"]=="not_applicable" for row in data["structure"]["form_options"]+data["structure"]["business_lines"])
    assert all(point["exact_date"]<="2026-10-22" for row in data["structure"]["business_lines"] for point in row["history"])
    assert any(point["snapshot_alias"]=="CURRENT" for row in data["structure"]["business_lines"] for point in row["history"])
    point=client.get("/api/v1/management/overview",params={"version_id":version_id,"analysis_period":"2026-10-22","baseline_period":"2025-12-31","structure_metric":"point_inventory"})
    assert point.status_code==200
    structure=point.json()["data"]["structure"]
    assert structure["reconciliation"]["status"]=="matched"
    assert abs(sum(Decimal(row["share"]) for row in structure["business_lines"] if row["share"] is not None)-Decimal("1")) < Decimal("1e-24")
    assert sum(Decimal(row["value"]) for row in structure["business_lines"] if row["value"] is not None)==Decimal(structure["scope_summary"]["value"])
    for item in point.json()["data"]["conclusions"]["items"]:
        if item["drilldown"] is None:
            assert len(item["entities"]) > 1
            continue
        assert item["drilldown"]["query"]["current_alias"]=="CURRENT"
        assert item["drilldown"]["query"]["baseline_alias"]=="YEAR_START"
    non_alias=client.get("/api/v1/management/overview",params={"version_id":version_id,"analysis_period":"2026-08-31","baseline_period":"2025-12-31"})
    assert non_alias.status_code==200
    assert all(item["drilldown"] is None for item in non_alias.json()["data"]["conclusions"]["items"])
    for analysis, baseline in (("2026-10-22","2026-05-31"),("2026-05-31","2025-12-31")):
        response=client.get("/api/v1/management/overview",params={"version_id":version_id,"analysis_period":analysis,"baseline_period":baseline,"structure_metric":"point_inventory"})
        assert response.status_code==200
        # Sparse/non-snapshot periods are safely suppressed instead of sending
        # a None delta into a max() ranking.
        rule_ids={item["rule_id"] for item in response.json()["data"]["conclusions"]["items"]}
        assert "OVR_FORM_MAX_POSITIVE_INVENTORY_DELTA_V1" not in rule_ids
    required_evidence={"entity_label","current_share","baseline_share","share_delta","amount_direction","share_direction","target_period","target","gap","coverage_state"}
    assert all(required_evidence <= set(evidence) for item in point.json()["data"]["conclusions"]["items"] for evidence in item["evidence"])
    invalid=client.get("/api/v1/management/overview",params={"version_id":version_id,"structure_metric":"not-a-metric"})
    assert invalid.status_code==422 and invalid.json()["error"]["code"]=="INVALID_STRUCTURE_METRIC"


def test_management_structure_preserves_zero_missing_partial_and_tied_rule_semantics(monkeypatch):
    payload=json.loads((ROOT / "data" / "management-demo.json").read_text(encoding="utf-8"))
    # Work with a payload copy only: no seed/version content is mutated.
    monkeypatch.setattr(overview_module,"_payload",lambda _db,_version:(None,payload))
    policy=AccessPolicy()
    result=overview_module.enrich_overview(object(),"unused","GROUP","ALL","2026-10-22","2025-12-31","point_inventory",policy)
    assert result["structure"]["scope_summary"]["value"] is not None
    absent=overview_module.enrich_overview(object(),"unused","GROUP","ALL","2099-01-01","2025-12-31","point_inventory",policy)
    assert absent["structure"]["scope_summary"]["value"] is None
    assert absent["structure"]["scope_summary"]["coverage_state"]=="unavailable"
    # A known zero baseline is distinct from a missing value and never gets a
    # made-up relative percentage.
    for fact in payload["inventory_facts"]:
        if fact["snapshot_key"]=="demo-2025-12-31" and fact["material_form"]=="raw": fact["inventory_amount"]="0"; fact["amount_known"]=True
    zero=overview_module.enrich_overview(object(),"unused","GROUP","ALL","2026-10-22","2025-12-31","point_inventory",policy)
    raw=next(row for row in zero["structure"]["form_options"] if row["id"]=="raw")
    assert raw["baseline"]=="0" and raw["relative_delta"] is None and raw["absolute_delta"] is not None
    # Incomplete facts stop the whole-form ranking; no remaining form is
    # misleadingly presented as the complete-population maximum.
    next(fact for fact in payload["inventory_facts"] if fact["snapshot_key"]=="demo-2026-10-22" and fact["material_form"]=="semi_finished")["amount_known"]=False
    partial=overview_module.enrich_overview(object(),"unused","GROUP","ALL","2026-10-22","2025-12-31","point_inventory",policy)
    rules={item["rule_id"] for item in partial["conclusions"]["items"]}
    assert "OVR_DATA_COVERAGE_INCOMPLETE_V1" in rules
    assert "OVR_FORM_MAX_POSITIVE_INVENTORY_DELTA_V1" not in rules
    semi=next(row for row in partial["structure"]["form_options"] if row["id"]=="semi_finished")
    assert semi["coverage_state"]=="partial" and semi["current_coverage_state"]=="partial"
    coverage=next(item for item in partial["conclusions"]["items"] if item["rule_id"]=="OVR_DATA_COVERAGE_INCOMPLETE_V1")
    assert all(evidence[key] is None for evidence in coverage["evidence"] for key in ("current","baseline","absolute_delta","relative_delta","current_share","baseline_share","share_delta","target","gap"))
    # Removing a precomputed turnover fact stays unavailable; no neighbouring
    # period, ALL row, or aggregate is used as a substitute.
    payload["metric_facts"]=[fact for fact in payload["metric_facts"] if not (fact.get("metric_id")=="turnover_days" and fact.get("scope_id")=="DEMO-BL-NETWORK" and fact.get("material_form")=="ALL" and fact.get("period_key")=="2026-10-22")]
    missing=overview_module.enrich_overview(object(),"unused","GROUP","ALL","2026-10-22","2025-12-31","turnover_days",policy)
    line=next(row for row in missing["structure"]["business_lines"] if row["id"]=="DEMO-BL-NETWORK")
    assert line["value"] is None and line["coverage_state"]=="unavailable"
    # Exact Decimal ties are returned as one rule with every winner, rather
    # than relying on an input-order winner.
    tie_payload=json.loads((ROOT / "data" / "management-demo.json").read_text(encoding="utf-8"))
    for fact in tie_payload["inventory_facts"]:
        if fact["material_form"] in {"raw","semi_finished"} and fact["snapshot_key"] in {"demo-2025-12-31","demo-2026-10-22"}:
            fact["inventory_amount"]="2" if fact["snapshot_key"]=="demo-2026-10-22" else "1"; fact["amount_known"]=True
        elif fact["material_form"]=="finished" and fact["snapshot_key"] in {"demo-2025-12-31","demo-2026-10-22"}:
            fact["inventory_amount"]="0"; fact["amount_known"]=True
    monkeypatch.setattr(overview_module,"_payload",lambda _db,_version:(None,tie_payload))
    tied=overview_module.enrich_overview(object(),"unused","GROUP","ALL","2026-10-22","2025-12-31","point_inventory",policy)
    form_rule=next(item for item in tied["conclusions"]["items"] if item["rule_id"]=="OVR_FORM_MAX_POSITIVE_INVENTORY_DELTA_V1")
    assert {entity["id"] for entity in form_rule["entities"]}=={"raw","semi_finished"}
    assert form_rule["drilldown"] is None
    # An empty selected population is unavailable, while actual zero records
    # remain a separately supported known-zero case.
    empty_payload=json.loads((ROOT / "data" / "management-demo.json").read_text(encoding="utf-8"))
    empty_payload["inventory_facts"]=[fact for fact in empty_payload["inventory_facts"] if not (fact["snapshot_key"]=="demo-2026-10-22" and fact["material_form"]=="raw")]
    monkeypatch.setattr(overview_module,"_payload",lambda _db,_version:(None,empty_payload))
    empty=overview_module.enrich_overview(object(),"unused","GROUP","raw","2026-10-22","2025-12-31","point_inventory",policy)
    assert empty["structure"]["scope_summary"]["value"] is None
    assert empty["structure"]["scope_summary"]["coverage_state"]=="unavailable"
    composite_payload=json.loads((ROOT / "data" / "management-demo.json").read_text(encoding="utf-8"))
    composite_payload["inventory_facts"]=[fact for fact in composite_payload["inventory_facts"] if not (fact["snapshot_key"]=="demo-2026-10-22" and fact["material_form"]=="raw")]
    monkeypatch.setattr(overview_module,"_payload",lambda _db,_version:(None,composite_payload))
    composite=overview_module.enrich_overview(object(),"unused","GROUP","ALL","2026-10-22","2025-12-31","point_inventory",policy)
    assert composite["structure"]["scope_summary"]["coverage_state"]=="partial"
    assert composite["structure"]["scope_summary"]["share"] is None
    composite_rules={item["rule_id"] for item in composite["conclusions"]["items"]}
    assert "OVR_OVER180_AMOUNT_SHARE_DIRECTION_V1" not in composite_rules
    assert "OVR_FORM_MAX_POSITIVE_INVENTORY_DELTA_V1" not in composite_rules
    line_payload=json.loads((ROOT / "data" / "management-demo.json").read_text(encoding="utf-8"))
    line_payload["inventory_facts"]=[fact for fact in line_payload["inventory_facts"] if not (fact["snapshot_key"]=="demo-2026-10-22" and fact["business_line_id"]=="DEMO-BL-NETWORK")]
    monkeypatch.setattr(overview_module,"_payload",lambda _db,_version:(None,line_payload))
    missing_line=overview_module.enrich_overview(object(),"unused","GROUP","ALL","2026-10-22","2025-12-31","point_inventory",policy)
    assert missing_line["structure"]["scope_summary"]["coverage_state"]=="partial"
    assert "OVR_LINE_MAX_POSITIVE_INVENTORY_DELTA_V1" not in {item["rule_id"] for item in missing_line["conclusions"]["items"]}
    target_payload=json.loads((ROOT / "data" / "management-demo.json").read_text(encoding="utf-8"))
    target=next(item for item in target_payload["targets"] if item["metric_id"]=="turnover_days" and item["scope_id"]=="GROUP" and item.get("material_form")=="ALL" and item["period_key"]=="2026-Q4")
    target["value"]="20"
    monkeypatch.setattr(overview_module,"_payload",lambda _db,_version:(None,target_payload))
    target_result=overview_module.enrich_overview(object(),"unused","GROUP","ALL","2026-10-22","2025-12-31","turnover_days",policy)
    target_rule=next(item for item in target_result["conclusions"]["items"] if item["rule_id"]=="OVR_TURNOVER_ABOVE_TARGET_V1")
    assert target_rule["evidence"][0]["target"]=="20" and target_rule["evidence"][0]["gap"]=="7.8"
    zero_payload=json.loads((ROOT / "data" / "management-demo.json").read_text(encoding="utf-8"))
    for fact in zero_payload["inventory_facts"]:
        if fact["snapshot_key"] in {"demo-2025-12-31","demo-2026-10-22"}: fact["inventory_amount"]="0"; fact["amount_known"]=True
    zero_payload["targets"]=[item for item in zero_payload["targets"] if item.get("metric_id")!="turnover_days"]
    monkeypatch.setattr(overview_module,"_payload",lambda _db,_version:(None,zero_payload))
    zero_result=overview_module.enrich_overview(object(),"unused","GROUP","ALL","2026-10-22","2025-12-31","point_inventory",policy)
    assert zero_result["structure"]["scope_summary"]["coverage_state"]=="complete"
    assert zero_result["structure"]["scope_summary"]["share_status"]=="zero_denominator"
    assert zero_result["conclusions"]["items"]==[]
