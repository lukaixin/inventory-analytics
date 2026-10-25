"""Structure and deterministic conclusions for the management overview.

This module deliberately consumes the immutable management payload only.  It
does not turn the precomputed turnover KPI into an additive measure and it
keeps incomplete inventory populations out of rankings.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from .management import FORMS, _aliases, _amount, _decimal, _delta, _filter_facts, _metric_match, _payload, _relative, _str
from .policy import AccessPolicy

RULESET_ID = "management_overview_rules_v1"
FORM_LABELS = {"raw": "原材料", "semi_finished": "半成品", "finished": "成品", "ALL": "全部"}


def _refs(rows: list[dict]) -> list[str]:
    return sorted({str(x["source_ref"]) for x in rows if x.get("source_ref")})


def _coverage(row: dict | None) -> str:
    return row.get("coverage_state", "unavailable") if row else "unavailable"


def _complete(row: dict | None) -> bool:
    return _coverage(row) == "complete"


def _inventory_rows(payload: dict, snapshot_key: str | None, policy: AccessPolicy, scope_id: str, form: str) -> list[dict]:
    if not snapshot_key:
        return []
    business_line = None if scope_id == "GROUP" else scope_id
    return _filter_facts(payload, snapshot_key, policy, business_line, form)


def _inventory_value(payload: dict, snapshot_key: str | None, policy: AccessPolicy, scope_id: str, form: str) -> dict:
    if not snapshot_key:
        return {"value": None, "coverage_state": "unavailable", "source_refs": []}
    rows = _inventory_rows(payload, snapshot_key, policy, scope_id, form)
    if not rows:
        return {"value": None, "coverage_state": "unavailable", "source_refs": []}
    amount = _amount(rows)
    # The absence of an expected authorised line/form combination at a given
    # snapshot is not evidence of a complete zero.  Expected combinations are
    # learned only from this immutable dataset's authorised facts (never an
    # invented organisation list), then checked before reporting GROUP sums.
    universe = [x for x in payload.get("inventory_facts", []) if isinstance(x, dict) and policy.management(x.get("business_line_id"))]
    def matches(x: dict) -> bool:
        return (scope_id == "GROUP" or x.get("business_line_id") == scope_id) and (form == "ALL" or x.get("material_form") == form)
    expected = {(x.get("business_line_id"), x.get("material_form")) for x in universe if matches(x) and x.get("business_line_id") and x.get("material_form")}
    present = {(x.get("business_line_id"), x.get("material_form")) for x in rows if x.get("business_line_id") and x.get("material_form")}
    state = amount["coverage_state"]
    if expected - present:
        state = "partial" if amount["value"] is not None else "unavailable"
    return {"value": amount["value"], "coverage_state": state, "source_refs": _refs(rows)}


def _turnover_value(actuals: list[dict], period: str | None, scope_id: str, form: str) -> dict:
    fact = _metric_match(actuals, "turnover_days", period, scope_id, form)
    return {"value": _decimal(fact.get("value")) if fact else None, "coverage_state": _coverage(fact), "source_refs": _refs([fact] if fact else [])}


def _label(payload: dict, scope_id: str) -> str:
    if scope_id == "GROUP":
        return "集团"
    for row in payload.get("metric_facts", []):
        if row.get("scope_id") == scope_id and row.get("scope_label"):
            return row["scope_label"]
    for row in payload.get("inventory_facts", []):
        if row.get("business_line_id") == scope_id:
            return row.get("business_line_name") or scope_id
    return scope_id


def _share(value: dict, denominator: dict, applicable: bool) -> tuple[Decimal | None, str]:
    if not applicable:
        return None, "not_applicable"
    if not _complete(value) or not _complete(denominator):
        return None, "partial" if value.get("value") is not None or denominator.get("value") is not None else "unavailable"
    denominator_value = denominator.get("value")
    if denominator_value is None:
        return None, "unavailable"
    if denominator_value == 0:
        return None, "zero_denominator"
    if value.get("value") is None:
        return None, "unavailable"
    return value["value"] / denominator_value, "available"


def _value_row(entity_id: str, label: str, current: dict, baseline: dict, denominator: dict, share_applicable: bool) -> dict:
    complete = _complete(current) and _complete(baseline)
    delta = _delta(current.get("value"), baseline.get("value")) if complete else None
    relative = _relative(current.get("value"), baseline.get("value")) if complete else None
    share, share_status = _share(current, denominator, share_applicable)
    combined_coverage = "unavailable" if "unavailable" in {current["coverage_state"], baseline["coverage_state"]} else "partial" if "partial" in {current["coverage_state"], baseline["coverage_state"]} else "complete"
    return {
        "id": entity_id, "label": label, "value": _str(current.get("value")),
        "baseline": _str(baseline.get("value")), "absolute_delta": _str(delta),
        "relative_delta": _str(relative), "share": _str(share), "share_status": share_status,
        "coverage_state": combined_coverage, "current_coverage_state": current["coverage_state"], "baseline_coverage_state": baseline["coverage_state"],
        "source_refs": sorted(set(current.get("source_refs", [])) | set(baseline.get("source_refs", []))),
    }


def _business_lines(payload: dict, policy: AccessPolicy, scope_id: str) -> list[str]:
    if scope_id != "GROUP":
        return [scope_id] if policy.management(scope_id) else []
    return sorted({x.get("business_line_id") for x in payload.get("inventory_facts", []) if x.get("business_line_id") and policy.management(x.get("business_line_id"))})


def _history(payload: dict, actuals: list[dict], aliases: dict[str, dict], policy: AccessPolicy, metric: str, scope_id: str, form: str, analysis_date: str | None) -> list[dict]:
    alias_by_date = {snap.get("exact_date"): alias for alias, snap in aliases.items()}
    points: list[tuple[str, str, dict]] = []
    if metric == "turnover_days":
        for fact in actuals:
            if fact.get("metric_id") != metric or fact.get("scope_id") != scope_id or fact.get("material_form", "ALL") != form:
                continue
            exact = fact.get("exact_date") or fact.get("period_key")
            if exact and (analysis_date is None or exact <= analysis_date):
                points.append((exact, fact.get("period_key", exact), {"value": _decimal(fact.get("value")), "coverage_state": _coverage(fact), "source_refs": _refs([fact])}))
    else:
        for snap in payload.get("snapshots", []):
            exact = snap.get("exact_date")
            if exact and (analysis_date is None or exact <= analysis_date):
                points.append((exact, snap.get("key", exact), _inventory_value(payload, snap.get("key"), policy, scope_id, form)))
    result = []
    for exact, key, value in sorted(points, key=lambda x: (x[0], x[1])):
        result.append({"period_key": key if metric == "point_inventory" else key, "label": exact, "exact_date": exact,
                       "snapshot_alias": alias_by_date.get(exact), "value": _str(value["value"]),
                       "coverage_state": value["coverage_state"], "source_refs": value["source_refs"]})
    return result


def _evidence(metric_id: str, entity: dict, unit: str, scope_id: str, material_form: str, analysis_period: str, baseline_period: str) -> dict:
    return {"metric_id": metric_id, "entity_id": entity["id"], "current": entity["value"], "baseline": entity["baseline"],
            "absolute_delta": entity["absolute_delta"], "relative_delta": entity["relative_delta"], "unit": unit,
            "scope_id": scope_id, "material_form": material_form, "current_period": analysis_period,
            "baseline_period": baseline_period, "source_refs": entity["source_refs"], "entity_label": entity["label"],
            "coverage_state": entity["coverage_state"], "current_share": entity.get("share"), "baseline_share": None,
            "share_delta": None, "amount_direction": None, "share_direction": None, "target_period": None,
            "target": None, "gap": None, "share_unit": "ratio"}


def _coverage_evidence(metric_id: str, entity: dict, unit: str, scope_id: str, material_form: str, analysis_period: str, baseline_period: str) -> dict:
    periods = []
    if entity.get("current_coverage_state") != "complete": periods.append("current")
    if entity.get("baseline_coverage_state") != "complete": periods.append("baseline")
    return {"metric_id": metric_id, "entity_id": entity["id"], "entity_label": entity["label"], "current": None, "baseline": None,
            "absolute_delta": None, "relative_delta": None, "current_share": None, "baseline_share": None, "share_delta": None,
            "amount_direction": None, "share_direction": None, "target_period": None, "target": None, "gap": None,
            "share_unit": "ratio", "coverage_state": entity["coverage_state"], "incomplete_periods": periods,
            "unit": unit, "scope_id": scope_id, "material_form": material_form, "current_period": analysis_period,
            "baseline_period": baseline_period, "source_refs": entity["source_refs"]}


def _direction(value: Decimal) -> str:
    return "up" if value > 0 else "down" if value < 0 else "flat"


def _summary_amount(value: Decimal) -> str:
    """Human-readable summary only; evidence keeps the unrounded Decimal."""
    return format(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), ",.2f")


def _summary_percent(value: Decimal) -> str:
    return format((value * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), ".2f")


def _coverage_conclusion(affected: list[str], evidence: list[dict]) -> dict | None:
    if not affected:
        return None
    return {"rule_id": "OVR_DATA_COVERAGE_INCOMPLETE_V1", "category": "data_quality", "title": "数据覆盖不完整，已抑制相关比较结论",
            "summary": "部分当前或基期事实不可完整比较。", "condition": {"operator": "REQUIRED_COVERAGE_COMPLETE", "affected_rule_ids": affected},
            "entities": [], "evidence": evidence, "drilldown": {"page": "management-analysis", "query": {}}}


def _conclusions(payload: dict, actuals: list[dict], policy: AccessPolicy, scope_id: str, form: str, analysis_period: str, baseline_period: str,
                 analysis_snap: dict | None, baseline_snap: dict | None, form_rows: list[dict], line_rows: list[dict], scope_inventory: dict, baseline_inventory: dict) -> dict:
    unit = payload.get("unit_policy", {}).get("detail_amount")
    affected: list[str] = []
    coverage_evidence: list[dict] = []
    form_complete = all(row["absolute_delta"] is not None for row in form_rows)
    if not form_complete:
        affected.append("OVR_FORM_MAX_POSITIVE_INVENTORY_DELTA_V1")
        coverage_evidence.extend(_coverage_evidence("point_inventory", row, unit, scope_id, row["id"], analysis_period, baseline_period) for row in form_rows if row["absolute_delta"] is None)
    line_complete = all(row["absolute_delta"] is not None for row in line_rows)
    if scope_id == "GROUP" and (len(line_rows) < 2 or not line_complete):
        affected.append("OVR_LINE_MAX_POSITIVE_INVENTORY_DELTA_V1")
        coverage_evidence.extend(_coverage_evidence("point_inventory", row, unit, scope_id, form, analysis_period, baseline_period) for row in line_rows if row["absolute_delta"] is None)
    over_coverage_complete = _complete(scope_inventory) and _complete(baseline_inventory)
    over_complete = over_coverage_complete and scope_inventory.get("value") not in (None, Decimal("0")) and baseline_inventory.get("value") not in (None, Decimal("0"))
    # A complete zero denominator makes the share undefined, not incomplete.
    # Rule 10 reports only missing/partial facts, never a valid zero state.
    if not over_coverage_complete:
        affected.append("OVR_OVER180_AMOUNT_SHARE_DIRECTION_V1")
    current_turnover = _turnover_value(actuals, analysis_period, scope_id, form)
    if not _complete(current_turnover):
        affected.append("OVR_TURNOVER_ABOVE_TARGET_V1")
        coverage_evidence.append({"metric_id": "turnover_days", "entity_id": scope_id, "entity_label": _label(payload, scope_id), "current": None, "baseline": None, "absolute_delta": None, "relative_delta": None, "current_share": None, "baseline_share": None, "share_delta": None, "amount_direction": None, "share_direction": None, "target_period": None, "target": None, "gap": None, "share_unit": "ratio", "coverage_state": current_turnover["coverage_state"], "incomplete_periods": ["current"], "unit": "天", "scope_id": scope_id, "material_form": form, "current_period": analysis_period, "baseline_period": baseline_period, "source_refs": current_turnover["source_refs"]})
    items: list[dict] = []
    coverage = _coverage_conclusion(sorted(set(affected)), coverage_evidence)
    if coverage:
        items.append(coverage)
    if form_complete:
        maximum = max(_decimal(row["absolute_delta"]) for row in form_rows)
        if maximum is not None and maximum > 0:
            winners = [row for row in form_rows if _decimal(row["absolute_delta"]) == maximum]
            names = "、".join(row["label"] for row in winners)
            tie = "并列为" if len(winners) > 1 else "为"
            items.append({"rule_id": "OVR_FORM_MAX_POSITIVE_INVENTORY_DELTA_V1", "category": "inventory_change", "title": f"{names}{tie}库存增量贡献最高形态",
                           "summary": f"上述形态均较基期增加 {_summary_amount(maximum)} {unit}。" if len(winners) > 1 else f"较基期增加 {_summary_amount(maximum)} {unit}。", "condition": {"operator": "MAX_POSITIVE_ABSOLUTE_DELTA_WITH_TIES", "current_period": analysis_period, "baseline_period": baseline_period, "required_coverage": "complete", "evaluation_material_form": "ALL"},
                          "entities": [{"id": row["id"], "label": row["label"]} for row in winners],
                          "evidence": [_evidence("point_inventory", row, unit, scope_id, row["id"], analysis_period, baseline_period) for row in winners],
                           "drilldown": None if len(winners) > 1 else {"page": "management-analysis", "query": {"material_form": winners[0]["id"]}}})
    if scope_id == "GROUP" and len(line_rows) >= 2 and line_complete:
        maximum = max(_decimal(row["absolute_delta"]) for row in line_rows)
        if maximum is not None and maximum > 0:
            winners = [row for row in line_rows if _decimal(row["absolute_delta"]) == maximum]
            names = "、".join(row["label"] for row in winners)
            tie = "并列为" if len(winners) > 1 else "为"
            items.append({"rule_id": "OVR_LINE_MAX_POSITIVE_INVENTORY_DELTA_V1", "category": "inventory_change", "title": f"{names}{tie}库存增量最高业务线",
                           "summary": f"上述业务线均较基期增加 {_summary_amount(maximum)} {unit}。" if len(winners) > 1 else f"较基期增加 {_summary_amount(maximum)} {unit}。", "condition": {"operator": "MAX_POSITIVE_ABSOLUTE_DELTA_WITH_TIES", "current_period": analysis_period, "baseline_period": baseline_period, "required_coverage": "complete", "material_form": form},
                          "entities": [{"id": row["id"], "label": row["label"]} for row in winners], "evidence": [_evidence("point_inventory", row, unit, scope_id, form, analysis_period, baseline_period) for row in winners],
                           "drilldown": None if len(winners) > 1 else {"page": "management-analysis", "query": {"business_line_id": winners[0]["id"], "material_form": form}}})
    if over_complete and analysis_snap and baseline_snap:
        current_over = _inventory_value(payload, analysis_snap["key"], policy, scope_id, form)
        baseline_over = _inventory_value(payload, baseline_snap["key"], policy, scope_id, form)
        current_over = {**current_over, "value": _amount([x for x in _inventory_rows(payload, analysis_snap["key"], policy, scope_id, form) if x.get("aging_bucket") == "D181_PLUS"])["value"]}
        baseline_over = {**baseline_over, "value": _amount([x for x in _inventory_rows(payload, baseline_snap["key"], policy, scope_id, form) if x.get("aging_bucket") == "D181_PLUS"])["value"]}
        amount_delta = _delta(current_over["value"], baseline_over["value"])
        current_share = current_over["value"] / scope_inventory["value"]
        baseline_share = baseline_over["value"] / baseline_inventory["value"]
        share_delta = current_share - baseline_share
        if amount_delta != 0 or share_delta != 0:
            words = {"up": "增加", "down": "减少", "flat": "持平"}
            amount_text = f">180 天金额由 {_summary_amount(baseline_over['value'])} 变为 {_summary_amount(current_over['value'])} {unit}（{words[_direction(amount_delta)]} {_summary_amount(abs(amount_delta))} {unit}）"
            share_text = f"占比由 {_summary_percent(baseline_share)}% 变为 {_summary_percent(current_share)}%（{words[_direction(share_delta)]} {_summary_percent(abs(share_delta))} 个百分点）"
            items.append({"rule_id": "OVR_OVER180_AMOUNT_SHARE_DIRECTION_V1", "category": "aging_direction", "title": ">180 天库存金额与占比变化", "summary": amount_text + "；" + share_text + "。" + ("占比下降，但 >180 天绝对金额仍增加，不能理解为绝对额改善。" if amount_delta > 0 and share_delta < 0 else ""),
                          "condition": {"operator": "OVER180_AMOUNT_AND_SHARE_DIRECTION", "current_period": analysis_period, "baseline_period": baseline_period, "required_coverage": "complete", "amount_delta": _str(amount_delta), "amount_direction": _direction(amount_delta), "share_delta": _str(share_delta), "share_direction": _direction(share_delta)},
                          "entities": [{"id": scope_id, "label": _label(payload, scope_id)}],
                           "evidence": [{"metric_id": "over_180_amount", "entity_id": scope_id, "entity_label": _label(payload, scope_id), "current": _str(current_over["value"]), "baseline": _str(baseline_over["value"]), "absolute_delta": _str(amount_delta), "relative_delta": _str(_relative(current_over["value"], baseline_over["value"])), "current_share": _str(current_share), "baseline_share": _str(baseline_share), "share_delta": _str(share_delta), "amount_direction": _direction(amount_delta), "share_direction": _direction(share_delta), "target_period": None, "target": None, "gap": None, "share_unit": "ratio", "coverage_state": "complete", "unit": unit, "scope_id": scope_id, "material_form": form, "current_period": analysis_period, "baseline_period": baseline_period, "source_refs": sorted(set(current_over["source_refs"]) | set(baseline_over["source_refs"]))}],
                          "drilldown": {"page": "management-analysis", "query": {"material_form": form}}})
    target = None
    current_fact = _metric_match(actuals, "turnover_days", analysis_period, scope_id, form)
    if current_fact and current_fact.get("reference_target_period_key"):
        target = _metric_match(payload.get("targets", []), "turnover_days", current_fact["reference_target_period_key"], scope_id, form)
    target_value = _decimal(target.get("value")) if target else None
    target_complete = target_value is not None and (not target or target.get("coverage_state") not in {"partial", "unavailable"})
    if _complete(current_turnover) and target_complete and current_turnover["value"] - target_value > 0:
        gap = current_turnover["value"] - target_value
        items.append({"rule_id": "OVR_TURNOVER_ABOVE_TARGET_V1", "category": "turnover_target", "title": "库存周转天数高于目标", "summary": f"当前周转天数高于目标 {_str(gap)} 天。", "condition": {"operator": "ACTUAL_MINUS_EXACT_TARGET_GT_ZERO", "current_period": analysis_period, "target_period": current_fact.get("reference_target_period_key"), "scope_id": scope_id, "material_form": form}, "entities": [{"id": scope_id, "label": _label(payload, scope_id)}], "evidence": [{"metric_id": "turnover_days", "entity_id": scope_id, "entity_label": _label(payload, scope_id), "current": _str(current_turnover["value"]), "baseline": None, "absolute_delta": None, "relative_delta": None, "current_share": None, "baseline_share": None, "share_delta": None, "amount_direction": None, "share_direction": None, "target": _str(target_value), "gap": _str(gap), "unit": "天", "share_unit": "ratio", "coverage_state": "complete", "scope_id": scope_id, "material_form": form, "current_period": analysis_period, "baseline_period": baseline_period, "target_period": current_fact.get("reference_target_period_key"), "source_refs": sorted(set(current_turnover["source_refs"]) | set(_refs([target])))}], "drilldown": {"page": "management-analysis", "query": {"material_form": form}}})
    items = items[:5]
    for rank, item in enumerate(items, start=1):
        item["rank"] = rank
    return {"ruleset_id": RULESET_ID, "max_items": 5, "items": items}


def enrich_overview(db: Any, version_id: str, scope_id: str, material_form: str, analysis_period: str, baseline_period: str, structure_metric: str, policy: AccessPolicy) -> dict:
    if structure_metric not in {"turnover_days", "point_inventory"}:
        raise ValueError("INVALID_STRUCTURE_METRIC")
    _, payload = _payload(db, version_id)
    aliases = _aliases(payload)
    snapshots_by_date = {x.get("exact_date"): x for x in payload.get("snapshots", []) if x.get("exact_date")}
    analysis_snap, baseline_snap = snapshots_by_date.get(analysis_period), snapshots_by_date.get(baseline_period)
    actuals = [x for x in payload.get("metric_facts", []) if x.get("observation_type") == "actual"]
    is_turnover = structure_metric == "turnover_days"
    get_value = (lambda period, scope, form: _turnover_value(actuals, period, scope, form)) if is_turnover else (lambda period, scope, form: _inventory_value(payload, snapshots_by_date.get(period, {}).get("key"), policy, scope, form))
    denominator = get_value(analysis_period, scope_id, "ALL") if not is_turnover else {"value": None, "coverage_state": "unavailable", "source_refs": []}
    current = get_value(analysis_period, scope_id, material_form); baseline = get_value(baseline_period, scope_id, material_form)
    scope_summary = _value_row(scope_id, _label(payload, scope_id), current, baseline, denominator, not is_turnover)
    forms = [_value_row(form, FORM_LABELS[form], get_value(analysis_period, scope_id, form), get_value(baseline_period, scope_id, form), denominator, not is_turnover) for form in ("ALL", *FORMS)]
    for row in forms:
        row["selected"] = row["id"] == material_form
    line_denominator = get_value(analysis_period, scope_id, material_form) if not is_turnover else denominator
    lines = []
    for line in _business_lines(payload, policy, scope_id):
        row = _value_row(line, _label(payload, line), get_value(analysis_period, line, material_form), get_value(baseline_period, line, material_form), line_denominator, not is_turnover)
        row["history"] = _history(payload, actuals, aliases, policy, structure_metric, line, material_form, analysis_period)
        lines.append(row)
    reconciliation = None
    if not is_turnover:
        config = payload.get("reconciliation", {}).get("point_inventory", {})
        divisor = _decimal(config.get("conversion_divisor"))
        overview = _metric_match(actuals, "point_inventory", analysis_period, scope_id, material_form)
        overview_value = _decimal(overview.get("value")) if overview else None
        if current["coverage_state"] != "complete": status, converted, gap = "partial", None, None
        elif divisor in (None, Decimal("0")) or current["value"] is None or overview_value is None: status, converted, gap = "unavailable", None, None
        else:
            converted = current["value"] / divisor; gap = converted - overview_value; status = "matched" if gap == 0 else "mismatch"
        reconciliation = {"detail_value": _str(current["value"]), "detail_unit": config.get("detail_amount_unit"), "conversion_factor": _str(Decimal("1") / divisor) if divisor not in (None, Decimal("0")) else None, "converted_value": _str(converted), "overview_fact_value": _str(overview_value), "overview_unit": config.get("metric_unit"), "gap": _str(gap), "status": status, "source_refs": sorted(set(current["source_refs"]) | set(_refs([overview] if overview else [])))}
    metric_info = next((x for x in payload.get("metric_catalog", []) if x.get("id") == structure_metric), {})
    structure = {"metric_id": structure_metric, "label": metric_info.get("label"), "unit": "天" if is_turnover else payload.get("unit_policy", {}).get("detail_amount"), "value_source": "PRECOMPUTED_METRIC_FACT" if is_turnover else "AUTHORIZED_INVENTORY_FACTS", "aggregation_rule": "PRECOMPUTED_NON_ADDITIVE" if is_turnover else "ADDITIVE_WITHIN_ONE_SNAPSHOT", "share_applicability": "not_applicable" if is_turnover else "available_when_complete", "analysis": {"period_key": analysis_period, "exact_date": analysis_period}, "baseline": {"period_key": baseline_period, "exact_date": baseline_period}, "scope_summary": scope_summary, "form_options": forms, "business_lines": lines, "reconciliation": reconciliation}
    # Rules always use leaf inventory and turnover, independent of the display metric.
    rules_forms = [_value_row(form, FORM_LABELS[form], _inventory_value(payload, analysis_snap.get("key") if analysis_snap else None, policy, scope_id, form), _inventory_value(payload, baseline_snap.get("key") if baseline_snap else None, policy, scope_id, form), {"value": None, "coverage_state": "unavailable", "source_refs": []}, False) for form in FORMS]
    rules_lines = [_value_row(line, _label(payload, line), _inventory_value(payload, analysis_snap.get("key") if analysis_snap else None, policy, line, material_form), _inventory_value(payload, baseline_snap.get("key") if baseline_snap else None, policy, line, material_form), {"value": None, "coverage_state": "unavailable", "source_refs": []}, False) for line in _business_lines(payload, policy, scope_id)]
    conclusions = _conclusions(payload, actuals, policy, scope_id, material_form, analysis_period, baseline_period, analysis_snap, baseline_snap, rules_forms, rules_lines, _inventory_value(payload, analysis_snap.get("key") if analysis_snap else None, policy, scope_id, material_form), _inventory_value(payload, baseline_snap.get("key") if baseline_snap else None, policy, scope_id, material_form))
    # The analysis page takes aliases rather than free-form dates.  Never let a
    # non-alias overview selection silently jump to its DEFAULT CURRENT state.
    alias_by_date = {snap.get("exact_date"): alias for alias, snap in aliases.items()}
    current_alias, base_alias = alias_by_date.get(analysis_period), alias_by_date.get(baseline_period)
    for item in conclusions["items"]:
        if item.get("drilldown") is None:
            continue
        if not current_alias or not base_alias:
            item["drilldown"] = None
            continue
        query = dict((item.get("drilldown") or {}).get("query") or {})
        query.setdefault("current_alias", current_alias)
        query.setdefault("baseline_alias", base_alias)
        query.setdefault("material_form", material_form)
        if scope_id != "GROUP":
            query.setdefault("business_line_id", scope_id)
        item["drilldown"] = {"page": "management-analysis", "query": query}
    return {"structure": structure, "conclusions": conclusions}
