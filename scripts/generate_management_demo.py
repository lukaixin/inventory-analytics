"""Deterministically generate the V6 local management demonstration payload."""
from __future__ import annotations
import argparse, hashlib, json
from datetime import date
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "management-demo.json"
MANIFEST = ROOT / "data" / "management-demo-manifest.json"
REF = "SRC-SYNTHETIC-MANAGEMENT-GENERATOR-V1"
DIV = Decimal("10000")
LINES = (("DEMO-BL-NETWORK", "演示业务线·网络"), ("DEMO-BL-ICE", "演示业务线·冰河"),
         ("DEMO-BL-ATHENA", "演示业务线·雅典娜"), ("DEMO-BL-STANDARD", "演示业务线·标品"),
         ("DEMO-BL-HOLLYWOOD", "演示业务线·好莱坞"), ("DEMO-BL-DOHKO", "演示业务线·童虎"))
FORMS = (("raw", "原材料"), ("semi_finished", "半成品"), ("finished", "成品"))
SNAPSHOTS = (("demo-2025-12-31", "2025-12-31", "年初 2025-12-31", "YEAR_START"),
 ("demo-2026-01-31", "2026-01-31", "1月末 2026-01-31", "HISTORY"),
 ("demo-2026-02-28", "2026-02-28", "2月末 2026-02-28", "HISTORY"),
 ("demo-2026-03-31", "2026-03-31", "3月末 2026-03-31", "HISTORY"),
 ("demo-2026-04-30", "2026-04-30", "4月末 2026-04-30", "HISTORY"),
 ("demo-2026-05-31", "2026-05-31", "年中 2026-05-31", "MID_YEAR"),
 ("demo-2026-06-30", "2026-06-30", "6月末 2026-06-30", "HISTORY"),
 ("demo-2026-07-31", "2026-07-31", "7月末 2026-07-31", "HISTORY"),
 ("demo-2026-08-31", "2026-08-31", "8月末 2026-08-31", "HISTORY"),
 ("demo-2026-09-30", "2026-09-30", "月初锚点 2026-09-30", "MONTH_START"),
 ("demo-2026-10-22", "2026-10-22", "当前 2026-10-22", "CURRENT"))

def s(v, q="0.01"): return str(Decimal(v).quantize(Decimal(q)))

def inventory(snapshots):
    rows=[]
    buckets=("D0_7","D8_14","D15_30","D31_60","D61_90","D91_180","D181_PLUS","UNKNOWN")
    for so, snap in enumerate(snapshots, 1):
      for li,(bid,bname) in enumerate(LINES,1):
       for pi in (1,2):
        for si in (1,2):
         for fi,(form,flabel) in enumerate(FORMS,1):
          missing=snap["key"]=="demo-2026-05-31" and (li,pi,si,form)==(2,1,2,"raw")
          amount=Decimal(310+li*37+pi*23+si*11+fi*29+so*13)
          if snap["key"]=="demo-2026-09-30" and (li,pi,si,form)==(6,2,2,"semi_finished"): amount=Decimal(0)
          aging=buckets[(li+pi+si+fi+so)%8]
          if snap["key"]=="demo-2026-10-22" and (li,pi,si,form)==(1,1,1,"raw"): aging="UNKNOWN"
          unit="件" if (li+fi)%3 else "箱"
          rows.append({"snapshot_key":snap["key"],"record_key":f"{snap['key']}-{li:02d}-{pi}-{si}-{fi}",
           "business_line_id":bid,"business_line_name":bname,"project_id":f"{bid}-P{pi}","project_name":f"{bname}·项目{pi}",
           "material_subclass_id":f"{bid}-P{pi}-S{si}","material_subclass_name":f"演示物料小类{si}",
           "material_code":f"DEMO-M{li:02d}{pi}{si}{fi}","material_description":f"{flabel}·演示物料{li:02d}{pi}{si}",
           "material_form":form,"aging_bucket":aging,"inventory_amount":None if missing else s(amount),
           "quantity":s(40+li*5+pi*3+si+fi,"0.001"),"quantity_unit":unit,"amount_known":not missing,
           "quantity_additive":unit=="件" and not(pi==2 and form=="semi_finished"),"source_ref":REF})
    return rows

def subset(rows,key,scope,form):
 return [r for r in rows if r["snapshot_key"]==key and (scope=="GROUP" or r["business_line_id"]==scope) and (form=="ALL" or r["material_form"]==form)]

def metrics(snapshots, rows):
 out=[]; scopes=[("GROUP",0)]+[(x[0],i) for i,x in enumerate(LINES,1)]; forms=[("ALL",0)]+[(x[0],i) for i,x in enumerate(FORMS,1)]
 defs=(("turnover_days","天","0.1"),("average_inventory","演示亿元","0.0001"),("point_inventory","演示亿元","0.0001"),("shipment_cost","演示亿元","0.0001"))
 for snap in snapshots:
  for scope,xi in scopes:
   for form,fi in forms:
    part=subset(rows,snap["key"],scope,form); partial=any(not r["amount_known"] for r in part)
    for mid,unit,q in defs:
     if mid=="point_inventory": value=sum((Decimal(r["inventory_amount"]) for r in part if r["amount_known"]),Decimal())/DIV
     else:
      base={"turnover_days":Decimal("32.4"),"average_inventory":Decimal("1.82"),"shipment_cost":Decimal("0.76")}[mid]
      step={"turnover_days":Decimal("-.46"),"average_inventory":Decimal(".031"),"shipment_cost":Decimal(".017")}[mid]
      value=base+(snap["ordinal"]-1)*step+Decimal(xi)*Decimal(".11")+Decimal(fi)*Decimal(".07")
     now=snap["role"]=="CURRENT"; forecast_ref="2026-10" if mid=="shipment_cost" else "2026-Q4"
     out.append({"metric_id":mid,"period_key":snap["exact_date"],"period_label":snap["label"],"period_order":snap["ordinal"],"period_type":"snapshot","value":s(value,q),"unit":unit,"observation_type":"actual","scope_id":scope,"material_form":form,"reference_target_period_key":"2026-Q4" if now else None,"reference_forecast_period_key":forecast_ref if now else None,"source_ref":REF,"coverage_state":"partial" if partial else "complete"})
 return out

def targets():
 values={"turnover_days":("天",("30.2","29.5"),("31.4","30.8","30.1","30.8")),"average_inventory":("演示亿元",("2.0400","2.1500"),("2.0900","2.1800","2.2700","2.2700")),"point_inventory":("演示亿元",("2.1800","2.3000"),("2.2400","2.3300","2.4200","2.4200")),"shipment_cost":("演示亿元",("0.9000","0.9800"),("0.9400","0.9900","1.0300","1.0300"))}; ts=[]; fs=[]
 for mid,(unit,(q3,q4),(oct_,nov,dec,q4f)) in values.items():
  for key,label,order,value in (("2026-Q3","2026-Q3",12,q3),("2026-Q4","2026-Q4",16,q4)):
   ts.append({"metric_id":mid,"period_key":key,"period_label":label,"period_order":order,"period_type":"quarter","scope_id":"GROUP","material_form":"ALL","value":value,"unit":unit,"target_kind":"quarterly","source_ref":REF})
  for key,label,exact,order,value in (("2026-10","2026-10", "2026-10-31",12,oct_),("2026-11","2026-11","2026-11-30",13,nov),("2026-12","2026-12","2026-12-31",14,dec),("2026-Q4","2026-Q4",None,16,q4f)):
   fs.append({"metric_id":mid,"period_key":key,"period_label":label,"period_order":order,"period_type":"month" if exact else "quarter","exact_date":exact,"scope_id":"GROUP","material_form":"ALL","value":value,"unit":unit,"forecast_as_of":"2026-10-22","forecast_method":"supplied_demo","source_ref":REF})
 ts.append({"metric_id":"point_inventory","period_key":"2026-Q4","period_label":"2026-Q4","period_order":16,"period_type":"quarter","scope_id":"DEMO-BL-NETWORK","material_form":"ALL","value":"0.4100","unit":"演示亿元","target_kind":"quarterly","source_ref":REF})
 return ts,fs

def payload():
 snaps=[{"key":k,"exact_date":d,"label":l,"ordinal":i,"role":r} for i,(k,d,l,r) in enumerate(SNAPSHOTS,1)]
 rows=inventory(snaps); ts,fs=targets()
 return {"schema_version":"management_demo_v1","domain":"inventory_management","evidence_level":"SYNTHETIC_MANAGEMENT_DEMO","series":{"code":"management-demo-v6","title":"库存管理合成演示"},"version_label":"V6重构合成管理演示（确定性）","data_as_of":"2026-10-22","unit_policy":{"currency":"DEMO_CURRENCY","inventory_amount":"演示亿元","detail_amount":"演示万元"},"reconciliation":{"point_inventory":{"detail_amount_unit":"演示万元","metric_unit":"演示亿元","conversion_divisor":"10000"}},"snapshot_manifest":{"YEAR_START":"demo-2025-12-31","MID_YEAR":"demo-2026-05-31","MONTH_START":"demo-2026-09-30","CURRENT":"demo-2026-10-22"},"snapshots":snaps,"metric_catalog":[{"id":"turnover_days","label":"库存周转","unit":"天","aggregation_rule":"PRECOMPUTED_NON_ADDITIVE"},{"id":"average_inventory","label":"平均库存","unit":"演示亿元","aggregation_rule":"PRECOMPUTED_NON_ADDITIVE"},{"id":"point_inventory","label":"时点库存","unit":"演示亿元","aggregation_rule":"PRECOMPUTED_RECONCILABLE"},{"id":"shipment_cost","label":"发货成本","unit":"演示亿元","aggregation_rule":"PRECOMPUTED_NON_ADDITIVE"}],"metric_facts":metrics(snaps,rows),"targets":ts,"forecasts":fs,"inventory_facts":rows,"risk_policies":[{"material_form":"raw","threshold_days":None,"comparison":None,"classification":"RULE_PENDING","label":"原材料规则待确认"},{"material_form":"semi_finished","threshold_days":None,"comparison":None,"classification":"RULE_PENDING","label":"半成品规则待确认"},{"material_form":"finished","threshold_days":60,"comparison":"GT","classification":"DEMO_RULE_CONFIG","label":"成品 >60天（演示规则）"}],"sources":{REF:{"type":"deterministic_synthetic_generator","generator":"scripts/generate_management_demo.py","purpose":"local V6 reconstruction functional verification only","not_business_source":True}},"limitations":["全部数值为确定性合成演示，不代表真实 V6、ERP 或经营数据。","周转、平均库存和发货成本为预计算演示事实，不可由明细重算。","2026-05-31 有一条金额未知事实，相关人口覆盖状态为 partial。","原材料和半成品风险阈值未知；仅成品配置 >60 天演示规则。"]}

def check(p):
 assert p["schema_version"]=="management_demo_v1" and p["snapshot_manifest"]=={"YEAR_START":"demo-2025-12-31","MID_YEAR":"demo-2026-05-31","MONTH_START":"demo-2026-09-30","CURRENT":"demo-2026-10-22"}
 snaps={x["key"]:x for x in p["snapshots"]}; assert all(date.fromisoformat(x["exact_date"]) for x in snaps.values())
 rows=p["inventory_facts"]; assert len(rows)==len({(x["snapshot_key"],x["record_key"]) for x in rows}) and all(x["snapshot_key"] in snaps for x in rows)
 assert all((x["inventory_amount"] is not None)==x["amount_known"] for x in rows) and all(Decimal(x["inventory_amount"])>=0 for x in rows if x["amount_known"])
 assert any(x["inventory_amount"]=="0.00" for x in rows) and any(not x["amount_known"] for x in rows) and any(x["aging_bucket"]=="UNKNOWN" for x in rows)
 cur=[x for x in rows if x["snapshot_key"]=="demo-2026-10-22"]; assert all(x["amount_known"] for x in cur)
 fact=next(x for x in p["metric_facts"] if (x["metric_id"],x["period_key"],x["scope_id"],x["material_form"])==("point_inventory","2026-10-22","GROUP","ALL")); assert Decimal(fact["value"])==sum((Decimal(x["inventory_amount"]) for x in cur),Decimal())/DIV and fact["coverage_state"]=="complete"
 assert len({(x["metric_id"],x["period_key"],x["scope_id"],x["material_form"]) for x in p["metric_facts"]})==len(p["metric_facts"])
 assert {(x["metric_id"],x["period_key"]) for x in p["targets"] if x["scope_id"]=="GROUP"} >= {(mid,period) for mid in ("turnover_days","average_inventory","point_inventory","shipment_cost") for period in ("2026-Q3","2026-Q4")}
 assert {(x["metric_id"],x["period_key"]) for x in p["forecasts"]} >= {(mid,period) for mid in ("turnover_days","average_inventory","point_inventory","shipment_cost") for period in ("2026-10","2026-11","2026-12","2026-Q4")}
 assert next(x for x in p["metric_facts"] if x["metric_id"]=="shipment_cost" and x["period_key"]=="2026-10-22" and x["scope_id"]=="GROUP" and x["material_form"]=="ALL")["reference_forecast_period_key"]=="2026-10"
 assert all(x["threshold_days"] is None for x in p["risk_policies"] if x["material_form"]!="finished")
 return {"snapshot_count":len(snaps),"inventory_fact_count":len(rows),"metric_fact_count":len(p["metric_facts"]),"target_count":len(p["targets"]),"forecast_count":len(p["forecasts"]),"current_point_inventory":fact["value"],"current_unknown_amount_count":0,"partial_snapshot":"demo-2026-05-31"}

def dump(x): return (json.dumps(x,ensure_ascii=False,indent=2)+"\n").encode()
def main():
 ap=argparse.ArgumentParser(); ap.add_argument("--check",action="store_true"); a=ap.parse_args()
 if a.check:
  p=json.loads(DATA.read_text(encoding="utf8")); info=check(p); m=json.loads(MANIFEST.read_text(encoding="utf8")); digest=hashlib.sha256(DATA.read_bytes()).hexdigest(); assert m["payload_sha256"]==digest; print(json.dumps({"status":"passed","sha256":digest,"counts":info},ensure_ascii=False)); return
 p=payload(); info=check(p); raw=dump(p); digest=hashlib.sha256(raw).hexdigest(); m={"generator":"scripts/generate_management_demo.py","schema_version":"management_demo_manifest_v1","evidence_level":"SYNTHETIC_MANAGEMENT_DEMO","payload_filename":DATA.name,"payload_sha256":digest,"deterministic":True,"snapshot_manifest":p["snapshot_manifest"],"counts":info,"validation":{"status":"passed","checks":["alias dates","unique fact keys","null versus zero","mixed quantity units","current point inventory reconciliation","target and forecast match keys","risk policy boundary"]},"limitations":p["limitations"]}; DATA.write_bytes(raw); MANIFEST.write_bytes(dump(m)); print(json.dumps({"status":"generated","sha256":digest,"counts":info},ensure_ascii=False))
if __name__=="__main__": main()
