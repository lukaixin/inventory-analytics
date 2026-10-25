"""Read-only services for the isolated management_demo dataset.

All filtering happens on leaf facts before an aggregate is made.  The payload is
versioned JSON on purpose: the local demo is immutable and does not claim an ERP
data model.
"""
from __future__ import annotations

import csv
import io
import re
from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy.orm import Session

from .models import DatasetSeries, DatasetVersion
from .policy import AccessPolicy, POLICY
from .services import meta, version

ALIASES = ("YEAR_START", "MID_YEAR", "MONTH_START", "CURRENT")
BUCKETS = ("D0_7", "D8_14", "D15_30", "D31_60", "D61_90", "D91_180", "D181_PLUS", "UNKNOWN")
FORMS = ("raw", "semi_finished", "finished")


def _decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _str(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return format(value, "f")


def _delta(current: Decimal | None, baseline: Decimal | None) -> Decimal | None:
    return current - baseline if current is not None and baseline is not None else None


def _relative(current: Decimal | None, baseline: Decimal | None) -> Decimal | None:
    return None if current is None or baseline in (None, Decimal("0")) else (current - baseline) / baseline


def _payload(db: Session, version_id: str) -> tuple[DatasetVersion, dict]:
    dv, series = version(db, version_id, "management_demo")
    if dv.schema_version != "management_demo_v1" or not isinstance(dv.payload, dict):
        raise ValueError("MANAGEMENT_SCHEMA_MISMATCH")
    return dv, dv.payload


def _snapshots(payload: dict) -> dict[str, dict]:
    snapshots = {x.get("key"): x for x in payload.get("snapshots", []) if isinstance(x, dict) and x.get("key")}
    if not snapshots:
        raise ValueError("MANAGEMENT_SNAPSHOTS_MISSING")
    return snapshots


def _aliases(payload: dict) -> dict[str, dict]:
    snapshots = _snapshots(payload)
    manifest = payload.get("snapshot_manifest")
    if not isinstance(manifest, dict):
        raise ValueError("SNAPSHOT_MANIFEST_MISSING")
    resolved: dict[str, dict] = {}
    for alias in ALIASES:
        key = manifest.get(alias)
        if key not in snapshots:
            raise ValueError(f"SNAPSHOT_ALIAS_MISSING:{alias}")
        resolved[alias] = snapshots[key]
    return resolved


def _resolve_alias(payload: dict, alias: str) -> dict:
    if alias not in ALIASES:
        raise ValueError("INVALID_SNAPSHOT_ALIAS")
    return _aliases(payload)[alias]


def _allowed(facts: list[dict], policy: AccessPolicy) -> list[dict]:
    return [x for x in facts if policy.management(x.get("business_line_id"))]


def _amount(facts: list[dict]) -> dict:
    known = [(_decimal(x.get("inventory_amount"))) for x in facts if x.get("amount_known") is True]
    known = [x for x in known if x is not None]
    unknown = sum(1 for x in facts if x.get("amount_known") is not True)
    value = sum(known, Decimal("0")) if known else (Decimal("0") if not facts else None)
    state = "partial" if unknown and known else "unavailable" if unknown else "complete"
    return {"value": value, "unknown_amount_count": unknown, "coverage_state": state}


def _quantity(facts: list[dict]) -> tuple[Decimal | None, str | None, str]:
    if not facts:
        return Decimal("0"), None, "complete"
    units = {x.get("quantity_unit") for x in facts}
    if any(x.get("quantity_additive") is False for x in facts):
        return None, None, "non_additive"
    if len(units) != 1 or None in units:
        return None, None, "mixed_unit"
    values = [_decimal(x.get("quantity")) for x in facts]
    if any(v is None for v in values):
        return None, None, "partial" if any(v is not None for v in values) else "unavailable"
    return sum(values, Decimal("0")), next(iter(units)), "complete"


def _over_180(facts: list[dict]) -> Decimal | None:
    return _amount([x for x in facts if x.get("aging_bucket") == "D181_PLUS"])["value"]


def _policy_hit(fact: dict, policies: list[dict]) -> bool | None:
    matching = [p for p in policies if p.get("material_form") == fact.get("material_form")]
    if not matching:
        return None
    bucket_days = {"D0_7": 7, "D8_14": 14, "D15_30": 30, "D31_60": 60, "D61_90": 90, "D91_180": 180, "D181_PLUS": 181}
    days = bucket_days.get(fact.get("aging_bucket"))
    if days is None:
        return None
    policy = matching[0]
    threshold = policy.get("threshold_days")
    if threshold is None:
        return None
    return days > int(threshold) if policy.get("comparison") == "GT" else None


def _risk(facts: list[dict], policies: list[dict]) -> tuple[Decimal | None, str]:
    if not facts:
        return Decimal("0"), "evaluated"
    classified = [_policy_hit(x, policies) for x in facts]
    if any(x is None for x in classified):
        return None, "unclassified"
    hits = [fact for fact, hit in zip(facts, classified) if hit]
    value = _amount(hits)["value"]
    return value, "evaluated" if _amount(hits)["coverage_state"] == "complete" else "partially_evaluated"


def _filter_facts(payload: dict, snapshot_key: str, policy: AccessPolicy, business_line_id: str | None = None,
                  material_form: str = "ALL", search: str | None = None, risk_view: str = "all") -> list[dict]:
    if material_form != "ALL" and material_form not in FORMS:
        raise ValueError("INVALID_MATERIAL_FORM")
    if risk_view not in {"all", "policy_hit", "over_180", "unclassified"}:
        raise ValueError("INVALID_RISK_VIEW")
    if business_line_id and not policy.management(business_line_id):
        raise PermissionError("MANAGEMENT_SCOPE_DENIED")
    policies = payload.get("risk_policies", [])
    result = []
    needle = (search or "").strip().lower()
    for fact in _allowed([x for x in payload.get("inventory_facts", []) if isinstance(x, dict)], policy):
        if fact.get("snapshot_key") != snapshot_key or (business_line_id and fact.get("business_line_id") != business_line_id):
            continue
        if material_form != "ALL" and fact.get("material_form") != material_form:
            continue
        if needle and needle not in " ".join(str(fact.get(k, "")) for k in ("material_code", "material_description", "project_name", "material_subclass_name", "business_line_name")).lower():
            continue
        hit = _policy_hit(fact, policies)
        if risk_view == "policy_hit" and hit is not True:
            continue
        if risk_view == "over_180" and fact.get("aging_bucket") != "D181_PLUS":
            continue
        if risk_view == "unclassified" and hit is not None:
            continue
        result.append(fact)
    return result


def catalog(db: Session, version_id: str, policy: AccessPolicy = POLICY):
    dv, payload = _payload(db, version_id)
    aliases = _aliases(payload)
    facts = _allowed([x for x in payload.get("inventory_facts", []) if isinstance(x, dict)], policy)
    seen: dict[str, str] = {}
    for x in facts:
        if x.get("business_line_id"):
            seen[x["business_line_id"]] = x.get("business_line_name") or x["business_line_id"]
    periods = payload.get("periods") or []
    if not periods:
        period_index: dict[tuple[str, str], dict] = {}
        for rows, default_observation in ((payload.get("metric_facts", []), "actual"), (payload.get("targets", []), "target"), (payload.get("forecasts", []), "forecast")):
            for x in rows:
                key, observation = x.get("period_key"), x.get("observation_type", default_observation)
                if key:
                    period_index[(key, observation)] = {"key": key, "label": x.get("period_label", key), "order": x.get("period_order", 999), "period_type": x.get("period_type", "snapshot" if len(key) == 10 else "quarter"), "observation_type": observation}
        periods = sorted(period_index.values(), key=lambda x: (x["order"], x["key"], x["observation_type"]))
    return {
        "metrics": payload.get("metric_catalog", []), "periods": periods,
        "snapshot_aliases": [{"alias": alias, "snapshot_key": s["key"], "label": s.get("label"), "exact_date": s.get("exact_date"), "ordinal": s.get("ordinal")} for alias, s in aliases.items()],
        "business_lines": [{"id": key, "label": seen[key]} for key in sorted(seen)],
        "material_forms": [{"id": "ALL", "label": "全部"}] + [{"id": x, "label": {"raw": "原材料", "semi_finished": "半成品", "finished": "成品"}[x]} for x in FORMS],
        "risk_policies": payload.get("risk_policies", []), "unit_policy": payload.get("unit_policy", {}),
        "data_as_of": aliases["CURRENT"].get("exact_date"), "evidence_level": dv.evidence_level,
    }, meta(dv)


def _metric_match(rows: list[dict], metric_id: str, period: str | None, scope: str, form: str) -> dict | None:
    return next((x for x in rows if x.get("metric_id") == metric_id and x.get("period_key") == period and x.get("scope_id") == scope and x.get("material_form", "ALL") == form), None)

def _series_date(row: dict) -> str | None:
    exact = row.get("exact_date") or row.get("period_key")
    if isinstance(exact, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", exact): return exact
    m = re.fullmatch(r"(\d{4})-Q([1-4])", str(row.get("period_key")))
    if m:
        year, quarter = int(m.group(1)), int(m.group(2))
        return date(year, quarter * 3, (31, 30, 30, 31)[quarter - 1]).isoformat()
    return None

def _series_rows(actuals: list[dict], targets: list[dict], forecasts: list[dict], metric_id: str, scope: str, form: str) -> list[dict]:
    result=[]
    for rows, observation in ((actuals,"actual"),(targets,"target"),(forecasts,"forecast")):
        for row in rows:
            if row.get("metric_id")==metric_id and row.get("scope_id")==scope and row.get("material_form","ALL")==form:
                copy=dict(row); copy["observation_type"]=observation; copy["exact_date"]=_series_date(copy); result.append(copy)
    monthly_quarters={(x["exact_date"][:4], (int(x["exact_date"][5:7])-1)//3+1) for x in result if x["observation_type"]=="forecast" and x.get("period_type")=="month" and x.get("exact_date")}
    def duplicate_quarter_forecast(row: dict) -> bool:
        if row["observation_type"] != "forecast" or row.get("period_type") != "quarter": return False
        match=re.fullmatch(r"(\d{4})-Q([1-4])", str(row.get("period_key")))
        return bool(match and (match.group(1), int(match.group(2))) in monthly_quarters)
    result=[x for x in result if not duplicate_quarter_forecast(x)]
    dates=sorted({x["exact_date"] for x in result if x.get("exact_date")}); positions={x:i+1 for i,x in enumerate(dates)}
    result.sort(key=lambda x:(x.get("exact_date") or "9999-12-31",{"actual":0,"target":1,"forecast":2}[x["observation_type"]],x.get("period_key","")))
    for row in result: row["display_order"]=positions.get(row.get("exact_date"),row.get("period_order"))
    return result


def overview(db: Session, version_id: str, scope_id: str = "GROUP", material_form: str = "ALL", analysis_period: str | None = None,
             baseline_period: str | None = None, policy: AccessPolicy = POLICY, structure_metric: str = "turnover_days"):
    dv, payload = _payload(db, version_id)
    if material_form != "ALL" and material_form not in FORMS:
        raise ValueError("INVALID_MATERIAL_FORM")
    if scope_id == "GROUP" and not policy.management_group():
        raise PermissionError("MANAGEMENT_GROUP_DENIED")
    if scope_id != "GROUP" and not policy.management(scope_id):
        raise PermissionError("MANAGEMENT_SCOPE_DENIED")
    actuals = [x for x in payload.get("metric_facts", []) if x.get("observation_type") == "actual"]
    if not analysis_period:
        analysis_period = max((x.get("period_key") for x in actuals if x.get("scope_id") == scope_id and x.get("material_form", "ALL") == material_form), default=None)
    if not analysis_period:
        raise ValueError("ANALYSIS_PERIOD_MISSING")
    if baseline_period is None:
        baseline_period = min((x.get("period_key") for x in actuals if x.get("scope_id") == scope_id and x.get("material_form", "ALL") == material_form), default=None)
    targets, forecasts = payload.get("targets", []), payload.get("forecasts", [])
    cards = []
    for metric in payload.get("metric_catalog", []):
        metric_id = metric.get("id") or metric.get("metric_id")
        current = _metric_match(actuals, metric_id, analysis_period, scope_id, material_form)
        base = _metric_match(actuals, metric_id, baseline_period, scope_id, material_form)
        actual, baseline = _decimal(current.get("value")) if current else None, _decimal(base.get("value")) if base else None
        def reference(rows: list[dict], key: str, extra: bool = False) -> dict:
            ref = current.get(key) if current else None
            found = _metric_match(rows, metric_id, ref, scope_id, material_form) if ref else None
            value = _decimal(found.get("value")) if found else None
            result = {"reference_period_key": ref, "value": _str(value), "period_key": found.get("period_key") if found else None, "match_status": "matched" if found else "missing", "gap": _str(_delta(actual, value))}
            if extra: result["as_of"] = found.get("forecast_as_of") if found else None
            return result
        series = _series_rows(actuals, targets, forecasts, metric_id, scope_id, material_form)
        cards.append({"metric_id": metric_id, "label": metric.get("label"), "unit": metric.get("unit"), "actual": _str(actual), "baseline": _str(baseline), "absolute_delta": _str(_delta(actual, baseline)), "relative_delta": _str(_relative(actual, baseline)), "target": reference(targets, "reference_target_period_key"), "forecast": reference(forecasts, "reference_forecast_period_key", True), "series": [{"period_key": x.get("period_key"), "label": x.get("period_label"), "order": x.get("display_order"), "source_order": x.get("period_order"), "period_type": x.get("period_type"), "exact_date": x.get("exact_date"), "value": _str(_decimal(x.get("value"))), "observation_type": x["observation_type"]} for x in series], "aggregation_rule": metric.get("aggregation_rule"), "coverage_state": current.get("coverage_state") if current else "unavailable", "source_ref": current.get("source_ref") if current else None})
    # Keep the original cards calculation independent from the optional
    # structure extension.  The import is local to avoid a module cycle: the
    # extension reuses these immutable-payload helpers.
    from .management_overview import enrich_overview
    result = {"scope_id": scope_id, "material_form": material_form, "analysis_period": analysis_period, "baseline_period": baseline_period, "cards": cards}
    result.update(enrich_overview(db, version_id, scope_id, material_form, analysis_period, baseline_period, structure_metric, policy))
    return result, meta(dv)


def _summary(facts: list[dict], policies: list[dict]) -> dict:
    amounts = _amount(facts); over = _over_180(facts); risk, evaluation = _risk(facts, policies); quantity, quantity_unit, quantity_status = _quantity(facts)
    aging = {bucket: _str(_amount([x for x in facts if x.get("aging_bucket") == bucket])["value"]) for bucket in BUCKETS}
    aging_quantities = {bucket: _str(_quantity([x for x in facts if x.get("aging_bucket") == bucket])[0]) for bucket in BUCKETS}
    return {"aging_amounts": aging, "aging_quantities": aging_quantities, "inventory_amount": _str(amounts["value"]), "quantity": _str(quantity), "quantity_unit": quantity_unit, "quantity_status": quantity_status, "over_180_amount": _str(over), "policy_risk_amount": _str(risk), "risk_evaluation": evaluation, "unknown_amount_count": amounts["unknown_amount_count"], "coverage_state": amounts["coverage_state"]}


def analysis(db: Session, version_id: str, current_alias: str, baseline_alias: str, business_line_id: str | None = None,
             material_form: str = "ALL", policy: AccessPolicy = POLICY):
    dv, payload = _payload(db, version_id); current_s = _resolve_alias(payload, current_alias); baseline_s = _resolve_alias(payload, baseline_alias)
    policies = payload.get("risk_policies", [])
    current = _filter_facts(payload, current_s["key"], policy, business_line_id, material_form)
    baseline = _filter_facts(payload, baseline_s["key"], policy, business_line_id, material_form)
    c, b = _summary(current, policies), _summary(baseline, policies)
    cv, bv, co, bo = map(_decimal, (c["inventory_amount"], b["inventory_amount"], c["over_180_amount"], b["over_180_amount"]))
    cshare = None if c["coverage_state"] != "complete" or cv in (None, Decimal("0")) else co / cv
    bshare = None if b["coverage_state"] != "complete" or bv in (None, Decimal("0")) else bo / bv
    aliases = _aliases(payload)
    def trend(alias: str):
        s = aliases[alias]; result = _summary(_filter_facts(payload, s["key"], policy, business_line_id, material_form), policies)
        return alias, s, result
    trend_rows = [trend(alias) for alias in ALIASES]
    current_metrics = [x for x in payload.get("metric_facts", []) if x.get("metric_id") == "turnover_days" and x.get("period_key") == current_s.get("exact_date") and x.get("material_form", "ALL") == material_form and x.get("scope_id") != "GROUP" and policy.management(x.get("scope_id")) and (business_line_id is None or x.get("scope_id") == business_line_id)]
    baseline_metrics = payload.get("metric_facts", [])
    turnover = []
    for x in current_metrics:
        before = _metric_match(baseline_metrics, "turnover_days", baseline_s.get("exact_date"), x.get("scope_id"), material_form)
        value, previous = _decimal(x.get("value")), _decimal(before.get("value")) if before else None
        turnover.append({"business_line_id": x.get("scope_id"), "business_line_label": x.get("scope_label", x.get("scope_id")), "current": _str(value), "baseline": _str(previous), "delta": _str(_delta(value, previous)), "unit": x.get("unit"), "coverage_state": x.get("coverage_state", "unavailable")})
    def breakdown(key: str, label: str):
        vals=[]
        for value in sorted({x.get(key) for x in current if x.get(key) is not None}):
            rows=[x for x in current if x.get(key)==value]; s=_summary(rows, policies); amount=_decimal(s["inventory_amount"])
            vals.append({"key":value,"label":rows[0].get(label,value),"inventory_amount":s["inventory_amount"],"share":_str(amount/cv) if amount is not None and cv not in (None,Decimal("0")) and c["coverage_state"]=="complete" else None,"over_180_amount":s["over_180_amount"],"policy_risk_amount":s["policy_risk_amount"],"risk_evaluation":s["risk_evaluation"],"coverage_state":s["coverage_state"]})
        return vals
    # Inventory facts are stored in the detail amount unit; do not label their
    # direct aggregate as the separately precomputed KPI unit.
    unit = payload.get("unit_policy", {}).get("detail_amount")
    return {"selection":{"current_alias":current_alias,"current_snapshot_key":current_s["key"],"current_date":current_s.get("exact_date"),"baseline_alias":baseline_alias,"baseline_snapshot_key":baseline_s["key"],"baseline_date":baseline_s.get("exact_date"),"business_line_id":business_line_id,"material_form":material_form},"summary":{"inventory_amount":c["inventory_amount"],"baseline_inventory_amount":b["inventory_amount"],"inventory_delta":_str(_delta(cv,bv)),"over_180_amount":c["over_180_amount"],"baseline_over_180_amount":b["over_180_amount"],"over_180_delta":_str(_delta(co,bo)),"over_180_share":_str(cshare),"baseline_over_180_share":_str(bshare),"over_180_share_delta":_str(_delta(cshare,bshare)),"policy_risk_amount":c["policy_risk_amount"],"risk_evaluation":c["risk_evaluation"],"unit":unit},"turnover_facts":turnover,"amount_trend":[{"alias":a,"snapshot_key":s["key"],"exact_date":s.get("exact_date"),"value":r["inventory_amount"],"unit":unit,"coverage_state":r["coverage_state"]} for a,s,r in trend_rows],"over_180_trend":[{"alias":a,"snapshot_key":s["key"],"exact_date":s.get("exact_date"),"amount":r["over_180_amount"],"share":_str((_decimal(r["over_180_amount"])/_decimal(r["inventory_amount"])) if r["coverage_state"]=="complete" and _decimal(r["inventory_amount"]) not in (None,Decimal("0")) else None),"unit":unit,"coverage_state":r["coverage_state"]} for a,s,r in trend_rows],"material_form_breakdown":breakdown("material_form","material_form"),"business_line_breakdown":breakdown("business_line_id","business_line_name"),"coverage":{"current_unknown_amount_count":c["unknown_amount_count"],"baseline_unknown_amount_count":b["unknown_amount_count"],"current_state":c["coverage_state"],"baseline_state":b["coverage_state"]}},meta(dv)


def _node(facts: list[dict], level: str, key: str, parent_key: str | None, label: str, has_children: bool, policies: list[dict], unit: str | None) -> dict:
    row = _summary(facts, policies); row.update({"row_key":key,"parent_key":parent_key,"level":level,"label":label,"has_children":has_children,"unit":unit}); return row


def inventory_table(db: Session, version_id: str, snapshot_alias: str, business_line_id: str | None = None, material_form: str = "ALL", risk_view: str = "all", search: str | None = None, parent_key: str | None = None, sort_by: str = "inventory_amount", sort_dir: str = "desc", page: int = 1, size: int = 50, policy: AccessPolicy = POLICY):
    if page < 1 or size < 1 or size > 100: raise ValueError("INVALID_PAGE")
    if sort_by not in {"inventory_amount","over_180_amount","quantity","name"} or sort_dir not in {"asc","desc"}: raise ValueError("INVALID_SORT")
    dv,payload=_payload(db,version_id); snap=_resolve_alias(payload,snapshot_alias); policies=payload.get("risk_policies",[]); facts=_filter_facts(payload,snap["key"],policy,business_line_id,material_form,search,risk_view)
    unit=payload.get("unit_policy",{}).get("detail_amount"); totals=_summary(facts,policies); totals["unit"]=unit
    level="business_line"; scoped=facts; parent=None
    if parent_key:
        parts=parent_key.split(":")
        if len(parts)==2 and parts[0]=="bl": level="project"; parent=parent_key; scoped=[x for x in facts if x.get("business_line_id")==parts[1]]
        elif len(parts)==3 and parts[0]=="project": level="material_subclass"; parent=parent_key; scoped=[x for x in facts if x.get("business_line_id")==parts[1] and x.get("project_id")==parts[2]]
        else: raise ValueError("INVALID_PARENT_KEY")
    key_field,label_field,prefix,next_field = {"business_line":("business_line_id","business_line_name","bl","project_id"),"project":("project_id","project_name","project","material_subclass_id"),"material_subclass":("material_subclass_id","material_subclass_name","subclass",None)}[level]
    groups=defaultdict(list)
    for fact in scoped: groups[fact.get(key_field) or "UNCLASSIFIED"].append(fact)
    rows=[]
    for value, items in groups.items():
        if level=="business_line": row_key=f"bl:{value}"
        elif level=="project": row_key=f"project:{items[0].get('business_line_id')}:{value}"
        else: row_key=f"subclass:{items[0].get('business_line_id')}:{items[0].get('project_id')}:{value}"
        rows.append(_node(items,level,row_key,parent,items[0].get(label_field) or value,bool(next_field and any(x.get(next_field) for x in items)),policies,unit))
    def order(row):
        if sort_by=="name": return row["label"].lower()
        return _decimal(row.get(sort_by)) or Decimal("-Infinity")
    rows.sort(key=order,reverse=sort_dir=="desc")
    total=len(rows); rows=rows[(page-1)*size:page*size]
    return {"resolved_snapshot":{"alias":snapshot_alias,"snapshot_key":snap["key"],"exact_date":snap.get("exact_date"),"label":snap.get("label")},"totals":totals,"rows":rows,"total":total,"page":page,"size":size},meta(dv)


def management_export(db: Session, version_id: str, snapshot_alias: str, business_line_id: str | None = None, material_form: str = "ALL", risk_view: str = "all", search: str | None = None, policy: AccessPolicy = POLICY) -> str:
    dv,payload=_payload(db,version_id); snap=_resolve_alias(payload,snapshot_alias); facts=_filter_facts(payload,snap["key"],policy,business_line_id,material_form,search,risk_view)
    fields=("record_key","business_line_id","business_line_name","project_id","project_name","material_subclass_id","material_subclass_name","material_code","material_description","material_form","aging_bucket","inventory_amount","amount_known","quantity","quantity_unit","quantity_additive","source_ref")
    output=io.StringIO(); output.write("数据版本,%s\n快照别名,%s\n快照日期,%s\n数据性质,合成管理演示\n业务线筛选,%s\n物料形态筛选,%s\n风险范围,%s\n搜索条件,%s\n" % (dv.label,snapshot_alias,snap.get("exact_date"),business_line_id or "ALL",material_form,risk_view,search or ""))
    writer=csv.DictWriter(output,fieldnames=fields); writer.writeheader()
    def safe(value: Any):
        text="" if value is None else str(value); return "'"+text if text.startswith(("=","+","-","@")) else text
    for fact in sorted(facts,key=lambda x:x.get("record_key", "")): writer.writerow({field:safe(fact.get(field)) for field in fields})
    return "\ufeff"+output.getvalue()
