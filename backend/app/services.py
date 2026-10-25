from __future__ import annotations
import csv, hashlib, io, json, uuid, math
from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from .policy import POLICY
from .models import DatasetSeries, DatasetVersion, ImportBatch, InventoryItem, InventorySnapshot, SourceFile
from .database_adapter import import_write_lock, write_lock

MAX_FILE=5*1024*1024; MAX_RECORDS=10000; MAX_SNAPSHOTS=32
def dec(v): return None if v is None else str(v if isinstance(v,Decimal) else Decimal(str(v)))
def json_safe(v):
    if isinstance(v,Decimal): return str(v)
    if isinstance(v,float): return str(Decimal(str(v)))
    if isinstance(v,dict): return {k:json_safe(x) for k,x in v.items()}
    if isinstance(v,list): return [json_safe(x) for x in v]
    return v
def meta(version: DatasetVersion): return {"version_id":str(version.id),"evidence_level":version.evidence_level,"limitations":version.limitations or []}
def public_source(sf: SourceFile): return {"id":str(sf.id),"filename":sf.filename,"sha256":sf.sha256,"evidence_level":sf.evidence_level,"metadata":sf.metadata_json,"limitations":sf.metadata_json.get("limitations",[])}
def version(db:Session, version_id:str, kind:str|None=None):
    v=db.get(DatasetVersion,uuid.UUID(version_id))
    if not v: raise KeyError("VERSION_NOT_FOUND")
    s=db.get(DatasetSeries,v.series_id)
    if kind and s.kind!=kind: raise ValueError("VERSION_KIND_MISMATCH")
    return v,s
def scope_ok(scope:str|None): return POLICY.legacy(scope)
def pdt_ok(pdt:str|None): return POLICY.pdt(pdt)
def legacy_payload(db, version_id):
    v,_=version(db,version_id,"legacy")
    return v,v.payload
def legacy_dashboard(db,version_id,scope=None):
    v,p=legacy_payload(db,version_id)
    if scope and not scope_ok(scope): return {"periods":p.get("periods",[]),"scopes":[],"metrics":p.get("metrics",[]),"rows":[],"checks":[],"reconciliations":[]},meta(v)
    rows=[x for x in p.get("trend",[]) if (not scope or x.get("scope")==scope) and scope_ok(x.get("scope"))]
    scopes=[x for x in p.get("scopes",[]) if scope_ok(x)]
    checks=p.get("checks",[]) if POLICY.global_evidence() else []
    rec=[x for x in p.get("reconciliations",[]) if scope_ok(x.get("scope"))]
    return {"periods":p.get("periods",[]),"scopes":scopes,"metrics":p.get("metrics",[]),"rows":json_safe(rows),"checks":checks,"reconciliations":json_safe(rec)},meta(v)
def legacy_aging(db,version_id):
    v,p=legacy_payload(db,version_id)
    reconciliations=p.get("reconciliations",[])
    records=[]
    for raw in p.get("aging",[]):
        if not scope_ok(raw.get("scope")): continue
        item=dict(raw); total_ref=(raw.get("sources") or {}).get("total")
        matching=[r for r in reconciliations if str(r.get("id","")).startswith("aging") and total_ref and total_ref in (r.get("sources") or [])]
        item["reconciliation_gap"]=dec(matching[0].get("gap")) if matching and matching[0].get("gap") is not None else None
        records.append(item)
    return {"records":json_safe(records)},meta(v)
def legacy_mwd(db,version_id):
    v,p=legacy_payload(db,version_id); m=p.get("mwd",{})
    return {"summary":json_safe([x for x in m.get("summary",[]) if scope_ok(x.get("scope"))]),"details":json_safe([x for x in m.get("details",[]) if scope_ok(x.get("scope"))]),"note":m.get("note")},meta(v)
def source_for_version(db,version_id):
    v,series=version(db,version_id)
    if series.kind == "management_demo":
        if not POLICY.management_group(): raise PermissionError("SOURCE_SCOPE_DENIED")
    elif not POLICY.global_evidence(): raise PermissionError("SOURCE_SCOPE_DENIED")
    sf=db.get(SourceFile,v.source_file_id) if v.source_file_id else None
    if not sf: raise KeyError("SOURCE_NOT_FOUND")
    return public_source(sf),meta(v)
def evidence_for_version(db,version_id,ref):
    v,series=version(db,version_id)
    if series.kind == "management_demo":
        if not POLICY.management_group(): raise PermissionError("SOURCE_SCOPE_DENIED")
        item=(v.payload.get("sources") or {}).get(ref)
        if not item: raise KeyError("EVIDENCE_NOT_FOUND")
        return {"ref":ref,**json_safe(item)},meta(v)
    if not POLICY.global_evidence(): raise PermissionError("SOURCE_SCOPE_DENIED")
    v,p=legacy_payload(db,version_id)
    item=(p.get("sources") or {}).get(ref)
    if not item: raise KeyError("EVIDENCE_NOT_FOUND")
    return {"ref":ref,**json_safe(item)},meta(v)
def query_items(db, version_id, snapshot_id, pdt=None,customer=None,project=None,material_category=None,search=None):
    v,_=version(db,version_id,"inventory_detail")
    snap=db.get(InventorySnapshot,uuid.UUID(snapshot_id))
    if not snap or snap.version_id!=v.id: raise ValueError("SNAPSHOT_VERSION_MISMATCH")
    q=select(InventoryItem).where(InventoryItem.snapshot_id==snap.id)
    if pdt: q=q.where(InventoryItem.pdt==pdt)
    if customer: q=q.where(InventoryItem.customer==customer)
    if project: q=q.where(InventoryItem.project==project)
    if material_category: q=q.where(InventoryItem.material_category==material_category)
    if search:
        needle=f"%{search}%";q=q.where(InventoryItem.material_code.ilike(needle)|InventoryItem.material_description.ilike(needle))
    if POLICY.actor.pdt_scopes:q=q.where(InventoryItem.pdt.in_(POLICY.actor.pdt_scopes))
    return v,snap,q
def snapshots(db,version_id):
    v,_=version(db,version_id,"inventory_detail")
    rows=db.scalars(select(InventorySnapshot).where(InventorySnapshot.version_id==v.id).order_by(InventorySnapshot.ordinal)).all()
    result=[]
    for s in rows:
        q=select(func.count()).select_from(InventoryItem).where(InventoryItem.snapshot_id==s.id)
        if POLICY.actor.pdt_scopes: q=q.where(InventoryItem.pdt.in_(POLICY.actor.pdt_scopes))
        result.append({"id":str(s.id),"label":s.label,"exact_date":s.exact_date.isoformat(),"ordinal":s.ordinal,"row_count":db.scalar(q)})
    return result,meta(v)
def inventory_items(db,version_id,snapshot_id,page,size,**filters):
    v,_,q=query_items(db,version_id,snapshot_id,**filters); total=db.scalar(select(func.count()).select_from(q.subquery())); rows=db.scalars(q.order_by(InventoryItem.record_key).offset((page-1)*size).limit(size)).all()
    cols=("id","record_key","material_code","material_description","pdt","customer","project","material_category","subinventory_code","quantity","unit_cost","total_cost_amount")
    return {"items":[{k:(str(getattr(x,k)) if k=="id" else dec(getattr(x,k)) if k in {"quantity","unit_cost","total_cost_amount"} else getattr(x,k)) for k in cols} for x in rows],"total":total,"page":page,"size":size},meta(v)
def explore(db,version_id,snapshot_id,baseline_id=None,group_by="material_category",**filters):
    allowed={"material_category","pdt","customer","project","material_code"}
    if group_by not in allowed: raise ValueError("INVALID_GROUP_BY")
    v,snap,q=query_items(db,version_id,snapshot_id,**filters); current=db.scalars(q).all()
    baseline=[]
    if baseline_id: _,_,bq=query_items(db,version_id,baseline_id,**filters);baseline=db.scalars(bq).all()
    def grouped(rows):
        d=defaultdict(lambda:Decimal("0"));unknown=0;unknown_keys=defaultdict(int);known=0;known_keys=defaultdict(int);row_count=0
        for r in rows:
            key=getattr(r,group_by) or "未分类"
            row_count+=1
            if r.total_cost_amount is None:
                unknown+=1;unknown_keys[key]+=1;d[key]+=Decimal("0")
            else:
                d[key]+=r.total_cost_amount;known+=1;known_keys[key]+=1
        return d,unknown,unknown_keys,known,known_keys,row_count
    cg,unknown,cunknown,cknown,cknown_keys,crows=grouped(current); bg,bunknown_total,bunknown,bknown,bknown_keys,brows=grouped(baseline); ct=sum(cg.values(),Decimal("0"));bt=sum(bg.values(),Decimal("0")) if baseline_id else None
    groups=[]
    for k in sorted(set(cg)|set(bg),key=lambda x:cg.get(x,Decimal("0")),reverse=True):
        current_unknown=bool(cunknown.get(k)) and not cknown_keys.get(k)
        baseline_unknown=bool(bunknown.get(k)) and not bknown_keys.get(k)
        current_value=None if current_unknown else dec(cg.get(k,Decimal("0")))
        baseline_value=(None if baseline_unknown else dec(bg.get(k,Decimal("0")))) if baseline_id else None
        groups.append({"key":k,"current":current_value,"baseline":baseline_value,"delta":dec(cg.get(k,Decimal("0"))-bg.get(k,Decimal("0"))) if baseline_id and current_value is not None and baseline_value is not None else None,"share":dec(cg.get(k,Decimal("0"))/ct) if current_value is not None and ct else None})
    trend=[]
    for s in db.scalars(select(InventorySnapshot).where(InventorySnapshot.version_id==v.id).order_by(InventorySnapshot.ordinal)):
        _,_,tq=query_items(db,version_id,str(s.id),**filters); trend_rows=list(db.scalars(tq)); known=[r.total_cost_amount for r in trend_rows if r.total_cost_amount is not None]; amount=sum(known,Decimal("0"));trend.append({"snapshot_id":str(s.id),"label":s.label,"total":dec(amount) if known else ("0" if not trend_rows else None)})
    filters_out={}
    for col in ("pdt","customer","project","material_category"):
        fq=select(getattr(InventoryItem,col)).join(InventorySnapshot).where(InventorySnapshot.version_id==v.id)
        if POLICY.actor.pdt_scopes: fq=fq.where(InventoryItem.pdt.in_(POLICY.actor.pdt_scopes))
        vals=db.scalars(fq.distinct()).all();filters_out[col]=sorted([x for x in vals if x])
    return {"current_total":dec(ct) if cknown else ("0" if not crows else None),"baseline_total":(dec(bt) if bknown else ("0" if not brows else None)) if baseline_id else None,"delta":dec(ct-bt) if baseline_id and cknown and bknown else None,"unit":"演示元","unknown_count":unknown,"baseline_unknown_count":bunknown_total if baseline_id else None,"groups":groups,"trend":trend,"filters":filters_out},meta(v)
def csv_export(data):
    output=io.StringIO(); writer=csv.DictWriter(output,fieldnames=["record_key","material_code","material_description","pdt","customer","project","material_category","subinventory_code","quantity","unit_cost","total_cost_amount"]);writer.writeheader()
    def safe(x):
        x="" if x is None else str(x)
        return "'"+x if x.startswith(("=","+","-","@")) else x
    for row in data["items"]: writer.writerow({k:safe(v) for k,v in row.items() if k!="id"})
    return "\ufeff"+output.getvalue()
def export_rows(db,version_id,snapshot_id,**filters):
    v,_,q=query_items(db,version_id,snapshot_id,**filters)
    rows=db.scalars(q.order_by(InventoryItem.record_key)).all(); cols=("record_key","material_code","material_description","pdt","customer","project","material_category","subinventory_code","quantity","unit_cost","total_cost_amount")
    return {"items":[{k:dec(getattr(x,k)) if k in {"quantity","unit_cost","total_cost_amount"} else getattr(x,k) for k in cols} for x in rows]},meta(v)
def template(): return {"schema_version":"1.0","domain":"inventory_detail","series":{"code":"synthetic-inventory","title":"合成库存明细"},"evidence_level":"SYNTHETIC_DEMO","version_label":"示例版本","snapshots":[{"key":"demo-2026-01-01","label":"2026-01-01","exact_date":"2026-01-01","ordinal":1}],"records":[{"snapshot_key":"demo-2026-01-01","record_key":"DEMO-001-01","material_code":"DEMO-M001","material_description":"演示物料001","pdt":"DEMO-PDT-A","customer":"DEMO-客户01","project":"DEMO-项目01","material_category":"原材料","subinventory_code":"DEMO-WH01","quantity":"100.00","unit_cost":"25.00","total_cost_amount":"2500.00"}]}
def validate_payload(payload):
    errors=[]
    if not isinstance(payload,dict):return ["文件顶层必须是对象"]
    unknown_top=set(payload)-{"schema_version","domain","series","evidence_level","version_label","snapshots","records"}
    if unknown_top: errors.append("存在未定义的顶层字段")
    if payload.get("schema_version")!="1.0":errors.append("仅支持schema_version 1.0")
    if payload.get("domain")!="inventory_detail":errors.append("domain必须为inventory_detail")
    if payload.get("evidence_level")!="SYNTHETIC_DEMO":errors.append("当前只允许SYNTHETIC_DEMO")
    series=payload.get("series")
    if not isinstance(series,dict) or not all(isinstance(series.get(k),str) and series[k].strip() for k in ("code","title")) or len(series.get("code", ""))>100 or len(series.get("title", ""))>200:errors.append("series必须含长度合规的code和title")
    if not isinstance(payload.get("version_label"),str) or not payload["version_label"].strip() or len(payload.get("version_label", ""))>200:errors.append("version_label不能为空且最长200字符")
    snaps=payload.get("snapshots");records=payload.get("records")
    if not isinstance(snaps,list) or not snaps or len(snaps)>MAX_SNAPSHOTS:errors.append("snapshots必须为1至32项")
    if not isinstance(records,list) or len(records)>MAX_RECORDS:errors.append("records最多10000项")
    keys=set()
    if isinstance(snaps,list):
        ordinals=set()
        for x in snaps:
            if not isinstance(x,dict):errors.append("snapshot必须是对象");continue
            if set(x)-{"key","label","exact_date","ordinal"}: errors.append("snapshot存在未定义字段")
            try: date.fromisoformat(x.get("exact_date",""))
            except (ValueError,TypeError):errors.append("snapshot exact_date必须是ISO日期")
            key=x.get("key"); ordinal=x.get("ordinal")
            if not isinstance(key,str) or not key or key in keys:errors.append("snapshot key缺失或重复")
            else: keys.add(key)
            if not isinstance(x.get("label"),str) or len(x.get("label", ""))>100 or type(ordinal) is not int or ordinal in ordinals: errors.append("snapshot缺少label或ordinal重复")
            else: ordinals.add(ordinal)
    record_keys=set()
    if isinstance(records,list):
        for x in records:
            if not isinstance(x,dict): errors.append("record必须是对象");continue
            if set(x)-{"snapshot_key","record_key","material_code","material_description","pdt","customer","project","material_category","subinventory_code","quantity","unit_cost","total_cost_amount"}: errors.append("record存在未定义字段")
            if not all(isinstance(x.get(k),str) and x[k] for k in ("snapshot_key","record_key","material_code","material_description")) or any(len(x.get(k, ""))>limit for k,limit in {"record_key":160,"material_code":120,"material_description":10000,"pdt":120,"customer":160,"project":160,"material_category":120,"subinventory_code":120}.items() if x.get(k) is not None): errors.append("record缺少必填字段或字段过长")
            if not isinstance(x.get("snapshot_key"),str) or x.get("snapshot_key") not in keys:errors.append("record引用了不存在的snapshot")
            rk=x.get("record_key"); snapshot_key=x.get("snapshot_key")
            if not isinstance(rk,str) or not rk or not isinstance(snapshot_key,str):errors.append("record_key缺失或在同一快照重复")
            else:
                compound=(snapshot_key,rk)
                if compound in record_keys:errors.append("record_key缺失或在同一快照重复")
                record_keys.add(compound)
            try:
                q=None if x.get("quantity") is None else Decimal(str(x.get("quantity")))
                u=None if x.get("unit_cost") is None else Decimal(str(x.get("unit_cost")))
                t=None if x.get("total_cost_amount") is None else Decimal(str(x.get("total_cost_amount")))
                nums=[n for n in (q,u,t) if n is not None]
                if any(n.is_nan() or n.is_infinite() or n.adjusted()>15 or n.as_tuple().exponent < -4 for n in nums) or (q is not None and q<0) or (u is not None and u<0) or (t is not None and t<0) or (q is not None and u is not None and t is not None and q*u!=t):errors.append("数量、单价、金额必须是NUMERIC(20,4)范围内非负值，金额=数量×单价")
            except (InvalidOperation,TypeError):errors.append("数量、单价、金额必须是有限数字")
    return list(dict.fromkeys(errors))
def preview(db,filename,content):
    if len(content)>MAX_FILE: raise OverflowError("文件超过5MiB")
    try:payload=json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError,json.JSONDecodeError): raise ValueError("文件不是UTF-8 JSON")
    errors=validate_payload(payload);sha=hashlib.sha256(content).hexdigest()
    row_count=len(payload.get("records")) if isinstance(payload,dict) and isinstance(payload.get("records"),list) else 0
    snapshot_count=len(payload.get("snapshots")) if isinstance(payload,dict) and isinstance(payload.get("snapshots"),list) else 0
    with write_lock(db):
        existing=db.scalar(select(DatasetVersion).join(SourceFile,DatasetVersion.source_file_id==SourceFile.id).where(SourceFile.sha256==sha))
        batch=ImportBatch(sha256=sha,filename=filename,payload=payload if not errors else {},validation={"errors":errors,"row_count":row_count,"snapshot_count":snapshot_count,"existing_version_id":str(existing.id) if existing else None},status="rejected" if errors else "preview")
        db.add(batch);db.commit();db.refresh(batch);return batch
def batch_view(batch):
    v=batch.validation;return {"id":str(batch.id),"status":batch.status,"sha256":batch.sha256,"row_count":v.get("row_count",0),"snapshot_count":v.get("snapshot_count",0),"errors":v.get("errors",[]),"warnings":v.get("warnings",[]),"sample":(batch.payload.get("records") or [])[:3],"existing_version_id":v.get("existing_version_id"),"committed_version_id":str(batch.committed_version_id) if batch.committed_version_id else None}
def commit_batch(db,batch,set_current=False):
    with import_write_lock(db,batch.id) as batch:
        return _commit_batch_locked(db,batch,set_current)
def _commit_batch_locked(db,batch,set_current=False):
    if batch.committed_version_id:return db.get(DatasetVersion,batch.committed_version_id),True
    if batch.status!="preview":raise RuntimeError("IMPORT_NOT_COMMITTABLE")
    existing=db.scalar(select(DatasetVersion).join(SourceFile,DatasetVersion.source_file_id==SourceFile.id).where(SourceFile.sha256==batch.sha256))
    if existing:batch.committed_version_id=existing.id;batch.status="committed";db.commit();return existing,True
    p=batch.payload;series_data=p["series"]; series=db.scalar(select(DatasetSeries).where(DatasetSeries.code==series_data["code"]))
    if not series: series=DatasetSeries(code=series_data["code"],title=series_data["title"],kind="inventory_detail");db.add(series);db.flush()
    sf=SourceFile(filename=batch.filename,sha256=batch.sha256,evidence_level="SYNTHETIC_DEMO",metadata_json={"adapter":"canonical_json_v1"});db.add(sf);db.flush()
    dv=DatasetVersion(series_id=series.id,label=p["version_label"],schema_version="1.0",evidence_level="SYNTHETIC_DEMO",source_file_id=sf.id,payload={},limitations=[]);db.add(dv);db.flush()
    snap_ids={}
    for s in p["snapshots"]:
        o=InventorySnapshot(version_id=dv.id,label=s["label"],exact_date=date.fromisoformat(s["exact_date"]),ordinal=s["ordinal"]);db.add(o);db.flush();snap_ids[s["key"]]=o.id
    for r in p["records"]:
        db.add(InventoryItem(snapshot_id=snap_ids[r["snapshot_key"]],record_key=r["record_key"],material_code=r["material_code"],material_description=r["material_description"],pdt=r.get("pdt"),customer=r.get("customer"),project=r.get("project"),material_category=r.get("material_category"),subinventory_code=r.get("subinventory_code"),quantity=Decimal(r["quantity"]) if r.get("quantity") is not None else None,unit_cost=Decimal(r["unit_cost"]) if r.get("unit_cost") is not None else None,total_cost_amount=Decimal(r["total_cost_amount"]) if r.get("total_cost_amount") is not None else None))
    if set_current or series.current_version_id is None:series.current_version_id=dv.id
    batch.committed_version_id=dv.id;batch.status="committed";db.commit();return dv,False
